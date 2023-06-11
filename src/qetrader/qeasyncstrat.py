# -*- coding: utf-8 -*-
"""
Created on Wed Nov  3 12:38:18 2021

@author: ScottStation
"""

import time
import asyncio
import nest_asyncio
nest_asyncio.apply()

from .qecontext import qeContextBase
from .qetype import qetype
from datetime import datetime,timedelta
from .qeglobal import  is_trade_day
from .qectpmarket_wrap import changeCtpInstIDs
#from .qestockmarket import changeStockInstIDs
#from .qesoptmarket import changeSoptInstIDs
#from .qesoptmarket import changeSoptInstIDs
from .qeredisdb import saveHedgeMarketToDB
#from .qeredisdb import saveStrategyContextToDB
#from .qeredisdb import saveOrderDatarealToDB,saveOrderDataToDB,saveTradeDatarealToDB,savePositionDatarealToDB
from .qeredisdb import saveTradingDay
from .qeredisdb import loadSettingData, loadSettingDatareal, saveSettingDataToDB, saveSettingDatarealToDB
#from .qeredisdb import saveStrategyfreqToDB,saveStrategyfreqrealToDB
from .qelogger import logger
from threading import Timer
#from .qectpmarket import checkMarketTime
#from .qecontext import transInstID2Real,transInstID2Context
#from .qeaccount import realaccount
from .qesimtrader import simuaccount
#from .qeriskctl import soptriskctl
#from .qeinterface import cancel_order, make_order
from .qeglobal import g_userinfo, qeInstSett, setTradingDaySaved, getTradingDaySaved
#import random
from .qestratmarket_wrap import readStratPosition_wrap, writeStratPosition_wrap,writeStratStat_wrap,writeStratTrade_wrap
from .qestratmarket_wrap import readStratStat_wrap,writeContract_messages_wrap,writeContractTable_wrap

from .qeasyncdata import buffer_get_bar, reset_buffer_data, buffer_get_dominant_instIDs
try:
    from .qestockmarket import changeStockInstIDs
except:
    changeStockInstIDs = lambda x,y:None

def formhedgeInstid(instid):
    for i in range(len(instid)):
        if i == 0:
            instid_hedge = str(instid[i])+'_'
        else:
            instid_hedge += str(instid[i])+'_'
    instid_hedge = instid_hedge[:-1]
    return instid_hedge
        
        
def getBarTime(minu, freq):
    tday = datetime.today()
    
    try:
        curminu = int(minu) - 2400 if int(minu) >= 2400 else int(minu)
        timestr = tday.strftime('%Y-%m-%d') + ' '+str(curminu)+'00'
        bartime = datetime.strptime(timestr, '%Y-%m-%d %H%M%S')
        if freq == 1:
            return bartime
        else:    
            startday = tday if int(minu) < 2400 else tday + timedelta(days=1)
            starttime = datetime.strptime(startday.strftime('%Y-%m-%d') + ' 210000','%Y-%m-%d %H%M%S')
            if int((bartime - starttime).seconds/60) % freq == 0:
                return bartime
            else:
                return None
    except:
        now = datetime.now()
        curminu = int(now.hour*100+now.minute)
        curminu = int(minu) - 2400 if int(minu) >= 2400 else int(minu)
        timestr = tday.strftime('%Y-%m-%d') + ' '+str(curminu)+'00'
        bartime = datetime.strptime(timestr, '%Y-%m-%d %H%M%S')
        if freq == 1:
            return bartime
        else:    
            startday = tday if int(minu) < 2400 else tday + timedelta(days=1)
            starttime = datetime.strptime(startday.strftime('%Y-%m-%d') + ' 210000','%Y-%m-%d %H%M%S')
            if int((bartime - starttime).seconds/60) % freq == 0:
                return bartime
            else:
                return None
def getDailyCloseTime(instid, leftminu):
    now = datetime.now()
    endtime = []
    for inst in instid:
        if inst[-3:] == 'SGE':
            endtime.append(1530)
        elif inst[0] == 'T':
            endtime.append(1515)
        
        else:
            endtime.append(1500)
    endt = min(endtime)
    endday=now.strftime("%Y-%m-%d ")
    return datetime.strptime(endday+str(endt)+'00', '%Y-%m-%d %H%M%S') - timedelta(minutes=leftminu)
            
class qeAsyncStratProcess:
    def __init__(self, strats, Queue, realTrade=False):

        self.instid = []          # list of instrument
        #self.instid_ex = []
        #self.exID = []
        self.stratQueue = Queue
        #self.tqueue = traderQ
        #self.name = name
        self.feesmult = 1
        self.realTrade = realTrade
        self.referenceID = datetime.now().strftime('%H%M%S')+'0000'
        self.time_delay = 0   
        self.formula = None
        self.curtime = None
        self.curday = None
        self.lasttime = None
        self.lastday = None
        self.hedgemodel = False
        self.printlog = True
        self.hedgemodel_price = 0
        self.hedgemodel_time = 0
        self.user = "unknown"
        self.token = ''
        self.Timer_interval = 30
        self.work = True
        self.trigger = False
        self.current_timedigit = 0
        self.balance=0
        self.evalmode = False
        self.daily_called = False
        #bar
        self.wait_all=True
        self.freq=1 #0为tick
        #self.info_time_new=0
        #self.info_time_all=0
        self.info_time = 0
        self.posLoaded = False
        self.bDataRead = False
        self.bCross = False
        self.instids = set()
        self.dataslide = {}
        self.presett = {}
        #self.saveTradingday = False
    def getLocalTradingDay(self):
        tday = datetime.now()
        if tday.hour > 18:
            days = 1 if tday.weekday() < 4 else 3
            tday += timedelta(days=days)
        elif tday.hour < 8 and tday.weekday()==5:
            tday += timedelta(days=2)
        return tday

    def checkCrossDay(self):
        if self.bDataRead:
            now = datetime.now()
            ##set crossDay True
            if not self.bCross and now.hour == 19:
                self.bCross = True
                return True
            ##restore crossDay to False
            elif self.bCross and now.hour > 19:
                self.bCross = False
                
        return False
        #if not self.lasttime:
        #    return False
        #if self.lastday != '' and self.tradingday != self.lastday:
        #    return True
        #elif (self.lasttime.hour == 14 or self.lasttime.hour == 15) and self.curtime.hour != 14 and self.curtime.hour != 15:
        #    return True
        #return False
    
    def callStratOnBar(self):
        #global loop
        start = datetime.now()
        try:
            buffer_get_bar(list(self.instids), self.tradingday)
            tasks = []
            for strat in self.strats:
                bartime = getBarTime(self.info_time, strat.freq)
                if bartime and strat.context.bDataRead:
                    strat.context.bartime= bartime
                    tasks.append(asyncio.ensure_future(strat.aio_onBar(strat.context)))
            if len(tasks) > 0:
                self.loop.run_until_complete(asyncio.wait(tasks))
                    
        except Exception as e:
            logger.error(f'Error on strat.onBar {e}',exc_info=True)
        end = datetime.now()
        secs = (end-start).seconds
        logger.info(f'callStratOnBar cost {secs} seconds')
    
    def callStratCrossDay(self):
        #global loop
        start = datetime.now()
        try:
            buffer_get_dominant_instIDs(list(self.instids), self.tradingday)
            tasks = []
            for strat in self.strats:
                if strat.context.bDataRead:
                    tasks.append(asyncio.ensure_future(strat.aio_crossDay(strat.context)))
            if len(tasks) > 0:
                self.loop.run_until_complete(asyncio.wait(tasks))
                
        except Exception as e:
            logger.error(f'Error on strat.crossDay {e}',exc_info=True)
        end = datetime.now()
        secs = (end-start).seconds
        logger.info(f'callStratCrossDay cost {secs} seconds')

    def stratProcess(self, strats):
        global info_time
        print(u"策略进程启动成功!")
        logger.info(u"策略进程启动成功!")
        logger.info("strat user "+str(self.user))
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        for strat in strats:
            strat.context = qeContextBase(strat.instid)
            #g_userinfo = globalInfo()  
            #print(g_userinfo.info_time,'#')
            #print(1)
            strat.posLoaded = False
            strat.context.user = self.user
            strat.context.token = self.token
            strat.context.hedgemodel = strat.hedgemodel
            strat.context.recmode = self.recmode
            strat.context.printlog = self.printlog
            strat.context.trader = self.trader
            strat.context.runmode = 'simu' if self.trader =='simu' else 'real'
            if strat.hedgemodel:
                strat.context.formula = strat.formula
                strat.instid_hedge = formhedgeInstid(strat.instid)
    
                
            #strat.context.init_orderid = int(str(self.ID)+ self.referenceID)
            #strat.context.orderid = context.init_orderid
            strat.context.freq=strat.freq
            #context.instid = self.instid #self.instid_ex  
            strat.context.stratName = strat.name
            strat.context.realTrade = self.realTrade
            strat.context.feesMult = 1
            if self.realTrade:
                strat.context.accounts = self.accounts
                strat.context.account = strat.context.accounts[0]
            else:
                strat.context.account = simuaccount
                strat.context.accounts = [simuaccount]
            strat.context.dataslide = self.dataslide
            strat.context.presett = self.presett
            self.instids.update(strat.instid)
            
        self.strats = strats
        
        if self.recmode:
            simuaccount.loadPosition = False
            
        #print(3,g_userinfo.info_time_all)
        #print(2,self.freq)
        #print(1,self.wait_all)
        #strat.initStrat(context)
        #context.freq=self.freq
        #print('111',info_time)
        #if self.evalmode:
        self.callTimer()

        if self.stratQueue:
            while True:
                #print("strat:", self.name)
                while not self.stratQueue.empty():
                    #print(123)
                    try:
                        d = self.stratQueue.get(block = True, timeout = 1)
                        #print(d)
                        if d['type'] == qetype.KEY_MARKET_DATA or d['type'] == qetype.KEY_MARKET_MULTIDATA:           
#                             print('stratprocess market data')
                            savedInsts = {}
                            if d['type'] == qetype.KEY_MARKET_DATA:
                                self.updateData(d)
                                self.updateTime(d)
                            else:    
                                for data in d['data']:
                                    self.updateData(data)
                                self.updateTime(d['data'][0])    
                            for strat in self.strats:
                                savedInsts[strat.name] = strat.instid.copy()
                                #if d['instid'] in strat.instid:
                                    #self.autoOrders(d, strat.context)
                                    #self.algoTrade(d, strat.context)

                            try:
                                if strat.datamode=='minute':
                                    renew = False
                                    if self.wait_all and self.info_time != g_userinfo.info_time_all:
                                        self.info_time = g_userinfo.info_time_all
                                        renew = True
                                    elif not self.wait_all and  self.info_time != g_userinfo.info_time_new : 
                                        self.info_time = g_userinfo.info_time_new 
                                        renew = True
                                    if renew:
                                        self.callStratOnBar()
                                
                                for strat in self.strats:
                                    if isinstance(strat.instid, str):
                                        strat.instid = [strat.instid]
                                    if savedInsts[strat.name] !=  strat.instid:
                                        print(f'{strat.name} instid changed from {savedInsts[strat.name]} to {strat.instid}')
                                        self.changeInstIDs(strat.context, savedInsts[strat.name], strat.instid)
                                        strat.context.instid = strat.instid
#                                         self.trigger = False
                            except Exception as e:
                                logger.error(f'Error on strat.handleData {e}',exc_info=True)
                        elif d['type'] == qetype.KEY_ON_ORDER:
                            #print('on_Order')
                            #print('3',d)
                            self.handleOrder(d)
                        elif d['type'] == qetype.KEY_ON_TRADE:
                            self.handleTrade(d)  
                            #print('on_Trade')
                        elif d['type'] == qetype.KEY_ON_ORDER_ERROR:
                            #print('stratprocess on order error')
                            self.handleOrder(d)
                        elif d['type'] == qetype.KEY_TIMER_PROCESS:
                            #logger.info(f'strat minu report:{self.info_time_new},{self.info_time_all}')
                            self.bCrossDay = self.checkCrossDay()
                            if self.bCrossDay:
                                logger.info(f'strat.crossDay {strat.name}')
                               #self.saveTradingday = False
                                savedInsts = {}
                                for strat in self.strats:
                                    savedInsts[strat.name] = strat.instid.copy()
                                    strat.context.dayStatistics()
                                    strat.context.crossDay()
                                self.crossDay()
                                self.callStratCrossDay()
                                for strat in self.strats:
                                    if isinstance(strat.instid, str):
                                        strat.instid = [strat.instid]

                                    if savedInsts[strat.name] !=  strat.instid:
                                        print(f'{strat.name} instid changed from {savedInsts[strat.name]} to {strat.instid}')
                                        self.changeInstIDs(strat.context, savedInsts[strat.name], strat.instid)
                                        strat.context.instid = strat.instid
                           
                    except Exception as e:
                        logger.error(f"qestratprocess stratqueue error {e}",exc_info=True )  
                time.sleep(0.001)

    def changeInstIDs(self, context, old, new):
        if context.stratName != 'csvorders':
            if context.runmode == 'simu':
                stgsett = loadSettingData(self.user, self.token)
                stgsett[context.stratName] = new
                saveSettingDataToDB(self.user, self.token,  stgsett)
            elif context.runmode == 'real':
                stgsett = loadSettingDatareal(self.user, self.token)
                stgsett[context.stratName] = new
                saveSettingDatarealToDB(self.user, self.token, stgsett)
        
        
        newinsts = []
        for inst in new:
            if not inst in old :
                newinsts.append(inst)
        context.addNewInsts(newinsts)
        self.instids.update(new)
        #adds = []; removes = [];
        ###need fix
        if 'ctp' in self.mduser:
                changeCtpInstIDs(context.stratName, new)
        elif 'stock' in self.mduser:
                changeStockInstIDs(context.stratName, new)
        #if 'sopt' in self.mduser :
        #        changeSoptInstIDs(context.stratName, new)

           
    def callTimer(self):     
        timer = Timer(self.Timer_interval,self.callTimer)
        d = {}
        d['type'] = qetype.KEY_TIMER_PROCESS
#         logger.info('timer '+str(datetime.now()))
        
        if self.stratQueue:
            self.stratQueue.put(d)
        else:
            logger.info('Timer is pending')
        timer.start()
        return    
  
                
            
       
    def getPreviousTradingDay(self):
        prev_date = datetime.strptime(self.tradingday,'%Y%m%d') 
        days = 3 if prev_date.weekday() == 0 else 1
        prev_date -= timedelta(days=days)
        while not is_trade_day(prev_date):
            prev_date -= timedelta(days=1)
        return prev_date    
    
    def updateTime(self,d):
        try:
            self.bDataRead = True
            self.tradingday = d['data']['tradingday']
            if not getTradingDaySaved():
                saveTradingDay(self.user, self.token, str(self.tradingday))
                setTradingDaySaved(True)
            curtime = datetime.strptime(d['data']['time'],'%Y%m%d %H:%M:%S.%f')
            if self.curtime is None or curtime > self.curtime :
                self.lasttime = self.curtime
                self.curtime = curtime
            self.curday= self.curtime.strftime('%Y-%m-%d')
            if self.lasttime:
                self.lastday=self.lasttime.strftime('%Y-%m-%d')
            for strat in self.strats:
                    strat.context.bDataRead = True
                    #strat.context.dataslide.update({tempinstid : d['data']}) 
                    #print(tempinstid, context.dataslide[tempinstid]['a1_p'])
                    strat.context.timedigit = d['data']['timedigit']
                    strat.context.updateTradingday(str(self.tradingday))
                    strat.context.curtime = self.curtime
                    strat.context.lasttime = self.lasttime
                    strat.context.curday = self.curday
                    strat.context.lastday = self.lastday
                    if self.recmode and not strat.posLoaded:
                        strat.posLoaded = True
                        pos,instPnl = readStratPosition_wrap(strat.name, strat.context.tradingday)
                        if pos == {} and instPnl == {}:
                            prev_date = self.getPreviousTradingDay() 
                            strat.context.position, tmp = readStratPosition_wrap(strat.name, prev_date.strftime('%Y%m%d'))
                            ## Can not load closepnl from previous day
                            strat.context.instClosePnl = {}
                            strat.context.prodMaxMarg,strat.context.prodTurnover = readStratStat_wrap(strat.name,prev_date)
                        else:
                            strat.context.position = pos
                            strat.context.instClosePnl = instPnl
                            strat.context.prodMaxMarg,strat.context.prodTurnover = readStratStat_wrap(strat.name,strat.context.tradingday)
                        simuaccount.updateStratPostion(strat.context.position)
                        ## write back to database
                        strat.context.clearExpirePosition()
                        writeStratPosition_wrap(strat.name, strat.context.tradingday,strat.context.position,strat.context.instClosePnl)
                        writeContractTable_wrap(strat.name, strat.context.tradingday,strat.context.position)
                        writeStratStat_wrap(strat.name,strat.context.tradingday, strat.context.prodMaxMarg, strat.context.prodTurnover)
                        strat.context.instsett = qeInstSett()   
                    if strat.hedgemodel:

                        if len(strat.context.dataslide) == len(strat.context.instid):
                            strat.hedgemodel_price = self.calculatemul(strat.context)
                            if strat.hedgemodel_time == 0:             
                                strat.hedgemodel_time = strat.context.timedigit
                            elif strat.context.timedigit > strat.hedgemodel_time:
                                d ={}
                                d['current'] = strat.hedgemodel_price
                                d['time'] = strat.hedgemodel_time
                                #if self.realTrade:
                                #    saveHedgeMarketrealToDB(self.user,self.name, self.instid_hedge, self.hedgemodel_time, d) 
                                #else:    
                                saveHedgeMarketToDB(self.user,strat.name, strat.instid_hedge, strat.hedgemodel_time, d)
                                strat.hedgemodel_time = strat.context.timedigit
        except Exception as e:
            logger.info(f"qestratprocess stratqueue error {e}",exc_info=True )  
    
    
    def updateData(self,d):
        try:
            tempinstid = d['instid']
            ## add by scott
            presett = float(d['data'].get('presett',0))
                
            if presett  > 0.01 and not tempinstid in self.presett:
                self.presett.update({tempinstid:presett})
                logger.info(f"New data on {tempinstid},presett:{self.presett[tempinstid]}")
            self.dataslide.update({tempinstid:d['data']})
            
            
            
            for strat in self.strats:
                if tempinstid in strat.instid: # or self.recmode:
                    strat.context.current[tempinstid] = d['data']['current']
                    if tempinstid in strat.context.lastvol:
                        if strat.context.lastvol[tempinstid] == 0:
                            strat.context.lastvol[tempinstid] = strat.context.dataslide[tempinstid]['volume']
                            strat.context.curvol[tempinstid] = 0
                        else:
                            strat.context.curvol[tempinstid] = strat.context.dataslide[tempinstid]['volume'] - strat.context.lastvol[tempinstid]
                            strat.context.lastvol[tempinstid] = strat.context.dataslide[tempinstid]['volume']
                    else:
                            strat.context.curvol[tempinstid] = strat.context.dataslide[tempinstid]['volume'] 
                            strat.context.lastvol[tempinstid] = strat.context.dataslide[tempinstid]['volume']
                        
                                        
        except Exception as e:
            logger.info(f"qestratprocess stratqueue error {e}",exc_info=True )  

    def calculatemul(self,context):
        a = [0, 0, 0, 0, 0]
        for i in range(len(context.instid)):
            a[i] = context.dataslide[context.instid[i]]['current']
        # print(context.formula)
        multiresult = eval(context.formula, {'a': a[0], 'b': a[1], 'c': a[2], 'd': a[3], 'e': a[4]})
        # print(multiresult)
        return multiresult

    #def refresh(self,d,context):
        #if d['data']['timedigit'] - self.time_delay > 2000:
        #    self.time_delay = d['data']['timedigit']  
        #    if self.realTrade:
        #        #saveStrategyContextrealToDB(self.user,self.name,d['data']['tradingday'],context)
        #        saveStrategyfreqrealToDB(self.user,self.token, self.name,d['data']['tradingday'],context)
        #    else:
        #        #saveStrategyContextToDB(self.user,self.name,d['data']['tradingday'],context)
        #        saveStrategyfreqToDB(self.user,self.token, self.name,d['data']['tradingday'],context)
#       #      print('redis context')        
    
    def crossDay(self):
        self.info_time_all = 0
        self.info_time_new = 0
        self.daily_called = False
        logger.info('Strat Process crossDay')    
        reset_buffer_data()
        if self.recmode:
            
            for strat in self.strats:
                context = strat.context
                lastday = context.lastday.replace('-','')
                strat.context.clearExpirePosition()
                writeStratPosition_wrap(strat.name, lastday,context.position,context.instClosePnl)
                writeContractTable_wrap(strat.name, lastday,context.position)
                writeStratStat_wrap(strat.name,lastday, context.prodMaxMarg, context.prodTurnover)
        self.dataslide = {}
        self.presett = {}
           
    def handleOrder(self,order):  
        
        try:
            for strat in self.strats:
                if strat.name == order['stratName']:
                    context = strat.context
                
                    corder = context.orders.get(order['orderid'],None)
                    if corder:
                        corder['status'] = order['status']
                        corder['tradevol'] = order['tradevol']
                        corder['cancelvol'] = order['cancelvol']
                        corder['leftvol'] = order['leftvol']
                        corder['stratName'] = strat.name
                        corder['timedigit'] = order['timedigit']
                        corder['errorid'] = order.get('errorid',0)
                        corder['errormsg'] = order.get('errormsg','')
                        context.orders[order['orderid']] = corder
                
                
        except Exception as e:
            logger.error(f"handleorder error {e}",exc_info=True)  


    def handleTrade(self,trade):
        try:
            for strat in self.strats:
                if strat.name == trade['stratName']:
                    context = strat.context
                    context.simuTrade(trade)
                    context.updateData() 
                    if self.recmode:
                        writeStratPosition_wrap(strat.name, context.tradingday,context.position,context.instClosePnl)
                        writeContractTable_wrap(strat.name, context.tradingday,context.position)
                        writeStratStat_wrap(strat.name,context.tradingday, context.prodMaxMarg, context.prodTurnover)
                        writeStratTrade_wrap(strat.name,context.tradingday, trade)
                        writeContract_messages_wrap(strat.name,context.tradingday, trade)
        except Exception as e:
            logger.error(f"handletrade error {e}",exc_info=True )
    
    
if __name__ == '__main__':
    from multiprocessing import Queue
    class stratBase:
        def initStrat(self, context):
            print("Init strategy which will do nothing.")      

        def handleData(self, context):     
            print("Process time:",context.curtime)

        def crossDay(self,context):
            print('Cross day:', context.lastday)    
    strat = stratBase()
    tq = Queue()
    mq = Queue()
    p = qeAsyncStratProcess('n',tq,mq)
    p.ID = 100000
    #p.instid_ex,p.exID = transInstIDs('AG2206.SFE')
    p.stratProcess(strat)