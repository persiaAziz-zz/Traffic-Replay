import string
import cgi
import time
import sys
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn, ForkingMixIn

import sessionvalidation.sessionvalidation as sv


SERVER_PORT = 5005 # default port
HTTP_VERSION = 'HTTP/1.1'
G_replay_dict = {}


class ThreadingServer(ThreadingMixIn, HTTPServer):
    '''This class forces the creation of a new thread on each connection'''
    pass

class ForkingServer(ForkingMixIn, HTTPServer):
    '''This class forces the creation of a new process on each connection'''
    pass


# Warning: if you can't tell already, it's pretty hacky
#
# The standard library HTTP server doesn't exactly provide all the functionality we need from the API it exposes,
# so we have to go in and override various methods that probably weren't intended to be overridden
#
# See the source code (https://hg.python.org/cpython/file/3.5/Lib/http/server.py) if you want to see where all these
# variables are coming from
class MyHandler(BaseHTTPRequestHandler):
    def get_response_code(self, header):
        # this could totally go wrong
        return int(header.split(' ')[1])


    def send_response(self, code, message=None):
        ''' Override `send_response()`'s tacking on of server and date header lines. '''
        #self.log_request(code)
        self.send_response_only(code, message)


    def do_GET(self):
        global G_replay_dict
        #print("ATS sent me==================>",self.headers)
        request_hash, __ = cgi.parse_header(self.headers.get('Content-MD5'))
        
        if request_hash not in G_replay_dict:
            self.send_response(404)
            self.send_header('Connection', 'close')
            self.end_headers()

        else:
            resp = G_replay_dict[request_hash]
            headers = resp.getHeaders().split('\r\n')

            # set status codes
            status_code = self.get_response_code(headers[0])
            self.send_response(status_code)

            # set headers
            for header in headers[1:]: # skip first one b/c it's response code
                if header == '':
                    continue
                elif 'Content-Length' in header:
                    # we drop the Content-Length header because the wiretrace JSON files are inaccurate
                    # TODO: run time option to force Content-Length to be in headers
                    length = len(bytes(resp.getBody(),'UTF-8')) if resp.getBody() else 0
                    self.send_header('Content-Length', str(length))
                    continue
        
                header_parts = header.split(':', 1)
                header_field = str(header_parts[0].strip())
                header_field_val = str(header_parts[1].strip())
                #print("{0} === >{1}".format(header_field, header_field_val))
                self.send_header(header_field, header_field_val)

            self.end_headers()

            # set body
            response_string = resp.getBody()
            self.wfile.write(bytes(response_string, 'UTF-8'))

        return


def populate_global_replay_dictionary(sessions):
    ''' Populates the global dictionary of {uuid (string): reponse (Response object)} '''
    global G_replay_dict
    print("size",len(G_replay_dict))
    for session in sessions:
        for txn in session.getTransactionIter():
            G_replay_dict[txn._uuid] = txn.getResponse()


def main():
    if len(sys.argv) < 2:
        print("Usage: ./uWs.py replay_files_dir [server_port] [socket_timeout]")
        sys.exit(1)

    # set up global dictionary of {uuid (string): response (Response object)}
    s = sv.SessionValidator(sys.argv[1])
    populate_global_replay_dictionary(s.getSessionIter())
    print("Dropped {0} sessions for being malformed".format(len(s.getBadSessionList())))

    # start server
    try:
        server_port = SERVER_PORT
        socket_timeout = None

        if len(sys.argv) >= 3:
            server_port = int(sys.argv[2])

        if len(sys.argv) >= 4:
            socket_timeout = int(sys.argv[3])

        MyHandler.protocol_version = HTTP_VERSION
        server = ThreadingServer(('', server_port), MyHandler)
        server.timeout = socket_timeout or 5
        print("=== started httpserver ===")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n=== ^C received, shutting down httpserver ===")
        server.socket.close()
        sys.exit(0)


if __name__ == '__main__':
    main()
