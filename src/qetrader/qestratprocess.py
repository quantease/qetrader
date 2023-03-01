# -*- coding: utf-8 -*-
"""
Created on Wed Nov  3 12:38:18 2021

@author: ScottStation
"""

import time
from .qecontext import qeContextBase
from .qetype import qetype
from datetime import datetime,timedelta
from .qeglobal import  is_trade_day
from .qectpmarket_wrap import changeCtpInstIDs
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
from .qeinterface import cancel_order, make_order
from .qeglobal import g_userinfo, qeInstSett, instSetts, setTradingDaySaved, getTradingDaySaved,getPositionLoaded
import random
from .qestratmarket_wrap import readStratPosition_wrap, writeStratPosition_wrap,writeStratStat_wrap,writeStratTrade_wrap
from .qestratmarket_wrap import readStratStat_wrap,writeContract_messages_wrap,writeContractTable_wrap


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
            
class qeStratProcess:
    def __init__(self, name, Queue, realTrade=False):

        self.instid = []          # list of instrument
        #self.instid_ex = []
        #self.exID = []
        self.stratQueue = Queue
        #self.tqueue = traderQ
        self.name = name
        self.realTrade = realTrade
        self.referenceID = datetime.now().strftime('%H%M%S')+'0000'
        self.time_delay = 0   
        self.formula = None
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
        self.wait_all=True #
        #self.freq=0 #0为tick
        #self.info_time_new=0
        #self.info_time_all=0
        self.info_time = 0
        self.posLoaded = False
        
        self.bDataRead = False
        self.bCross = False
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
    
    def stratProcess(self, strat):
        global info_time
        print(u"策略进程启动成功；"+str(strat.name))
        logger.info(u"策略进程启动成功；"+str(strat.name))
        logger.info("strat user "+str(self.user))
        context = qeContextBase(self.instid)
        #g_userinfo = globalInfo()  
        #print(g_userinfo.info_time,'#')
        #print(1)
        
        context.user = self.user
        context.token = self.token
        context.hedgemodel = self.hedgemodel
        context.printlog = self.printlog
        context.trader = self.trader
        context.runmode = 'simu' if self.trader =='simu' else 'real'
        if self.hedgemodel:
            context.formula = self.formula
            self.instid_hedge = formhedgeInstid(self.instid)

            
        context.init_orderid = int(str(self.ID)+ self.referenceID)
        context.orderid = context.init_orderid
        context.freq=strat.freq
        #context.instid = self.instid #self.instid_ex  
        context.stratName = self.name
        context.realTrade = self.realTrade
        context.feesMult = self.feesmult
        if self.realTrade:
            context.accounts = self.accounts
            context.account = context.accounts[0]
        else:
            context.account = simuaccount
            context.accounts = [simuaccount]
        if self.recmode:
            simuaccount.loadPosition = False
            context.recmode = True
            
        #print(3,g_userinfo.info_time_all)
        #print(2,self.freq)
        #print(1,self.wait_all)
        #strat.initStrat(context)
        #context.freq=self.freq
        #print('111',info_time)
        if self.evalmode:
            self.Timer_interval = 8
        self.callTimer()

        if self.stratQueue:
            while True:
                #print("strat:", self.name)
                while not self.stratQueue.empty():
                    #print(123)
                    try:
                        d = self.stratQueue.get(block = True, timeout = 1)
                        #print(d)
                        if d['type'] == qetype.KEY_MARKET_DATA:           
#                             print('stratprocess market data')
                            savedInsts = strat.instid.copy();
                            self.updateData(d,context)
                            #self.autoOrders(d, context)
                            #self.algoTrade(d,context)
                                #if context.runmode == 'simu':
                                #    context.account.noticeCrossDay(self.name)
                            #self.refresh(d,context) 
                            #if isinstance(context.trader, list)  and 'stockoption' in context.trader:
                            #    retryorders =  soptriskctl.getRetryOrders()
                            #    if retryorders:
                            #        for oid in retryorders:
                            #            cancel_order(context, oid)
                            if context.runmode=='real' and not getPositionLoaded():
                                continue
                            try:
                                    #print(1)
                                    #print(self.wait_all)
                                    

                                strat.handleData(context)
                                if strat.datamode=='minute':
                                    renew = False
                                    if self.wait_all and self.info_time != g_userinfo.info_time_all:
                                        self.info_time = g_userinfo.info_time_all
                                        renew = True
                                    elif not self.wait_all and  self.info_time != g_userinfo.info_time_new : 
                                        self.info_time = g_userinfo.info_time_new 
                                        renew = True
                                    if renew:
                                        bartime = getBarTime(self.info_time, strat.freq)
                                        if bartime:
                                            context.bartime = bartime
                                            strat.onBar(context)
                                    
                                elif strat.datamode == 'daily':
                                    if not  self.daily_called and context.curtime >= getDailyCloseTime(strat.instid, strat.dailyminutes):
                                        self.daily_called = True
                                        strat.onBar(context)
                                #strat.instid = getValidInstIDs(strat.instid)
                                if savedInsts !=  strat.instid:
                                    print("instid changed from ", savedInsts, 'to', strat.instid)
                                    self.changeInstIDs(context, savedInsts, strat.instid)
                                    context.instid = strat.instid
#                                         self.trigger = False
                            except Exception as e:
                                logger.error(f'Error on strat.handleData {e}',exc_info=True)
                        elif d['type'] == qetype.KEY_ON_ORDER:
                            #print('on_Order')
                            #print('3',d)
                            try:
                                strat.handleOrder(d,context)
                            except Exception as e:
                                print(f'Error on strat.handleOrder: {e}')
                            self.handleOrder(d,context)
                        elif d['type'] == qetype.KEY_ON_ORDER_ERROR:
                            #print('on_Order')
                            #print('3',d)
                            try:
                                strat.handleOrderError(d,context)
                            except Exception as e:
                                print(f'Error on strat.handleOrderError: {e}')
                            self.handleOrder(d,context)
                        elif d['type'] == qetype.KEY_ON_TRADE:
                            try:
                                strat.handleTrade(d,context)
                            except Exception as e:
                                print(f'Error on strat.handelTrade: {e}')    
                            self.handleTrade(d,context)  
                            #print('on_Trade')
                        elif d['type'] == qetype.KEY_ON_ORDER_ERROR:
                            #print('stratprocess on order error')
                            self.handleOrder(d,context)
                        elif d['type'] == qetype.KEY_TIMER_PROCESS:
                            #logger.info(f'strat minu report:{self.info_time}')
                            if self.evalmode and strat.datamode == 'minute':
                                try:
                                    savedInsts = strat.instid.copy();
                                    context.curtime = datetime.now()
                                    tday = self.getLocalTradingDay()
                                    self.tradingday = tday.strftime('%Y%m%d')
                                    context.updateTradingday(str(self.tradingday))
                                    if not getTradingDaySaved():
                                        saveTradingDay(self.user, self.token, str(self.tradingday))
                                        setTradingDaySaved(True)
                                    
                                    #context.instsett = qeInstSett()
                                    for inst in savedInsts:
                                        tmpd ={'instid':inst}
                                        #self.autoOrders(tmpd, context)
                                        #self.algoTrade(tmpd,context)
                                    renew = False
                                    if self.wait_all and self.info_time != g_userinfo.info_time_all:
                                        self.info_time = g_userinfo.info_time_all
                                        renew = True
                                    elif not self.wait_all and  self.info_time != g_userinfo.info_time_new : 
                                        self.info_time = g_userinfo.info_time_new 
                                        renew = True
                                    if renew:
                                        bartime = getBarTime(self.info_time, strat.freq)
                                        if bartime:
                                            context.bartime = bartime
                                            strat.onBar(context)
                                    if savedInsts !=  strat.instid:
                                        print("instid changed from ", savedInsts, 'to', strat.instid)
                                        self.changeInstIDs(context, savedInsts, strat.instid)
                                        context.instid = strat.instid
                                except Exception as e:
                                    logger.error(f'Error on strat.handleData {e}',exc_info=True)

                            context.bCrossDay = self.checkCrossDay()
                            if context.bCrossDay:
                                logger.info(f'strat.crossDay {strat.name}')
                               #self.saveTradingday = False
                                savedInsts = strat.instid.copy();
                                try:
                                    context.dayStatistics()
                                    context.crossDay()
                                    
                                    self.crossDay(context)
                                    strat.crossDay(context)
                                except Exception as e:
                                    logger.error(f'Error on strat.crossDay {e}',exc_info=True)
                                if isinstance(strat.instid, str):
                                    strat.instid = [strat.instid]
                                if savedInsts !=  strat.instid:
                                    print("instid changed from ", savedInsts, 'to', strat.instid)
                                    self.changeInstIDs(context, savedInsts, strat.instid)
                                    context.instid = strat.instid
                    except Exception as e:
                        logger.error(f"qestratprocess stratqueue error {e}",exc_info=True )  
                time.sleep(0.001)

    def changeInstIDs(self, context, old, new):
        if context.stratName != 'csvorders':
            if context.runmode == 'simu':
                stgsett = loadSettingData(self.user, self.token)
                stgsett[self.name] = new
                saveSettingDataToDB(self.user, self.token,  stgsett)
            elif context.runmode == 'real':
                stgsett = loadSettingDatareal(self.user, self.token)
                stgsett[self.name] = new
                saveSettingDatarealToDB(self.user, self.token, stgsett)
        
        
        newinsts = []
        for inst in new:
            if not inst in old :
                newinsts.append(inst)
        context.addNewInsts(newinsts)

        #adds = []; removes = [];
        ###need fix
        if 'ctp' in self.mduser:
                changeCtpInstIDs(self.name, new)
        #if 'sopt' in self.mduser :
        #        changeSoptInstIDs(self.name, new)

           
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
  
                
    def confirm(self,code,context):
        # print('confirm')
        #saveRequestToDB(self.user,self.name,-code,context.realTrade)
        if abs(code) == 1:
            print('stop strategy '+str(self.name))
        elif abs(code) == 2:
            print('resume strategy '+str(self.name))
        elif abs(code) == 3:
            print('liquidate strategy '+str(self.name))
    
            
       
    def getPreviousTradingDay(self):
        prev_date = datetime.strptime(self.tradingday,'%Y%m%d') 
        days = 3 if prev_date.weekday() == 0 else 1
        prev_date -= timedelta(days=days)
        while not is_trade_day(prev_date):
            prev_date -= timedelta(days=1)
        return prev_date    
    
    
    
    
    def updateData(self,d,context):
        try:
            tempinstid = d['instid']
            self.bDataRead = True
            context.dataslide[tempinstid] = d['data']
            #print(tempinstid, context.dataslide[tempinstid]['a1_p'])
            context.timedigit = d['data']['timedigit']
            self.tradingday = d['data']['tradingday']
            context.updateTradingday(str(self.tradingday))
            if not getTradingDaySaved():
                saveTradingDay(self.user, self.token, str(self.tradingday))
                setTradingDaySaved(True)
            
            curtime = datetime.strptime(d['data']['time'],'%Y%m%d %H:%M:%S.%f')
            if context.curtime is None or curtime > context.curtime :
                context.lasttime=context.curtime
                context.curtime = curtime
            context.curday= context.curtime.strftime('%Y-%m-%d')
            if context.lasttime:
                context.lastday=context.lasttime.strftime('%Y-%m-%d')
            
            if self.recmode and not self.posLoaded:
                self.posLoaded = True
                pos,instPnl = readStratPosition_wrap(self.name, context.tradingday)
                if pos == {} and instPnl == {}:
                    prev_date = self.getPreviousTradingDay() 
                    context.position, context.instClosePnl = readStratPosition_wrap(self.name, prev_date.strftime('%Y%m%d'))
                    
                else:
                    context.position = pos
                    context.instClosePnl = instPnl
                simuaccount.updateStratPostion(context.position)
                context.prodMaxMarg,context.prodTurnover = readStratStat_wrap(self.name,context.tradingday)
                ## write back to database
                writeStratPosition_wrap(self.name, context.tradingday,context.position,context.instClosePnl)
                writeContractTable_wrap(self.name, context.tradingday,context.position)
                writeStratStat_wrap(self.name,context.tradingday, context.prodMaxMarg, context.prodTurnover)
                #context.instsett = qeInstSett()        
                
            context.current[tempinstid] = d['data']['current']
        
            if tempinstid in context.lastvol:
                if context.lastvol[tempinstid] == 0:
                    context.lastvol[tempinstid] = context.dataslide[tempinstid]['volume']
                    context.curvol[tempinstid] = 0
                else:
                    context.curvol[tempinstid] = context.dataslide[tempinstid]['volume'] - context.lastvol[tempinstid]
                    context.lastvol[tempinstid] = context.dataslide[tempinstid]['volume']
            else:
                context.curvol[tempinstid] = context.dataslide[tempinstid]['volume'] 
                context.lastvol[tempinstid] = context.dataslide[tempinstid]['volume']
           
            if self.hedgemodel:

                if len(context.dataslide) == len(context.instid):
                    self.hedgemodel_price = self.calculatemul(context)
                    if self.hedgemodel_time == 0:             
                        self.hedgemodel_time = context.timedigit
                    elif context.timedigit > self.hedgemodel_time:
                        d ={}
                        d['current'] = self.hedgemodel_price
                        d['time'] = self.hedgemodel_time
                        #if self.realTrade:
                        #    saveHedgeMarketrealToDB(self.user,self.name, self.instid_hedge, self.hedgemodel_time, d) 
                        #else:    
                        saveHedgeMarketToDB(self.user,self.name, self.instid_hedge, self.hedgemodel_time, d)
                        self.hedgemodel_time = context.timedigit
                                       
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
    
    def crossDay(self,context):
        self.info_time = 0
        #self.info_time_all = 0
        #self.info_time_new = 0
        self.daily_called = False
        logger.info('Strat Process crossDay')        
        if self.recmode:
            lastday = context.lastday.replace('-','')
            writeStratPosition_wrap(self.name, lastday,context.position,context.instClosePnl)
            writeContractTable_wrap(self.name, lastday,context.position)
            writeStratStat_wrap(self.name,lastday, context.prodMaxMarg, context.prodTurnover)
           
    def handleOrder(self,order,context):  
        try:     
            corder = context.orders.get(order['orderid'],None)
            #print('1',corder)
            if corder:
                #time = str(order['timedigit'])
                corder['status'] = order['status']
                corder['tradevol'] = order['tradevol']
                corder['cancelvol'] = order['cancelvol']
                corder['leftvol'] = order['leftvol']
                corder['stratName'] = self.name
                #corder['time'] = time[:8]+' '+time[8:10]+':'+time[10:12]+':'+time[12:14]+"."+time[14:]
                corder['timedigit'] = order['timedigit']
                corder['errorid'] = order.get('errorid',0)
                corder['errormsg'] = order.get('errormsg','')
                #print('123',order)
                #corder['torderid']=order['torderid']
                '''
                if self.current_timedigit == 0:
                    self.current_timedigit = (order['timedigit'])
                else:
                    self.current_timedigit = max(self.current_timedigit+5,(order['timedigit'])) # increment by 5 ms to identify time change
                
                # logger.debug(str(self.name)+'-'+str(order['timedigit']))
                '''
                context.orders[order['orderid']] = corder
                
                
        except Exception as e:
            logger.error(f"handleorder error {e}",exc_info=True)  


    def handleTrade(self,trade,context):
        try:
            context.simuTrade(trade)
            context.updateData() 
            if self.recmode:
                writeStratPosition_wrap(self.name, context.tradingday,context.position,context.instClosePnl)
                writeContractTable_wrap(self.name, context.tradingday,context.position)
                writeStratStat_wrap(self.name,context.tradingday, context.prodMaxMarg, context.prodTurnover)
                writeStratTrade_wrap(self.name,context.tradingday, trade)
                writeContract_messages_wrap(self.name,context.tradingday, trade)
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
    p = qeStratProcess('n',tq,mq)
    p.ID = 100000
    #p.instid_ex,p.exID = transInstIDs('AG2206.SFE')
    p.stratProcess(strat)