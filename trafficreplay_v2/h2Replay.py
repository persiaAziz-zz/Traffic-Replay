import gevent
import os
from threading import Thread
import sys
from multiprocessing import current_process
import sessionvalidation.sessionvalidation as sv
import lib.result as result
import extractHeader
import mainProcess
import json
from hyper import HTTP20Connection
import hyper

bSTOP = False
hyper.tls._context = hyper.tls.init_context()
hyper.tls._context.check_hostname = False
hyper.tls._context.verify_mode = hyper.compat.ssl.CERT_NONE

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

def txn_replay(session_filename, txn, proxy, result_queue, h2conn,request_IDs):
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
    responseID = -1
    #print("Replaying session")
    try:
        #response = request_session.request(extractHeader.extract_txn_req_method(txn_req_headers),
        #                            'http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
        #                            headers=txn_req_headers_dict,stream=False) # making stream=False raises contentdecoding exception? kill me
        method = extractHeader.extract_txn_req_method(txn_req_headers)
        response = None
        mbody=None
        if 'Transfer-Encoding' in txn_req_headers_dict:
            # deleting the host key, since the STUPID post/get functions are going to add host field anyway, so there will be multiple host fields in the header
            # This confuses the ATS and it returns 400 "Invalid HTTP request". I don't believe this
            # BUT, this is not a problem if the data is not chunked encoded.. Strange, huh?
            del txn_req_headers_dict['Host']
            if 'Content-Length' in txn_req_headers_dict:
                #print("ewww !")
                del txn_req_headers_dict['Content-Length']
                mbody = gen()
        if 'Content-Length' in txn_req_headers_dict:
            nBytes=int(txn_req_headers_dict['Content-Length'])
            mbody = createDummyBodywithLength(nBytes)
        #extractHeader.extract_host(txn_req_headers)+ extractHeader.extract_GET_path(txn_req_headers)
        if method == 'GET':
            #,'Cookie': 'B=64jquc99p42n7&b=4&d=enp9TGNpYEIKTob5dtylGwwB7oOcBLfDRVt4hg--&s=ih&i=Ie61vTBrDuG24oybu9GW; AO=u=1&o=0; F=a=344VOSMMvSvdYQM3vP0tBeijN5LduAtdRsK9TFCaUoDq2cACSB3umQrggAoTT_afLT2oqhCYAKybAUiwloRNtIDniQ--&b=_4ns&d=7.AUgqg9vPtCmTqqtC2UUunc6lCjVyH60u37M9dvlhg-; U=mt=INdsq52MhY9Nbg0xoxhmNfMFSj_DUELVVlSPQVs-&ux=M5rpWB&un=agcdaj3apu8q5; YLS=v=1&p=1&n=0; Y=v=1&n=agcdaj3apu8q5&l=20hd8j07eb82/o&p=f242rsr353000100&r=2s&lg=&intl=us; ucs=bnas=0&sfcTs=1426178993&sfc=1&fs=1&lnct=1440457481&tr=1440606784291; s_pers=%20s_c20%3D1406654291912%7C1501262291912%3B%20s_c20_s%3DLess%2520than%25207%2520days%7C1406656091912%3B%20s_gpv_pn%3DGMAY%253AAndi_Dorfman%253AAndi%2520Dorfman%2520and%2520Josh%2520Murray%2520Share%2520Details%2520of%2520Their%2520Fantasy%2520Suite%2520Stay%7C1406656091920%3B; YP=v=AwAAY&d=AEkAMEYCIQCttOGs9cSYOmSscZdWu4ygUhRaR1H1JBYvK.SNCy6aJgIhAMkqMJbiwGVVOMGwoWPb0SxqBL4i.NpebT6LkbxPu4PvAA--; PH=fn=bCJag48xXD1PllyIo9GFPg--&i=us; SSL=v=1&s=K9Qm.kKvPM4anlnP8YzsU8fAimEeiuItWE_fG92IYTzm_qfJCdoeTIyfgGMvhPCiNbeCR042n9CDUnZ0ZzK_ww--&kv=0; T=z=GZjmXBGtKrXBWBxWKR2vEXfNjM3NwYzNzY3MzcyTk4-&a=YAE&sk=DAAstXw5JWiCVT&ks=EAA3iopIpqeJDSb4BPFsuBmTQ--~E&kt=EAA6h3_gtnHDO8ZX26hL.59JQ--~F&d=c2wBTVRRd01BRTBNREV3TkRBMU9Uay0BYQFZQUUBZwFXWlBEU0UyTkFQTjVQR0tUTVZaWlFMQTM0VQFzY2lkAWlvS1Rsc2c0cVVMdlFkQjFMc29zc3ltLmppZy0BYWMBQU56M0ZCb0MBb2sBWlcwLQF0aXABZ1oxcXBEAXNjAWRlc2t0b3Bfd2ViAWZzAUFOR25IdlZTelpQbAF6egFHWmptWEJBN0U-; DNT=1'
            responseID = h2conn.request('GET',url=''+txn._uuid,
                                    headers={'Accept': '*/*','Referer': 'https://www.yahoo.com','Accept-Language': 'en-US','Origin': 'https://www.yahoo.com','Accept-Encoding': 'gzip, deflate','User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko/20100101 Firefox/12.0','Host': 'video-api.yql.yahoo.com','DNT': '1','Connection': 'Keep-Alive','Cache-Control': 'no-cache'})
            print("get reso", responseID)
            return responseID
            #request_IDs.append(responseID)
            #response = h2conn.get_response(id)
            #print(response.headers)
            #if 'Content-Length' in response.headers:
            #        content = response.read()
                    #print("len: {0} received {1}".format(response.headers['Content-Length'],content))
        '''
        elif method == 'POST':
            response = request_session.post('http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers), 
                                             headers=txn_req_headers_dict, stream=True, data=body, allow_redirects=False)
            
            if 'Content-Length' in response.headers:
                content = response.raw
                #print("len: {0} received {1}".format(response.headers['Content-Length'],content))
        elif method == 'HEAD':
            response = request_session.head('http://' + extractHeader.extract_host(txn_req_headers) + extractHeader.extract_GET_path(txn_req_headers),
                                    headers=txn_req_headers_dict, stream=True)
        '''
        #print(response.headers)
        #print("logged respose")
        expected=extractHeader.responseHeader_to_dict(resp.getHeaders())
        #print(expected)
        if mainProcess.verbose:
            expected_output_split = resp.getHeaders().split('\r\n')[ 0].split(' ', 2)
            expected_output = (int(expected_output_split[1]), str( expected_output_split[2]))
            r = result.Result(session_filename, expected_output[0], response.status_code)
            print(r.getResultString(response.headers,expected,colorize=True))

        #return responseID
        
    except UnicodeEncodeError as e:
        # these unicode errors are due to the interaction between Requests and our wiretrace data. 
        # TODO fix
        print("UnicodeEncodeError exception")

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
            print(bSTOP)
            if session == 'STOP':
                print("Queue is empty")
                bSTOP = True
                break
            with HTTP20Connection('localhost:443', secure=True) as h2conn:
                request_IDs = []
                for txn in session.getTransactionIter():
                    try:
                        ret = txn_replay(session._filename, txn, proxy, result_queue, h2conn,request_IDs)
                        request_IDs.append(ret)
                        #print("txn return value is ",ret)
                    except:
                        e=sys.exc_info()
                        print("ERROR in replaying: ",e,txn.getRequest().getHeaders())
                for id in request_IDs:
                    print("extracting",id)
                    response = h2conn.get_response(id)
                    print("code{0}:{1}".format(response.status,response.headers))

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
