# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 15:24:34 2022

@author: ScottStation
"""
import threading
from multiprocessing import Queue
from qesdk import  get_instrument_setting
import platform
from datetime import datetime 
import chinese_calendar

dbconfig = {'ip': '103.36.172.183','port': 58888, 'local':'127.0.0.1'};
try:
    from .qedbconfig import dbconfig_outside
    dbconfig = {**dbconfig, **dbconfig_outside}
except:
    pass




mutex = threading.Lock()
import collections
class qeInstSett(collections.UserDict):
    def __missing__(self, key):
        key = str(key)
        if not key in self.data:
            cursett = get_instrument_setting(key)
            #print(cursett)
            if cursett is None:
                raise KeyError
            else:    
                self.data[key] = cursett    
                return cursett    
        return self.data[key]
 
    def __contains__(self, key):
        return str(key) in self.data
 
    def __setitem__(self, key, item):
        self.data[str(key)] = item
    
    def __getitem__(self, key):
        key = str(key)
        if not key in self.data:
            cursett = get_instrument_setting(key)
            #print(cursett)
            if cursett is None:
                raise KeyError
            else:    
                self.data[key] = cursett    
                return cursett    
        return self.data[key]
        
## qeglobal.py
instSetts = qeInstSett()

class globalInfo(object):
    def __init__(self):
        self.info_time_all=0
        self.info_time_new=0
        self.first_t={}

g_tradingdaySaved = False

def setTradingDaySaved(flag):
    global g_tradingdaySaved
    mutex.acquire()
    g_tradingdaySaved = flag
    mutex.release()

def getTradingDaySaved():
    return g_tradingdaySaved
        

g_positionLoaded = False
def setPositionLoaded():
    global g_positionLoaded
    g_positionLoaded = True

def getPositionLoaded():
    global g_positionLoaded
    return g_positionLoaded
        

g_userinfo = globalInfo()  



#def getValidInstIDs(instids):
#    return [getValidInstID(inst) for inst in instids]
        
realQueues = {}
mapClassIDs = {}

def getAccidTraderQueue(accid):
    global realQueues
    #classname = getInstClass(instid)
    if not accid in realQueues:
        realQueues[accid] = Queue()
    return realQueues[accid]

def getInstTraderQueue(instid):
    queues = []
    accids  = getInstAccID(instid)
    for acc in accids:
        queues.append(getAccidTraderQueue(acc))
    return queues


def getClassInstIDs(instIDs, classnames):
    insts = []
    for inst in instIDs:
        if getInstClass(inst) in classnames:
            insts.append(inst)
    return insts        


def setClassAccID(classname, accid):
    global mapClassIDs
    if not classname in mapClassIDs:
        mapClassIDs[classname] = [accid]
    else:
        mapClassIDs[classname].append(accid)

def getInstAccID(instid):
    classname = getInstClass(instid)
    return getClassAccID(classname)
    
def getClassAccID(classname):
    global mapClassIDs
    if classname in mapClassIDs:
        return mapClassIDs[classname]
    else:
        return [0]


def getInstClass(instid):
    if instid[-3:] =='SSE':
        if len(instid) == 10:
            return 'stock'
        else:
            return 'stockoption'
    elif instid[-3:] == 'SGE':
        return 'gold'
    else:
        return 'future'
    
import importlib
def import_source(name, path):
     module_file_path = path
     module_name = name
      
     module_spec = importlib.util.spec_from_file_location(module_name,module_file_path)
     module = importlib.util.module_from_spec(module_spec)
     module_spec.loader.exec_module(module)
     return module    
     
def getExemode():
    try:
        from .execonfig import get_exe_mode
        #print('exemode', get_exe_mode())
        return get_exe_mode()
    except:
        return False


def is_trade_day(date):
    try:
        assert isinstance(date, datetime), 'date must be instance of datetime'
        if date.weekday() > 4:
            return False
        else:
            return chinese_calendar.is_workday(date)
    except Exception as e:
        print('is_trade_day Error:',e)
        
        
#def is_future_expired(instid):
#    getym = lambda x : '20'+x[1:3]+'-'+x[3:5] if x[1].isdigit() else '20'+x[2:4]+'-'+x[4:6]
#    ym = getym(instid)
#    curdate = datetime.today().strftime('%Y-%m-%d')
#    curym = curdate[:7]
#    if curym < ym:
#        #print(ym,curym)
#        return False
#    elif curym == ym:
#        df = get_future_details(instid, expire=curym)
#        if not df.empty:
#            #print(df)
#            return curdate >= df['expire'].iloc[0]
#        else:
#            #print(df)
#            return False
#    else:
#        return True


def get_Instrument_volmult(instid):
    volmult = {'AG':15,'CU':5,'AL':5,'HC':10,'RB':10,'PB':5,'NI':1,'RU':10,'AU':1000,
                'ZN':5,'BU':10,'FU':10,'SP':10,'SN':1,
              'A':10,'B':10,'C':10,'M':10,'Y':10,'P':10,'L':5,'V':5,'J':100,'JM':60,'I':100,'JD':10,'FB':10,'BB':500,'PP':5,'CS':10,'EG':10,'RR':10,'EB':5,'PG':20,'LH':16,
              'PM':50,'WH':20,'SR':10,'CF':5,'TA':5,'OI':10,'RI':20,'MA':10,'FG':20,'RS':10,'RM':10,'ZC':100,'JR':20,'LR':20,'SF':5,'SM':5,'CY':5,'AP':10,'CJ':5,'UR':20,'SA':20,'PF':5,'PK':5,
              'SC':1000,'LU':10,'NR':10,'BC':10,
              'IF':300,'IC':200,'IH':300,'IM':200}  
    getProd = lambda x: x[0] if x[1].isdigit() else x[:2]
    return volmult.get(getProd(instid),1)


def getInstrumentSetting(instid):
    res = get_instrument_setting(instid, True)
    if res:
        return res
    else:
        return get_instrument_setting(instid, False)
    
    
def getPlatform():
    return platform.system().lower()