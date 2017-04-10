#!/usr/bin/python
import socket
import requests
import os
#import threading
import sys
from multiprocessing import current_process
import sessionvalidation.sessionvalidation as sv
import lib.result as result
from progress.bar import Bar
import extractHeader
import RandomReplay
import SSLReplay
import h2Replay
def worker(input,output,proxy,replay_type,nThread):
    #progress_bar = Bar(" Replaying sessions {0}".format(current_process().name), max=input.qsize())
        #print("playing {0}=>{1}:{2}".format(current_process().name,session._timestamp,proxy))
    if replay_type == 'random':
        RandomReplay.client_replay(input, proxy, output, nThread)
    elif replay_type == 'ssl':
        SSLReplay.client_replay(input, proxy, output,nThread)
    elif replay_type == 'h2':
        h2Replay.client_replay(input, proxy, output,nThread)
        #progress_bar.next()
    #progress_bar.finish()
    print("process{0} has exited".format(current_process().name)) 
    
