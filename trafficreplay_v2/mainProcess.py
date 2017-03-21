#!/usr/bin/python
import sys
import json
import socket
import os
import threading
import time
import argparse
import subprocess
import shlex
from multiprocessing import Pool, Process
from collections import deque
from progress.bar import Bar
import sessionvalidation.sessionvalidation as sv
import lib.result as result
import WorkerTask
import Scheduler
import Config
verbose = False
def check_for_ats(hostname, port):
    ''' Checks to see if ATS is running on `hostname` and `port`
    If not running, this function will terminate the script
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((hostname, port))
    if result != 0:
        # hostname:port is not being listened to
        print('==========')
        print('Error: Apache Traffic Server is not running on {0}:{1}'.format(hostname, port))
        print('Aborting')
        print('==========')
        sys.exit()
# Note: this function can't handle multi-line (ie wrapped line) headers
# Hopefully this isn't an issue because multi-line headers are deprecated now        
        
def main(path, replay_type, Bverbose):
    global verbose
    verbose = Bverbose
    check_for_ats(Config.proxy_host, Config.proxy_nonssl_port)
    proxy = {"http": "http://{0}:{1}".format(Config.proxy_host, Config.proxy_nonssl_port)}
    Scheduler.LaunchWorkers(path,Config.nProcess,proxy,replay_type, Config.nThread)
    
    

