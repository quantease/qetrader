# -*- coding: utf-8 -*-
"""
Created on Tue Oct 12 20:03:20 2021

@author: ScottStation
"""
import pandas as pd
import numpy as np
import traceback
#import json
# import talib
# from talib import MA_Type
from qesdk import get_price, get_ticks, is_valid_trade_time, is_valid_instID
from .qeglobal import getInstrumentSetting
import matplotlib.pyplot as plt
from .qelogger import initBacktestLogger, logger
#from .qeglobal import getValidInstIDs
import datetime
from .qeinterface import qeStratBase, force_close
from .qeredisdb import saveBackTestData, saveBackTestReport,saveBackTestList, saveBackTestSetting,saveBackTestDataDynamic,clearBackTestData
from .qestratmarket_wrap import save_trades_wrap, writeStratStat_wrap,  writeStratPosition_wrap,update_stratCard_wrap,writeStratPnl_wrap,clearStratTrades_wrap,readStratPosition_wrap,update_stratCard_append_wrap,readFullStratStat_wrap,clearStratStat_wrap,clearStratPosition_wrap
from dateutil.relativedelta import relativedelta
from .qesysconf import read_sysconfig
import asyncio
import nest_asyncio
nest_asyncio.apply()

def getProd(instid):
    return instid[:2] if not instid[1].isdigit() else instid[:1]

class testAccountInfo:
    def __init__(self, balance=0):
        self.balance = balance
        self.avail = balance
        self.margin = 0
        self.frozenMarg = 0
        self.position = {}
        self.closeProf = 0
        self.posProf = 0
        self.daypnl = 0
        self.totalpnl = 0
        self.dayfees = 0
        self.totalfees = 0
        self.tradingDay = ""
        self.trades={}
        self.orders={}

    def setData(self,context):
        self.balance = context.stat.balance
        self.avail = context.stat.avail
        self.margin = context.marg
        self.frozenMarg = context.frozenMarg
        self.position = context.position
        self.trades = context.trades
        self.orders = context.orders
        self.closeProf = context.closeProf
        self.posProf = context.posProf
        self.daypnl = context.stat.daypnl
        #self.accupnl = context.stat.accupnl
        self.totalpnl = context.stat.totalpnl
        self.dayfees =  context.stat.dayfees
        self.totalfees = context.stat.totalfees
        d = datetime.datetime.strptime(context.curday, "%Y-%m-%d")
        if context.curtime.hour >= 8 and context.curtime.hour < 16:
            self.tradingDay = context.curday
        elif context.curtime.hour < 6:
            
            if d.weekday() < 5:
                self.tradingDay = context.curday
            else:
                self.tradingDay = (d + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
        elif context.curtime.hour > 19:
            if d.weekday() < 4:
                self.tradingDay = (d + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                self.tradingDay = (d + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
        


class qeStratStatistics:
    

    def __init__(self, initCap):
        self.curret = 0.0
        self.balance = 0.0
        self.avail = 0.0
        self.lastPosProf = 0.0
        self.dayfees = 0.0
        self.totalfees = 0.0
        self.daypnl = 0.0
        self.totalpnl = 0.0
        self.opens = {}
        self.closes = {}
        self.dayorders = 0
        self.daycancels = 0
        self.dayopens = 0

        self.maxmarg = 0
        self.turnover = 0
        self.startbal = 0.0
        self.highwater = 0.0
        self.accpnl = 0
        self.accfee = 0
        self.accret = 0
        self.winamount = 0
        self.lossamount = 0
        self.wincount = 0
        self.losscount = 0
        self.daycloses = 0
        self.totalpos = {}
        self.balance = initCap
        self.startbal = initCap
        self.avail = initCap
        self.highwater=initCap
        self.underwater=0
        self.dailyreport = pd.DataFrame(columns=['dayret','accret','daypnl','accpnl','maxmarg',\
                                 'turnover','highwater','drawback','dayfee',\
                                 'accfee','balance','winamount','wincount','lossamount','losscount'])
        self.dailyreport.drop(self.dailyreport.index,inplace=True)                         
    def calcIndicators(self, startbal):
        self.dailyreport['accpnl'] = self.dailyreport['daypnl'].cumsum()
        self.dailyreport['balance'] = startbal + self.dailyreport['accpnl']
        self.dailyreport['accfee'] = self.dailyreport['dayfee'].cumsum()
        self.dailyreport['highwater'] = self.dailyreport['balance'].cummax()
        self.dailyreport['drawback'] = np.where(self.dailyreport['balance'] < self.dailyreport['highwater'], -self.dailyreport['highwater'] + self.dailyreport['balance'], 0)
        self.dailyreport['dayret'] = np.log(self.dailyreport['balance'].astype('float')) - np.log(self.dailyreport['balance'].shift(1).fillna(startbal).astype('float'))
        self.dailyreport['accret'] = self.dailyreport['dayret'].cumsum()
    
    
    
    def crossDay(self,curday,daypnl):
        #print('stat.crossDay', daypnl)
        self.accpnl += self.daypnl
        dayret = np.log(self.balance / self.startbal) if self.startbal > 0 else 0
        self.accret += dayret
        self.accfee += self.dayfees
        #self.highwater = max(self.balance, self.highwater)
        #self.underwater = -self.highwater + self.balance if self.balance < self.highwater else 0
        day = datetime.datetime.strptime(curday, "%Y-%m-%d")
        #self.dailyreport.loc[day, 'dayret'] = dayret
        #self.dailyreport.loc[day, 'accret'] = self.accret
        self.dailyreport.loc[day, 'daypnl'] = daypnl
        #self.dailyreport.loc[day, 'accpnl'] = self.accpnl
        self.dailyreport.loc[day, 'dayfee'] = self.dayfees
        #self.dailyreport.loc[day, 'accfee'] = self.accfee
        #self.dailyreport.loc[day, 'highwater'] = self.highwater
        #self.dailyreport.loc[day, 'drawback'] = self.underwater
        #self.dailyreport.loc[day, 'balance'] = self.balance
        self.dailyreport.loc[day, 'maxmarg'] = self.maxmarg
        self.dailyreport.loc[day, 'turnover'] = self.turnover
        self.dailyreport.loc[day, 'winamount'] = self.winamount
        self.dailyreport.loc[day, 'wincount'] = self.wincount
        self.dailyreport.loc[day, 'lossamount'] = self.lossamount
        self.dailyreport.loc[day, 'losscount'] = self.losscount
        
        self.startbal = self.balance
        self.daypnl = 0
        self.dayopens = 0
        self.daycloses = 0
        self.dayfees = 0
        self.dayorders = 0
        self.daycancels = 0
        self.maxmarg = 0
        self.turnover = 0
        self.underwater = 0
        self.winamount = 0
        self.wincount = 0
        self.lossamount = 0
        self.losscount = 0


class qeContextBase:

    def __init__(self, instid, initCap):
        # self.formula=formula
        self.instid = instid  # list
        self.dataslide = {}
        self.datamode = ''
        self.exID = instid[0][-3:]
        self.traderate = 1
        self.feesMult = 1.0
        self.initCapital = initCap
        self.stat = qeStratStatistics(self.initCapital)
        self.orders = {}
        self.ROrders = pd.DataFrame()
        self.Cancels = {}
        self.trades = {}
        self.marg = 0
        self.frozenMarg = 0
        self.closeProf = 0.0
        self.posProf = 0.0
        self.logret = 0
        self.bCrossDay = False
        self.curtime = None
        self.lasttime = None
        self.curday = ''
        self.lastday = ''
        self.lastvol = {}
        self.curvol = {}
        self.orderid = 0
        self.tradeid = 0
        #self.maxpos = {}
        self.curpnl = 0
        self.printlog = True
        self.flippage = 0
        self.lastclose = {}
        self.current = {}
        self.position = {}
        self.instsett = {}
        self.longpendvol = {}
        self.shortpendvol = {}
        self.frozenVol = {}
        self.openPrice = {}
        #self.maxmarg = 0
        self.hedgemodel = True
        self.formula = ''
        self.record = pd.DataFrame()
        self.d = pd.DataFrame()
        self.highwater=0
        self.savedbardata = {}
        self.addInstids(instid)
        self.prodMaxmarg={}
        self.prodTMaxmarg = {}
        self.prodTurnover={}
        self.instCloseProf = {}
        self.dailyPnl = pd.DataFrame(columns=['daypnl', 'maxmarg', 'turnover'])
        self.presettleL = {}
        self.presettleS = {}
        self.dailySettle = {}
        self.fcDict = {}
            #self.maxpos[instid[i]] = 0

    def addInstids(self, instid):
        
            for i in range(len(instid)):
                self.lastclose[instid[i]] = 0
                self.lastvol[instid[i]] = 0
                self.curvol[instid[i]] = 0
                self.position[instid[i]] = {'long': {'volume': 0, 'poscost': 0, 'yesvol': 0},
                                            'short': {'volume': 0, 'poscost': 0, 'yesvol': 0}}
                self.instsett[instid[i]] = getInstrumentSetting(instid[i].replace('.', '_').upper())
                #self.longpendvol[instid[i]] = {'volume':0,'poscost':0}
                #self.shortpendvol[instid[i]] = {'volume':0,'poscost':0}
                self.openPrice[instid[i]] = 0
                self.stat.opens[instid[i]] = {'long': {'price': np.nan, 'vol': 0},
                                                           'short': {'price': np.nan, 'vol': 0}}
                self.stat.closes[instid[i]] = {'long': {'price': np.nan, 'vol': 0},
                                                           'short': {'price': np.nan, 'vol': 0}}
 


    #def getFrozenVol(self, instid, dirstr):
    #    if instid in self.frozenVol:
    #        if dirstr in self.frozenVol[instid]:
    #            return self.frozenVol[instid][dirstr]
    #    return 0
    def calcFrozenVol(self, instid, direction):
        fvol = 0
        for oid in self.orders:
            order = self.orders[oid]
            if order['instid']==instid and  order['leftvol'] > 0 and order['action']=='close' and order['direction'] == direction:
                fvol += order['leftvol']
        return fvol


    def getMargin(self, price, bLong, vol, instid):
        if not instid in self.instsett:
            return 0
        if isinstance(self.instsett[instid]['marglong'],str):
            marginrate = 0.15
        else:
            marginrate = self.instsett[instid]['marglong'] if bLong else self.instsett[instid]['margshort']
        return price * marginrate / 100 * vol * self.instsett[instid]['volmult']

    def getCommission(self, action, price, vol, yesvol, instid):
        ## Calculate commission by Different Exchange
        ## commissionByMoney and ByVolume, closeToday and closeYesterday
        ## fees multiple
        if vol == 0:
            return 0
        if action == 'open':

            return self.instsett[instid]['openfee'] * vol + self.instsett[instid]['openfeerate'] * vol * price * \
                   self.instsett[instid]['volmult']
        else:
            yesrate = yesvol / vol  # 昨日的持仓占总持仓的比例
            totalrate = self.instsett[instid]['closetodayrate'] * (1 - yesrate) + yesrate if yesrate < 1 else yesrate
            return totalrate * (self.instsett[instid]['closefee'] * vol + self.instsett[instid]['closefeerate'] * vol * price * self.instsett[instid]['volmult'])

    def updateData(self):
        try:

            
                # 最大保证金额
            #if mm > self.stat.maxmarg:  # 如果账户的最大保证金大于规定的最大保证金
            #    self.stat.maxmarg = mm
            if self.datamode == 'daily':
                for inst in self.instid:
                    self.dailySettle[inst] = self.getDataSlide(inst,'settle')
            self.updateMarg()
            self.posProf = self.getPosProf()
            lastcap = self.stat.balance
            self.stat.balance += self.curpnl + self.posProf - self.stat.lastPosProf
            self.stat.lastPosProf = self.posProf
            self.logret = np.log(self.stat.balance / lastcap)
            self.stat.curret += self.logret
            self.stat.avail = self.stat.balance - self.marg - self.frozenMarg
            self.stat.highwater=max(self.stat.highwater,self.stat.balance)
            #self.stat.underwater =   self.stat.balance-self.stat.highwater
        except Exception as e:
            print('updatedata',e.__traceback__.tb_lineno ,e)
    
    def updateProdData(self, curday):
        writeStratStat_wrap(self.stratname, curday.replace('-',''),self.prodMaxmarg,self.prodTurnover) 
        day = datetime.datetime.strptime(curday, "%Y-%m-%d")
        self.dailyPnl.loc[day , 'maxmarg'] = sum([val for val in self.prodMaxmarg.values()])
        self.dailyPnl.loc[day, 'turnover'] = sum([val for val in self.prodTurnover.values()])
        for prod in self.prodMaxmarg:
            if not prod in self.prodTMaxmarg:
                self.prodTMaxmarg[prod] = self.prodMaxmarg[prod]
            else:
                self.prodTMaxmarg[prod] = max(self.prodTMaxmarg[prod], self.prodMaxmarg[prod])
        
    def getSettlePrice(self, inst):
        curday = self.lastday if self.datamode != 'daily' else self.curday
        
        try:
            if self.datamode != 'daily':
                curdate = pd.to_datetime(curday)
                if inst in self.instid and curdate in list(self.dailySettle[inst].index):
                        settle = self.dailySettle[inst].loc[pd.to_datetime(curday),'settle'] 
                else:
                    settle = self.dailySettle[inst].loc[self.dailySettle[inst].index[-1],'settle']
            else:
                settle = self.getDataSlide(inst, 'settle')
        except:
            print('Error on settle price', curday, inst, self.dailySettle[inst])
            settle = 0
            traceback.print_exc()
        return settle
    
    def updateDailyPnl(self, curday):
        prodPnl = {}
        try:
            for inst in self.dailySettle:
                settle = self.getSettlePrice(inst)
                volmult = self.instsett[inst]['volmult']
                if not inst in self.presettleL or self.presettleL[inst] == 0:
                    longprof =  volmult * self.getPosition(inst,'long','volume') *(settle - self.getPosition(inst, 'long','poscost'))
                else:
                    longprof =  volmult * self.getPosition(inst,'long','volume') *(settle - self.presettleL[inst])
                self.presettleL[inst] = settle   if  self.getPosition(inst,'long','volume') > 0 else 0

                if not inst in self.presettleS or self.presettleS[inst] == 0:
                    shortprof = volmult * self.getPosition(inst,'short','volume') *(self.getPosition(inst, 'short','poscost') - settle)
                else:
                    shortprof = volmult * self.getPosition(inst,'short','volume') *(self.presettleS[inst] - settle)
                self.presettleS[inst] = settle   if  self.getPosition(inst,'short','volume') > 0 else 0
                instCloseProf = self.instCloseProf[inst] if inst in self.instCloseProf else 0
                tprof = longprof + shortprof + instCloseProf #- self.stat.dayfees
                prod = getProd(inst)
                if prod in prodPnl :
                    prodPnl[prod] += tprof
                else:
                    prodPnl[prod] = tprof
            if self.record_strat:
                for prod in prodPnl:
                    writeStratPnl_wrap(self.stratname, curday.replace('-',''), prod, prodPnl[prod])    
            day = datetime.datetime.strptime(curday, "%Y-%m-%d")
            daypnl = sum([ val for val in prodPnl.values()]) # - self.stat.dayfees
            #print(daypnl)
            self.dailyPnl.loc[day , 'daypnl'] = daypnl
            return daypnl
        except:
            traceback.print_exc()
    
    ## X > (A-B)/(f1+f2)
    def getFCVol(self, isToday, price, bLong, cost, presett, instid):
        volmult = self.instsett[instid]['volmult']
        yvol = 0 if isToday else 1
        factor1 = self.getMargin(price, bLong, 1, instid)
        cost = presett if not isToday else cost
        priceDiff = price - cost if bLong else cost - price 
        factor2 = priceDiff * volmult - self.getCommission('close',price, 1,yvol,instid)
        return factor1, factor2
        #return np.ceil((marg - balance) / (factor1 + factor2) )
        
        
    def calcForceClose(self, instid, marg, balance):
        A = marg
        B = balance
        tL, yL, tS, yS = self.getPositionVol(instid)
        psL , psS = self.presettleL.get(instid, 0), self.presettleS.get(instid, 0)
        costL, costS = self.getPosition(instid, 'long', 'poscost'), self.getPosition(instid, 'short', 'poscost'), 
        price = self.getCurrent(instid)
        finished = False
        fclist = [0,0,0,0]
        if yL > 0:
            f1, f2 = self.getFCVol(False, price, True, costL, psL, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),yL)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[0] = fcvol
            finished = A < B
        if not finished and yS > 0:
            f1, f2 = self.getFCVol(False, price, False, costS, psS, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),yS)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[1] = fcvol
            finished = A < B
        if not finished and tL > 0:
            f1, f2 = self.getFCVol(True, price, True, costL, psL, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),tL)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[2] = fcvol
            finished = A < B
        if not finished and tS > 0:
            f1, f2 = self.getFCVol(True, price, False, costS, psS, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),tS)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[3] = fcvol
            finished = A < B
        return finished, A, B, fclist
          
    
    
    def checkforceclose(self):
        if self.stat.balance <  self.marg:
            ## touch force close
            ## get max marg instid
            A = self.marg
            B = self.stat.balance
            fcDict = {}
            for instid in self.position:
                finished, A, B, fclist = self.calcForceClose(instid, A, B)
                fcDict[instid] = fclist
                if finished:
                    break
            print('权益低于保证金，触发平台强平操作')
            self.fcDict = fcDict
            #force_close(self, fcDict)

    
    def crossDay(self):
        try:
            self.frozenMarg = 0
            #self.longpendvol = {}
            #self.shortpendvol = {}
            self.savedbardata = {}
            curday = self.lastday if self.datamode != 'daily' else self.curday
            daynum = int(curday.replace('-', ''))*10000
            if len(self.orders) > 0:
                if self.ROrders is None : 
                    self.ROrders = pd.DataFrame.from_dict(self.orders, orient='index')
                    self.ROrders.index = self.ROrders.index + daynum
                else:
                    ROrders = pd.DataFrame.from_dict(self.orders, orient='index')
                    ROrders.index = ROrders.index + daynum
                    self.ROrders = self.ROrders.append(ROrders)
            
            self.orders = {}
            # self.trades = {}
            self.lastvol = {}
            ## on trades
            if self.record_strat:
                writeStratPosition_wrap(self.stratname,curday.replace('-',''),self.position,self.instCloseProf)
                self.updateProdData(curday)
            for inst in self.position:
                self.position[inst]['long']['yesvol'] = self.position[inst]['long']['volume']
                self.position[inst]['short']['yesvol'] = self.position[inst]['short']['volume']
                #self.longpendvol[self.instid[i]] = {'volume':0,'poscost':0}
                #self.shortpendvol[self.instid[i]] = {'volume':0,'poscost':0}
                self.lastvol[inst] = 0
            daypnl = self.updateDailyPnl(curday)
            self.updateMarg()
            #print('crossDay',self.prodMaxmarg)
            if curday != "":
                self.stat.crossDay(curday, daypnl)
                #print('save postion into stratgy market database sucessfully')
            self.checkforceclose()
            self.prodMaxmarg={}
            self.prodTurnover={}
            self.instCloseProf = {}
        except Exception as e:
            logger.error(f'context.crossDay {e.__traceback__.tb_lineno} {e}')
        
    def getDailyData(self, instid):
        curday = self.curtime.strftime('%Y-%m-%d 00:00:00')
        if self.datamode == 'daily':
            d = {curday:{'open':self.dataslide[instid]['open'],
                 'close':self.dataslide[instid]['close'],
                 'high':self.dataslide[instid]['high'],
                 'low':self.dataslide[instid]['low'],
                 'volume':self.dataslide[instid]['volume'],
                 'money':self.dataslide[instid]['money'],
                 'position':self.dataslide[instid]['position'],
                 'upperlimit':self.dataslide[instid]['upperlimit'],
                 'lowerlimit':self.dataslide[instid]['lowerlimit'],
                 'presett':self.dataslide[instid]['presett'],
                 'preclose':self.dataslide[instid]['preclose']}}
            return pd.DataFrame.from_dict(d, orient='index')
        else:
            return pd.DataFrame()

    def checkCrossDay(self):
        if not self.lasttime:
            return False
        if (self.lasttime.hour == 14 or self.lasttime.hour == 15 or self.lasttime.hour == 16) and self.curtime.hour != 14 and self.curtime.hour != 15 and self.curtime.hour != 16:
            return True
        return False

    def dayStatistics(self):
        self.posProf = self.getPosProf(True)    
        self.stat.balance += self.posProf - self.stat.lastPosProf
        self.stat.lastPosProf = self.posProf
        if self.printlog:
            print("Day statistics:", self.lastday)
            print("orders:", int(self.stat.dayorders), "cancels:", int(self.stat.daycancels), 'opens:',
                  int(self.stat.dayopens), "closes:", int(self.stat.daycloses),
                  "dayclosepnl:", round(self.stat.daypnl, 2), "dayfees:", round(self.stat.dayfees, 2))
            print("totalclosepnl:", round(self.stat.totalpnl, 2), "totalfees:", round(self.stat.totalfees, 2),
                  'balance:', round(self.stat.balance, 2), 'accumlated return:',
                  str(round(100 * self.stat.curret, 2)) + '%')

    def totalStatistics(self):
        self.lastday = self.tradingday
        self.posProf = self.getPosProf(True)    
        self.stat.balance += self.posProf - self.stat.lastPosProf
        self.stat.lastPosProf = self.posProf
        if self.printlog:
            print("Total statistics:")
            print(f"Last datetime: {self.curtime}")
            print("totalclosepnl:", round(self.stat.totalpnl, 2), "totalfees:", round(self.stat.totalfees, 2), 'maxmargin:',
                  round(self.stat.maxmarg, 2),
                  'balance:', round(self.stat.balance, 2), 'accumlated return:',
                  str(round(100 * self.stat.curret, 2)) + '%')

    #def updateFrozenMarg(self):
    #    self.frozenMarg = 0
    #    for i in range(len(self.instid)):
    #        self.frozenMarg += self.getMargin(True,self.longpendvol[self.instid[i]]['poscost'], self.longpendvol[self.instid[i]]['volume'], self.instid[i]) + self.getMargin(
    #            False,self.shortpendvol[self.instid[i]]['poscost'],
    #            self.shortpendvol[self.instid[i]]['volume'], self.instid[i])

    def updateFrozenMarg(self):
        fm = 0
        for oid in self.orders:
            order = self.orders[oid]
            if order['leftvol'] >0 and order['action'] == 'open':
                inst = order['instid']
                odir = order['direction']
                if order['ordertype'] == 'market':
                    current = self.getCurrent(inst)
                else:
                    current = order['price']
                if current > 0:
                    fm += self.getMargin(current, odir > 0, order['leftvol'], inst)
        self.frozenMarg = fm        
   
    def updateStatWinLoss(self, closeProf, fee):
        if closeProf > fee:
            self.stat.wincount += 1
            self.stat.winamount += closeProf - fee
        elif closeProf < fee:
            self.stat.losscount += 1
            self.stat.lossamount += closeProf - fee
    
    def updateInstClosePnl(self, instid, dirstr, volmult, tradeprice, tradevol, poscost,fee):
        presettle = self.presettleL.get(instid,0) if dirstr == 'long' else self.presettleS.get(instid,0)
        #presettle = self.presettleL[instid] if dirstr == 'long' else self.presettleS[instid]
        if presettle != 0:
            poscost = presettle
            
        closeProf = volmult * tradevol * (tradeprice - poscost) if dirstr == 'long' else volmult * tradevol * (poscost - tradeprice)
    
        if instid in self.instCloseProf:
            self.instCloseProf[instid] += closeProf - fee
        else:
            self.instCloseProf[instid] = closeProf - fee
            
    
    
    
    def addTrade(self, instid, direction, price, volume, volMult, action, closetype='auto'):
        try:
            result = {}
            closeProf = 0
            tradevol = 0
            prod = getProd(instid)
            if direction > 0:
                #if action == 'open':
                #    self.longpendvol[instid]['volume'] = max(self.longpendvol[instid]['volume'] - volume, 0)
                #    if self.longpendvol[instid]['volume'] <= 0:
                #        self.longpendvol[instid] = {'volume':0,'poscost':0}
                        
                if action != 'open' and self.position[instid]['short']['volume'] > 0:
                    tradevol = volume if volume <= self.position[instid]['short']['volume'] else \
                        self.position[instid]['short']['volume']
                    self.position[instid]['short']['volume'] -= tradevol
                    #self.frozenVol[instid]['short'] = max(0, self.frozenVol[instid]["short"] - tradevol)
                    
                    tradeyesvol = tradevol if tradevol <= self.position[instid]['short']['yesvol'] else \
                        self.position[instid]['short']['yesvol']
                    todayvol = self.position[instid]['short']['volume'] - self.position[instid]['short']['yesvol']
                    if closetype == 'auto' or closetype == 'closeyesterday':
                        self.position[instid]['short']['yesvol'] -= tradeyesvol
                    elif todayvol < tradevol:
                        ## if today volume is not enough , close some yesterday volume
                        self.position[instid]['short']['yesvol'] -= tradevol - todayvol

                    closeProf = volMult * tradevol * (self.position[instid]['short']['poscost'] - price)
                    #fee = self.feesMult * self.getCommission('open', self.position[instid]['short']['poscost'], tradevol, 0, instid)
                    fee = self.feesMult * self.getCommission('close', price, tradevol, tradeyesvol, instid)
                    self.updateStatWinLoss(closeProf, fee)
                    self.updateInstClosePnl(instid, 'short', volMult, price, tradevol, self.position[instid]['short']['poscost'],fee)
                    #self.updateInstClosePnl(instid, closeProf,fee)
                    result["close"] = {'direction': -1, 'price': price,
                                       'poscost': self.position[instid]['short']['poscost'],
                                       'volume': tradevol, 'closeyesvol': tradeyesvol,
                                       'closeProf': closeProf}
                    if self.position[instid]['short']['volume'] <= 0:
                        self.position[instid]['short'] = {'volume': 0, 'poscost': 0, 'yesvol': 0}
                        self.presettleS[instid] = 0
                    volume -= tradevol
                if volume > 0 and action != 'close':
                    if self.position[instid]['long']['volume'] == 0:
                        self.position[instid]['long'] = {'poscost': price, 'volume': volume, 'posProf': 0,
                                                         'yesvol': 0}
                    else:
                        self.position[instid]['long']['poscost'] = (price * volume + self.position[instid]['long'][
                            'poscost'] *
                                                                    self.position[instid]['long']['volume']) / (
                                                                           self.position[instid]['long'][
                                                                               'volume'] + volume)
                        self.position[instid]['long']['volume'] += volume
                    result['open'] = {'direction': 1, 'poscost': price, 'volume': volume}
                    tradevol = volume
            else:
                #if action == 'open':
                #   self.shortpendvol[instid]['volume'] = max(self.shortpendvol[instid]['volume'] - volume, 0)
                #   if self.shortpendvol[instid]['volume'] <= 0:
                #       self.shortpendvol[instid] = {'volume':0,'poscost':0}
                if action != 'open' and self.position[instid]['long']['volume'] > 0:
                    tradevol = volume if volume <= self.position[instid]['long']['volume'] else \
                        self.position[instid]['long']['volume']
                    tradeyesvol = tradevol if tradevol <= self.position[instid]['long']['yesvol'] else \
                        self.position[instid]['long']['yesvol']
                    todayvol = self.position[instid]['long']['volume'] - self.position[instid]['long']['yesvol']
                    if closetype == 'auto' or closetype == 'closeyesterday':
                        self.position[instid]['long']['yesvol'] -= tradeyesvol
                    elif todayvol < tradevol:
                        ## if today volume is not enough , close some yesterday volume
                        self.position[instid]['long']['yesvol'] -= tradevol - todayvol

                    self.position[instid]['long']['volume'] -= tradevol
                    #self.frozenVol[instid]['long'] = max(0, self.frozenVol[instid]["long"] - tradevol)
                    closeProf = volMult * tradevol * (price - self.position[instid]['long']['poscost'])
                    #fee = self.feesMult * self.getCommission('open', self.position[instid]['long']['poscost'], tradevol, 0, instid)
                    fee = self.feesMult * self.getCommission('close', price, tradevol, tradeyesvol, instid)
                    self.updateInstClosePnl(instid, 'long', volMult, price, tradevol, self.position[instid]['long']['poscost'],fee)
                    self.updateStatWinLoss(closeProf, fee)
                    result["close"] = {'direction': 1, 'price': price,
                                       'poscost': self.position[instid]['long']['poscost'],
                                       'volume': tradevol, 'closeyesvol': tradeyesvol, 'closeProf': closeProf}
                    if self.position[instid]['long']['volume'] == 0:
                        self.position[instid]['long'] = {'volume': 0, 'poscost': 0, 'yesvol': 0}
                        self.presettleL[instid] = 0
                    volume -= tradevol
                if volume > 0 and action != 'close':
                    if self.position[instid]['short']['volume'] == 0:
                        self.position[instid]['short'] = {'poscost': price, 'volume': volume, 'posProf': 0,
                                                          'yesvol': 0}
                    else:
                        self.position[instid]['short']['poscost'] = (price * volume +
                                                                     self.position[instid]['short']['poscost'] *
                                                                     self.position[instid]['short']['volume']) / (
                                                                            self.position[instid]['short'][
                                                                                'volume'] + volume)
                        self.position[instid]['short']['volume'] += volume
                    result['open'] = {'direction': -1, 'poscost': price, 'volume': volume}
                    tradevol = volume
            
            #if action == 'close':
            turnover = price * tradevol * self.instsett[instid]['volmult']
            if prod in self.prodTurnover:
                self.prodTurnover[prod] += turnover
            else:
                self.prodTurnover[prod] = turnover
            
            self.stat.turnover += turnover
            self.updateFrozenMarg()
            return result
        except Exception as e:
            print("Add trade fail on ", e.__traceback__.tb_lineno, e)
            return None

    def getPosProf(self, settle=False):
        posProf = 0
        for i in range(len(self.instid)):

            instid = self.instid[i]
            # print(instid)
            volMult = self.instsett[instid]['volmult']
            # print(volMult)
            current = self.getCurrent(instid) if not settle else self.getSettlePrice(instid)

            if self.position[instid]['long']['volume'] != 0:
                # position['long']['posProf'] = volMult * (current - position['long']['poscost']) * position['long']['volume']
                posProf += volMult * (current - self.position[instid]['long']['poscost']) * \
                           self.position[instid]['long']['volume']
            if self.position[instid]['short']['volume'] != 0:
                posProf += volMult * (self.position[instid]['short']['poscost'] - current) * \
                           self.position[instid]['short']['volume']
                # posProf += position['short']['posProf']
        return posProf

    def getPositionVol(self,instid):
        totalL = self.getPosition(instid, 'long', 'volume')
        totalS = self.getPosition(instid, 'short', 'volume')
        yesL = self.getPosition(instid, 'long','yesvol')
        yesS = self.getPosition(instid, 'short', 'yesvol')
        return totalL - yesL , yesL, totalS - yesS, yesS

    def updateMarg(self):
        try:
            self.marg = 0
            prodmarg = {}
            for instid in self.position.keys():
                
                tL, yL, tS, yS = self.getPositionVol(instid)
                margL = self.getMargin(self.getPosition(instid, 'long', 'poscost'), True, tL, instid) 
                if yL > 0:
                    margL += self.getMargin(self.presettleL.get(instid,0), True, yL, instid)
                margS = self.getMargin(self.getPosition(instid, 'short', 'poscost'),False, tS, instid)
                if yS > 0:
                    margS += self.getMargin(self.presettleS.get(instid,0), False, yS, instid)
                marg = margL + margS
                #marg = self.getMargin(self.position[instid]['long']['poscost'], True, self.position[instid]['long']['volume'], instid) + self.getMargin(self.position[instid]['short']['poscost'], False, self.position[instid]['short']['volume'], instid)
                self.marg += marg
                prod = getProd(instid)
                if not prod in prodmarg:
                    prodmarg[prod] = marg
                else:
                    prodmarg[prod] += marg
            self.stat.maxmarg = max(self.marg , self.stat.maxmarg)
            for prod in prodmarg:
                if not prod in self.prodMaxmarg:
                    self.prodMaxmarg[prod] = prodmarg[prod]
                else:
                    self.prodMaxmarg[prod] = max(prodmarg[prod],self.prodMaxmarg[prod])
        except Exception as e:
            logger.error(f'updateMarg {e.__traceback__.tb_lineno} {e}')
        
    def getCurrent(self,instid):
        if instid in self.dataslide:
           if "current" in self.dataslide[instid]:
               return self.dataslide[instid]['current']
           elif "close" in self.dataslide[instid]:
               return self.dataslide[instid]['close']
        return 0

    def getDayStart(self):
        days = 1
        if self.curtime.hour >= 19:
            days = 0
        elif self.curtime.weekday() == 0:
            days = 3
        return (self.curtime - pd.Timedelta(days=days)).strftime("%Y-%m-%d 19:00:00")    
       


    def getDataSlide(self, instid, field):
        if instid in self.dataslide:
            if field in self.dataslide[instid]:
                return self.dataslide[instid][field]
            else:
                logger.warning("Invalide field name",field)

        return 0    
        
    def getPosition(self, instid, direction, field):
        if instid in self.position:
            if direction in self.position[instid]:
                if field in self.position[instid][direction]:
                    return self.position[instid][direction][field]
                else:
                     logger.warning("Invalide field name",field)
                   
        return 0

    def getAccountPosition(self, instid, direction, field):     
        if instid in self.account.position:
            if direction in self.account.position[instid]:
                if field in self.account.position[instid][direction]:
                    return self.account.position[instid][direction][field]
                else:
                    logger.warning("Invalide field name",field)
        return 0
    
        
        
    def checkTrades(self, trades):
        ## Close yesterday first
    
        def statAddTrade(pos, price, vol):
            # print(pos, 'before')
            if not np.isnan(pos['price']):
                pos['price'] = (pos['price'] * pos['vol'] + price * vol) / (pos['vol'] + vol)
                pos['vol'] += vol
            else:
                pos['price'] = price
                pos['vol'] = vol
            # print(pos, 'after')

        try:
            # current = self.current

            # self.stat.opens = {
            # 'instid': {'long': {'price': np.nan, 'vol': 0}, 'short': {'price': np.nan, 'vol': 0}}}
            # self.stat.closes = {
            # 'instid': {'long': {'price': np.nan, 'vol': 0}, 'short': {'price': np.nan, 'vol': 0}}}
            self.stat.opens = {}
            self.stat.closes = {}
            for inst in self.instid:
                self.stat.opens[inst] = {'long': {'price': np.nan, 'vol': 0},
                                                   'short': {'price': np.nan, 'vol': 0}}
                self.stat.closes[inst] = {'long': {'price': np.nan, 'vol': 0},
                                                    'short': {'price': np.nan, 'vol': 0}}

            res = {}
            closeProf = 0
            fees = 0
            bTraded = False
            for id in trades:
                # global tradeinstid1

                tradeprice = trades[id]['tradeprice']
                tradevol = trades[id]['tradevol']
                tradeinstid = trades[id]['instid']
                if not tradeinstid in self.stat.opens:
                    self.stat.opens[tradeinstid] = {'long': {'price': np.nan, 'vol': 0},
                                                   'short': {'price': np.nan, 'vol': 0}}
                if not tradeinstid in self.stat.closes:
                    self.stat.closes[tradeinstid] = {'long': {'price': np.nan, 'vol': 0},
                                                   'short': {'price': np.nan, 'vol': 0}}
                
                
                # print('1',tradeinstid)
                # current = self.current[tradeinstid]
                # print(self.current)
                self.orders[id]['tradevol'] += tradevol
                self.orders[id]['leftvol'] -= tradevol
                res = self.addTrade(tradeinstid, self.orders[id]['direction'], tradeprice,
                                    tradevol, self.instsett[tradeinstid]['volmult'],
                                    self.orders[id]['action'], self.orders[id]['closetype'])
                # print(res.keys())
                
                if self.orders[id]['timecond'] == 'FAK':
                    self.orders[id]['cancelvol'] = self.orders[id]['leftvol']
                    self.orders[id]['leftvol'] = 0
                    self.orders[id]['status'] = 'alltraded' if self.orders[id]['cancelvol'] == 0 else 'ptpc'
                else:    
                    if self.orders[id]['leftvol'] > 0:
                        self.orders[id]['status'] = "parttraded"
                    else:
                        self.orders[id]['status'] = 'alltraded'

                if 'open' in res.keys():
                    # print(20)
                    # print(res['open']['direction'])
                    dirstr = 'long' if res['open']['direction'] > 0 else 'short'
                    if self.printlog:
                        print(self.curtime.strftime("%Y-%m-%d %H:%M:%S"), "Open", dirstr, ", vol",
                              int(res['open']['volume']), \
                              "price(O/T)", self.orders[id]['price'], tradeprice, "position(L/S)", \
                              int(self.position[tradeinstid]['long']['volume']),
                              int(self.position[tradeinstid]['short']['volume']),
                              'posiProf', round(self.posProf, 2), tradeinstid)
                    self.updateMarg()
                    self.stat.dayopens += res['open']['volume']
                    if dirstr == 'long':
                        statAddTrade(self.stat.opens[tradeinstid]['long'], tradeprice, tradevol)
                    else:
                        statAddTrade(self.stat.opens[tradeinstid]['short'], tradeprice, tradevol)
                    openfee = self.feesMult * self.getCommission('open', tradeprice, tradevol, 0, tradeinstid)
                    fees += openfee 
                    if tradeinstid in self.instCloseProf:
                        self.instCloseProf[tradeinstid] -= openfee
                    else:
                        self.instCloseProf[tradeinstid] = - openfee
                    self.tradeid += 1
                    self.posProf = self.getPosProf()
                    
                    self.trades[self.tradeid] = {'time': self.curtime, 'action': 'open', 'dir': dirstr,
                                                 'price': self.orders[id]['price'], 'instid': tradeinstid,
                                                 'tradeprice': tradeprice, 'vol': int(tradevol), 'orderid': id,
                                                 'poscostl': self.position[tradeinstid]['long']['poscost'],
                                                 'poscostS': self.position[tradeinstid]['short']['poscost'],
                                                 'current': self.getCurrent(tradeinstid),
                                                 'posProf': self.posProf, 'closeProf': self.closeProf,
                                                 'date': self.tradingday}
                    bTraded = True

                if 'close' in res.keys():
                    dirstr = 'long' if res['close']['direction'] > 0 else 'short'
                    closeProf += res['close']['closeProf']
                    self.closeProf += res['close']['closeProf']
                    if self.printlog:
                        print(self.curtime.strftime("%Y-%m-%d %H:%M:%S"), "Close", dirstr, "vol/yes",
                              int(res['close']['volume']), \
                              int(res['close']['closeyesvol']), "price(C/T)", self.orders[id]['price'],
                              tradeprice, \
                              "position(L/S)", int(self.position[tradeinstid]['long']['volume']),
                              int(self.position[tradeinstid]['short']['volume']), \
                              'closeProf', round(res['close']['closeProf'], 2), round(self.closeProf, 2), tradeinstid)
                    self.updateMarg()
                    fees += self.feesMult * self.getCommission('close', tradeprice,
                                                               res['close']['volume'], res['close']['closeyesvol'],
                                                               tradeinstid)
                    self.stat.daycloses += res['close']['volume']
                    if dirstr == 'long':
                        statAddTrade(self.stat.closes[tradeinstid]['long'], tradeprice, tradevol)
                    else:
                        statAddTrade(self.stat.closes[tradeinstid]['short'], tradeprice, tradevol)
                    self.tradeid += 1
                    self.posProf = self.getPosProf()
                    self.trades[self.tradeid] = {'time': self.curtime, 'action': 'close', 'dir': dirstr,
                                                 'price': self.orders[id]['price'], 'instid': tradeinstid,
                                                 'tradeprice': tradeprice, 'vol': int(tradevol), 'orderid': id,
                                                 'poscostl': self.position[tradeinstid]['long']['poscost'],
                                                 'poscostS': self.position[tradeinstid]['short']['poscost'],
                                                 'current': self.getCurrent(tradeinstid),
                                                 'posProf': self.posProf, 'closeProf': self.closeProf,
                                                 'date': self.tradingday}
                    bTraded = True

            # self.stat.totalfees += fees

            if bTraded:
                # print(self.marg)
                # print(self.Trades[self.curtime])
                self.stat.daypnl += closeProf
                self.stat.totalpnl += closeProf
                self.stat.dayfees += fees
                # print(closeProf, self.closeProf,self.stat.totalpnl)
                self.stat.totalfees += fees

                self.curpnl = closeProf - fees
            else:
                self.curpnl = 0
                self.lastclose = self.current
        except Exception as e:
            print("Check Trades on line", e.__traceback__.tb_lineno, e)

    def updateTime(self, time):
        # print("time",time)
        self.lasttime = self.curtime
        self.curtime = time
        self.curday = time.strftime('%Y-%m-%d')
        # print('curday',self.curday)
        if self.lasttime:
            # print('lasttime',self.lasttime)
            self.lastday = self.lasttime.strftime('%Y-%m-%d')
            # print('lastday', self.lastday)

    def updateOpenPrice(self, instid):
        if 'open' in self.dataslide[instid].keys() and self.dataslide[instid]['open'] and self.dataslide[instid][
            'open'] > 0:
            self.openPrice[instid] = self.dataslide[instid]['open']
        else:
            self.openPrice[instid] = self.current[instid]

    def isTradeTime(self):
        return is_valid_trade_time(self.instid[0], self.curtime)  # all the contracts trades on the same time






def akshare_data_convert(dataDict, source, datamode, data_type='stock',tick_date=None):
    '''
    

    Parameters
    ----------
    dataDict : Dict
        DESCRIPTION.
    source : str
        DESCRIPTION.
    datamode : str
        DESCRIPTION.
    data_type : str, optional
        DESCRIPTION. The default is 'stock'.
    tick_date : str, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    TYPE
        DESCRIPTION.
    TYPE
        DESCRIPTION.

    '''
    source_collection =['sina','tencent','163']
    freq_collection = ['daily','minute','tick']
    data_type_collection = ['stock','index','kcb']

    if not isinstance(dataDict, dict):
        print ("dataDict should be a dict which key is instrumentID and value is pandas.DataFrame")
        return None
    
    for k in dataDict.keys():
        if not isinstance(k, str):
            print("dataDict's key should be instrumentID")
            return None
        if not isinstance(dataDict[k], pd.DataFrame):
            print("dataDict's value should be pandas.DataFrame")
            return None
           
    
    if not source in source_collection:
        print("source must be one of ", source_collection, "your data:", source)
        return None

    if not datamode in freq_collection:
        print("datamode must be one of ", freq_collection, "your data:", datamode)
        return None

    if not data_type in data_type_collection:
        print("data_type must be one of ", data_type_collection, "your data:", data_type)
        return None 
    
    l = list(dataDict.keys())
    for i in range(len(l)):
        instid = l[i]
        df = dataDict[instid]
        if i == 0:
            df1 = convert_I(df,instid,source,datamode,data_type,tick_date)
            if len(df1) == 0:
                print('Can not find data of', instid, 'in this period.')
                return (None,[])
        else:
            tempdf = convert_I(df,instid,source,datamode,data_type,tick_date)
            if len(tempdf) == 0:
                print('Can not find data of', instid, 'in this period.')
                return (None,[])
            df1 = pd.merge_ordered(df1, tempdf, on='time', fill_method="ffill",
                                              suffixes=("", instid))
            #df1 = pd.concat(df1,tempdf)
            
    if len(l) > 1:
        df1.index = df1['time']
    else:
        df1['time'] = df1.index
        
    return (df1,l)

        
def convert_I(df,instid,source,datamode,data_type='stock',date=None):
    import pandas as pd
    import copy

#     source_collection =['sina','tencent','163']
#     freq_collection = ['daily','minute','tick']
#     data_type_collection = ['stock','index','kcb']

#     if not source in source_collection:
#         print("source must be one of ", source_collection, "your data:", source)
#         return None

#     if not datamode in freq_collection:
#         print("datamode must be one of ", freq_collection, "your data:", datamode)
#         return None

#     if not data_type in data_type_collection:
#         print("data_type must be one of ", data_type_collection, "your data:", data_type)
#         return None  

    try:
        df = copy.copy(df)      
        tempdf = pd.DataFrame()
        title = {'成交价格':'current','成交量':'volume','成交量(手)':'volume','成交额':'money','成交额(元)':'money',
                'amount':'money'}
        
        if len(df) == 0:
            return tempdf
        
        if source == 'sina':
            
            if datamode== 'daily' and (data_type== 'stock' or data_type == 'index'):

                for tempdata in df.columns:
                    if tempdata != 'date':
                        tempdf[tempdata] = df[tempdata].astype('float')
                tempdf['money'] = tempdf['close'] - tempdf['close']
                tempdf['position'] = tempdf['money']
                tempdf['upperlimit'] = tempdf['position']
                tempdf['lowerlimit'] = tempdf['position']
                tempdf['presett'] = tempdf['position']
                tempdf['preclose'] = tempdf['position']
                df['time'] = df['date']
                tempdf.index = pd.to_datetime(df['time'])
                #tempdf['time'] = tempdf.index
                tempdf.columns = tempdf.columns +'-'+ instid
                return tempdf
            
            elif datamode== 'daily' and data_type == 'kcb':
                
                for tempdata in df.columns:
                    if tempdata != 'date':
                        tempdf[tempdata] = df[tempdata].astype('float')
                tempdf['money'] = tempdf['close'] - tempdf['close']
                tempdf['position'] = tempdf['money']
                tempdf['upperlimit'] = tempdf['position']
                tempdf['lowerlimit'] = tempdf['position']
                tempdf['presett'] = tempdf['position']
                tempdf['preclose'] = tempdf['position']
                df['time'] = df.index
                tempdf.index = pd.to_datetime(df['time'])
                #tempdf['time'] = tempdf.index
                tempdf.columns = tempdf.columns +'-'+ instid
                return tempdf
            elif datamode == 'minute':
                for tempdata in df.columns:
                    if tempdata != 'day':
                        tempdf[tempdata] = df[tempdata].astype('float')
                tempdf['money'] = tempdf['close'] - tempdf['close']
                df['time'] = df['day']
                tempdf.index = pd.to_datetime(df['time'])
                #tempdf['time'] = tempdf.index
                tempdf.columns = tempdf.columns +'-'+ instid
                return tempdf
            
        elif source == 'tencent':
            
            if datamode == 'tick':
                if date is None:
                    print("please provide date for tick data")
                    return tempdf
                else:          
                    temptitle = list(df.columns)
                    for i in range(len(temptitle)):
                        a = title.get(temptitle[i],-1)
                        if a != -1:
                            temptitle[i] = a
                    df.columns = temptitle   
                    for tempdata in df.columns:
                        if tempdata != '成交时间':
                            
                            if tempdata != '性质':
                                tempdf[tempdata] = df[tempdata].astype('float')
                            else:
                                tempdf[tempdata] = df[tempdata]
                                
                    tempdf['high'] = tempdf['current'] - tempdf['current']
                    tempdf['low'] = tempdf['current'] - tempdf['current']
                    tempdf['position'] = tempdf['low']
                    tempdf['a1_p'] = tempdf['low']
                    tempdf['b1_p'] = tempdf['low']
                    tempdf['a1_v'] = tempdf['low']
                    tempdf['b1_v'] = tempdf['low']
                    
                    tempstring = date.replace("/","")
                    tempstring = tempstring.replace("-","")
                    tempstring = tempstring[:8]+" "
                    df['time'] = tempstring + df['成交时间']
                    
                    tempdf['tradingday'] = int(tempstring)               
                    tempdf.index = pd.to_datetime(df['time'])  
                    #tempdf['time'] = tempdf.index
                    tempdf.columns = tempdf.columns +'-'+ instid
                    return tempdf
                
            elif datamode == 'daily' and data_type == 'index':
                for tempdata in df.columns:
                    if tempdata != 'date':
                        tempdf[tempdata] = df[tempdata].astype('float')
                tempdf['money'] = tempdf['amount']

                del tempdf['amount']

                tempdf['position'] = tempdf['close'] - tempdf['close']
                tempdf['upperlimit'] = tempdf['position']
                tempdf['lowerlimit'] = tempdf['position']
                tempdf['presett'] = tempdf['position']
                tempdf['preclose'] = tempdf['position']
                df['time'] = df['date']
                tempdf.index = pd.to_datetime(df['time'])
                #tempdf['time'] = tempdf.index
                tempdf.columns = tempdf.columns +'-'+ instid
                return tempdf
                    
        elif source == '163':
            # tick has issue
            return None

    except Exception as e:
        print("convert_I error", e)

#stock_zh_a_daily_hfq_df = ak.stock_zh_a_daily(symbol="sh600582", adjust="hfq") #sina
# print(stock_zh_a_daily_hfq_df.head())

#stock_zh_index_daily_df = ak.stock_zh_index_daily(symbol="sz399552")
#print(stock_zh_index_daily_df.head())

#stock_zh_a_minute_df = ak.stock_zh_a_minute(symbol='sz000876', period='1', adjust="qfq") # sina
#print(stock_zh_a_minute_df.head())

#stock_zh_a_tick_tx_df = ak.stock_zh_a_tick_tx("sh600848", trade_date="20191011") # tencent
# print(stock_zh_a_tick_tx_df.columns)

#stock_zh_a_tick_163_df = ak.stock_zh_a_tick_163("sh600848", trade_date="20200408") # 163
#print(stock_zh_a_tick_163_df)



def showOpenClose(Report, instids, stgtype=None):
    if stgtype == 'hedge':

        plt.figure(figsize=(16, 10))
        plt.plot(Report.index, Report['current'], color='lightgrey', label='Price')

        if 'openlong' in Report.columns:
            plt.scatter(Report.index, Report['openlong'], marker='^', c='r', label='Open Long position')
        if 'closelong' in Report.columns:
            plt.scatter(Report.index, Report['closelong'], marker='x', c='r', label='Close long position')
        if 'openshort' in Report.columns:
            plt.scatter(Report.index, Report['openshort'], marker='v', c='b', label='Open short position')
        if 'closeshort' in Report.columns:
            plt.scatter(Report.index, Report['closeshort'], marker='x', c='b', label='Close short position')
        plt.xlabel('Data Index')
        plt.title('Open and Close Actions of instid')
        plt.ylabel('Price')
        plt.legend(loc=0)
        plt.grid()
        plt.show()
    else:
        try:
            for inst in instids:
                plt.figure(figsize=(16, 10))
                if 'current' in Report[inst].columns:
                    plt.plot(Report[inst].index, Report[inst]['current'], color='lightgrey', label='Price')
                else:
                    plt.plot(Report[inst].index, Report[inst]['close'], color='lightgrey', label='Price')
                    
                if 'openlong' in Report[inst].columns:
                    plt.scatter(Report[inst].index, Report[inst]['openlong'], marker='^', c='r',
                            label='Open Long position')
                if 'closelong' in Report[inst].columns:
                    plt.scatter(Report[inst].index, Report[inst]['closelong'], marker='x', c='r',
                            label='Close long position')
                if 'openshort' in Report[inst].columns:
                    plt.scatter(Report[inst].index, Report[inst]['openshort'], marker='v', c='b',
                            label='Open short position')
                if 'closeshort' in Report[inst].columns:
                    plt.scatter(Report[inst].index, Report[inst]['closeshort'], marker='x', c='b',
                            label='Close short position')
                plt.xlabel('Data Index')
                plt.title('Open and Close Actions of ' + inst)
                plt.ylabel('Price')
                plt.legend(loc=0)
                plt.grid()
                plt.show()
        except Exception as e:
            print("ShowOpenClose", e)


def showPnlRets(Report):
        fig = plt.figure(figsize=(16, 10))
        ax = fig.add_subplot(111)
        ax.plot(Report.index, Report['accret'], '-', c='red', label='Accumulative Return')
        ax.plot(Report.index, Report['dayret'], '-', c='orange', label='Daily Log Return')
        ax.legend(loc=2)
        ax.grid()
        ax.set_title('Return and P&L Curves of instid')
        ax.set_xlabel('Date')
        ax.set_ylabel('Return Rate')
        ax2 = ax.twinx()
        ax2.plot(Report.index, Report['accpnl'], '-r', c='darkblue', label='Total P&L')
        ax2.plot(Report.index, Report['accfee'], '-r', c='mediumblue', alpha=0.5, label='Total Commission')
        ax2.legend(loc=4)
        ax2.set_ylabel("money:RMB")
        plt.show()


def showPosBalance(Report):
        Report.index = np.array(Report.index)
        fig = plt.figure(figsize=(16, 10))
        ax = fig.add_subplot(111)
        ax.plot(Report.index, Report['balance'], '-', c='blue', label='Balance')
        #line1=Report[instids[0]]['underwater']
        #line1
        #ax.fill_between(Report[instids[0]].index,0,Report[instids[0]]['underwater'],'lightblue')
        ax.legend(loc=2)
        #ax.grid()
        ax.set_title('Balance and Position Curves')
        ax.set_xlabel('Date')
        ax.set_ylabel('money:RMB')
        ax2 = ax.twinx()
        # ax2.plot(Report.index, Report['longpos'],'-r',c='red',label='Long Position')
        # ax2.plot(Report.index, Report['shortpos'],'-r',c='green',label='Short Position')
        ax2.plot(Report.index, Report['drawback'], '-', c='orange', label='underwater')
        ax2.fill_between(Report.index.values, list(Report['drawback']),0, facecolor='orange', alpha=0.3)
        
        ax2.scatter(Report.index, Report['maxmarg'], s=20, marker='o',
                        alpha=0.5,
                        label='maxmargin')
        
        ax2.legend(loc=4)
        ax2.set_ylabel("Maxium Margin")
        plt.show()


def calculateOpenClose(context, formula, instid, calculatetype, dir_index):
    inst_leng=len(instid)
    a = inst_leng * ['0']
    tdir = 0
    if calculatetype == 'open':
        for i in range(len(instid)):
            if dir_index == 'long':
                tdir = 1
            else:
                tdir = 2
            # print(context.stat.opens)
            if not np.isnan(context.stat.opens[instid[i]]['long']['price']):
                a[i] = context.stat.opens[instid[i]]['long']['price']

            else:
                a[i] = context.stat.opens[instid[i]]['short']['price']

    else:
        for i in range(len(instid)):
            if dir_index == 'long':
                tdir = 3
            else:
                tdir = 4
            if not np.isnan(context.stat.closes[instid[i]]['long']['price']):
                a[i] = context.stat.closes[instid[i]]['long']['price']

            else:
                a[i] = context.stat.closes[instid[i]]['short']['price']
    dict1={}
    list2 = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
             'v', 'w', 'x', 'y', 'z']
    for i in range(inst_leng):
        dict1[list2[i]] = a[i]

    multiresult = eval(formula, dict1)

    if tdir == 1:
        return multiresult, np.nan, np.nan, np.nan
    elif tdir == 2:
        return np.nan, multiresult, np.nan, np.nan
    elif tdir == 3:
        return np.nan, np.nan, multiresult, np.nan
    else:
        return np.nan, np.nan, np.nan, multiresult


def calculatemul(context, formula, instid, calculatetype):
    #a = [0, 0, 0, 0, 0]
    inst_leng=len(instid)
    a = inst_leng * ['0']
    for i in range(len(instid)):
        a[i] = context.getCurrent(instid[i])
    dict1={}
    list2 = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
             'v', 'w', 'x', 'y', 'z']
    for i in range(inst_leng):
        dict1[list2[i]] = a[i]
    multiresult = eval(formula, dict1)
    # print(multiresult)
    return multiresult


def checkFormula(num, formula):
    a = num*['0']
    import random
    for i in range(num):
        a[i] = random.randint(10, 1000)
    try:
        dict1={}
        list2 = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                 'u',
                 'v', 'w', 'x', 'y', 'z']
        for i in range(num):
            dict1[list2[i]] = a[i]
        #print(dict1)
        eval(formula, dict1)
    except Exception:
        return False
    return True


def mergedf(insts, start_date, end_date, datamode, freq=1,printlog=True):
    try:
        if printlog:
            print("Data is merging...")
        num = 0
        i = 0
        if datamode == 'tick':
            for i in range(len(insts)):
                multipledf = get_ticks(insts[i], start_date, end_date, fields=None,silent=True)
                if not multipledf is None and len(multipledf) > 0:
                    num+=1
                    break
            starti = i
            if multipledf is None or len(multipledf) == 0:
                return pd.DataFrame()
            else:
                multipledf.columns = multipledf.columns +'-'+ insts[starti]
                for i in range(starti+1, len(insts)):
                    instdf = get_ticks(insts[i ], start_date, end_date, fields=None,silent=True)
                    if instdf is None or len(instdf) == 0:
                        continue
                    # print(instdf)
                    num += 1
                    instdf.columns = instdf.columns+'-' + insts[i ]
                    multipledf = pd.merge_ordered(multipledf, instdf, on='time', fill_method="ffill")


        elif datamode == 'minute':
            freq = str(freq) + 'T'
            for i in range(len(insts)):
                multipledf = get_price(insts[i], start_date, end_date, freq=freq, fields=None,silent=True)
                if not multipledf is None and len(multipledf) > 0:
                    num+=1
                    break
            starti = i
            if multipledf is None or len(multipledf) == 0:
                return pd.DataFrame()
            else:
                multipledf.columns = multipledf.columns+'-' + insts[starti]
                for i in range(starti+1, len(insts)):
                    instdf = get_price(insts[i ], start_date, end_date, freq=freq, fields=None,silent=True)
                    if instdf is None or len(instdf) == 0:
                        continue
                    # print(instdf)
                    num += 1
                    instdf.columns = instdf.columns+'-' + insts[i ]
                    multipledf = pd.merge_ordered(multipledf, instdf, on='time', fill_method="ffill")
        else:
            for i in range(len(insts)):
                multipledf = get_price(insts[i], start_date, end_date, freq='daily', fields=None,silent=True)
                if not multipledf is None and len(multipledf) > 0:
                    num += 1   
                    break
            starti = i      
            if multipledf is None or len(multipledf) == 0:
                return pd.DataFrame()
            
            else:
                multipledf.columns = multipledf.columns +'-'+ insts[starti]
                for i in range(starti+1, len(insts)):
                    instdf = get_price(insts[i], start_date, end_date, freq='daily', fields=None,silent=True)
                    if instdf is None or len(instdf) == 0:
                        continue
                    num += 1
                    instdf.columns = instdf.columns +'-'+ insts[i]
                    multipledf = pd.merge_ordered(multipledf, instdf, on='time', fill_method="ffill")
        if num > 1:
            multipledf.index = multipledf['time']
        else:
            multipledf['time'] = multipledf.index
        multipledf = multipledf.fillna(0)
        return (multipledf)
    except Exception as e:
        print("Merge dataFrame error: ", e.__traceback__.tb_lineno, e)


# multiple instid back test
def historyDataBackTest(user, datamode, instids, start_date, end_date, strat, feesmult=1.0 ,exdata=None, printlog=True, initCap=10000000,showchart=False,rfrate=0.00, record_strat=False):
    
    '''


    Parameters
    ----------
    hedge_model: hedgeModel class
    paramter: formula

    datamode : 'daily'/'minute'/'tick'
        Data sample frequecy.
    instids : []
        List of instrumentIDs.
    start_date : str
        Start date, i.e. '2021-01-01'.
    end_date : TYPE
        End date, i.e. '2021-10-10'.
    strat : qeStratBase class
        Strategy of client.
    initCap: float
        initial Capital
    formula : str or None, optional
        If only one instrumentID, should be None. The default is None.
        If have multiple instrumentIDs, it should be the formula to calculate results.
        Such as 'a+b-2c' means Price of instids[0] + Price of instids[1] - 2*Price of instids[2]
    exdata: pandas.DataFrame or None, optional
        it only available under 'daily' or 'minute' mode, and its start_date/end_date/length must equal to results of get_price
    printlog : Boolean, optional
        If print the Open/Close infomation. The default is True.

    Returns
    -------
    Results : None or dict as {"Report": Report, "Orders": Orders, "Trades":Trades}
        Report : pandas.DataFrame
            detail reports such as order, trade , return rates, capitals on every single ticks.
        Orders :  pandas.DataFrame
            every order action details with timestamps.
        Trades : pandas.DataFrame
            every trade details with timestamps.
        Cancels: pandas.DataFrame
            every cancel details with timestamps.

    '''
    '''
    if len(instids) > 10:
        print("the max number of instruments is 10")
        return None
     '''
    '''
    if not isinstance(df, pd.DataFrame):
        print("df is not pandas.DataFrame")
        return None
    if len(df) == 0:
        print("length of df is zero")
        return None

    if not datamode in ['tick', 'minute', 'daily']:
        print("Unkonwn datamode")
        return None

    if hedge_model is None:
        pass # normal model
    elif not isinstance(hedge_model, hedgeModel):
        pass # hedgemode illegal, normal model
    else:

        if hedge_model.formula is None:
            pass # normal model
        elif hedge_model.formula is not None and len(instids) == 1:
            pass # normal model
        else:
            formula = hedge_model.formula    # hedegemodel
    '''

    '''
    formula = strat.formula
    if len(instids) == 1 and formula:
        print('Single instrument donot need formula.')
        return None
    elif len(instids) > 1:
        if not formula:
            print('Multiple instrument need formula.')
            return None
        elif not isinstance(formula, str):
            print("Formula is not str")
            return None
        elif not checkFormula(len(instids), formula):
            print('Check formula string failure, please check the API document.')
            return None
    '''
    if datamode == 'hour':
        datamode = 'minute'
        strat.datamode = datamode
        strat.freq = 60
    elif datamode == 'minute':
        if strat.freq == 0:
            strat.freq = 1
    
    elif not datamode in ['tick', 'minute', 'daily']:
        print("Unkonwn datamode")
        return None
   
    for i in range(len(instids)):
        if not is_valid_instID(instids[i].upper()):
            print("instid is not valid")
            return None
    
    df = mergedf(instids, start_date, end_date, datamode, strat.freq, printlog)
    strat.start_date = start_date
    strat.end_date = end_date
    #print(datamode,datafreq, len(df), df.columns)
    report = runBacktest(user, df,datamode, instids, strat, exdata=exdata, feesmult=feesmult, initCap=initCap,printlog=printlog,external_flag=False,showchart=showchart,rfrate=rfrate,
                         record_strat=record_strat)
    return report




def getAddress(user, rfrate):
    # webaddress = socket.gethostbyname(socket.gethostname())
    ip = '127.0.0.1:5000'
    json_data = read_sysconfig()
    if json_data:
        ip = f"{json_data['webpage']['host']}:{json_data['webpage']['port']}"

    address="http://" + str(ip) + "/backtest?user=" + str(user) + "&rfrate=" + str(rfrate)

    return address



def runBacktest(user, df,datamode, instids, strat, record_strat=False,exdata=None, feesmult=1.0, initCap=10000000, printlog=True, external_flag=True, showchart = False,rfrate=0.00):
    '''
    

    Parameters
    ----------
    df : pandas.DataFrame
        DESCRIPTION.
    datamode : 'daily'/'minute'/'tick'
        Data sample frequecy.
    instids : []
        List of instrumentIDs.
    strat : qeStratBase
        The strategy instance.
    exdata : TYPE, optional
        DESCRIPTION. The default is None.
    feesmult : TYPE, optional
        DESCRIPTION. The default is 1.0.
    initCap : TYPE, optional
        DESCRIPTION. The default is 10000000.
    printlog : TYPE, optional
        DESCRIPTION. The default is True.
    external_flag : TYPE, optional
        DESCRIPTION. The default is True.

    Returns
    -------
    None.

    '''
    if not isinstance(strat, qeStratBase):
        print("strat is not a instance of qeStratBase")
        return None

    if not isinstance(instids, list):
        print("instid is not list")
        return None
    
    recordinsts = strat.recordinsts
    if recordinsts:
        if not isinstance(recordinsts, list):
            print("recordinstid is not list")
            return None
        for inst in recordinsts:
            if not inst in instids:
                print("member of recordinsts ",inst, "is not in instids:")
                return None

    if not isinstance(feesmult, float):
        print("feesmult is not float")
        return None
    if feesmult<0:
        print("feesmult can't be negative")
        return None
    if initCap<0:
        print("initCap can't be negative")
        return None
    validdatamode = ['tick', 'minute', 'daily']
    if not datamode in validdatamode:
        print("Unkonwn datamode,only suport", validdatamode)
        return None
    #print(strat.datamode)  
    

    if df is None:
        return None
    if datamode == 'tick' and not exdata is None:
        print('The exdata cannot be used under tick mode')
        return None
    if not exdata is None:
        if len(exdata) != len(df) or exdata.index[0] != df.index[0] or exdata.index[-1] != df.index[-1]:
            print('Warning: The exdata should have same time index with get_price. Exdata length: ', \
                  len(exdata), 'vs data length:', len(df))
            #return None

    dir_index = strat.direction_index

    if not isinstance(dir_index, int):
        print('strat.direction_index should be integral')
        return None
    elif dir_index >= len(instids) or dir_index < 0:
        print('strat.direction_index should be an index(>=0) and less than lenghth of instids.')
        return None
    # judge the type of th strategy
    initBacktestLogger(printlog)
    clearBackTestData(user)

    formula = strat.formula
    
    context = qeContextBase(instids, initCap)
    context.account = testAccountInfo(initCap)
    #print(context.instid)
    context.formula = formula
    context.datamode = datamode
    context.traderate = strat.traderate
    context.freq = strat.freq
    context.feesMult = feesmult
    context.printlog = printlog
    context.flippage = strat.flippage
    context.runmode = 'test'
    context.instids = instids
    context.record_strat = record_strat
    if record_strat:
        assert hasattr(strat, 'name'),'Record strategy must have formal name, set strat.name firstly please'
        context.stratname = strat.name
        if not strat._append_mode:
            clearStratTrades_wrap(strat.name)
    
    if context.datamode != 'daily':
        ## Save daily settle price
        dstart = df.index[0]
        dend = df.index[-1] + pd.Timedelta(days=1)
        for inst in context.instid:
            context.dailySettle[inst] = get_price(inst, dstart,dend,'daily',fields=['settle'])
    
    if printlog:
        print("total", len(df), 'records')

    if len(instids) == 1:
        if formula:
            print('Single instrument donot need formula.')
            return None
        elif not formula:
            print('single instrument strategy')
            context.hedgemodel = False
    elif len(instids) > 1:
        if not formula:
            print('Multiple instruments with no hedging Strategy')
            context.hedgemodel = False
        elif not isinstance(formula, str):
            print("Formula is not str")
            return None
        elif not checkFormula(len(instids), formula):
            print('Check formula string failure, please check the API document.')
            return None
        else:
            if printlog:
                print('hedging Strategy')
            context.hedgemodel = True

    # if not exdata is None:
    #    df = pd.concat([df,exdata],axis=1, join='inner')

    # print(context.orders)
    # print(context.trades)
    # print(context.position)
    if printlog:
        print('Initcap', context.initCapital, 'balance', context.stat.balance, 'avail', context.stat.avail)

    if not context.instsett:
        print("Failed to get instrument settings of ", instids.upper())
        return None

    # Report = {}
    #try:
    #    strat.initStrat(context)
    #except Exception as e:
    #    logger.error(f'Error on strat.initStrat:{e}')
    #    return None
    try:
        if printlog:
            print("start backtest on current strategy...")
        
        if not 'time' in df.columns:
            df['time'] = df.index
        
        context.daystart = 0   
        context.bardata = {}
        df_dict = {}
        
        for inst in instids:
                
                if not external_flag:
                                       
                    colname = [x for x in df.columns if inst in x.split('-')]
                    if len(colname) > 0:
                        #print(colname)
                        df_dict[inst] = pd.concat([df['time'], (df.loc[:, colname])], axis=1)
                        # print(df1)
    
                        if datamode == 'tick':
                            dfname = ['time','current','open', 'volume', 'money', 'position', 'a1_p', 'a1_v',
                                      'b1_p',
                                      'b1_v', 'tradingday']
    
                            df_dict[inst].columns = dfname
                            
                        elif datamode == 'minute':
                            dfname = ['time', 'open', 'close', 'high', 'low', 'volume', 'money']
                            df_dict[inst].columns = dfname
                        else:
                            dfname = ['time', 'open', 'close', 'high', 'low', 'volume', 'money', 'position', 'upperlimit',
                                      'lowerlimit', 'presett', 'preclose','settle']
                            df_dict[inst].columns = dfname
                else:
                    colname = [x for x in df.columns if  inst in x.split('-') ]
                    #print(colname)
                    df_dict[inst] = pd.concat([df['time'], (df.loc[:, colname])], axis=1)
                    tempcolumns = ['time']
                    for title in colname:
                        tempa = title.split('-')
                        tempcolumns.append(tempa[0])
#                         print(tempcolumns) 
                    
                    df_dict[inst].columns = tempcolumns
            
        for i in range(len(df)):
            #print(i)
            # print(df)
            ##generate orders, position, capital, returns
            if not exdata is None:
                if df.index[i] in exdata.index:
                    context.dataslide['extra'] = exdata.loc[df.index[i], :].to_dict()
                else:
                    context.dataslide['extra'] = None
                

            for inst in instids:        
   
                # print(df1)
                if inst in df_dict:
                    context.dataslide[inst] = df_dict[inst].iloc[i, :].to_dict()
                    if datamode != 'tick' and datamode != 'daily':
                        context.bardata[inst]  = df_dict[inst].iloc[context.daystart:(i+1), :]
                    #print(context.dataslide)
                    context.current[inst] = context.dataslide[inst]['current'] if datamode == 'tick' else \
                        context.dataslide[inst]['close']
                    # print(context.current)
                    curtime = df_dict[inst]['time'][i]  # curtime = df.index[i]
                # print("curtime",curtime)
                # print(type(curtime))
                
                # for i in range(len(instids)):
                #    if context.lastclose[instids[i]] == 0:
                #             context.lastclose[instids[i]] = context.dataslide[instids[i]]['close']
                #            context.lastclose[instids[i]] = 0
                #        else:
                #            context.curvol[instids[i]] = context.dataslide[instids[i]]['volume'] - context.lastvol[instids[i]]
                #            context.lastvol[instids[i]] = context.dataslide[instids[i]]['volume']
    
                #print(context.curtime,context.lasttime, context.curday, context.lastday) #get those values
    
                if datamode == 'tick':  # 在tick中volume是累积成交量
                    if context.lastvol[inst] == 0:
                        context.lastvol[inst] = context.dataslide[inst]['volume']
                        context.curvol[inst] = 0
                    else:
                        context.curvol[inst] = context.dataslide[inst]['volume'] - context.lastvol[
                            inst]
                        context.lastvol[inst] = context.dataslide[inst]['volume']
                else:
                    context.curvol[inst] = context.dataslide[inst]['volume']  # minute中就是成交量
        
    
            context.updateTime(curtime)
            context.tradingday = context.curday if datamode == 'daily' else context.account.tradingDay
            context.tradingday = context.tradingday.replace('-','')
            #print(context.tradingday, context.curtime, context.isTradeTime())

            if True: # datamode == 'daily' or context.isTradeTime():  # 判断是否是交易时间
                # print(trades)
                if datamode != "daily":
                    context.bCrossDay = context.checkCrossDay()  # 判断是否隔一天
                    if context.bCrossDay:  # 如果隔了一天
                        if printlog:
                            context.dayStatistics()
                        context.crossDay()
                        context.daystart = i
                        try:
                            strat.crossDay(context)
                        except Exception as e:
                            logger.error(f"Error on strat.crossDay, {e}")
                            return None
                        if len(context.fcDict) > 0:
                            force_close(context)
                            context.fcDict = {}

                if datamode == 'tick':
                    trades = strat.matchTrade(context, datamode)
                    context.checkTrades(trades)  # trades表和position表的数据都更新了
                    context.updateData()  # 更新一些统计数据
                    
                context.account.setData(context)
                if datamode == 'tick':
                    try:
                        strat.handleData(context)
                    except Exception as e:
                        logger.error(f"{context.curtime},Error on strat.handleData {e}")
                        return None
                else:
                    try:
                        context.bartime = context.curtime
                        strat.onBar(context)
                    except Exception as e:
                        logger.error(f"{context.curtime},Error on strat.onBar {e}")
                        return None
                   # print(context.orders)

                if datamode != 'tick':
                    trades = strat.matchTrade(context, datamode)
                    context.checkTrades(trades)  # trades表和position表的数据都更新了
                    context.updateData()  # 更新一些统计数据
                    if datamode == "daily":
                        context.crossDay()
                        try:
                            strat.crossDay(context)
                        except Exception as e:
                            logger.error(f"Error on strat.crossDay {e}")
                            return None
                        if len(context.fcDict) > 0:
                            force_close(context)
                            context.fcDict = {}


 
                                                                            
            # print(Report)
            # print(Report['longpos' + instids[0]])
        if context.curtime.hour == 14 or context.curtime.hour == 15:
            context.crossDay()
            if printlog:
                context.dayStatistics()

        context.totalStatistics()
        if printlog:
            print('Generate reports...')
        # print(context.trades)

        # Reportmul['Report' + instids[i]] = Report
            
        #if len(context.ROrders) > 0:
        #    ROrders = pd.DataFrame.from_dict(context.ROrders, orient='index')
        #    ROrders.columns = ['orderid', 'price', 'direction', 'volume', 'ordertype', 'closetype', 'action',
        #                       'errorid',
        #                       'errormsg']
        #else:
        adddays = 1 if context.curtime.weekday() < 4 else 3
        curday = context.curtime + pd.Timedelta(days=adddays) 
        daynum = int(curday.strftime('%Y%m%d'))*10000
        if len(context.orders) > 0:
            if context.ROrders is None : 
                context.ROrders = pd.DataFrame.from_dict(context.orders, orient='index')
                context.ROrders.index = context.ROrders.index + daynum
            else:
                ROrders = pd.DataFrame.from_dict(context.orders, orient='index')
                ROrders.index = ROrders.index + daynum
                context.ROrders = context.ROrders.append(ROrders)

        if context.ROrders is None:    
            context.ROrders = pd.DataFrame()
        #if len(context.Cancels) > 0:
        #    Cancels = pd.DataFrame.from_dict(context.Cancels, orient='index')
        #    Cancels.columns = ['orderid', 'daycancels']
        #else:
        #    Cancels = pd.DataFrame()
        if len(context.trades) > 0:

            RTrades = pd.DataFrame.from_dict(context.trades, orient='index')
            RTrades.columns = ['time', 'action', 'dir', 'price', 'instid', 'tradeprice', 'vol', 'orderid',
                               'poscostl',
                               'poscosts', 'current', 'posprof', 'closeprof','date']
            #RTrades['totalpos'] = np.where(RTrades['action'] == 'open', RTrades['vol'], -RTrades['vol'])
            #RTrades['totalpos'] = RTrades['totalpos'].cumsum()
        else:
            RTrades = pd.DataFrame()
        
        if not context.hedgemodel:
            Report = {}
            if len(RTrades)>0:
                for inst in instids:
                    Report[inst] = pd.DataFrame(index = df_dict[inst].index, columns=['current'])
                    Report[inst]['current'] = df_dict[inst].close if datamode !='tick' else df_dict[inst].current
                    if datamode != 'tick':
                        Report[inst]['open'] = df_dict[inst].open
                        #Report[inst]['close'] = df_dict[inst].close
                        Report[inst]['high'] = df_dict[inst].high
                        Report[inst]['low'] = df_dict[inst].low
                        Report[inst]['volume'] = df_dict[inst].volume
                    tmpTrades = RTrades[RTrades.instid == inst]
                    OpenClose = pd.DataFrame(index = tmpTrades.time, columns=['openlong','openshort','closelong','closeshort'])
                    OpenClose['openlong'] = np.where((tmpTrades.action=='open')&(tmpTrades.dir=='long'),  tmpTrades.tradeprice, None)
                    OpenClose['openshort'] = np.where((tmpTrades.action=='open')&(tmpTrades.dir=='short'),  tmpTrades.tradeprice, None)
                    OpenClose['closelong'] = np.where((tmpTrades.action=='close')&(tmpTrades.dir=='long'),  tmpTrades.tradeprice, None)
                    OpenClose['closeshort'] = np.where((tmpTrades.action=='close')&(tmpTrades.dir=='short'),  tmpTrades.tradeprice, None)
                    #OpenClose['time'] = tmpTrades.index
                    Report[inst] = pd.merge(Report[inst],OpenClose,left_index=True, right_index=True,how='left')
                    Report[inst] = Report[inst].dropna(axis=1, how='all')
            #print(Report)
        else:
            Report = pd.DataFrame(index = df.index)
            letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',\
                         'v', 'w', 'x', 'y', 'z']
            mapDict = {}
            for i in range(len(instids)):
                inst = instids[i]
                Report[inst] = df_dict[inst]['current'] if datamode=='tick' else df_dict[inst]['close']
                mapDict[letters[i]] = Report[inst]
            Report['current'] = eval(context.formula, mapDict)
            #Rep['time'] = Rep.index
            Report = Report.drop(columns=instids)
            #context.d['time'] = context.d.index
            
            Report = pd.merge(Report, context.d,left_index=True, right_index=True, how='left')
            #print(Rep)
            Report = Report.dropna(axis=1, how='all')
        
        if printlog:
            print('done')
            print('Writing to redis database...')
        
        hedgeFlag = True if context.hedgemodel else False
        setting = {}
        setting['datamode'] = datamode
        setting['hedge'] = hedgeFlag
        setting['instids'] = instids
        setting['formula'] = formula
        setting['external'] = external_flag
        setting['startdate'] = strat.start_date.strftime("%Y-%m-%d") if not external_flag else False
        setting['enddate'] = strat.end_date.strftime("%Y-%m-%d") if not external_flag else False
        setting['tradenum'] = len(RTrades)
        setting['ordernum'] = len(context.ROrders)
        setting['stratname'] = strat.name if hasattr(strat, 'name') else 'strat001'
        saveBackTestSetting(user, setting)
        saveBackTestData(user, Report, hedgeFlag)
        if len(context.ROrders) > 0:
            context.ROrders['time'] = [ t.strftime('%Y-%m-%d %H:%M:%S') for t in context.ROrders['time']]#.strftime('%Y-%m-%d %H:%M:%S')
            rorders = context.ROrders.to_dict(orient='index')
            saveBackTestList(user, 'orders', rorders)
        if len(RTrades) > 0:
            RTrades['time'] = [ t.strftime('%Y-%m-%d %H:%M:%S') for t in RTrades['time']]#.strftime('%Y-%m-%d %H:%M:%S')
            rtrades = RTrades.to_dict(orient='index')
            #print(rtrades)
            saveBackTestList(user, 'trades', rtrades)
        #saveBackTestReport(user, 'Orders', context.ROrders)
        #saveBackTestReport(user, 'Trades', RTrades)
        
        context.stat.calcIndicators(initCap)
        context.stat.dailyreport = context.stat.dailyreport.sort_index()
        saveBackTestReport(user, 'Stat', context.stat.dailyreport)
        if printlog:
            print('请使用如下网址查看回测报告')
            print(getAddress(user,rfrate))
        tmpinsts = recordinsts if recordinsts else instids  
        #print('1111')
        #print(record_strat,'???')
        if context.datamode != 'daily':
            context.updateDailyPnl(context.curday)
        if record_strat:
            # trade data
            if len(RTrades) > 0:
                trade_m = RTrades.loc[:, ['time', 'action', 'dir', 'price', 'vol', 'orderid', 'instid', 'date']]
                trade_m['tradeid'] = RTrades.index.map(lambda x : str(10000000+x))
                #trade_m['date'] = trade_m['time'].map(lambda x: x[:10])
                trade_m['prod'] = trade_m['instid'].map(lambda x: getProd(x))
                #trade_m.columns = ['timestr', 'action', 'dir', 'price', 'volume', 'tradeid', 'instid', 'date', 'prod']
                save_trades_wrap(strat.name, trade_m, context.tradingday)
                print('save trades into stratgy market sucessfully')
            
            
            ## Write statistics to db for last day
            writeStratPosition_wrap(context.stratname,context.tradingday,context.position,context.instCloseProf)
            curday = context.curday
            context.updateProdData(curday)
            
            #save stratgy card
            card_indicators =  StratCardIndicatorsEx(context.dailyPnl, rfrate)
            #print(card_indicators)
            update_stratCard_wrap(strat.name,card_indicators, context.prodTMaxmarg)
        if showchart:
            hedgetype = 'hedge' if context.hedgemodel else None
            showOpenClose(Report, tmpinsts, hedgetype)
            showPosBalance(context.stat.dailyreport)
            showPnlRets(context.stat.dailyreport)
        Stat =  context.stat.dailyreport
        
        ROrders = context.ROrders
        del context.stat
        del context
        return {'Data': Report, 'Orders': ROrders, 
                'Trades': RTrades,  'Stat': Stat}


    except Exception as e:
        logger.error(f"Failed when execute HandleFunc on line: {e.__traceback__.tb_lineno}, {e}")
        return None

def getAddRemove(olds , news):
    adds = []; removes = []; lefts = [];
    for o in olds:
        if not o in news:
            removes.append(o)
        else:
            lefts.append(o)
    for n in news:
        if not n in olds:
            adds.append(n)
            
    return adds, removes, lefts        

def calcReportData(df, trades):
    
    Report = pd.DataFrame(index = df.index, columns=['open','close','high','low','volume'])
    Report['open'] = df.open
    Report['close'] = df.close
    Report['high'] = df.high
    Report['low'] = df.low
    Report['volume'] = df.volume
    OpenClose = pd.DataFrame(index = trades.time, columns=['openlong','openshort','closelong','closeshort'])
    OpenClose['openlong'] = np.where((trades.action=='open')&(trades.dir=='long'),  trades.tradeprice, None)
    OpenClose['openshort'] = np.where((trades.action=='open')&(trades.dir=='short'),  trades.tradeprice, None)
    OpenClose['closelong'] = np.where((trades.action=='close')&(trades.dir=='short'),  trades.tradeprice, None)
    OpenClose['closeshort'] = np.where((trades.action=='close')&(trades.dir=='long'),  trades.tradeprice, None)
    #OpenClose['time'] = trades.index
    Report = pd.merge(Report,OpenClose,left_index=True, right_index=True,how='left')
    return Report
    #Report = Report.dropna(axis=1, how='all')

def getDayStart(curtime):
    days = 1
    if curtime.hour >= 19:
        days = 0
    elif curtime.weekday() == 0:
        days = 3
    return (curtime - pd.Timedelta(days=days)).strftime("%Y-%m-%d 19:00:00")    

def getBarData(freq, inst, curtime):
    freq = str(freq)+'T' 
    start = getDayStart(curtime)
    end = curtime + pd.Timedelta(minutes=1)
    df = get_price(inst, start, end, freq=freq)
    if not 'time' in df.columns:
        df['time'] = df.index
    return df

def dynamicMerge(df, adds, removes, start, end, datamode, freq, printlog=True):
    if printlog:
        print("Data is merging dynamic...")
    try:
        delcols =[]
        for inst in removes:
            colname = [x for x in df.columns if inst in x.split('-')] 
            delcols += colname
        df = df.drop(columns=delcols)
        if 'time' in df.columns:
            df.set_index('time',inplace=True)
        for inst in adds:
            f = 'daily' if datamode =='daily' else 'minute'
            if f=='minute' and freq > 1:
                f = str(freq)+'T'
            instdf = get_price(inst, start, end, freq=f, fields=None,silent=True)
            if instdf is None or len(instdf) == 0:
                continue
            instdf.columns += instdf.columns+'-' + inst
            
            df = pd.merge_ordered(df, instdf, on='time', fill_method="ffill",how='left')
            #df = df.drop(columns=['time'])
        if 'time' in df.columns:
            df.set_index('time',inplace=True)
        if not 'time' in df.columns:
            df['time'] = df.index
        df = df.fillna(0)
        return df    
    except Exception as e:
        logger.error(f"Dynamic Merge on line: {e.__traceback__.tb_lineno}, {e}")
        return df

def dynamicBacktest(user, datamode, instids, start_date, end_date, strat, printlog=True, \
                    initCap=10000000,showchart=False, record_strat=False, async_strats=False, rfrate=0.00):
    if datamode == 'hour':
        datamode = 'minute'
        strat.datamode = datamode
        strat.freq = 60
    elif datamode == 'minute':
        if strat.freq == 0:
            strat.freq = 1
    for inst in instids:
        if not is_valid_instID(inst.upper()):
            print("该合约名不合法", inst)
            return None
    
    if not isinstance(strat, qeStratBase):
        print("strat必须是qeStratBase派生类实例")
        return None
    
    if strat.formula:
        print("回测动态合约模式下不支持对冲模式")
        return None
    
    if initCap<0:
        print("test_initcap必须是正数")
        return None

    #if isinstance(start_date, datetime.date):
    #    start_date = datetime.datetime.combine(start_date, datetime.time())
    #if isinstance(end_date, datetime.date):
    #    end_date = datetime.datetime.combine(end_date, datetime.time())

    initBacktestLogger(printlog)    #
    clearBackTestData(user)

    context = qeContextBase(instids, initCap)
    context.account = testAccountInfo(initCap)
    context.datamode = datamode
    context.traderate = strat.traderate
    context.freq = strat.freq
    context.printlog = printlog
    context.flippage = strat.flippage
    context.runmode = 'test'
    context.instids = instids
    context.record_strat = record_strat
    if record_strat:
        assert hasattr(strat, 'name'),'Record strategy must have formal name, set strat.name firstly please'
        context.stratname = strat.name
        if not strat._append_mode:
            clearStratTrades_wrap(strat.name)
            clearStratStat_wrap(strat.name, start_date)
            clearStratPosition_wrap(strat.name, start_date)            
        else:
            clearStratTrades_wrap(strat.name, start_date)
            clearStratStat_wrap(strat.name, start_date)
            clearStratPosition_wrap(strat.name, start_date)            
            context.position, tmp = readStratPosition_wrap(strat.name, start_date.strftime('%Y%m%d'))
            tmpstat = readFullStratStat_wrap(strat.name)
            initloss = min(0, sum(tmpstat['pnl']))
    #total_instid = instids
    record_instid = []
    curstart = start_date
    curend = start_date + pd.Timedelta(days=30)
    curend = min(end_date, curend)
    #print(curstart, curend)
    df = mergedf(instids, curstart, curend, datamode, strat.freq, printlog)
    if context.datamode != 'daily':
        ## Save daily settle price
        for inst in context.instid:
            context.dailySettle[inst] = get_price(inst, curstart,curend + pd.Timedelta(days=1),'daily',fields=['settle'])
    i = 0
    adds = []
    datarep = {}
    trade_cols = ['time', 'action', 'dir', 'price', 'instid', 'tradeprice', 'vol', 'orderid',
                                                   'poscostl','poscosts', 'current', 'posprof', 'closeprof','date']
    RTrades = pd.DataFrame(columns=trade_cols)
   
    #try:
    #    strat.initStrat(context)
    #except Exception as e:
    #    logger.error(f'Error on strat.initStrat:{e}')
    #    return None
    try:
        if printlog:
            print("start backtest on current strategy...")   
        
        if isinstance(strat.instid,str):
           strat.instid =[strat.instid]
   
        while curend < end_date or i < len(df) - 1:
            if not 'time' in df.columns:
                df['time'] = df.index
            #print('df.index',df.index[0])
            context.daystart = 0   
            context.bardata = {}
            df_dict = {}
            instids = strat.instid
            for inst in instids:
                
                colname = [x for x in df.columns if inst in x.split('-')]
                #print(inst, colname)
                if len(colname) > 0:
                    df_dict[inst] = pd.concat([df['time'], (df.loc[:, colname])], axis=1)
                    #print(df.columns, df_dict[inst].columns)
        
                    if datamode == 'minute':
                        dfname = ['time', 'open', 'close', 'high', 'low', 'volume', 'money']
                        df_dict[inst].columns = dfname
                    else:
                        dfname = ['time', 'open', 'close', 'high', 'low', 'volume', 'money', 'position', 'upperlimit',
                                  'lowerlimit', 'presett', 'preclose','settle']
                        df_dict[inst].columns = dfname
            
            #print('dflen',len(df))
            for i in range(len(df)):
                for inst in instids:        
       
                    # print(df1)
                    if inst in df_dict:
                        context.dataslide[inst] = df_dict[inst].iloc[i, :].to_dict()
                        if datamode == 'minute':
                            bardata = df_dict[inst].iloc[context.daystart:(i+1), :]
                            if inst in context.savedbardata:
                                context.bardata[inst] = context.savedbardata.append(bardata)
                            else:
                                context.bardata[inst]  = bardata
                        context.current[inst] = context.dataslide[inst]['current'] if datamode == 'tick' else \
                            context.dataslide[inst]['close']
                        curtime = df_dict[inst]['time'][i]  # curtime = df.index[i]
                        
    
                        context.curvol[inst] = context.dataslide[inst]['volume']  # minute中就是成交量
                context.updateTime(curtime)
                context.tradingday = context.curday if datamode == 'daily' else context.account.tradingDay

                if True : #datamode == 'daily' or context.isTradeTime():  # 判断是否是交易时间
                    savedinstid = strat.instid.copy()
                    if datamode != "daily":
                        context.bCrossDay = context.checkCrossDay()  # 判断是否隔一天
                        if context.bCrossDay:  # 如果隔了一天
                            if printlog:
                                context.dayStatistics()
                            context.crossDay()
                            context.daystart = i
                            try:
                                if async_strats:
                                    asyncio.run(strat.aio_crossDay(context))
                                else:
                                    strat.crossDay(context)
                            except Exception as e:
                                logger.error(f"Error on strat.crossDay, {e}")
                                return None
                            if len(context.fcDict) > 0:
                                force_close(context)
                                context.fcDict = {}
                           
                            
                            if isinstance(strat.instid,str):
                                strat.instid =[strat.instid]
                            if  strat.instid != savedinstid:
                                context.curtime -= pd.Timedelta(minutes=1)
                                
                    if strat.instid == savedinstid:       
                        context.account.setData(context)
                        context.bartime = context.curtime
                        try:
                            if async_strats:
                                asyncio.run(strat.aio_onBar(context))
                            else:
                                strat.onBar(context)
                            # print(context.orders)
                        except Exception as e:
                            logger.error(f"{context.curtime},Error on strat.onBar {e}")
                            return None
       
                        trades = strat.matchTrade(context, datamode)
                        context.checkTrades(trades)  # trades表和position表的数据都更新了
                        context.updateData()  # 更新一些统计数据
                    if datamode == "daily":
                        if printlog:
                            context.dayStatistics()
                        context.crossDay()
                        try:
                            if async_strats:
                                asyncio.run(strat.aio_crossDay(context))
                            else:
                                strat.crossDay(context)
                        except Exception as e:
                            logger.error(f"Error on strat.crossDay {e}")
                            return None
                        if len(context.fcDict) > 0:
                            force_close(context)
                            context.fcDict = {}
                   
                    if isinstance(strat.instid,str):
                        strat.instid =[strat.instid]
                    #strat.instid = getValidInstIDs(strat.instid)
                    if strat.instid != savedinstid:
                            adds, removes, lefts = getAddRemove(savedinstid, strat.instid)
                            if printlog:
                                print("strat.instid 切换中....")
                                print('Add contracts:', adds)
                                print('Remove contracts:', removes)
                            #total_instid += adds
                            context.instid = strat.instid
                            instids = strat.instid
                            if len(context.trades) > 0:
                                ### save data and trade report
                                Trades = pd.DataFrame.from_dict(context.trades, orient='index')
                                Trades.columns = trade_cols
                                for inst in removes:
                                    tmpTrades = Trades[Trades.instid == inst]
                                    if len(tmpTrades) > 0 :
                                        drep = calcReportData(df_dict[inst], tmpTrades)
                                        if inst in datarep:
                                            datarep[inst] = datarep[inst].append(drep)
                                            drep = datarep[inst]
                                            #print('del inst',inst)
                                            del datarep[inst]
                                        #print('SAVE to DB',inst)
                                        record_instid.append(inst)
                                        saveBackTestDataDynamic(user, inst, drep)  
                                '''
                                for inst in lefts:
                                    tmpTrades = Trades[Trades.instid == inst]
                                    if len(tmpTrades) > 0 :
                                        drep = calcReportData(df_dict[inst], tmpTrades)
                                        if inst in datarep:
                                            datarep[inst] = datarep[inst].append(drep)
                                        else:
                                            datarep[inst] = drep
                                context.trades = {}
                                RTrades = RTrades.append(Trades) 
                                ''' 
                            #if datamode == 'minute':
                            #    for inst in adds:
                            #        context.bardata[inst] = getBarData(strat.freq, inst, context.curtime)
                            context.addInstids(adds)
                            #print(context.shortpendvol.keys())
                            #print("done")
                            if i != len(df) -1:
                                #print('before',len(df))
                                df = dynamicMerge(df, adds, removes, curstart, curend, datamode, strat.freq, printlog)  
                                #print('after', len(df))
                                if context.datamode != 'daily':
                                    for inst in context.instid:
                                        context.dailySettle[inst] = get_price(inst, curstart,curend + pd.Timedelta(days=1),'daily',fields=['settle'])
                               
                                for inst in adds:
                                    colname = [x for x in df.columns if inst in x.split('-')]
                                    #print(inst, len(colname))
                                    if len(colname) > 0:
                                        df_dict[inst] = pd.concat([df['time'], (df.loc[:, colname])], axis=1)
                                        if datamode == 'minute':
                                            dfname = ['time', 'open', 'close', 'high', 'low', 'volume', 'money']
                                            df_dict[inst].columns = dfname
                                        else:
                                            dfname = ['time', 'open', 'close', 'high', 'low', 'volume', 'money', 'position', 'upperlimit',
                                                      'lowerlimit', 'presett', 'preclose','settle']
                                            df_dict[inst].columns = dfname
                                            #print('load',inst)
                                     

            #print('comeon', curend, end_date)
            if context.curtime < end_date and curend < end_date:
                if datamode == 'minute':
                    curstart = context.curtime + pd.Timedelta(minutes=strat.freq)
                else:
                    curstart = context.curtime + pd.Timedelta(days=1)
                curend = curstart + pd.Timedelta(days = 30)
                curend = min(curend, end_date)
                #print(strat.instid)
                if printlog:
                    print("Switch to next month", curstart, curend)
                if curstart < curend:
                    df = mergedf(strat.instid, curstart, curend, datamode, strat.freq, printlog)
                    assert len(df) > 0, f'新合约取不到数据 {strat.instid}'
                    if context.datamode != 'daily':
                        for inst in context.instid:
                            context.dailySettle[inst] = get_price(inst, curstart,curend + pd.Timedelta(days=1),'daily',fields=['settle'])
                    i = 0
                    if len(context.trades) > 0:
                                ### save data and trade report
                        Trades = pd.DataFrame.from_dict(context.trades, orient='index')
                        Trades.columns = trade_cols
                        for inst in strat.instid:
                            tmpTrades = Trades[Trades.instid == inst]
                            if len(tmpTrades) > 0 :
                                drep = calcReportData(df_dict[inst], tmpTrades)
                                if inst in datarep:
                                    datarep[inst] = datarep[inst].append(drep)
                                else:
                                    datarep[inst] = drep
                        context.trades = {}
                        RTrades = RTrades.append(Trades) 

        
        if len(context.trades) > 0:
            Trades = pd.DataFrame.from_dict(context.trades, orient='index')
            Trades.columns = trade_cols
            for inst in strat.instid:
                tmpTrades = Trades[Trades.instid == inst]
                if len(tmpTrades) > 0 :
                    drep = calcReportData(df_dict[inst], tmpTrades)
                    if inst in datarep:
                        datarep[inst] = datarep[inst].append(drep)
                        drep = datarep[inst]
                    else:
                        datarep[inst] = drep
                    #print('SAVE to DB',inst,len(drep))
                    record_instid.append(inst)
                    saveBackTestDataDynamic(user, inst, drep)
                    #del drep[inst]
            RTrades = RTrades.append(Trades)         
        for inst in datarep:
            #print('SAVE left to DB', inst,len(datarep[inst]))
            record_instid.append(inst)
            saveBackTestDataDynamic(user, inst,datarep[inst])
        if context.curtime.hour >= 14 and context.curtime.hour <= 16:
            context.crossDay()
            if printlog:
                context.dayStatistics()
        context.totalStatistics()
        if printlog:
            print('done')
            print('Writing to redis database...')
        
        
        setting = {}
        setting['datamode'] = strat.datamode
        setting['hedge'] = False
        setting['instids'] = record_instid if len(record_instid) > 0 else instids
        setting['formula'] = None
        setting['external'] = False
        setting['startdate'] = start_date.strftime("%Y-%m-%d") 
        setting['enddate'] = end_date.strftime("%Y-%m-%d") 
        setting['tradenum'] = len(RTrades)
        setting['ordernum'] = len(context.ROrders)
        setting['stratname'] = strat.name  if hasattr(strat, 'name') else 'strat001'
        saveBackTestSetting(user, setting)
        
        adddays = 1 if context.curtime.weekday() < 4 else 3
        curday = context.curtime + pd.Timedelta(days=adddays) 
        daynum = int(curday.strftime('%Y%m%d'))*10000
        if len(context.orders) > 0:
            if context.ROrders is None : 
                context.ROrders = pd.DataFrame.from_dict(context.orders, orient='index')
                context.ROrders.index = context.ROrders.index + daynum
            else:
                ROrders = pd.DataFrame.from_dict(context.orders, orient='index')
                ROrders.index = ROrders.index + daynum
                context.ROrders = context.ROrders.append(ROrders)

        
        
        if len(context.ROrders) > 0:
            context.ROrders['time'] = [ t.strftime('%Y-%m-%d %H:%M:%S') for t in context.ROrders['time']]#.strftime('%Y-%m-%d %H:%M:%S')
            rorders = context.ROrders.to_dict(orient='index')
            saveBackTestList(user, 'orders', rorders)
        if len(RTrades) > 0:
            RTrades['time'] = [ t.strftime('%Y-%m-%d %H:%M:%S') for t in RTrades['time']]#.strftime('%Y-%m-%d %H:%M:%S')
            rtrades = RTrades.to_dict(orient='index')
            #print(rtrades)
            saveBackTestList(user, 'trades', rtrades)
        print('initCap',initCap)    
        context.stat.calcIndicators(initCap)
        context.stat.dailyreport = context.stat.dailyreport.sort_index()
        
        saveBackTestReport(user, 'Stat', context.stat.dailyreport)
        if printlog:
            print('请使用如下网址查看回测报告')
            print(getAddress(user,strat.rfrate))
        if context.datamode != 'daily':
            context.updateDailyPnl(context.curday)
        if record_strat:
            # trade data
            if len(RTrades) > 0:
                trade_m = RTrades.loc[:, ['time', 'action', 'dir', 'price', 'vol', 'orderid', 'instid']]
                trade_m['tradeid'] = RTrades.index.map(lambda x : str(10000000+x))
                trade_m['date'] = trade_m['time'].map(lambda x: x[:10])
                trade_m['prod'] = trade_m['instid'].map(lambda x: getProd(x))
                #trade_m.columns = ['timestr', 'action', 'dir', 'price', 'volume', 'tradeid', 'instid', 'date', 'prod']
                save_trades_wrap(strat.name,trade_m, context.tradingday)
                print('save trades into stratgy market sucessfully')
            
            
            ## Write statistics to db for last day
            
            date_pos = context.tradingday.replace("-","")
            #print(date_pos,'??')
            writeStratPosition_wrap(context.stratname,date_pos,context.position,context.instCloseProf)
            curday = context.curday
            context.updateProdData(curday)
            print('prodTMaxmarg',context.prodTMaxmarg)
            
            #save stratgy card
            card_indicators =  StratCardIndicatorsEx(context.dailyPnl,rfrate)
            #print(card_indicators)
            if not strat._append_mode:
                update_stratCard_wrap( strat.name, card_indicators, context.prodTMaxmarg)
            else:
                initloss += sum(context.dailyPnl['daypnl'])
                update_stratCard_append_wrap(strat.name, min(initloss,0))
        
        if showchart:
            showOpenClose(datarep, strat.instid)
            showPosBalance(context.stat.dailyreport)
            showPnlRets(context.stat.dailyreport)
        
        ROrders = context.ROrders.copy()
        Stat = context.stat.dailyreport.copy()
        del context.stat
        del context
        return {'Data': datarep, 'Orders': ROrders, 
                'Trades': RTrades,  'Stat': Stat }                

            
    
    
    except Exception as e:
        logger.error(f"Failed when execute HandleFunc on line: {e.__traceback__.tb_lineno}, {e}")
        return None













def showCharts(report):
    '''
    

    Parameters
    ----------
    report : dict
        Return data of runBacktest.

    Returns
    -------
    None.

    '''
    Report = report['Data']
    Stat = report['Stat']
    hedgetype = 'hedge'
    instids = []
    if isinstance(Report, dict):
        hedgetype = None
        instids = Report.keys()
        showOpenClose(Report, instids, hedgetype)
        showPosBalance(Stat)
        showPnlRets(Stat)
    else:
        instids = Report.keys()
        showOpenClose(Report, instids, hedgetype)
        showPosBalance(Stat)
        showPnlRets(Stat)
        

def reportPerformance(report, benchmark=None):
    import quantstats as qs
    Stat = report['Stat']
    if Stat.index[-1] - Stat.index[0] <= pd.Timedelta(days=180):
        print("业绩评估需要至少半年以上数据")
        return 
    else:
        ret = pd.Series(index=Stat.index, data=list(Stat['dayret']))
        if benchmark:
            qs.reports.full(ret, benchmark=benchmark)
        else:
            qs.reports.full(ret)        



def reportIndicators(report, riskfree, benchmark=None):
    indicators = {}
    stat = report['Stat']
    totaldays = (stat.index[-1] - stat.index[0]).days
    #print(totaldays)
    indicators['accret'] = stat.accret[-1]
    indicators['arr'] = stat.accret[-1]*365 / totaldays 
    indicators['highwater'] = stat.highwater[-1]/stat.balance[0]
    indicators['maxdrawback'] = min(stat.drawback)/stat.balance[0]
    indicators['avol'] = np.std(stat.dayret) * np.sqrt(365)
    indicators['winrate'] = sum(stat.wincount) / (sum(stat.wincount) + sum(stat.losscount))
    indicators['odds'] = np.mean(stat.winamount) / abs(np.mean(stat.lossamount))  if np.mean(stat.lossamount) != 0 else 1
    downside = [-ret for ret in stat.dayret if ret < riskfree]
    indicators['downrisk'] = np.std(downside) 
    indicators['sharpratio'] = (indicators['arr'] - riskfree)/indicators['avol']
    indicators['sortinoratio'] = (indicators['arr'] - riskfree)/(np.std(downside)*np.sqrt(365))
    indicators['calmarratio'] = (indicators['arr'] - riskfree)/abs(indicators['maxdrawback'])
    indicators['maxmarg'] = max(stat.maxmarg)
    if benchmark:
        if len(benchmark) != len(stat):
            print('benchmark必须是与回测同时间段，同等长度的日对数收益率')
        else:
            try:
                indicators['relativeret'] = stat.accret[-1] - sum(benchmark)
                indicators['arrr'] = 365 * indicators['relativeret'] / totaldays 
                stat2 = pd.DataFrame(columns=['a','b'])
                stat2['a'] = list(stat['dayret'])
                stat2['b'] = list(benchmark)
                stat2 = stat2[stat2.a != 0]
                indicators['correlation'] = stat2['a'].corr(stat2['b'])
                ssr = np.sum((stat2.a - stat2.b) ** 2)
                sst = np.sum((stat2.a - np.mean(stat2.a))** 2)
                indicators['rsquare'] = 1-float(ssr)/sst
            except:
                print("Invalid benchmark data.")
        
    return indicators
def StratCardIndicators(stat, riskfree,prod):
    try:
        indicators = {}
        annual_workdays = 250
        startbal = stat.loc[stat.index[0], 'balance']
        stat['logreturn'] = np.log(stat['balance'].astype('float')) - np.log(stat['balance'].astype('float').shift(1))
        # print('balance', startbal)
        if len(stat) < 2 or (len(stat) >= 2 and startbal == 0):
            indicators[u'年化回报率'] = '0.00%'
            indicators[u'年化波动率'] = '0.00%'
            indicators[u'净值'] = '0'
            indicators[u'recentreturn'] = '0.00%'
            indicators[u'maxmarg'] = '0'
            indicators[u'无风险利率'] = round(100 * riskfree, 2)
            return indicators
        totaldays = len(stat)
        # print(totaldays)
        indicators[u'记录天数'] = totaldays
        arr = stat.loc[stat.index[len(stat) - 1], 'accret'] * annual_workdays / totaldays
        indicators[u'年化回报率'] = str(round(arr, 2))
        maxdrawback = min(stat.drawback) / startbal
        indicators[u'最大回撤率'] = str(round(maxdrawback, 2))
        indicators[u'maxmarg'] = {prod: str(round(max(stat.maxmarg), 2))}
        # indicators[u'无风险利率'] = str(round(100*riskfree,2))+'%'
        indicators[u'净值'] = str(round(sum(stat['logreturn'].iloc[1:]), 2) + 1)
        # recentreturn
        lastyearday = stat.index[-1] - relativedelta(years=1)
        firstday = stat.index[0]
        if lastyearday > firstday:
            indicators[u'recentreturn'] = str(
                round(stat.loc[stat.index[-1], 'balance'] / stat.loc[lastyearday, 'balance'] - 1, 2)) + '%'
        else:
            indicators[u'recentreturn'] = float(0)

        return indicators
    except Exception as e:
        print('reportIndicators', e, e.__traceback__.tb_lineno)
        return {}
        
        
def StratCardIndicatorsEx(dailyPnl, rfrate):
    try:
        annual_days = 250
        #totaldays = (dailyPnl.index[-1] - dailyPnl.index[0]).days
        indicators = {}
        if len(dailyPnl) < 2:
            indicators[u'annualret'] = 0
            indicators[u'annualvol'] = 0
            indicators[u'maxdrawdown'] = 0
            indicators[u'netval'] = 0
            indicators[u'retayear'] = 0
            indicators[u'maxmarg'] = 0
            return indicators
        #dailyPnl['bal'] = startbal
        dailyPnl['accpnl'] = dailyPnl['daypnl'].cumsum()
        startbal = max(dailyPnl.loc[:,'maxmarg']) - min(min(dailyPnl['accpnl']), 0)
        print('StratCard: startbal', startbal)
        dailyPnl['bal'] = startbal + dailyPnl['accpnl']
        dailyPnl['lastbal'] = dailyPnl['bal'].shift(1).fillna(startbal)
        dailyPnl['highwater'] = dailyPnl['bal'].cummax()
        dailyPnl['drawback'] = 1- dailyPnl['bal']/dailyPnl['highwater']
        
        #result = pd.DataFrame(index=dailyPnl.index, columns=['logret','accret'])
        dailyPnl['logret'] = np.log(dailyPnl['bal'].astype('float')) - np.log(dailyPnl['lastbal'].astype('float'))
        
        
        indicators['days'] = len(dailyPnl)
        annualret = sum(dailyPnl['logret']) * annual_days/ len(dailyPnl)
        indicators['annualret'] = round(annualret,4)    
        annualvol = np.std(dailyPnl['logret']) * np.sqrt(annual_days)
        indicators['annualvol'] = round(annualvol, 4) 
        maxdrawback = max(max(dailyPnl['drawback']),0) 
        indicators['maxdrawdown'] = round(maxdrawback, 4)   
        dailyPnl['netval'] = dailyPnl['bal'] / startbal
        netval =   dailyPnl.loc[dailyPnl.index[-1],'netval'] 
        indicators['netval'] = round(netval,2)
        indicators['maxmarg'] = max(dailyPnl.loc[:,'maxmarg'])
        indicators['maxloss'] = - min(min(dailyPnl['accpnl']), 0)
        #firstday = dailyPnl.index[-1] - relativedelta(years=1)
        #firstday = max(firstday, dailyPnl.index[0])
        recentret = sum(dailyPnl.loc[dailyPnl.index[-annual_days:], 'logret'])
        indicators['retayear'] = round(recentret, 4)    
        return indicators
    except:
        traceback.print_exc()