import gevent
import socket
import requests
import os
#import threading
import sys
from multiprocessing import current_process
import sessionvalidation.sessionvalidation as sv
import lib.result as result
import extractHeader
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
        response = request_session.request(extractHeader.extract_txn_req_method(txn_req_headers),
                                    'http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict,
                                    #data=req.getBody(),
                                    proxies=proxy,
                                    timeout=2.0,
                                    stream=True,
                                    allow_redirects=False)  # so 302 responses doesn't spin in circles

        expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
        expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
        r = result.Result(session_filename, expected_output[0], response.status_code)
        print(r.getResultString(colorize=True))
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

def client_replay(input, proxy, result_queue):
    ''' Replay all transactions in session 
    
    This entire session will be replayed in one requests.Session (so one socket / TCP connection)'''
    #if timing_control:
    #    time.sleep(float(session._timestamp))  # allow other threads to run
    for session in iter(input.get, 'STOP'): 
        with requests.Session() as request_session:
            for txn in session.getTransactionIter():
                try:
                   txn_replay(session._filename, txn, proxy, result_queue, request_session)
                except:
                   e=sys.exc_info()
                   print("ERROR in replaying: ",e,txn.getRequest().getHeaders())
               
