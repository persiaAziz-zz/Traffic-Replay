#!/bin/env python

import sys
import os
import collections
import re
import json
import urllib.request
import uuid
import time
PROCESSOR_VERSION = "0.1"
def process(trace_dir, out_dir):
    #order files
    trace_files = os.listdir(trace_dir)
    trace_files = sorted(trace_files)
    if trace_files[0] == "error.log": #we need to do this in case the last traces are in an error log file that wasn't rotated yet
        print ("Rotating to properly order logs.")
        trace_files = collections.deque(trace_files)
        trace_files.rotate(-1)
    for file_name in trace_files:
        print ("Processing: " + str(file_name))
        with open(os.path.join(trace_dir, file_name), "rb") as f:
            #lines = f.read(1)
            for line in f:
                print(line)
               
def main(argv):
    if len(argv) != 3:
        print( "Script to preprocess trace logs for client.")
        print( "Outputs JSONs to directory 'sessions'")
        print( "Usage: python " + str(argv[0]) + " <in directory> <out directory>")
        return

    if not os.path.isdir(argv[1]):
        print( str(argv[1]) + " is not a directory. Aborting.")
        return
    if not os.path.exists(argv[2]):
        os.makedirs(argv[2])
    else:
        print( str(argv[2]) + " already exists, choose another output directory!")
        return
    t1=time.time()
    process(argv[1], argv[2])
    t2=time.time()
    print("time taken:",(t2-t1))
if __name__ == "__main__":
    main(sys.argv)