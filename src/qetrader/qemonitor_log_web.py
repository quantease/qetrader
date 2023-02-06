#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  5 07:34:57 2022

@author: root
"""

#from datetime import datetime, timedelta
import pandas as pd
#import numpy as np
#from .qelogger import initTableLogger, logger,
from .qelogger import getLoggerPath
#from .qeglobal import getPlatform
import os
import platform


def get_qemonitor_log(user,password,mode):
    
    max_line = 5000
#     current_line = 0    
    log_path = getLoggerPath()
    if mode == 'real':  
        filename = f'{log_path}/qelog_real_{user}'           
    elif mode == 'simu':
        filename = f'{log_path}/qelog_{user}'
    if platform.system().lower() == 'windows':
        filename = filename.replace('/','\\')
    #print(filename)
    pd.set_option('max_colwidth',180)
    if os.path.isfile(filename):
        #try:
        #    df = pd.read_csv(filename,sep='/n',header=None,memory_map=True)  
        #    print('readfile')
        #    #LT = len(df)
        #except:
        #    try:
        #        df = pd.read_csv(filename,sep='/n',header=None,memory_map=True,encoding='GB18030')
        #    except:
        #        print('empty')
        #        return pd.DataFrame()
        #    
        #
        #logdata = df[-max_line:]
        try:
            with open(filename,'r') as f:
                data = f.readlines()
            data = data[-max_line:]
            data = [line.replace('\n','') for line in data]
            logdata = pd.DataFrame(index=range(len(data)),data=data,columns=['日志'])
            #logdata = logdata.sort_index(ascending=False)
            #print(logdata[:10])
        except:
            logdata = pd.DataFrame()
        #logdata = logdata[-max_line:]
    else:
        logdata = pd.DataFrame()

    return logdata
            
    
