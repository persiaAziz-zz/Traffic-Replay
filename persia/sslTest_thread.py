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
#from threading import Thread
bSTOP = False
class ssl_socket():
   
    def readFromWire(self):
        print("blabla")
    
    def __init__(self, ssl_sock, bStop):
        self.ssl_sock=ssl_sock
        self.bStop = bStop
def createDummyBodywithLength(numberOfbytes):
    if numberOfbytes==0:
        return None
    body= 'a'
    while numberOfbytes!=1:
        body += 'b'
        numberOfbytes -= 1
    return body

def generator():
    yield 'persia'
    yield 'aziz'
def SendRequest(ssl_sock, txn_req_headers_dict):
    if 'Transfer-Encoding' in txn_req_headers_dict and txn_req_headers_dict['Transfer-Encoding'] == 'chunked':
        writeChunkedData(ssl_sock)
    if 'Content-Length' in txn_req_headers_dict:
        nBytes=int(txn_req_headers_dict['Content-Length'])
        body = createDummyBodywithLength(nBytes);
        ssl_sock.write(body)
        
def writeChunkedData(ssl_sock):
    for chunk in generator():
        chunk_string=bytes('%X\r\n%s\r\n'%(len(chunk),chunk),'UTF-8')
        ssl_sock.write(chunk_string)
    last_chunk=bytes('0\r\n\r\n','UTF-8')
    ssl_sock.write(last_chunk)

def removeContent_length(txn_req_headers):
    h1,h2 = txn_req_headers.split('Content-Length')
    h3,h4 = h2.split('\r\n',1)
    return h1+h4

def txn_replay(session_filename, txn, proxy, result_queue, ssl_sock):
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
        txn_req_headers = txn_req_headers[:-2]+"Content-MD5: "+txn._uuid+"\r\n"
        #print(txn_req_headers)
        #requestString=bytes(txn_req_headers,'utf-8')
        #requestString=str.encode(txn_req_headers)
        if 'Transfer-Encoding' in txn_req_headers_dict and 'Content-Length' in txn_req_headers_dict:
            txn_req_headers=removeContent_length(txn_req_headers)
            #print(txn_req_headers)
        s1=b""
        s1 +=txn_req_headers.encode()
        s1 +=b'\r\n'
        ssl_sock.write(s1)
        if 'Transfer-Encoding' in txn_req_headers_dict and txn_req_headers_dict['Transfer-Encoding'] == 'chunked':
            writeChunkedData(ssl_sock)
        elif 'Content-Length' in txn_req_headers_dict:
            nBytes=int(txn_req_headers_dict['Content-Length'])
            body = createDummyBodywithLength(nBytes);
            print("creating body")
            ssl_sock.write(body)
        response = ssl_sock.read()
        if mainProcess.verbose:
            status=response.decode().split('\r\n')[0]
            print(status)
        #sendRequest(b'%s' % bytes(txn_req_headers,'utf_8'))
    except UnicodeEncodeError as e:
        # these unicode errors are due to the interaction between Requests and our wiretrace data. 
        # TODO fix
        print("UnicodeEncodeError exception")

    except requests.exceptions.ContentDecodingError as e:
        print("ContentDecodingError exception thrown: probably has to do with how ATS wiretracing encodes body data. Skipping this transaction")
    except:
        e=sys.exc_info()
        print("ERROR in requests: ",e)
        

           
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
    while bSTOP == False:
        for session in iter(input.get, 'STOP'):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ssl_sock = ssl.wrap_socket(s,
                                ca_certs="/home/persia/server.pem",
                                cert_reqs=ssl.CERT_OPTIONAL,
                                do_handshake_on_connect=True)

            ssl_sock.connect(('localhost', 443))
            sslSocket=ssl_socket(ssl_sock,True)
            for txn in session.getTransactionIter():
                try:
                    txn_replay(session._filename, txn, proxy, result_queue, ssl_sock)
                except:
                    e=sys.exc_info()
                    print("ERROR in replaying: ",e,txn.getRequest().getHeaders())
            sslSocket.bStop = False
            sslSocket.ssl_sock.close()
        bSTOP = True
        print("stopping now")
        input.put('STOP')
        break