import http.client
import socket, ssl, pprint
import gevent
import requests
import os
#import threading
import sys
from multiprocessing import current_process
import sessionvalidation.sessionvalidation as sv
import lib.result as result
import extractHeader
from gevent import monkey, sleep
from threading import Thread
import mainProcess
import json
import extractHeader
import time
import Config
bSTOP = False
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
        content=None
        if 'Transfer-Encoding' in txn_req_headers_dict:
            # deleting the host key, since the STUPID post/get functions are going to add host field anyway, so there will be multiple host fields in the header
            # This confuses the ATS and it returns 400 "Invalid HTTP request". I don't believe this
            # BUT, this is not a problem if the data is not chunked encoded.. Strange, huh?
            del txn_req_headers_dict['Host']
            if 'Content-Length' in txn_req_headers_dict:
                #print("ewww !")
                del txn_req_headers_dict['Content-Length']
                body = gen()
        if 'Content-Length' in txn_req_headers_dict:
            nBytes=int(txn_req_headers_dict['Content-Length'])
            body = createDummyBodywithLength(nBytes)
        #print("request session is",id(request_session))
        if method == 'GET':     
            request_session.request('GET','http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict,body=body)
            r1 = request_session.getresponse()
            print(r1.getheaders())
            print(r1.read())

        elif method == 'POST':
            response = request_session.post('http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers), 
                                             headers=txn_req_headers_dict, stream=False, data=body, allow_redirects=False)
            
            if 'Content-Length' in response.headers:
                content = response.raw
                #print("reading==========>>>>>>>>>>>>>.")
                #print(content.data)
                #print("len: {0} received {1}".format(response.headers['Content-Length'],content))
        elif method == 'HEAD':
            response = request_session.head('http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict, stream=False)

            #gzip_file = gzip.GzipFile(fileobj=content)
            #shutil.copyfileobj(gzip_file, f)
        expected=extractHeader.responseHeader_to_dict(resp.getHeaders())
        #print(expected)
        if mainProcess.verbose:
            expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
            expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
            r = result.Result(session_filename, expected_output[0], r1.status)
            #print(r.getResultString(response.headers,expected,colorize=True))
            #r.Compare(response.headers,expected)
        #result_queue.put(r)
    except UnicodeEncodeError as e:
        # these unicode errors are due to the interaction between Requests and our wiretrace data. 
        # TODO fix
        print("UnicodeEncodeError exception")

    except requests.exceptions.ContentDecodingError as e:
        print("ContentDecodingError",e)
    except:
        e=sys.exc_info()
        print("ERROR in requests: ",e,response, session_filename)
def client_replay(input, proxy, result_queue, nThread):
    Threads = []
    for i in range(nThread):
        t = Thread(target=session_replay, args=[input, proxy, result_queue])
        t.start()
        Threads.append(t)

    for t1 in Threads:
        t1.join()

def session_replay(input, proxy, result_queue):

    ''' Replay all transactions in session 
    
    This entire session will be replayed in one requests.Session (so one socket / TCP connection)'''
    #if timing_control:
    #    time.sleep(float(session._timestamp))  # allow other threads to run
    global bSTOP
    sslSocks = []
    while bSTOP == False:
        for session in iter(input.get, 'STOP'):
            sc = ssl.SSLContext(protocol=ssl.PROTOCOL_SSLv23)
            sc.load_cert_chain(Config.ca_certs,keyfile=Config.keyfile)
            conn = http.client.HTTPSConnection(Config.proxy_host,Config.proxy_ssl_port,context=sc)
            for txn in session.getTransactionIter():
                try:
                    #print(txn._uuid)
                    txn_replay(session._filename, txn, proxy, result_queue, conn)
                except:
                    e=sys.exc_info()
                    print("ERROR in replaying: ",e,txn.getRequest().getHeaders())
            #sslSocket.bStop = False

        bSTOP = True
        print("stopping now")
        input.put('STOP')
        break

    time.sleep(2.5)
    for sslSock in sslSocks:
        sslSock.ssl_sock.close()