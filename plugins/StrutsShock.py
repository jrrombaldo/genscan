'''
Created on 24 Jul 2017

@author: junior
'''
from GenScan import BasePlugin
import random

class StrutsShock(BasePlugin):
    def validate(self, app):
       
        result =  random.randint(0,2)
        self.output(app+' -> '+str(result))
        
#         self.process_result(result)