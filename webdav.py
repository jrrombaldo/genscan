'''
Created on 3 Apr 2017
@author: Carlos Rombaldo Jr
'''


import argparse
import os.path
import socket
import requests
from requests import exceptions
from urlparse import urlparse


_timeout_read       = 15
_timeout_connect    = 5 # time to open the connection
_socket_timeout     =2  # test if port is enabled


interesting_headers = ('server', 'allow')
propfind_paylod = '<?xml version="1.0"?>\r\n<a:propfind xmlns:a="DAV:">\r\n<a:prop><a:getcontenttype/></a:prop>\r\n<a:prop><a:getcontentlength/></a:prop>\r\n</a:propfind>'
propfind_headers = {'Content-Type': 'text/xml', 'Depth': '0', 'Translate': 'f', }

output_format = '{code:}|{method:}|{app:}|{port:}|{status_code:}|{status_msg:}|{vulnerable:}|{banner:}|{allowed_methods:}|{error_details:}'

session = requests.Session()

# disable SSL messages: InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised.
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # @UndefinedVariable




class Validation(object):
    
    def __init__(self, addr, port, debug, proxy):
        self.addr = addr
        self.debug = debug
        self.port = port
        
        if proxy:
            self.proxy = {'https':'https://'+proxy, 'http':'http://'+proxy}
        else:
            self.proxy = None
        
        if port == 443:
            self.url = 'HTTPS://{}:{}'.format(addr, port)
            
        if port == 80:
            self.url = 'HTTP://{}:{}'.format(addr, port)
            
            
            
    def test_connectiviy(self):
        try:
            socket.gethostbyname_ex((self.addr))
        except socket.gaierror:
            return "ERR_DNS"
    
        s = socket.socket()
        s.settimeout(_socket_timeout)
        result = s.connect_ex((self.addr, self.port))
        
        if result == 0:
            return 'OK'
        else:
            return 'ERR_PORT_CLOSED'
    #         import errno
    #         print errno.errorcode[result]
    
    
    def url_parse(self):
        uparse = urlparse(self.app)
        self.proto = uparse.scheme
        self.host =  uparse.netloc
        self.port =  uparse.port
        
        if  self.port == None and self.proto != None:
            if self.proto == 'https':   self.port = 443
            if self.proto == 'http':    self.port = 80
            
        if self.port != None and self.proto == None:
            if self.port == 80 or self.port == 8080:    self.proto = 'http'
            if self.port == 443 or self.port == 8443:    self.proto = 'https'


    def print_headers(self, resp):     
        vulnerable = ''
        if  resp.status_code == 207:
            vulnerable = 'VULNERABLE'
        
        banner = ''
        if 'server' in resp.headers:
            banner = resp.headers['server']
        
        allow = ''
        if 'allow' in resp.headers:
            allow = resp.headers['allow']
        
        self.do_output(code='OK', method=resp.request.method, status_code=resp.status_code, 
                       status_msg=resp.reason, vulnerable=vulnerable, banner=banner, 
                       allowed_methods=allow, error_details='')
            
#     #     print '\n'.join('{}: {}'.format(k, v) for k, v in resp.headers.items())
#         if type(resp) == requests.Response:
#             print '{0:<10} {1:} {2:}\r\n\t{3:} - {4:}'.format(resp.request.method, resp.url, vulnerable, resp.status_code, resp.reason)
#         
#         for k, v in resp.headers.items():
#             if str(k).lower() in interesting_headers:
#                 print '\t{}: {}'.format(k, v)
#          
               
    
    def print_error(self, error, exp):
#         print  '{0:<10}  {1:}  {2:}'.format(error, self.url, exp)
        self.do_output(code=error, error_details=exp)
    
    
    def do_output(self, code='', method='', status_code='', status_msg='', vulnerable='', banner='', allowed_methods='', error_details=''):
        print output_format.format(app=self.addr, port=self.port, code=code, method=method, status_code=status_code, 
                             status_msg=status_msg, vulnerable= vulnerable, banner=banner, allowed_methods=allowed_methods, error_details= error_details)



    def execute(self, method, data='', headers=''):
        req = requests.Request(method, self.url, headers=headers, data=data)
        prepped = req.prepare()
        
        if bool(self.proxy):
            return session.send(prepped, allow_redirects=True, timeout=(_timeout_read, _timeout_connect), verify=False, proxies=self.proxy)
        else:
            return session.send(prepped, allow_redirects=True, timeout=(_timeout_read, _timeout_connect), verify=False)
    
    
    
    def validate(self):
        try:
            addr_status = self.test_connectiviy()

            if not addr_status == 'OK':
                self.print_error(addr_status, '')
            else:
                resp = self.execute("OPTIONS")
                self.print_headers(resp)
                 
                 
                resp = self.execute('PROPFIND',  propfind_paylod, propfind_headers)
                self.print_headers(resp)
                
        except exceptions.ProxyError as exp:
            self.print_error('ERR_TIMEDOUT', exp)       
        except exceptions.SSLError as exp:
            self.print_error( 'ERR_SSL', exp)
        except (exceptions.Timeout , exceptions.ConnectTimeout , exceptions.ReadTimeout) as exp:
            self.print_error( 'ERR_TIMEDOUT', exp)            
        except (exceptions.URLRequired , exceptions.MissingSchema , exceptions.InvalidSchema, exceptions.InvalidURL) as exp:
            self.print_error( 'ERR_INVALID_URL', exp)
        except exceptions.ConnectionError as exp:
            self.print_error( 'ERR_CONNECT', exp)
        except exceptions.RequestException as exp:
            self.print_error( 'ERR_REQ', exp)
        except Exception as exp:
            self.print_error( 'ERR_GENERIC', exp)
                    



# Instantiate the parser
parser = argparse.ArgumentParser(
    description='Scan multiple applications by probing them and printing their responses. At this time, it will consider only ports 80 and 443 (independently) for each application.',
     epilog='Note: This script is set to following server redirections, in case a status code 301/302 is received from server, the new URL will be used.')
# Required positional argument
parser.add_argument('apps_file', type=str, 
                    help='A text file containing all targeted applications. One application per line')
# Optional positional argument
parser.add_argument('-thread', action='store_true',
                    help='Executes the scan in multiple threads in order to reduce the execution time (NOT IMPLEMENTED)')
parser.add_argument('-proxy', type=str,
                    help='A proxy can be specified, so that all connections can be trapped and monitored. This will come handy on trouble shooting scenarios. An example of proxy is 127.0.0.1:80')

parser.add_argument('-debug', action='store_true',
                    help='Increase the out level, printing all request and response headers, as well the https response body.')


args = parser.parse_args()


if not os.path.exists(args.apps_file):
    parser.error("Can not read {}".format(args.apps_file))


with open(args.apps_file) as f:
    app_list = f.read().splitlines()
        
    print "OUTPUT Format:"
    print output_format.format(code=' Execution code ', method=' HTTP method ', app=' Application ', port=' Port ',
                               status_code=' HTTP Status Code ', status_msg=' HTTP Status Message ', vulnerable=' If Vulnerable ',
                               banner = ' Server Banner ', allowed_methods = ' HTTP allowed methods ', error_details=' Error Details ')
                               
                               
    for app in app_list:
        if not str(app).startswith("#") and len(app) > 3:
            print '-'*72
            Validation(app, 80, args.debug, args.proxy).validate()
            Validation(app, 443, args.debug, args.proxy).validate()

