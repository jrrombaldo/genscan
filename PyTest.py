
'''
Created on 21 Jul 2017

@author: junior
'''

import threading
import logging
import sys
import Queue
from Queue import Empty


##################  LOGGING CONFIGURATION ######################

logging.basicConfig(format='%(asctime)s   %(levelname)-8s %(message)s', level=logging.DEBUG, stream=sys.stdout)
# logging.basicConfig(format='-> %(message)s',level=logging.DEBUG, stream=sys.stdout)

# this is to synchronize access to STDOUT
log_lock = threading.Condition()

def safeOutput(msg, level=logging.INFO):
        with log_lock:
            while not log_lock.acquire():
                log_lock.wait()
            try:
                logging.log(msg, level)
            finally:
                log_lock.release()
                log_lock.notifyAll()
 




########################## JOBS QUEUE   ########################

appsQueue = Queue.Queue()

def getNextApp():
    # decide to run a get without block and just return None when app queue is empty. No not even empty check is required in this case
    try:
        return  appsQueue.get(block=None)
    except Empty:
        return None





####################### PLUGIN CLASS   ########################

class BasePlugin(object):
    
    def __init__(self, tid):
        self.tid = tid

            
    def validate(self):
        app = getNextApp()
        while app:
            self.safeOutput('working at '+str(app))
            app = getNextApp()
           
       
    def safeOutput(self, msg, level = logging.INFO):
        safeOutput(level, 'THREAD-{0}\t{1}'.format(self.tid, msg))      

    
    
    
    
    

     
     
     
     
for x in range(20):
    appsQueue.put('app->'+str(x))
    
# while not appsQueue.empty():
#     print getNextApp()
     
 

# time.sleep(2)
      
threads = [] 
 
  
for t in range(10):
    thread = threading.Thread(target=BasePlugin(t).validate(), args=())
    thread.daemon = True
    threads.append(thread)
    thread.start()
     
     
# making sure the program waits from all threads to finish.
for t2 in threads:
    t2.join()

     

    
