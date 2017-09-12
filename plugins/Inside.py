'''
Created on 24 Jul 2017

@author: junior
'''

import time
import random

from CJ_Framework import BasePlugin

class Inside (BasePlugin):
    def validate(self, app):
        time.sleep(random.uniform(0.2, 2.0))
        
        result =  random.randint(0,2)
        
        self.process_result(app, result)
    
