'''
Created on 24 Jul 2017

@author: junior
'''

from GenScan import BasePlugin
import random

class WebDav(BasePlugin):
    def validate(self, app):
        result =  random.randint(0,2)
        
        self.process_result(app, result)
