#!/bin/env python

import sys
import os
import collections
import re
import json
import urllib
import urllib.request
import uuid
import time
PROCESSOR_VERSION = "0.2"

raw_session_dict = dict()
session_JSON = dict()
serverPort = '443'
serverIP = '127.0.0.1'
def processTraceBlock(block, ip_port_key):
    ''' format of the trace block
    [timestamp]\r\n\r\n<REQUEST HEADER>\r\n\r\n\r\n\r\nbody\r\n\r\n[timestamp]\r\n\r\n<REQUEST HEADER>\r\n\r\n\r\n\r\nbody\r\n\r\n................
    '''
    reqCount = -1
    respCount =-1
    session_JSON[ip_port_key] = dict()
    session_JSON[ip_port_key]["version"] = PROCESSOR_VERSION
    session_JSON[ip_port_key]["encoding"] = "url_encoded"
    #get the full header
    raw_block=iter(block.split('\r\n\r\n\r\n\r\n'))
    for chunk in raw_block:
        print("followig=====>\n",chunk)
    '''
    timestamp = next(raw_block)
    timestamp = timestamp[1:-1]
    print(timestamp)
    session_JSON[ip_port_key]["timestamp"]=timestamp
    session_JSON[ip_port_key]["txns"]=list()
    for line in raw_block:
        request_chunk = re.findall(r'^(GET|HEAD|POST)\s/\S+\sHTTP/\d\.\d', line) #\S+\s/\S+\sHTTP/\d\.\d\r\n
        response_chunk = re.findall(r'^HTTP/\d\.\d\s\d{3}\s[\s\S]+\r\n', line)
        if(request_chunk):
            print(line)
            reqCount+=1
            session_JSON[ip_port_key]["txns"].append(dict())
            session_JSON[ip_port_key]["txns"][reqCount]["request"]=dict()
            next_line = raw_block.next()
            while next_line:
                session_JSON[ip_port_key]["txns"][reqCount]["request"]["headers"]+=next_line + "\r\n"
                next_line=raw_block.next()
                if re.findall(r'\r\n\r\n',next_line):
                    break
                          
            session_JSON[ip_port_key]["txns"][reqCount]["request"]["headers"]+="\r\n"
    '''

def processFile(trace_dir,file_name):
    global raw_session_dict
    full_trace = b""
    all_lines= ""
    print ("Processing: " + str(file_name))
    with open(os.path.join(trace_dir, file_name), "rb") as f:
        for line in f:
            try:
                dline=line.decode('utf-8')
                #print(dline)                
                send_recv = re.findall(r'(SEND|RECV)', dline)
                ipv4_port = re.findall(r'[0-9]+(?:\.[0-9]+){3}:[0-9]+', dline)
                ipv6_port = re.findall(r'(\S+\:)',dline)
                if ipv4_port:                    
                    ip_port_key = ipv4_port[0]
                elif ipv6_port:
                    ip_port_key = ipv6_port[0]
                    print("found",ip_port_key)
                timestamp = re.findall(r'\[[0-9]+(?:\.[0-9]+)\]',dline)
                #print(ipv4_port)
                if send_recv:
                    next_line=f.readline()
                    #print(timestamp)
                    isHttp=re.findall(r'(WIRE TRACE)',next_line.decode('utf-8')) # make sure this is not a log related to ssl stuff, also we only match WIRE TRACE to drop server side stuffs
                    if not isHttp:
                        while next_line: # we don't want the ssl stuff
                            next_line=f.readline().decode('utf-8')
                            #print(next_line)
                            end_trace = re.findall(r'\[End Trace\]', next_line)
                            if end_trace:
                                break                                
                        continue # we don't want the ssl stuff yet
                        
                # get trace block
                #check if this is server side block
                '''
                if ipv4_port:
                    port = re.findall(r':[0-9]+$', ipv4_port[0])
                    if port:
                        if port[0] == ":"+serverPort:                            
                            next_line=f.readline().decode('utf-8')
                            while next_line: # we don't want the server conn side stuff yet
                                end_trace = re.findall(r'\[End Trace\]', next_line)
                                if end_trace:
                                    break
                                next_line=f.readline().decode('utf-8')
                            continue # we don't want the server conn side stuff yet
                '''
                
                if send_recv and (ipv4_port or ipv6_port):                                 
                    #print(methodLine)
                    #get the rest of the block
                    block = b''
                    next_line=f.readline()
                    while next_line:
                        end_trace = re.findall(r'\[End Trace\]', next_line.decode('utf-8'))
                        if end_trace:
                            break
                        block+=next_line
                        next_line=f.readline()
                    if ip_port_key not in raw_session_dict:
                        raw_session_dict[ip_port_key]=''
                    block=re.sub(r'(?<!\r)\n', '\r\n\r\n', block.decode('utf-8'))
                    raw_session_dict[ip_port_key]+=timestamp[0]+'\r\n\r\n'
                    raw_session_dict[ip_port_key]+=block
                    #request_chunk = re.findall(r'^\S+\s/\S+\sHTTP/\d\.\d\r\n', block)
                    #response_chunk = re.findall(r'^HTTP/\d\.\d\s\d{3}\s[\s\S]+\r\n', block)
                    #print(response_chunk)

            except UnicodeDecodeError:
                print("weird text")
    # let's fix any pesky solitary \n's (these are at the end of all the bodies)
    #full_trace = re.sub(r'(?<!\r)\n', '\r\n\r\n', all_lines)

def process(trace_dir, out_dir):
    #order files
    trace_files = os.listdir(trace_dir)
    trace_files = sorted(trace_files)
    if trace_files[0] == "error.log": #we need to do this in case the last traces are in an error log file that wasn't rotated yet
        print ("Rotating to properly order logs.")
        trace_files = collections.deque(trace_files)
        trace_files.rotate(-1)

    #combine
    full_trace = b""
    all_lines= ""
    for file_name in trace_files:
        print ("Processing: " + str(file_name))
        processFile(trace_dir,file_name)
    for session,traceblock in raw_session_dict.items():
        processTraceBlock(traceblock,session)
    #print(raw_session_dict)
    '''
    Is the issue with the input or my processing? 
    tmp_file = open('full_trace.json', 'wb')
    json.dump(full_trace, tmp_file)
    tmp_file.close()
    INPUT Issue
    '''
'''
    #do the first step of preprocessing, getting raw sessions
    print( "Collecting raw sessions")
    raw_sessions = dict()
    full_trace_iterator = iter(full_trace.splitlines(full_trace.count('\n')))
    for line in full_trace_iterator:
        #TODO IPv6
        #TODO Responses (we get them but do we want to do this a different way)
        send_recv = re.findall(r'(SEND|RECV)', line)
        ipv4_port = re.findall(r'[0-9]+(?:\.[0-9]+){3}:[0-9]+', line)
        if ipv4_port:
            port = re.findall(r':[0-9]+$', ipv4_port[0])
            if port:
                if port[0] == ":443" or port[0] == ":80":
                    continue # we don't want the server conn side stuff yet
        if send_recv and ipv4_port:
            ip_port_key = ipv4_port[0]
            this_trace = line
            while True:
                try:
                    next_line = next(full_trace_iterator)
                    this_trace += next_line
                    end_trace = re.findall(r'\[End Trace\]', next_line)
                    if end_trace:
                        break
                except Exception as e:
                    #reached the end of the file
                    print( e)
                    break

            if ip_port_key not in raw_sessions:
                raw_sessions[ip_port_key] = this_trace
                print(ip_port_key)
            else:
                raw_sessions[ip_port_key] += this_trace

    #do the second step of preprocessing, getting JSONs from raw sessions
    print( "Constructing session JSONs")
    session_JSONs = dict()
    for session, raw_traces in raw_sessions.items():
        #basic data
        session_JSONs[session] = dict()
        session_JSONs[session]["version"] = PROCESSOR_VERSION
        session_JSONs[session]["encoding"] = "url_encoded"

        # let's get the raw text from the traces
        raw_text = ""
        timestamp = ""
        timestamp_list = list()
        for line in raw_traces.splitlines(raw_traces.count('\n')):
            trace_line = re.findall(r'^\d{8}\.\d{2}h\d{2}m\d{2}s', line)
            timestamp = re.findall(r'\[\d{10}\.\d{3}\]', line)
            if timestamp:
                timestamp_list.append(timestamp[0][1:-1])
            if not trace_line:
                raw_text += line
        
        #get session start timestamp
        session_JSONs[session]["timestamp"] = timestamp_list[0]
 
        # let's parse out requests and responses
        count = -1
        delimiter = "\r\n\r\n"
        is_request_chunk = True
        raw_text_chunks = iter(raw_text.split(delimiter))
        session_JSONs[session]["txns"] = list()
        for chunk in raw_text_chunks:
            #check if each chunk is request or response if it is do so accordingly
            #otherwise append it to the previous chunk's data
            request_chunk = re.findall(r'^\S+\s/\S+\sHTTP/\d\.\d\r\n', chunk)
            response_chunk = re.findall(r'^HTTP/\d\.\d\s\d{3}\s[\s\S]+\r\n', chunk)
            if request_chunk:
                count += 1
                is_reqeust_chunk = True
                chunk += delimiter
                if count <= len(session_JSONs[session]["txns"]):
                    session_JSONs[session]["txns"].append(dict())
                session_JSONs[session]["txns"][count]["request"] = dict()
                session_JSONs[session]["txns"][count]["request"]["timestamp"] = timestamp_list[count - 1] 
                session_JSONs[session]["txns"][count]["request"]["headers"] = chunk
                session_JSONs[session]["txns"][count]["uuid"] = uuid.uuid4().hex
            elif response_chunk:
                is_request_chunk = False
                chunk += delimiter
                if count <= len(session_JSONs[session]["txns"]):
                    session_JSONs[session]["txns"].append(dict())
                session_JSONs[session]["txns"][count]["response"] = dict()
                session_JSONs[session]["txns"][count]["response"]["timestamp"] = timestamp_list[count - 1] 
                session_JSONs[session]["txns"][count]["response"]["headers"] = chunk
            else: #is body chunk
                try:
                    if count == -1: continue #if we have garbage at the front
                    chunk = urllib.parse.quote(chunk)
                    if is_request_chunk:
                        if "body" not in session_JSONs[session]["txns"][count]["request"]:
                            session_JSONs[session]["txns"][count]["request"]["body"] = chunk
                        else:
                            session_JSONs[session]["txns"][count]["request"]["body"] += chunk
                    else:
                        if "body" not in session_JSONs[session]["txns"][count]["response"]:
                            session_JSONs[session]["txns"][count]["response"]["body"] = chunk
                        else:
                            session_JSONs[session]["txns"][count]["response"]["body"] += chunk
                except KeyError as k:
                    continue # for now we're dropping malformed bodies. will not be able to do this when we're validating. might have to go edit wiretracing code to give us better delimiters here for parsing. right now isn't particularly straightforward
        print(len(session_JSONs[session]["txns"]))
        session_JSONs[session]["txns"] = list(filter(bool, session_JSONs[session]["txns"]))
        if len(session_JSONs[session]["txns"]) == 0:
            del session_JSONs[session] 

    #write out
    unicode_errors = 0
    print( "Writing sessions to disk")
    out_files = dict()
    for session, data in session_JSONs.items():
        out_files[session] = open(os.path.join(out_dir, 'session_' + str(session)) + '.json', 'w')
        try:
            json.dump(data, out_files[session])
            out_files[session].close()     
        except:
            unicode_errors += 1
            out_files[session].close()
            os.remove(os.path.join(out_dir, 'session_' + str(session)) + '.json')     

    print( str(unicode_errors) + " unicode errors")
'''
def main(argv):
    if len(argv) != 3:
        print( "Script to preprocess trace logs for client.")
        print( "Outputs JSONs to directory 'sessions'")
        print( "Usage: python " + str(argv[0]) + " <in directory> <out directory>")
        return
    '''
    if not os.path.isdir(argv[1]):
        print( str(argv[1]) + " is not a directory. Aborting.")
        return
    if not os.path.exists(argv[2]):
        os.makedirs(argv[2])
    else:
        print( str(argv[2]) + " already exists, choose another output directory!")
        return
    '''
    t1=time.time()
    process(argv[1], argv[2])
    t2=time.time()
    print("time taken:",(t2-t1))
if __name__ == "__main__":
    main(sys.argv)
