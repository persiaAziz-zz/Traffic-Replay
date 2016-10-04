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
import mainProcess
import json
bSTOP = False
def createDummyBodywithLength(numberOfbytes):
    if numberOfbytes==0:
        return None
    body= 'a'
    while numberOfbytes!=1:
        body += 'b'
        numberOfbytes -= 1
    return body
    
def handleResponse(response,*args, **kwargs):
    print(response.status_code)
    #resp=args[0]
    #expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
    #expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
    #r = result.Result(session_filename, expected_output[0], response.status_code)
    #print(r.getResultString(colorize=True))
# make sure len of the message body is greater than length
def gen():
    yield 'pforpersia,champaignurbana'.encode('utf-8')
    yield 'there'.encode('utf-8')

def txn_replay(session_filename, txn, proxy, result_queue, request_session):
    """ Replays a single transaction
    :param request_session: has to be a valid requests session"""
    req = txn.getRequest()
    resp = txn.getResponse()

    # Construct HTTP request & fire it off
    txn_req_headers = req.getHeaders()
    txn_req_headers_dict = extractHeader.header_to_dict(txn_req_headers)
    txn_req_headers_dict['Content-MD5'] = txn._uuid  # used as unique identifier
    if 'body' in txn_req_headers_dict:
        del txn_req_headers_dict['body']
    
    #print("Replaying session")
    try:
        #response = request_session.request(extractHeader.extract_txn_req_method(txn_req_headers),
        #                            'http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
        #                            headers=txn_req_headers_dict,stream=False) # making stream=False raises contentdecoding exception? kill me
        method = extractHeader.extract_txn_req_method(txn_req_headers)
        response = None
        body=None
        if 'Transfer-Encoding' in txn_req_headers_dict:
            # deleting the host key, since the STUPID post/get functions are going to add host field anyway, so there will be multiple host fields in the header
            # This confuses the ATS and it returns 400 "Invalid HTTP request". I don't believe this
            # BUT, this is not a problem if the data is not chunked encoded.. Strange, huh?
            del txn_req_headers_dict['Host']
            if 'Content-Length' in txn_req_headers_dict:
                print("ewww !")
                del txn_req_headers_dict['Content-Length']
                body = gen()
        if 'Content-Length' in txn_req_headers_dict:
            nBytes=int(txn_req_headers_dict['Content-Length'])
            body = createDummyBodywithLength(nBytes)
        
        if method == 'GET':     
            response = request_session.get('http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict, stream=True, allow_redirects=False,data=body)
            if 'Content-Length' in response.headers:
                    content = response.raw
                    print("len: {0} received {1}".format(response.headers['Content-Length'],content))

        elif method == 'POST':
            response = request_session.post('http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers), 
                                             headers=txn_req_headers_dict, stream=True, data=body, allow_redirects=False)
            
            if 'Content-Length' in response.headers:
                content = response.raw
                print("len: {0} received {1}".format(response.headers['Content-Length'],content))
        elif method == 'HEAD':
            response = request_session.head('http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict, stream=True)
        if mainProcess.verbose:
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
        print("ContentDecodingError",e)
    except:
        e=sys.exc_info()
        print("ERROR in requests: ",e,response, session_filename)

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
                print("Queue is empty")
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
        print("Queue is empty")
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
