# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 15:24:34 2022

@author: ScottStation
"""
import threading
from multiprocessing import Queue
from qesdk import  get_instrument_setting, get_risk_control_parameter
import platform
from datetime import datetime 
import chinese_calendar
import collections
from .prodtables import prodTimes,ticksize,volmult

dbconfig = {'ip': 'data.quantease.store','port': 58888, 'local':'127.0.0.1'};
try:
    from .qedbconfig import dbconfig_outside
    dbconfig = {**dbconfig, **dbconfig_outside}
except:
    pass


class qeDataSlide(collections.UserDict):
    def __missing__(self, key):
        key = str(key)
        if not key in self.data:
            return {"current":0,"presett":0,"preclose":0}    
        return self.data[key]
 
    def __contains__(self, key):
        return str(key) in self.data
 
    def __setitem__(self, key, item):
        self.data[str(key)] = item
    
    def __getitem__(self, key):
        key = str(key)
        if not key in self.data:
            return {"current":0,"presett":0,"preclose":0}    
        return self.data[key]
    def update(self, datalist):
        for data in datalist:
            self.data[data['instid']] = data["data"]
g_dataSlide = qeDataSlide()


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
def get_Instrument_ticksize(instid):


    getProd = lambda x: x[0] if x[1].isdigit() else x[:2]
    return ticksize.get(getProd(instid),1)


def get_Instrument_volmult(instid):


    getProd = lambda x: x[0] if x[1].isdigit() else x[:2]
    return volmult.get(getProd(instid),1)


def getInstrumentSetting(instid):
    res = get_instrument_setting(instid, True)
    if res:
        return res
    else:
        return get_instrument_setting(instid, False)
    

def get_riskctl_paras():
    return get_risk_control_parameter()

def getPlatform():
    return platform.system().lower()



def getProdTime(instid):

    getProd = lambda x: x[0] if x[1].isdigit() else x[:2]
    prodid = getProd(instid).upper()
    exid = instid.split('.')[1].upper()
    if exid == 'SGE':
        prodid = 'SGE'
    res = {}
    if prodid in prodTimes.keys():
        pt = prodTimes[prodid]
        if pt['night'][0] == '':
            res['night'] = []
            res['morning'] = []
        elif pt['morning'][0] != '':
            res['night'] = [(pt['night'][0],'2359')]
            res['morning'] = [('0000',pt['morning'][1])]
        else:
            res['night'] = [(pt['night'][0],pt['night'][1])]
            res['morning'] = []
        if exid in ['CCF','SZE','SSE']:
            res['daytime'] = [('0930','1130')]
            res['daytime'] += [('1300', '1515')] if prodid[0] == 'T' else [('1300', '1500')]
        elif exid == 'SGE':
            res['daytime']= [('0900', '1500')]
        else:
            res['daytime'] = [('0900', '1015'),('1030', '1130'),('1330','1500')]
        return res
    else:
        return {}


def getProdOpenSeconds(timedict):
    #pt = getProdTime(instid)
    pt = timedict
    ret = {}
    today = datetime.today()
    for key in pt.keys():
        if len(pt[key]) == 0:
            ret[key] = [0]
            continue
        for tf in pt[key]:
            [start, end] = tf
            start = today.strftime('%Y%m%d') + start+'00'
            end = today.strftime('%Y%m%d') + end+'00'
            diff = (datetime.strptime(end, '%Y%m%d%H%M%S') - datetime.strptime(start, '%Y%m%d%H%M%S')).seconds
            if not key in ret.keys():
                ret[key] = [diff]
            else:
                ret[key].append(diff)
    return ret        
    #print('dataSlide',dataSlide)    