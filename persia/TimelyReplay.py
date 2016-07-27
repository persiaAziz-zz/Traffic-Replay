#!/usr/bin/python
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
import grequests as gRequests
Counter=0
def fastReplay(input, proxy, result_queue): 
    for session in iter(input.get, 'STOP'): 
        fast_txn_replay(session._filename, session, proxy, result_queue)
    
def exception_handler(request, exception):
    global Counter
    Counter = Counter+1
    print ("Request failed {0}=>{1} : {2}".format(current_process().name,Counter,exception))
  
def timed_session_replay(session_filename, session, proxy, result_queue):
    requests = []
    pool = gRequests.Pool(10)
    for txn in session.getTransactionIter():   
   
        req = txn.getRequest()
        resp = txn.getResponse()

        # Construct HTTP request & fire it off
        txn_req_headers = req.getHeaders()
        txn_req_headers_dict = extractHeader.header_to_dict(txn_req_headers)
        txn_req_headers_dict['Content-MD5'] = txn._uuid  # used as unique identifier
        #print("Replaying session")
        try:
            req_obj = gRequests.request(extractHeader.extract_txn_req_method(txn_req_headers),
                                        'http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                        headers=txn_req_headers_dict,
                                        #data=req.getBody(),
                                        proxies=proxy,
                                        timeout=2.0,
                                        stream=True,
                                        allow_redirects=False)  # so 302 responses doesn't spin in circles
            #expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
            #expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
            # = result.Result(session_filename, expected_output[0], response.status_code)
            #result_queue.put(r)
            #print("request created: ")
            job = gRequests.send(req_obj,pool,stream=False)
            #job.get();
            #requests.append(req_obj)
            #req_obj.send()
        except UnicodeEncodeError as e:
            # these unicode errors are due to the interaction between Requests and our wiretrace data. 
            # TODO fix
            print("UnicodeEncodeError exception")
            pass

        except requests.exceptions.ContentDecodingError as e:
            print("ContentDecodingError exception thrown")
        except:
            e=sys.exc_info()
            print("ERROR in timed_txn_replay: ",e,txn.getRequest().getHeaders())
       # end of for
    #gRequests.Pool.join()
    #gRequests.map(requests,stream=True,size=20,exception_handler=exception_handler)
