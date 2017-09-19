'''
Created on 24 Jul 2017

@author: Jr.Rombaldo
'''

import time
import random

from GenScan import BasePlugin

class Inside (BasePlugin):
    def validate(self, app):
        time.sleep(random.uniform(0.2, 2.0))
        
        result =  random.randint(0,2)
        
        self.process_result(app, result)
    
