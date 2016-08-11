#!/usr/bin/python
from __future__ import absolute_import, division, print_function
import mainProcess
import argparse

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-type",action='store', dest='replay_type', help="Replay type: fast/random")
    parser.add_argument("-np", type=int, action='store', dest='nProcess', help="Number of Processes", default=4)
    parser.add_argument("-nt", type=int, action='store', dest='nThread', help="Number of Threads per child process", default=4)
    parser.add_argument("hostname", help="hostname ATS is running under")
    parser.add_argument("port", type=int, help="port ATS is listening on")    
    parser.add_argument("log_dir", help="directory of JSON replay files")
    parser.add_argument("-v", dest="verbose", help="verify response status code", action="store_true")
    
    #parser.add_argument("--timing", "-t", action="store_true",  help="use timing controls for session replay")
    #parser.add_argument("--threads", "-n", type=int, help="number of parent threads to help manage session threads; this DOES NOT specify how many threads total will be spawned by this script")
    #parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # Let 'er loose
    #main(args.log_dir, args.hostname, int(args.port), args.threads, args.timing, args.verbose)
    mainProcess.main(args.log_dir, args.hostname, int(args.port), args.replay_type,args.nProcess,args.nThread,args.verbose)
