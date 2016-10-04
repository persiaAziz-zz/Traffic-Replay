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
        txn_req_headers = txn_req_headers[:-2]+"Content-MD5: "+txn._uuid+"\r\n\r\n"
        print(txn_req_headers)
        #requestString=bytes(txn_req_headers,'utf-8')
        #requestString=str.encode(txn_req_headers)
        s1=b""
        s1 +=txn_req_headers.encode()
        sendRequest(s1)
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
        
def sendRequest(requestString):

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Require a certificate from the server. We used a self-signed certificate
    # so here ca_certs must be the server certificate itself.
    ssl_sock = ssl.wrap_socket(s,
                               ca_certs="/home/persia/server.pem",
                               cert_reqs=ssl.CERT_OPTIONAL,
                               do_handshake_on_connect=True)
#
#                               ca_certs="/home/persia/server.crt",
    ssl_sock.connect(('localhost', 443))



    if True: # from the Python 2.7.3 docs        
        # read all the data returned by the server.
        #ssl_sock.write(b"""GET /blabla.jpg HTTP/1.1\r\nHost:example.com\r\n\r\n""") ## working write
        #ssl_sock.write(b"""GET /uu/api/res/1.2/Qz8h9xMcjAa0Gi3Z0i3t3g--/aD0zMTMuNTtxPTQ1O3c9NjAwLjA7c209MTthcHBpZD15dGFjaHlvbg--/https://s.yimg.com/av/moneyball/ads/1452749457755-3783.jpg HTTP/1.1\r\nAccept: image/png, image/svg+xml, image/*;q=0.8, */*;q=0.5\r\nReferer: https://tw.yahoo.com/\r\nAccept-Language: zh-TW\r\nUser-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko/20100101 Firefox/12.0\r\nAccept-Encoding: gzip, deflate\r\nHost: s.yimg.com\r\nDNT: 1\r\nConnection: Keep-Alive\r\nContent-MD5: 1998496becb64d56b1843530ec163be7\r\n\r\n""")
        #print(requestString)
        ssl_sock.write(requestString)
        data = ssl_sock.read()
        #status=data.decode().split('\r\n')[0]
        #print(status)
        #expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
        #expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
        #r = result.Result(session_filename, expected_output[0], response.status_code)
        #print(r.getResultString(colorize=True))
        # note that closing the SSLSocket will also close the underlying socket
        ssl_sock.close()
        
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
    
