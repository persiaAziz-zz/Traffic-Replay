#!/usr/bin/python
import sys
import json
import socket
import requests
import os
import threading
import time
import argparse
import subprocess
import shlex
from collections import deque

from progress.bar import Bar
import sessionvalidation.sessionvalidation as sv
import lib.result as result


# Note: this function can't handle multi-line (ie wrapped line) headers
# Hopefully this isn't an issue because multi-line headers are deprecated now
def header_to_dict(header):
    ''' Convert a HTTP header in string format to a python dictionary
    Returns a dictionary of header values
    '''
    header = header.split('\r\n')
    header = [x for x in header if (x != u'')]
    headers = {}
    for line in header:
        if 'GET' in line:     # ignore initial request line
            continue

        split_here = line.find(":")
        headers[line[:split_here]] = line[(split_here + 1):].strip()

    return headers


def extract_txn_req_method(headers):
    ''' Extracts the HTTP request method from the header in a string format '''
    line = (headers.split('\r\n'))[0]
    return (line.split(' '))[0]


def extract_GET_path(headers):
    ''' Extracts the HTTP request URL from the header in a string format '''
    line = (headers.split('\r\n'))[0]
    return (line.split(' '))[1]


def extract_host(headers):
    ''' Returns the host header from the given headers '''
    lines = headers.split('\r\n')
    for line in lines:
        if 'Host:' in line:
            return line.split(' ')[1]
    return "notfound"


def extract_http_version(headers):
    ''' Extracts and returns the HTTP version '''
    line = (headers.split('\r\n'))[0]
    return (line.split(' '))[2]


def parse_replay_logs(fname):
    ''' Parses & returns the given JSON file into default python JSON object '''
    with open(fname) as f:
        decoded_logs = json.load(f)
        return decoded_logs


def check_for_ats(hostname, port):
    ''' Checks to see if ATS is running on `hostname` and `port`
    If not running, this function will terminate the script
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((hostname, port))
    if result != 0:
        # hostname:port is not being listened to
        print('==========')
        print('Error: Apache Traffic Server is not running on {0}:{1}'.format(hostname, port))
        print('Aborting')
        print('==========')
        sys.exit()


def txn_replay(session_filename, txn, proxy, result_queue, request_session):
    """ Replays a single transaction

    :param request_session: has to be a valid requests session"""
    req = txn.getRequest()
    resp = txn.getResponse()

    # Construct HTTP request & fire it off
    txn_req_headers = req.getHeaders()
    txn_req_headers_dict = header_to_dict(txn_req_headers)
    txn_req_headers_dict['Content-MD5'] = txn._uuid  # used as unique identifier

    try:
        response = request_session.request(extract_txn_req_method(txn_req_headers),
                                    'http://' + extract_host(txn_req_headers) + extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict,
                                    #data=req.getBody(),
                                    proxies=proxy,
                                    timeout=2.0,
                                    stream=True,
                                    allow_redirects=False)  # so 302 responses doesn't spin in circles

        expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
        expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
        r = result.Result(session_filename, expected_output[0], response.status_code)
        result_queue.append(r)

    except UnicodeEncodeError as e:
        # these unicode errors are due to the interaction between Requests and our wiretrace data. 
        # TODO fix
        #print("UnicodeEncodeError exception thrown: someone else please fix this")
        pass

    except requests.exceptions.ContentDecodingError as e:
        print("ContentDecodingError exception thrown: probably has to do with how ATS wiretracing encodes body data. Skipping this transaction")


def client_replay(session, proxy, timing_control, result_queue):
    ''' Replay all transactions in session 
    
    This entire session will be replayed in one requests.Session (so one socket / TCP connection)'''
    if timing_control:
        time.sleep(float(session._timestamp))  # allow other threads to run

    with requests.Session() as request_session:
        for txn in session.getTransactionIter():
            try:
               txn_replay(session._filename, txn, proxy, result_queue, request_session)
            except:
               pass


def parent_thread(sessions, proxy, timing_control, result_queue):
    """ Sleeps and then spawns off a thread with a set number of ATS sessions to replay 
    
    XXX: this probably doesn't work right now. Fix as needed (shouldn't be difficult at all)"""
    if len(sessions) == 0:
        return

    if timing_control:
        # We have to re-subtract the earliest time stamps from all the sessions this parent thread is in charge
        # of because we don't want to double wait
        earliest_session_time = float(sessions[0]._timestamp)
        for session in sessions:
            session._timestamp = str(float(session._timestamp) - earliest_session_time)
        time.sleep(earliest_session_time)

    # Create & run a thread for each assigned session
    threads = list()
    for session in sessions:
        t = threading.Thread(target=client_replay, args=(session, proxy, timing_control, result_queue))
        t.daemon = True
        t.start()
        threads.append(t)
    for thread in threads:
        thread.join()

def worker_thread(sessions, proxy, timing_control, result_queue):
    if len(sessions) == 0:
        return
    # Create & run a thread for each assigned session
    for session in sessions:
        client_replay(session, proxy, timing_control, result_queue)
    print("processed:\t", len(sessions))

def main(path, hostname, port, num_parent_threads, timing_control, verbose):
    
    check_for_ats(hostname, port)
    proxy = {"http": "http://{0}:{1}".format(hostname, port)}
    num_fail, num_pass = 0, 0
    result_queue = deque()
    s = sv.SessionValidator(path)
    sessions = s.getSessionList()
    progress_bar = Bar("Replaying sessions", max=len(sessions))
    print("Dropped {0} sessions for being malformed".format(len(s.getBadSessionList())))

    sessions.sort(key=lambda x: float(x._timestamp)) # sort by session start time
    replays_start_time = time.time()  # Used for diagnostics

    # The timing_control cases are separated as opposed to just not subtracting the earliest start time from
    # each session because there's some race condition that's _probably_ the requests library's
    # fault when we use heirarchical threads
    if timing_control:
        # Get the time for the earliest session in replay logs
        #
        # Then, subtract that time from all session start times, so that each thread knows exactly how long to wait
        # before starting a session with ATS (ie compute a delta)
        earliest_session_time = float(sessions._timestamp)
        latest_session_time = float(sessions[-1]._timestamp)
        for session in sessions:
            session._timestamp = str(float(session._timestamp - earliest_session_time))

        # Segment session list into `num_parent_threads` lists - one list for each parent thread
        replay_data_parent_lists = [sessions[x:x + num_parent_threads] for x in range(0, len(sessions), num_parent_threads)]

        threads = list()
        print ("threads =",replay_data_parent_lists)
        for child_list in replay_data_parent_lists:
            t = threading.Thread(target=parent_thread, args=(child_list, proxy, timing_control, result_queue))
            t.daemon = True
            t.start()
            threads.append(t)
        for thread in threads:
            thread.join()

    elif num_parent_threads:
        print("muli-threaded")
        threads = list()
        chunksize = int((len(sessions) + num_parent_threads - 1)/ num_parent_threads)
        replay_data_parent_lists = [sessions[x:x + chunksize] for x in range(0, len(sessions), chunksize)]
        #print ("replay.lists.size:" + str(len(replay_data_parent_lists)))
        ith = 0
        for child_list in replay_data_parent_lists:
            t = threading.Thread(target=worker_thread, args=(child_list, proxy, timing_control, result_queue))
            t.daemon = True
            t.start()
            #print("thread start:" + str(ith))
            ith = ith+1
            threads.append(t)
        for thread in threads:
            thread.join()
    else:
        print("single threaded")
        
        for session in sessions:
            client_replay(session, proxy, timing_control, result_queue)
            progress_bar.next()
            
        progress_bar.finish()

    # print out our results
    for result in result_queue:
        if result.getResultBool():
            num_pass += 1
        else:
            print("{0}\t expected:{1} => received{2}".format(result._test_name, 
                                                             result._expected_response, 
                                                             result._received_response))
            num_fail += 1

        if verbose:
            print("------------------------------------------------")
            print('   Processed txn in: {0}:'.format(result.getTestName()))
            print('\t\t ==> {0}'.format(
                result.getResultString(colorize=True)))


    print('=====================================')
    print('All replays run; all threads joined')
    print('{0} transactions passed'.format(num_pass))
    print('{0} failures'.format(num_fail))
    print('Elapsed wall time: {0}s'.format(time.time() - replays_start_time))
    if timing_control:
        print('Expected wall time (with timing control on): {0}s'.format(
            latest_session_time - earliest_session_time))
    print('=====================================')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname", help="hostname ATS is running under")
    parser.add_argument("port", type=int, help="port ATS is listening on")
    parser.add_argument("log_dir", help="directory of JSON replay files")
    parser.add_argument("--timing", "-t", action="store_true",
                        help="use timing controls for session replay")
    parser.add_argument("--threads", "-n", type=int, help="number of parent threads to help manage session threads; \
                                                          this DOES NOT specify how many threads total will be spawned by this script")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # Let 'er loose
    main(args.log_dir, args.hostname, int(args.port), args.threads, args.timing, args.verbose)
