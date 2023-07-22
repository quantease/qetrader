# -*- coding: utf-8 -*-
"""
Created on Wed Oct 13 17:35:49 2021

@author: ScottStation
"""
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
from .qestatistics import getPrevTradingDay
from .qeglobal import getInstTraderQueue, getClassInstIDs
from .qeinterface import simuqueue
from qesdk import get_valid_instID
from .qeglobal import g_dataSlide
'''
以下为需要订阅行情的合约号，注意选择有效合约；
有效连上但没有行情可能是过期合约或者不再交易时间内导致
'''

import typing
from typing import Optional

from ctpwrapper.ApiStructure import (FensUserInfoField, UserLogoutField,
                                     ReqUserLoginField, QryMulticastInstrumentField)
from ctpwrapper.MdApi import MdApiWrapper


str2bytes = lambda x:bytes(x,'utf-8')

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
    
class CFtdcMdSpi(MdApiWrapper):
    def Create(self, pszFlowPath: Optional[str] = "",
               bIsUsingUdp: Optional[bool] = False,
               bIsMulticast: Optional[bool] = False) -> None:
        """
        创建MdApi
        :param pszFlowPath: 存贮订阅信息文件的目录，默认为当前目录
        :param bIsUsingUdp:
        :param bIsMulticast:
        """
        super(CFtdcMdSpi, self).Create(pszFlowPath.encode(), bIsUsingUdp, bIsMulticast)

    def __init__(self)->None:
        #self.tapi=tapi
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

    def Init(self) -> None:
        """
        初始化运行环境,只有调用后,接口才开始工作
        """
        super(CFtdcMdSpi, self).Init()
        time.sleep(1)  # wait for c++ init

    def Join(self) -> int:
        """
        等待接口线程结束运行
        @return 线程退出代码
        """
        return super(CFtdcMdSpi, self).Join()
        
    def initCallback(self, user, passwd):
        #self.callback = md_callback
        self.user = bytes(user,'utf-8')
        self.passwd = bytes(passwd,'utf-8')
        

    def ReqUserLogin(self, pReqUserLogin: "ReqUserLoginField", nRequestID: int) -> int:
        """
        用户登录请求
        """
        return super(CFtdcMdSpi, self).ReqUserLogin(pReqUserLogin, nRequestID)

    def ReqUserLogout(self, pUserLogout: "UserLogoutField", nRequestID: int) -> int:
        """
         登出请求
        """
        return super(CFtdcMdSpi, self).ReqUserLogout(pUserLogout, nRequestID)

   
    def OnFrontConnected(self) -> None:
        print(u"ctp行情服务器连接成功")
        logger.info (u"ctp行情服务器连接成功")
        now = datetime.now()
        if checkMarketTime(now):
            self.login()
        
        
    def login(self):    
        loginfield = ReqUserLoginField()
        loginfield.BrokerID=self.broker
        loginfield.UserID=self.user
        loginfield.Password=self.passwd
        loginfield.UserProductInfo=str2bytes("qe-pyctp") #"python dll"
        self.connected = True
        self.ReqUserLogin(loginfield,0)
        
    def logout(self):
        logoutfield = UserLogoutField()
        logoutfield.BrokerID = self.broker
        logoutfield.UserID = self.user
        self.ReqUserLogout(logoutfield,0)
    def ReqQryMulticastInstrument(self, pQryMulticastInstrument: "QryMulticastInstrumentField", nRequestID: int) -> int:
        """
        请求查询组播合约
        """
        return super(CFtdcMdSpi, self).ReqQryMulticastInstrument(pQryMulticastInstrument, nRequestID)

    def GetTradingDay(self) -> str:
        """
        获取当前交易日
        @retrun 获取到的交易日
        @remark 只有登录成功后,才能得到正确的交易日
        :return:
        """
        day = super(CFtdcMdSpi, self).GetTradingDay()
        return day.decode()
    
    def OnFrontDisconnected(self, nReason) -> None:
        if self.connected:
            print(u"ctp行情服务器已经断开")
            logger.info(u"ctp行情服务器已经断开")
        self.connected = False    

    def OnHeartBeatWarning(self, nTimeLapse) -> None:
        """
        心跳超时警告。当长时间未收到报文时，该方法被调用。

        :param nTimeLapse: 距离上次接收报文的时间
        :return:
        """
        pass
        
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast) -> None:
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
            self.SubscribeMarketData([id.encode('utf-8') for id in self.subID])

    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast) -> None:
        """
        登出请求响应
        :param pUserLogout:
        :param pRspInfo:
        :param nRequestID:
        :param bIsLast:
        :return:
        """
        pass
    def OnRspError(self, pRspInfo, nRequestID, bIsLast) -> None:
        """
        错误应答
        :param pRspInfo:
        :param nRequestID:
        :param bIsLast:
        :return:
        """
        pass

    def RegisterFront(self, pszFrontAddress: str) -> None:
        """
        注册前置机网络地址
        @param pszFrontAddress：前置机网络地址。
        @remark 网络地址的格式为：“protocol:# ipaddress:port”，如：”tcp:# 127.0.0.1:17001”。
        @remark “tcp”代表传输协议，“127.0.0.1”代表服务器地址。”17001”代表服务器端口号。
        """
        super(CFtdcMdSpi, self).RegisterFront(pszFrontAddress.encode())

        
    def SubscribeMarketData(self, pInstrumentID: typing.List[str]) -> int:
        """
         订阅行情。
        @param pInstrumentID 合约ID
        :return: int
        """
        logger.info(f'subscribe{pInstrumentID}')
        ids = [item for item in pInstrumentID]
        return super(CFtdcMdSpi, self).SubscribeMarketData(ids)

    def UnSubscribeMarketData(self, pInstrumentID: typing.List[str]) -> int:
        """
        退订行情。
        @param pInstrumentID 合约ID
        :return: int
        """
        logger.info(f'unsubscribe{pInstrumentID}')
        ids = [item for item in pInstrumentID]

        return super(CFtdcMdSpi, self).UnSubscribeMarketData(ids)
        
       
    def OnRtnDepthMarketData(self, pDepthMarketData) -> None:
        #global tradingDay, instTime
        instid = str(pDepthMarketData.InstrumentID)
        
        
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
        'inst':qeinst,\
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
        #print('market',d['instid'],mddata['current'])
        g_dataSlide.update([d])
        self.callback(d)
        
    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast) -> None:
        if pRspInfo.ErrorID == 0:
            logger.info(u"ctp行情订阅成功："+str(pSpecificInstrument.InstrumentID))
            print(u"ctp行情订阅成功："+str(pSpecificInstrument.InstrumentID))
        else:
            logger.error(f"Subscribe Failed id:{pRspInfo.ErrorID},instid:{pSpecificInstrument.InstrumentID},msg:{pRspInfo.ErrorMsg}")
    
    def OnRspUnSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast) -> None:
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
            elif d['type'] == qetype.KEY_ON_CROSS_DAY:
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
                    self.SubscribeMarketData([iid.encode('utf-8') for iid in subs])
                if len(unsubs) > 0:
                    self.UnSubscribeMarketData([iid.encode('utf-8') for iid in unsubs])
            else:
                self.subID = [get_valid_instID('AU9999')[:6].lower(), get_valid_instID('TF9999')[:6], get_valid_instID('IF9999')[:6]]
            #print('ctp adds',adds,'removes',removes)
            #print('ctp subs',subs,'unsubs',unsubs)
        return (adds, removes)

    def RegisterNameServer(self, pszNsAddress: str) -> None:
        """
        注册名字服务器网络地址
        @param pszNsAddress：名字服务器网络地址。
        @remark 网络地址的格式为：“protocol:# ipaddress:port”，如：”tcp:# 127.0.0.1:12001”。
        @remark “tcp”代表传输协议，“127.0.0.1”代表服务器地址。”12001”代表服务器端口号。
        @remark RegisterNameServer优先于RegisterFront
        """
        super(CFtdcMdSpi, self).RegisterNameServer(pszNsAddress.encode())

    def RegisterFensUserInfo(self, pFensUserInfo: "FensUserInfoField") -> None:
        """
        注册名字服务器用户信息
        @param pFensUserInfo：用户信息。
        """
        super(CFtdcMdSpi, self).RegisterFensUserInfo(pFensUserInfo)


    def SubscribeForQuoteRsp(self, pInstrumentID: typing.List[str]) -> int:
        """
        订阅询价。
        :param pInstrumentID: 合约ID list
        :return: int
        """
        ids = [bytes(item, encoding="utf-8") for item in pInstrumentID]

        return super(CFtdcMdSpi, self).SubscribeForQuoteRsp(ids)

    def UnSubscribeForQuoteRsp(self, pInstrumentID: typing.List[str]) -> int:
        """
        退订询价。
        :param pInstrumentID: 合约ID list
        :return: int
        """
        ids = [bytes(item, encoding="utf-8") for item in pInstrumentID]

        return super(CFtdcMdSpi, self).UnSubscribeForQuoteRsp(ids)


    def OnRspQryMulticastInstrument(self, pMulticastInstrument, pRspInfo, nRequestID, bIsLast) -> None:
        """
        请求查询组播合约响应
        :param pMulticastInstrument:
        :param pRspInfo:
        :param nRequestID:
        :param bIsLast:
        :return:
        """
        pass



    def OnRspSubForQuoteRsp(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast) -> None:
        """
        订阅询价应答
        :param pSpecificInstrument:
        :param pRspInfo:
        :param nRequestID:
        :param bIsLast:
        :return:
        """
        pass

    def OnRspUnSubForQuoteRsp(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast) -> None:
        """
        取消订阅询价应答
        :param pSpecificInstrument:
        :param pRspInfo:
        :param nRequestID:
        :param bIsLast:
        :return:
        """
        pass



    def OnRtnForQuoteRsp(self, pForQuoteRsp) -> None:
        """
        询价通知
        :param pForQuoteRsp:
        :return:
        """
        pass

def runQEMarketProcess(user, passwd, strats,runmode, setting_dict, mode_724=False):
    global mduserspi, g_mode_724, timer
    evalmode = False
    if setting_dict is not None and setting_dict['api'] == 'ctptest':
        evalmode = True
        
    mduserspi = CFtdcMdSpi()
    
    mduserspi.Create("./", False , True)  
    #mduserspi.Init()
    
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
        mduserspi.initCallback( setting_dict['investorid'],setting_dict['password'])
        mduserspi.broker = bytes(setting_dict['brokerid'],'utf-8')
        #print(setting_dict)
        address = setting_dict.get('mdaddress',-1)
        if address != -1:
            mduserspi.RegisterFront(address)
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
        print(f"CTP API MD version = {mduserspi.GetApiVersion()}")
        mduserspi.RegisterFront("tcp://222.66.192.247:47213")
        mduserspi.broker = bytes('4300','utf-8')

    if pass_flag:
        #mduserspi.RegisterSpi(mduserspi)  
        mduserspi.Init()    
        mduserspi.Join()
   


if __name__ == '__main__':
    runQEMarketProcess('scott','888888',None)