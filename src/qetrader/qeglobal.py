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
    ticksize = {'AG':1,'CU':10,'AL':5,'HC':1,'RB':1,'PB':5,'NI':10,'RU':5,'AU':0.05,'ZN':5,'BU':2,'FU':1,'SP':2,'SN':10,
					  'A':1,'B':1,'C':1,'M':1,'Y':2,'P':2,'L':5,'V':5,'J':0.5,'JM':0.5,'I':0.5,'JD':1,'FB':0.5,'BB':0.05,'PP':1,'CS':1,'EG':1,'RR':1,'EB':1,'PG':1,'LH':5,
					  'PM':1,'WH':1,'SR':1,'CF':5,'TA':2,'OI':1,'RI':1,'MA':1,'FG':1,'RS':1,'RM':1,'ZC':0.2,'JR':1,'LR':1,'SF':2,'SM':2,'CY':5,'AP':1,'CJ':5,'UR':1,'SA':1,'PF':2,'PK':2,
					  'SC':0.1,'LU':1,'NR':5,'BC':5,
					  'IF':0.2,'IC':0.2,'IH':0.2,'IM':0.2,'SI':5}
    getProd = lambda x: x[0] if x[1].isdigit() else x[:2]
    return ticksize.get(getProd(instid),1)


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
    

def get_riskctl_paras():
    return get_risk_control_parameter()

def getPlatform():
    return platform.system().lower()



def getProdTime(instid):
    prodTimes = {'A': {'morning': ['', ''], 'night': ['2100', '2300']},
             'AG': {'morning': ['0000', '0230'], 'night': ['2100', '2359']},
             'AL': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'AP': {'morning': ['', ''], 'night': ['', '']},
             'AO': {'morning': ['', ''], 'night': ['', '']},
             'AU': {'morning': ['0000', '0230'], 'night': ['2100', '2359']},
             'B': {'morning': ['', ''], 'night': ['2100', '2300']}, 'BB': {'morning': ['', ''], 'night': ['', '']},
             'BC': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'BU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'C': {'morning': ['', ''], 'night': ['2100', '2300']},
             'CF': {'morning': ['', ''], 'night': ['2100', '2300']}, 'CJ': {'morning': ['', ''], 'night': ['', '']},
             'CS': {'morning': ['', ''], 'night': ['2100', '2300']},
             'CU': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'CY': {'morning': ['', ''], 'night': ['2100', '2300']},
             'EB': {'morning': ['', ''], 'night': ['2100', '2300']},
             'EG': {'morning': ['', ''], 'night': ['2100', '2300']}, 'FB': {'morning': ['', ''], 'night': ['', '']},
             'FG': {'morning': ['', ''], 'night': ['2100', '2300']},
             'FU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'HC': {'morning': ['', ''], 'night': ['2100', '2300']},
             'I': {'morning': ['', ''], 'night': ['2100', '2300']}, 'IC': {'morning': ['', ''], 'night': ['', '']},
             'IO': {'morning': ['', ''], 'night': ['', '']}, 'IF': {'morning': ['', ''], 'night': ['', '']},
             'MO': {'morning': ['', ''], 'night': ['', '']}, 'IM': {'morning': ['', ''], 'night': ['', '']},
             'HO': {'morning': ['', ''], 'night': ['', '']}, 'IH': {'morning': ['', ''], 'night': ['', '']},
             'J': {'morning': ['', ''], 'night': ['2100', '2300']},
             'JD': {'morning': ['', ''], 'night': ['', '']}, 'JM': {'morning': ['', ''], 'night': ['2100', '2300']},
             'JR': {'morning': ['', ''], 'night': ['', '']}, 'L': {'morning': ['', ''], 'night': ['2100', '2300']},
             'LH': {'morning': ['', ''], 'night': ['', '']}, 'LR': {'morning': ['', ''], 'night': ['', '']},
             'LU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'M': {'morning': ['', ''], 'night': ['2100', '2300']},
             'MA': {'morning': ['', ''], 'night': ['2100', '2300']},
             'NI': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'NR': {'morning': ['', ''], 'night': ['2100', '2300']},
             'OI': {'morning': ['', ''], 'night': ['2100', '2300']},
             'P': {'morning': ['', ''], 'night': ['2100', '2300']},
             'PB': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'PF': {'morning': ['', ''], 'night': ['2100', '2300']},
             'PG': {'morning': ['', ''], 'night': ['2100', '2300']}, 'PK': {'morning': ['', ''], 'night': ['', '']},
             'PM': {'morning': ['', ''], 'night': ['', '']}, 'PP': {'morning': ['', ''], 'night': ['2100', '2300']},
             'RB': {'morning': ['', ''], 'night': ['2100', '2300']}, 'RI': {'morning': ['', ''], 'night': ['', '']},
             'RM': {'morning': ['', ''], 'night': ['2100', '2300']},
             'RR': {'morning': ['', ''], 'night': ['2100', '2300']}, 'RS': {'morning': ['', ''], 'night': ['', '']},
             'RU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SA': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SC': {'morning': ['0000', '0230'], 'night': ['2100', '2359']},
             'SF': {'morning': ['', ''], 'night': ['', '']}, 'SM': {'morning': ['', ''], 'night': ['', '']},
             'SN': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'SP': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SR': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SS': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'T': {'morning': ['', ''], 'night': ['', '']},
             'TA': {'morning': ['', ''], 'night': ['2100', '2300']},
             'TF': {'morning': ['', ''], 'night': ['', '']},
             'TL': {'morning': ['', ''], 'night': ['', '']},
             'TS': {'morning': ['', ''], 'night': ['', '']}, 
             'UR': {'morning': ['', ''], 'night': ['', '']},
             'V': {'morning': ['', ''], 'night': ['2100', '2300']}, 'WH': {'morning': ['', ''], 'night': ['', '']},
             'WR': {'morning': ['', ''], 'night': ['', '']}, 'Y': {'morning': ['', ''], 'night': ['2100', '2300']},
             'ZC': {'morning': ['', ''], 'night': ['2100', '2300']},
             'ZN': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'SGE': {'morning': ['0000', '0230'], 'night': ['2000', '2359']},
             'SSE': {'morning': ['',''],'night':['','']},
             'SZE': {'morning':['',''],'night':['','']},
             'SI': {'morning': ['', ''], 'night': ['', '']},
             'ME': {'morning': ['', ''], 'night': ['2100', '2300']},
             'RO': {'morning': ['', ''], 'night': ['2100', '2300']}, 
             'TC': {'morning': ['', ''], 'night': ['2100', '2300']},
             'WS': {'morning': ['', ''], 'night': ['2100', '2300']},
             'ER': {'morning': ['', ''], 'night': ['2100', '2300']}}
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