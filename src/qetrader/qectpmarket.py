# -*- coding: utf-8 -*-
"""
Created on Wed Oct 13 17:35:49 2021

@author: ScottStation
"""
import pyctp.thostmduserapi as ctpmdapi
from datetime import datetime, timedelta
import time
import json
#import os
from .qetype import qetype
import copy
import threading
from .qelogger import logger
from .qecontext import transInstID2Real,transInstID2Context
##from qesimtrader import marketReadyNotice
from .qeredisdb import saveMarketToDB, resetMarketData
from  pyctp.thostmduserapi import *
from .qestatistics import getPrevTradingDay
from .qeglobal import getInstTraderQueue, getInstClass,getClassInstIDs, import_source, getExemode,g_dataSlide
from .qeinterface import simuqueue
from qesdk import get_valid_instID
'''
以下为需要订阅行情的合约号，注意选择有效合约；
有效连上但没有行情可能是过期合约或者不再交易时间内导致
'''

#tqueue = None
mduserspi = None
timer = None
g_mode_724=False

def getLocalTradingDay(now):
    if now.hour < 19:
        return (now.strftime('%Y%m%d'))
    else:
        wday = now.weekday()
        days = 1 if wday != 4 else 3
        return ((now + timedelta(days=days)).strftime('%Y%m%d'))

def getValidPrice(price):
    return 0 if price > 100000000 else price
        


def timer_callback():
    global timer, mduserspi
    logger.debug('timer callback')
    now = datetime.now()
    if checkMarketTime(now) :
        '''if mduserspi and len(mduserspi.subID) > 0:
            subID = mduserspi.subID
            mduserspi.tapi.SubscribeMarketData([id.encode('utf-8') for id in subID],len(subID))
        else:
            print("No intrumentIDs be subscribed")
        '''
        if mduserspi and not mduserspi.bFirstLogin and not mduserspi.connected:
            mduserspi.login()    
    timer = threading.Timer(30, timer_callback)
    timer.start()
        
   
    
def checkMarketTime(now):
    global g_mode_724
    if g_mode_724:
        return True
    if (now.hour > 3 and now.hour < 8) or (now.hour >= 16 and now.hour <20) or (now.hour==8 and now.minute < 30) or (now.hour==20 and now.minute < 30) :
        return False
    elif now.weekday ==6 or (now.weekday==5 and now.hour > 3) or (now.weekday == 0 and now.hour < 8):
        return False
    return True 
  
def getMarketReady():
    global mduserspi
    
    if mduserspi:
        logger.info(mduserspi.bReady)
        return mduserspi.bReady
    else:
        logger.info('no mduserspi')
        return False

def changeCtpInstIDs(stratName, instIDs):
    global mduserspi
    return mduserspi.changeInstIDs(stratName, instIDs)

def marketLogout():
    global mduserspi
    mduserspi.logout()


'''
def md_register_strategy(stratName, strat):    
    global stratGroup, mduserspi, curInstSet ,instExIDs, subID  
    now = datetime.now()
    logger.info(f'register {stratName}')
    if not stratName in stratGroup:
        stratGroup[stratName] = strat
        curInstSet.update(strat.instid)
        instIDs = []
        for i in range(len(strat.instid_ex)):
            inst = strat.instid_ex[i]
#             print(inst)
            if not inst in subID:
                subID.append(inst)
                instIDs.append(inst)
            if not inst in instExIDs:
                instExIDs[inst] = strat.exID[i]
        if len(instIDs) > 0:
            before_time = getPrevTradingDay(now) + '160000000'    
            for inst in instIDs:
                resetMarketData(inst, before_time)
            if mduserspi:
                mduserspi.SubscribeMarketData(instIDs)
                print("subscribe ", instIDs)
            else:
                logger.info('mduserspi is not ready')
            
            #time.sleep(1)    
'''

       

# def on_data_callback(ctime, instid, mdata):
#     global stratGroup
#     datastr = json.dumps(mdata)
#     for key in stratGroup.keys():
#         if instid in stratGroup[key][0]:
            
#             stratGroup[key][1].put('mdata$$'+instid+'$$'+datastr)
#     print('callback', instid, time)
#     saveMarketToDB(instid, ctime, datastr )
    

def runQEMarketProcess(user, passwd, strats,runmode, setting_dict, mode_724=False):
    global mduserspi, g_mode_724,timer
    evalmode = False
    if setting_dict is not None and setting_dict['api'] == 'ctptest':
        evalmode = True
    if getExemode():
        #import pyctp.thostmduserapi as mdapi
        #import pyctptest.thostmdusertestapi as testmdapi
        mdapi = ctpmdapi  #testmdapi if evalmode else ctpmdapi
    else:
        print('normal mode')
        if evalmode:
            mdapi = __import__('pyctp.thostmdusertestapi',fromlist=['a'])
        else:
            mdapi = __import__('pyctp.thostmduserapi',fromlist=['a'])
    
    mduserapi=mdapi.CThostFtdcMdApi_CreateFtdcMdApi()
    
    class CFtdcMdSpi(mdapi.CThostFtdcMdSpi):

        def __init__(self, tapi):
            mdapi.CThostFtdcMdSpi.__init__(self)
            self.tapi=tapi
            self.recmode = False
            self.bReady = False
            self.broker = ''
            self.address = ''
            self.connected = False
            self.strats = None
            self.runmode ='simu'
            self.subID=[] #["au2112",","rb2201","TA201"]
            self.curInstSet = set()
            self.instExIDs = {}
            self.instTime = {}
            self.tradingDay = ''
            self.stratInstances = {}
            self.bFirstLogin = True
            
        def initCallback(self, user, passwd):
            #self.callback = md_callback
            self.user = user
            self.passwd = passwd
       
        def OnFrontConnected(self) -> "void":
            print(u"ctp行情服务器连接成功")
            logger.info (u"ctp行情服务器连接成功")
            now = datetime.now()
            if checkMarketTime(now):
                self.login()
            
        def login(self):    
            loginfield = mdapi.CThostFtdcReqUserLoginField()
            loginfield.BrokerID=self.broker
            loginfield.UserID=self.user
            loginfield.Password=self.passwd
            loginfield.UserProductInfo="qe-pyctp" #"python dll"
            self.connected = True
            self.tapi.ReqUserLogin(loginfield,0)
            
        def logout(self):
            logoutfield = mdapi.CThostFtdcUserLogoutField()
            logoutfield.BrokerID = self.broker
            logoutfield.UserID = self.user
            self.tapi.ReqUserLogout(logoutfield,0)
        
        def OnFrontDisconnected(self, nReason: "int") -> "void":
            if self.connected:
                print(u"ctp行情服务器已经断开")
                logger.info(u"ctp行情服务器已经断开")
            self.connected = False    
            #if not timer is None and not timer.finished:
            #    timer.cancel()
            #    timer.join()
            
        def OnRspUserLogin(self, pRspUserLogin: 'CThostFtdcRspUserLoginField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
            #global tradingDay, instTime
            if pRspInfo.ErrorID == 0:
                logger.info (f"Market Data System Login, SessionID={pRspUserLogin.SessionID},ErrorID={pRspInfo.ErrorID},ErrorMsg={pRspInfo.ErrorMsg}")
            else:
                logger.error (f"Market Data System Login, SessionID={pRspUserLogin.SessionID},ErrorID={pRspInfo.ErrorID},ErrorMsg={pRspInfo.ErrorMsg}")
                
            self.bReady = True
            self.bFirstLogin = False
            #now = datetime.now()
            if pRspUserLogin.TradingDay != '':
                if self.tradingDay != pRspUserLogin.TradingDay:
                    if self.tradingDay != '':
                        self.instTime ={}
                    self.tradingDay = pRspUserLogin.TradingDay
            elif self.tradingDay == '':
                self.tradingDay = getLocalTradingDay(now)
            #if checkMarketTime(now):
            if len(self.subID) >0:
                time.sleep(1)
                ret = self.tapi.SubscribeMarketData([id.encode('utf-8') for id in self.subID],len(self.subID))
            
            
        def SubscribeMarketData(self,instIDs):
            logger.info(f'subscribe{instIDs}')
            ret=self.tapi.SubscribeMarketData([id.encode('utf-8') for id in instIDs],len(instIDs))
    
        def UnSubscribeMarketData(self,instIDs):
            logger.info(f'unsubscribe{instIDs}')
            ret=self.tapi.UnSubscribeMarketData([id.encode('utf-8') for id in instIDs],len(instIDs))
           
        def OnRtnDepthMarketData(self, pDepthMarketData: 'CThostFtdcDepthMarketDataField') -> "void":
            #global tradingDay, instTime
            instid = pDepthMarketData.InstrumentID
            
            
            ctime = int(pDepthMarketData.UpdateTime.replace(':',''))*1000+ pDepthMarketData.UpdateMillisec
            
            ## fix repeat time problem
            inc = 0
            if instid in self.instTime.keys() and ctime == self.instTime[instid]['time']:
                inc =  self.instTime[instid]['inc'] + 1
    
            self.instTime[instid] = {'time':ctime, 'inc':inc}
            
        
            ## DCE actionDay problem
            actionDay = str(pDepthMarketData.ActionDay)
    
            exID = self.instExIDs[instid] if instid in self.instExIDs else 'XXX'
            #print(instid, type(pDepthMarketData.ActionDay), actionDay=="", exID)
            if (exID == 'DCE' and ctime >= 210000000) or actionDay == "":
                actionDay = datetime.now().strftime('%Y%m%d')
            
            timedigit = int(actionDay)*1000000000 +(ctime+inc)
            timestr = (actionDay +' '+ pDepthMarketData.UpdateTime+'.'+str(pDepthMarketData.UpdateMillisec + 1000)[1:])
            qeinst = transInstID2Context(instid, exID)
            mddata={'tradingday':self.tradingDay,\
            'time': timestr,\
            'timedigit': timedigit,\
            'instid': qeinst,\
            'current': getValidPrice(pDepthMarketData.LastPrice),\
            'presett': getValidPrice(pDepthMarketData.PreSettlementPrice),\
            'preclose':getValidPrice(pDepthMarketData.PreClosePrice),\
            'open':getValidPrice(pDepthMarketData.OpenPrice),\
            'high':getValidPrice(pDepthMarketData.HighestPrice),\
            'low':getValidPrice(pDepthMarketData.LowestPrice),\
            'volume':pDepthMarketData.Volume,\
            'money':pDepthMarketData.Turnover,\
            'position':pDepthMarketData.OpenInterest,\
            #'close':pDepthMarketData.ClosePrice,\
            'upperlimit':getValidPrice(pDepthMarketData.UpperLimitPrice),\
            'lowerlimit':getValidPrice(pDepthMarketData.LowerLimitPrice),\
            'b1_p':getValidPrice(pDepthMarketData.BidPrice1),\
            'b1_v':pDepthMarketData.BidVolume1,\
            'a1_p':getValidPrice(pDepthMarketData.AskPrice1),\
            'a1_v':pDepthMarketData.AskVolume1,}
    #         if time.minute % 5 == 1:
            d = {}
            d['type'] = qetype.KEY_MARKET_DATA
    #         d['time'] = timedigit
            d['instid'] = qeinst
            d['data'] = mddata
            #print(d)
            self.callback(d)
            
        def OnRspSubMarketData(self, pSpecificInstrument: 'CThostFtdcSpecificInstrumentField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
            if pRspInfo.ErrorID == 0:
                logger.info(u"ctp行情订阅成功："+str(pSpecificInstrument.InstrumentID))
                print(u"ctp行情订阅成功："+str(pSpecificInstrument.InstrumentID))
            else:
                logger.error(f"Subscribe Failed id:{pRspInfo.ErrorID},instid:{pSpecificInstrument.InstrumentID},msg:{pRspInfo.ErrorMsg}")
        
        def OnRspUnSubMarketData(self, pSpecificInstrument: 'CThostFtdcSpecificInstrumentField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
            if pRspInfo.ErrorID == 0:
                logger.info(u"ctp行情退订成功："+str(pSpecificInstrument.InstrumentID))
                print(u"ctp行情退订成功："+str(pSpecificInstrument.InstrumentID))
            else:
                logger.error(f"UnSubscribe Failed id:{pRspInfo.ErrorID},instid:{pSpecificInstrument.InstrumentID},msg:{pRspInfo.ErrorMsg}")
        def callback(self, d):
            try:
            
                instSave = False
            
                if d['type'] == qetype.KEY_MARKET_DATA:
                    datastr = json.dumps(d['data'])
                    cd = copy.copy(d)
                    g_dataSlide.update([d])
                    if self.strats['async'] and self.recmode:
                        self.strats['queue'].put(cd)
                    elif self.stratInsts:
                        for key in self.stratInsts:
                            #print(d['instid'], key, stratGroup, stratGroup[key].instid)
                            
                            if key in self.stratInstances and (d['instid'] in self.stratInsts[key] or key =='csvorders'):  
                                #print('ctp', key, d['instid'])
                                strat = self.stratInstances[key]
                                if self.strats['async']:
                                    self.strats['queue'].put(cd)
                                else:
                                    self.strats[key]['queue'].put(cd)
                                if strat.datamode == 'tick':
                                    instSave = True
                            #print(d['instid'])
                            
            
                    #print('callback '+ d['instid'])
                    if instSave:
                        saveMarketToDB(d['instid'], d['data']['timedigit'], datastr )
                    if self.runmode == 'simu':
                        simuqueue.put(cd)
                    else:
                        queues = getInstTraderQueue(d['instid'])
                        for queue in queues:
                            queue.put(cd)
                        #print('put tequeue',d['data']['timedigit'])
                        
                else:
                    logger.error('incorrect type given as type is'+str(d['type']))
            except Exception as e:
                logger.error(f"CTP market callback error {e}",exc_info=True )  
                
            
        def register(self):
            #global curInstSet ,instExIDs, subID   
            now = datetime.now()
            logger.info('ctp market register')
            
            self.stratInsts = {}
            for name in self.stratInstances:
                self.stratInsts[name]=self.stratInstances[name].instid
            
            
            realInstSet =set()
            realInstSet.update(self.subID)
            for name in self.stratInsts:
                instid = self.stratInsts[name]
                insts = getClassInstIDs(instid, ['future'])
                self.curInstSet.update(insts)
                self.stratInsts[name] = insts
                realinsts, exids = transInstID2Real(insts)
                for i in range(len(realinsts)):
                    if not realinsts[i] in self.instExIDs:
                        self.instExIDs[realinsts[i]] = exids[i]
                
                realInstSet.update(realinsts)
            #print('ctp strats', self.stratInsts)
            if len(realInstSet) > len(self.subID):
                instIDs = []
                for rinst in realInstSet:
                    if not rinst in self.subID:
                        instIDs.append(rinst)
                #self.SubscribeMarketData(instIDs)
                before_time = getPrevTradingDay(now) + '160000000'    
                for inst in instIDs:
                    resetMarketData(inst, before_time)
                self.subID = list(realInstSet)
            
            if self.recmode:
                self.subID = [get_valid_instID('AU9999')[:6].lower(), get_valid_instID('TF9999')[:6], get_valid_instID('IF9999')[:6]]
            #print('ctp sub', self.subID)
                
        def changeInstIDs(self, name, instIDs):
            adds =[]
            removes = []
            #if name in self.strats:
            #    self.strats[name]['instid'] = instIDs
            if name in self.stratInsts:
                instIDs = getClassInstIDs(instIDs, ['future'])
                newSet = set()
                self.stratInsts[name] = instIDs
                #print(instIDs, name, self.stratInsts)
                for key in self.stratInsts:
                    newSet.update(self.stratInsts[key])
                for inst in newSet:
                    if not inst in self.curInstSet:
                        adds.append(inst)
                for inst in self.curInstSet:
                    if not inst in newSet:
                        removes.append(inst)
                self.curInstSet = newSet
                
                unsubs, exids = transInstID2Real(removes)
                for inst in unsubs:
                    if inst in self.subID:
                        self.subID.remove(inst)
                    if inst in self.instExIDs:
                        del self.instExIDs[inst]
                subs, exids = transInstID2Real(adds)
                for i in range(len(subs)):
                    self.subID.append(subs[i])
                    self.instExIDs[subs[i]] = exids[i]
                if not self.recmode:
                    if len(subs)> 0:
                        self.SubscribeMarketData(subs)
                    if len(unsubs) > 0:
                        self.UnSubscribeMarketData(unsubs)
                else:
                    self.subID = [get_valid_instID('AU9999')[:6].lower(), get_valid_instID('TF9999')[:6], get_valid_instID('IF9999')[:6]]
                #print('ctp adds',adds,'removes',removes)
                #print('ctp subs',subs,'unsubs',unsubs)
            return (adds, removes)

    
    mduserspi=CFtdcMdSpi(mduserapi)   
    mduserspi.strats = strats
    if strats['async']:    
        for s in strats['strat']:
            mduserspi.stratInstances [s.name] = s 
            
    else:
        for name in strats:
            if name != 'async':
                mduserspi.stratInstances[name] = strats[name]['strat']
    #mduserspi.recmode = True if strats['async'] and strats['recmode'] else False
    mduserspi.runmode = runmode
    mduserspi.initCallback(user,passwd) 
    mduserspi.register()
    g_mode_724 = mode_724

    pass_flag = True
    timer = threading.Timer(30, timer_callback)
    timer.start()

    if setting_dict is not None:
        mduserspi.investor = setting_dict['investorid']
        mduserspi.password = setting_dict['password']
        mduserspi.broker = setting_dict['brokerid']
        #print(setting_dict)
        address = setting_dict.get('mdaddress',-1)
        if address != -1:
            mduserapi.RegisterFront(address)
            #mduserspi.broker = broker
        else:
            print('user setting has error')
            pass_flag = False

    else:
        #mduserapi.RegisterFront("tcp://101.230.209.178:53313")
        '''
        ctptrader.investor = user_setting['investorid']
        ctptrader.password = user_setting['password']
        ctptrader.broker = user_setting['brokerid']
        ctptrader.address = user_setting['mdaddress']   
        '''
        #mduserapi.RegisterFront("tcp://61.183.150.151:41213")
        print(f"CTP API MD version = {mduserapi.GetApiVersion()}")
        mduserapi.RegisterFront("tcp://222.66.192.247:47213")
        mduserspi.broker = '4300'

    if pass_flag:
        mduserapi.RegisterSpi(mduserspi)  
        mduserspi.tapi.Init()    
        mduserspi.tapi.Join()
   


if __name__ == '__main__':
    runQEMarketProcess('scott','888888',None)