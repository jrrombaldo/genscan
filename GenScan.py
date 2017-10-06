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
import argparse


# disable SSL messages: InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised.
from requests.packages.urllib3.exceptions import InsecureRequestWarning  # @UnresolvedImport
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # @UndefinedVariable



#############
#######  GLOBALCONFIGURATION SECTION
#############

_config = {
    'line_size'                 : 1,
    'result_format'             : '{app:25} -> {result}',
    'logging_level'             : logging.INFO,
#     'logging_format'            : '%(asctime)s   %(levelname)-8s %(message)s',
    'logging_format'            : '%(message)s',
    'plugin_directory'          : './plugins',

    'proxy'                     : None,        
    'follow_redirection'        : True,
    'verify_ssl_server_cert'    : False,
    'socket_timeout'            : 5,  # timeout in seconds that the program will wait to open a connection
    'http_timeout'              : 5,
    'thread_numbers'            : 150,
    
    'jason_output'              : False,
    }



#############
#######  LOGGING CONFIGURATION
#############

logging.basicConfig(format=_config['logging_format'], level=_config['logging_level'], stream=sys.stdout)

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
                safeOutput( 'thread error: [%s]' % e,  logging.ERROR)
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
    for pl in os.listdir(_config['plugin_directory']): 
        if pl.find('.py') > 0 and pl.find('.pyc') < 1 and pl != '__init__.py': 
            plugins_array.append(pl.replace('.py', ''))
    return plugins_array
    


class BasePlugin (object):
    
    def validate(self, app):
        """ >>> TO BE IMPLEMENTED <<<"""
        
        
    def output(self, msg):
        if _config['jason_output']:
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
            s.settimeout(_config['socket_timeout'])
            result = s.connect_ex((host, port))
            if result == 0: return 'OK'
            else: return 'ERROR_CODE=[%s] ERROR_MSG=[%s] ' % (str(result), errno.errorcode[result])
        except Exception as e:
            return "CONNECTIVITY_ERROR [%s]" % (str(e))
       
        
    def request(self, http_method, url, headers=None, files=None, data={}, params={}, auth=None, cookies=None,  redirect=False,  hooks=None, config=None, _poolmanager=None, session=None):
        """
        execute the request following the interface defined at: http://docs.python-requests.org/en/v0.10.6/api/#main-interface
        """
        return requests.request(method=http_method, url=url, 
                        headers=headers, 
                         files=files, 
                         data=data, 
                         params=params, 
                         auth=auth, 
                         cookies=cookies, 
                         timeout=_config['http_timeout'], 
#                          redirect=redirect, 
                         allow_redirects=_config['follow_redirection'], 
                         proxies = _config['proxy'], 
                         hooks=hooks, 
#                          config=config, 
#                          _poolmanager=_poolmanager, 
                         verify=_config['verify_ssl_server_cert'], 
#                          session=session
                         )
            
       
        
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



def parse_cli_args():
    plugin_list = list_available_plugins()
     
    parser = argparse.ArgumentParser(
         description="\n\nGenScan aims to be an enterprise-level framework to support scan to support any validation/reconnaissance against a high number of web applications."
            "\nBecause it has performance and scalability in mind, it offers advanced thread-pooling techniques in addition to its pluggable code."
            "\nAny desired validation is achieved by creating a small plugin with the validation checks only. GenScan will be responsible for delivery this plugin to each target applications in a timely fashion.",
         
         epilog=" Currently, GenScan it is in development...",
         formatter_class=argparse.RawTextHelpFormatter)
    
    
    parser.add_argument('plugin',  choices=plugin_list, metavar='plugin', action='store', help='One of the available plugins: %s' % plugin_list)
    parser.add_argument('targets',  action='store', help='file containing applications to be scanned. One application per line.')
    
    formats = ['JSON', 'CSV', 'TXT']
    parser.add_argument('-t', "--threads",  type=int, default=_config['thread_numbers'], help='Number of concurrent threads, (default %s)' % _config['thread_numbers'], metavar='')
    parser.add_argument('-o', "--output",  choices=formats, help="Specify output format, default is JSON, validations are %s" % formats, metavar='')
    parser.add_argument("--disable-redirection", action='store_true', help="Speicify if genscan should or not follow a server redirection, normally status code 301/302. By default the script do not follows redirections")
    parser.add_argument('-p', "--proxy", action='store_true', help="Specify HTTP proxy to be used, the expected format is \"{'http': 'localhost:9999', 'https': 'localhost:9999'}\" ")
    
    args = parser.parse_args()
    
    _config['thread_numbers']       = int(args.threads)
    target                          = args.targets
    plugin                          = args.plugin
    _config['proxy ']               = args.proxy
    _config['disable_redirection']  = args.disable_redirection
    _config['output_format']        = args.threads
    
    # checking if target file is existent
    if not os.path.isfile(target):
        print '\ninvalid/non-existing  file [apps_file]\n\n'
        exit(1)
    
    return target, plugin


if __name__ == '__main__':
    target_file, plugin = parse_cli_args()
    
    plugin_call = load_plugin(plugin)

    thread_pool = GS_ThreadPool(_config['thread_numbers'])
     
#    filling threadpool with apps at targets file
    for app in open(target_file).read().splitlines():
        if len(app) > 2 : thread_pool.add_task(plugin_call, app)
           
    thread_pool.wait_completion()
    
    
    
    
    
    


 


   
