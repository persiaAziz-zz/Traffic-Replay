import time
import random
import json
from multiprocessing import Process, Queue, current_process
from progress.bar import Bar
import sessionvalidation.sessionvalidation as sv
import WorkerTask
import time

    
def LaunchWorkers(path,nProcess,proxy,replay_type):
    ms1=time.time()
    s = sv.SessionValidator(path)
    sessions = s.getSessionList()
    sessions.sort(key=lambda session: session._timestamp)
    Processes=[]
    Qsize = int (1.1 * len(sessions)/(nProcess))
    QList=[Queue(Qsize) for i in range(nProcess)]
    print("Dropped {0} sessions for being malformed".format(len(s.getBadSessionList())))
    print(range(nProcess))
    OutputQ=Queue();
    #======================================== Pre-load queues
    for session in sessions:
        #if nProcess == 1:
        #    QList[0].put(session)
        #else:            
        QList[random.randint(0,nProcess-1)].put(session)
        #if QList[0].qsize() > 10 :
        #    break
    #=============================================== Launch Processes
    print("size",QList[0].qsize())
    for i in range(nProcess):
        QList[i].put('STOP')
    for i in range(nProcess):
        p=Process(target=WorkerTask.worker, args=[QList[i],OutputQ,proxy,replay_type])
        p.daemon=False
        Processes.append(p);
        p.start()
    
    for p in Processes:
        p.join()
    ms2=time.time()
    print("OK enough, it is time to exit, running time in seconds", (ms2-ms1)) 
