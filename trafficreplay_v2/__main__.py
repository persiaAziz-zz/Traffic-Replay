#!/usr/bin/python
from __future__ import absolute_import, division, print_function
import mainProcess
import argparse

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-type",action='store', dest='replay_type', help="Replay type: ssl/random/h2")
    parser.add_argument("-log_dir",type=str, help="directory of JSON replay files")
    parser.add_argument("-v", dest="verbose", help="verify response status code", action="store_true")

    args = parser.parse_args()

    # Let 'er loose
    #main(args.log_dir, args.hostname, int(args.port), args.threads, args.timing, args.verbose)
    mainProcess.main(args.log_dir, args.replay_type,args.verbose)
