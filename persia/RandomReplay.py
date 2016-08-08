import gevent
import socket
import requests
import os
from threading import Thread
import sys
from multiprocessing import current_process
import sessionvalidation.sessionvalidation as sv
import lib.result as result
import extractHeader

bSTOP = False
def handleResponse(response,*args, **kwargs):
    print(response.status_code)
    #resp=args[0]
    #expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
    #expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
    #r = result.Result(session_filename, expected_output[0], response.status_code)
    #print(r.getResultString(colorize=True))

def txn_replay(session_filename, txn, proxy, result_queue, request_session):
    """ Replays a single transaction

    :param request_session: has to be a valid requests session"""
    req = txn.getRequest()
    resp = txn.getResponse()

    # Construct HTTP request & fire it off
    txn_req_headers = req.getHeaders()
    txn_req_headers_dict = extractHeader.header_to_dict(txn_req_headers)
    txn_req_headers_dict['Content-MD5'] = txn._uuid  # used as unique identifier
    #print("Replaying session")
    try:
        request_session.request(extractHeader.extract_txn_req_method(txn_req_headers),
                                    'http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict)
                                    
                                    #data=req.getBody(),
                                    #proxies=proxy,
                                    #timeout=2.0,
                                    #stream=True)
                                    #allow_redirects=False)  # so 302 responses doesn't spin in circles
                                    #, hooks=dict(response=handleResponse))
        #expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
        #expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
        #r = result.Result(session_filename, expected_output[0], response.status_code)
        #print(r.getResultString(colorize=True))
        #result_queue.put(r)
        #print("response", response.status_code)
    except UnicodeEncodeError as e:
        # these unicode errors are due to the interaction between Requests and our wiretrace data. 
        # TODO fix
        print("UnicodeEncodeError exception")

    except requests.exceptions.ContentDecodingError as e:
        print("ContentDecodingError exception thrown: probably has to do with how ATS wiretracing encodes body data. Skipping this transaction")
    except:
        e=sys.exc_info()
        print("ERROR in requests: ",e,txn.getRequest().getHeaders())

def session_replay(input, proxy, result_queue):
    global bSTOP
    ''' Replay all transactions in session 
    
    This entire session will be replayed in one requests.Session (so one socket / TCP connection)'''
    #if timing_control:
    #    time.sleep(float(session._timestamp))  # allow other threads to run
    while bSTOP == False:
        for session in iter(input.get, 'STOP'):
            #print(bSTOP)
            if session == 'STOP':
                print("stopping now")
                bSTOP = True
                break
            with requests.Session() as request_session:
                request_session.proxies = proxy
                for txn in session.getTransactionIter():
                    try:
                        txn_replay(session._filename, txn, proxy, result_queue, request_session)
                    except:
                        e=sys.exc_info()
                        print("ERROR in replaying: ",e,txn.getRequest().getHeaders())
        bSTOP = True
        print("stopping now")
        input.put('STOP')
        break
                  
def client_replay(input, proxy, result_queue, nThread):
    Threads = []
    for i in range(nThread):
        t = Thread(target=session_replay, args=[input, proxy, result_queue])
        t.start()
        Threads.append(t)

    for t1 in Threads:
        t1.join()
