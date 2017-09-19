'''
Created on 24 Jul 2017

@author: Jr.Rombaldo
'''


from GenScan import BasePlugin
import requests

# extracted from https://www.owasp.org/index.php/OWASP_Secure_Headers_Project#tab=Headers
headers = [
    'Allow',
    'Public',
    'Server',
    'X-Powered-B',
    'Strict-Transport-Security',
    'Public-Key-Pins',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'Content-Security-Policy',
    'X-Permitted-Cross-Domain-Policies',
    'Referrer-Policy',
    'Authentication',
    'Proxy-Authenticate',
    'X-Pingback',
    'X-Forwarded-For',
    'Connection',
     ]

class Recon (BasePlugin):
    def validate(self, app): 
        result = {}
        
        if not str(app).lower().startswith("http"):
            self.validate("https://"+app)
            app = "http://"+app
        try:
            result['app']               = app
            self.url_parse(app)
           
            result['connectivity_test'] = self.test_connectiviy(self.host, self.port)
            
            response = requests.options(app, timeout=10, verify=False)
            result['all_headers']       = response.headers
            result['important_headers'] = self.extract_headers(response)
            result['req_url']           = response.request.url         
            result['req_method']        = response.request.method         
            result['status_code']       = response.status_code
            result['request_status']    = 'SUCCESS'
            
            result['proto']             = self.proto
            result['host']              = self.host
            result['port']              = self.port
            result['path']              = self.path
            result['query_string']      = self.query
                 

        except Exception as e:
            result['request_status']        = 'ERROR'
            result['request_error_details'] =   str(e)

        self.output(result)
        return result
        
    def extract_headers(self, response):
        headers_found = {}
        for header in headers:
            if header in response.headers: headers_found[header] = response.headers[header]
        return headers_found
    

        
        
if __name__ == '__main__':
    r = Recon()
    r.validate('https://uol.com/')
    

    
