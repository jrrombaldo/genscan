'''
Created on 21 Jul 2017

@author: Jr.Rombaldo
'''


from Queue import Queue
import threading
import logging
import sys
from importlib import import_module
import os





#############
#######  GLOBALCONFIGURATION SECTION
#############

config = {
    'line_size'         : 1,
    'result_format'     : '{app:25} -> {result}',
    'logging_level'     : logging.DEBUG,
    'logging_format'    : '%(asctime)s   %(levelname)-8s %(message)s',
    'plugin_directory'  : './plugins'
    }



#############
#######  LOGGING CONFIGURATION
#############

logging.basicConfig(format=config['logging_format'], level=config['logging_level'], stream=sys.stdout)

log_lock = threading.Condition()

def safeOutput(msg, level=logging.INFO):
    """thread safe stdout/stderr outputs"""
    with log_lock:
        while not log_lock.acquire(): log_lock.wait()
        try: logging.log(level=level, msg=msg)
        finally:
            log_lock.release()
            log_lock.notifyAll()
               
       
def exit_err(msg):   
    safeOutput(msg, logging.ERROR)
    exit(-1)  
    
    
  
        
#############
#######  THREADING IMPLEMENTATION
#############       

class GS_Thread(threading.Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        threading.Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()
    
    def run(self):
        while True:
            func, args, kargs = self.tasks.get(block=True)
            try: 
                func(*args, **kargs)
            except Exception, e: 
                print e
            self.tasks.task_done()


class GS_ThreadPool:
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads): 
            GS_Thread(self.tasks)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.tasks.join()





#############
####### PLUGINS BASE CLASS AND LOADER
#############  

def list_available_plugins():
    plugins_array =[]
    for pl in os.listdir(config['plugin_directory']): 
        if pl.find('.py') >0 and pl.find('.pyc') <1 and pl != '__init__.py': 
            plugins_array.append(pl.replace('.py',''))
    return plugins_array
    

class BasePlugin (object):
    
    SAFE = 0
    VULNERABLE = 1
    NOT_SURE = 2
    ERROR = 3
    
    result = {
        0: "SAFE",
        1: "VULNERABLE",
        2: "NOT_SURE",
        3: "ERROR"
    }
    
    def output(self, msg):
        safeOutput(msg)

    def validate(self, app):
        """ >>> TO BE IMPLEMENTED <<<"""
        
    
    def process_result(self, app, result):
        self.output(config['result_format'].format(**{'app':app, 'result':BasePlugin.result.get(result)}))
        
    def process_err(self, app, err):
        self.output(config['result_format'].format(**{'app':app, 'result':(self.ERROR+' - '+err)}))
        
        
def load_plugin(plugin_name):
    safeOutput('Loading plugin: %s' % plugin_name)
    try:
        plugin_mod = import_module("plugins." + plugin_name)
        
        if hasattr(plugin_mod, plugin_name): plugin_class = getattr(plugin_mod, plugin_name)
        elif hasattr(plugin_mod, plugin_name.title()): plugin_class = getattr(plugin_mod, plugin_name.title())
        else: exit_err('plugin name and class name does not match')
        
        return plugin_class().validate
    
    except ImportError as e:
        safeOutput('plugin [%s] not loaded, reason: [%s]' % (plugin_name, e), logging.ERROR)
        exit(-1)
    except AttributeError as e:
        safeOutput('plugin [%s] loaded, but problem with its class, reason: [%s]' % (plugin_name, e), logging.ERROR)
        exit(-1)    

    
   
#############
#######  PREPARING THREADS
############# 


def test_threads_n_plugins():
    
    pool = GS_ThreadPool(2)
    
    plugin_call = load_plugin("StrutsShock")
#     plugin_call = load_plugin("Inside")
    
    # adding Jobs to queue
    for i in range (10):
        pool.add_task(plugin_call, 'https://applications_%s.com/' % i)
        
    # making sure the program will wait until all jobs have been completed
    pool.wait_completion()




if __name__ == '__main__':
#     test_threads_n_plugins()
#     for pl in os.listdir('plugins'): 
#         if pl.find('.py') >0 and pl.find('.pyc') <1 and pl != '__init__.py': print pl.replace('.py','')
    print list_available_plugins()


   
