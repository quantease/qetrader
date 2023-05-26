# -*- coding: utf-8 -*-
"""
Created on Thu Dec  2 12:33:41 2021

@author: ScottStation
"""

import logging  # 引入logging模块
#import os.path
from logging.handlers import TimedRotatingFileHandler 
import time
import os
import datetime
from .qeglobal import getExemode, getPlatform

# 第一步，创建一个logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Log等级总开关
# 第二步，创建一个handler，用于写入日志文件

try:
    from .qedockerconfig import log_path
    logger_path = log_path
except:
    logger_path = os.path.abspath(os.path.dirname(__file__))
    logger_path = logger_path +'/qelog' if getPlatform()=='linux' else logger_path +'\\qelog'
    connector = '/' if getPlatform()=='linux' else '\\'


def getLoggerPath():
    return logger_path

def initBacktestLogger(printlog=True):
    global logger
    #rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
    #log_path = os.path.dirname(os.getcwd())
    #log_name = 'log'+rq + '.txt'
    #logfile = log_name
    #fh = logging.FileHandler(logfile, mode='w')
    if not os.path.exists(logger_path):
        os.mkdir(logger_path)
    
    fh = TimedRotatingFileHandler(filename=f"{logger_path}{connector}backtestLog", when="D", interval=1, backupCount=5)
    fh.setLevel(logging.DEBUG)  # 输出到file的log等级的开关
    ch = logging.StreamHandler()
    if printlog:
        ch.setLevel(logging.WARNING)  # 输出到console的log等级的开关
        logging.captureWarnings(True)
    else:
        ch.setLevel(logging.CRITICAL)  # 输出到console的log等级的开关
        logging.captureWarnings(False)
    # 第三步，定义handler的输出格式
    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    formatter.converter = lambda *args: datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8))).timetuple()
    fh.setFormatter(formatter)
    # 第四步，将logger添加到handler里面
    logger.addHandler(fh)
    ch.setFormatter(formatter)
    logger.addHandler(ch)




def initLogger(userid,real=False, printlog=True):
    global logger
    #rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
    #log_path = os.path.dirname(os.getcwd())
    #log_name = 'log'+rq + '.txt'
    #logfile = log_name
    #fh = logging.FileHandler(logfile, mode='w')
    if not os.path.exists(logger_path):
        os.mkdir(logger_path)
    try:

        if real:
            #if os.path.isfile("/var/log/qelog/qelog_real_"+str(userid)):
            #    os.system('rm -f /var/log/qelog/qelog_real_'+str(userid))
            
            fh = TimedRotatingFileHandler(filename=f'{logger_path}{connector}qelog_real_{str(userid)}', when="D", interval=1, backupCount=5)
        else:
            #if os.path.isfile("/var/log/qelog/qelog_"+str(userid)):
            #    os.system('rm -f /var/log/qelog/qelog_'+str(userid))
            fh = TimedRotatingFileHandler(filename=f'{logger_path}{connector}qelog_{str(userid)}', when="D", interval=1, backupCount=5)
        
          
    except Exception as e:
        logger.error('qelogger '+str(e),exc_info=True) 

    fh.setLevel(logging.DEBUG)  # 输出到file的log等级的开关
    ch = logging.StreamHandler()
    if printlog:
        ch.setLevel(logging.WARNING)  # 输出到console的log等级的开关
        logging.captureWarnings(True)
    else:
        ch.setLevel(logging.CRITICAL)  # 输出到console的log等级的开关
        logging.captureWarnings(False)

    # 第三步，定义handler的输出格式
    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    formatter.converter = lambda *args: datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8))).timetuple()
    fh.setFormatter(formatter)
    # 第四步，将logger添加到handler里面
    logger.addHandler(fh)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

   
def initTableLogger():    
    global logger
    #rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
    #log_path = os.path.dirname(os.getcwd())
    #log_name = 'log'+rq + '.txt'
    #logfile = log_name
    #fh = logging.FileHandler(logfile, mode='w')
    if not os.path.exists(logger_path):
        os.mkdir(logger_path)
    fh = TimedRotatingFileHandler(filename=f"{logger_path}{connector}tabLog", when="D", interval=1, backupCount=5)
    fh.setLevel(logging.DEBUG)  # 输出到file的log等级的开关
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)  # 输出到console的log等级的开关
    logging.captureWarnings(True)
    # 第三步，定义handler的输出格式
    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    formatter.converter = lambda *args: datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8))).timetuple()
    fh.setFormatter(formatter)
    # 第四步，将logger添加到handler里面
    logger.addHandler(fh)
    ch.setFormatter(formatter)
    logger.addHandler(ch)



if __name__ == '__main__':
    initLogger()
    logger.warning(u"只是")
    try:
        open('/path/to/does/not/exist', 'rb')
    except Exception as e:
        logger.error(f'Failed to open file {e}',exc_info=True)
        
    