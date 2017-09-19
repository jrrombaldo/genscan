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
import socket
import errno
from urlparse import urlparse
import json
import requests


# disable SSL messages: InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised.
from requests.packages.urllib3.exceptions import InsecureRequestWarning  # @UnresolvedImport
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # @UndefinedVariable



#############
#######  GLOBALCONFIGURATION SECTION
#############

config = {
    'line_size'         : 1,
    'result_format'     : '{app:25} -> {result}',
    'logging_level'     : logging.INFO,
#     'logging_format'    : '%(asctime)s   %(levelname)-8s %(message)s',
    'logging_format'    : '%(message)s',
    'plugin_directory'  : './plugins',
    'socket_timeout'    : 5,  # timeout in seconds that the program will wait to open a connection
    'jason_output'      : False,
    'thread_numbers'    : 150,
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
    plugins_array = []
    for pl in os.listdir(config['plugin_directory']): 
        if pl.find('.py') > 0 and pl.find('.pyc') < 1 and pl != '__init__.py': 
            plugins_array.append(pl.replace('.py', ''))
    return plugins_array
    


class BasePlugin (object):
    
    def validate(self, app):
        """ >>> TO BE IMPLEMENTED <<<"""
        
        
    def output(self, msg):
        if config['jason_output']:
            json.dumps( msg, indent=3)
        else:
            safeOutput(msg)
        

    def test_connectiviy(self, host, port):
        ''' test host DNS resolution and test if the open is open and reacheable '''
        try:
            socket.gethostbyname_ex(host)
        except socket.gaierror as err:
            return "DNS_ERROR -> %s" % err

        try:
            s = socket.socket()
            s.settimeout(config['socket_timeout'])
            result = s.connect_ex((host, port))
            if result == 0: return 'OK'
            else: return 'ERROR_CODE=[%s] ERROR_MSG=[%s] ' % (str(result), errno.errorcode[result])
        except Exception as e:
            return "CONNECTIVITY_ERROR [%s]" % (str(e))
            
       
        
    def url_parse(self, app):
        ''' extract all information from an URL '''
        uparse = urlparse(app)
        self.proto = uparse.scheme
        self.host = uparse.netloc
        self.port = uparse.port
        self.path = uparse.path
        self.query = uparse.query
        
        if  self.port == None and self.proto != None:
            if self.proto == 'https':   self.port = 443
            if self.proto == 'http':    self.port = 80
            
        if self.port != None and self.proto == None:
            if self.port == 80 or self.port == 8080:    self.proto = 'http'
            if self.port == 443 or self.port == 8443:    self.proto = 'https'
        

        

        
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

def usage():
    print "python genscan.py <plugin> <applications_file>"
    exit(1)





if __name__ == '__main__':
#     test_threads_n_plugins()

    if len(sys.argv) < 3:
        usage()
        
    # checking if pluing exists
    plugin = sys.argv[1]
    plugin_list = list_available_plugins()
    if plugin not in plugin_list:
        print '\ninvalid plugin [{0}], available options are: {1}\n\n'.format(plugin, plugin_list)
        exit(1)
    else:
        plugin_call = load_plugin(plugin)
        
    # checking if apps file is existent
    apps_file = sys.argv[2]
    if not os.path.isfile(apps_file):
        print '\ninvalid/non-existing  file [apps_file]\n\n'
        exit(1)
    
    
        
    
    
    thread_pool = GS_ThreadPool(config['thread_numbers'])

    
    
    #reading apps file  and launching
    for app in open(apps_file).read().splitlines():
        if len(app) > 2 : thread_pool.add_task(plugin_call, app)
        
    thread_pool.wait_completion()

    


   
