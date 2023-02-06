# -*- coding: utf-8 -*-
"""
Created on Fri Apr 29 13:18:09 2022

@author: ScottStation
"""
import pandas as pd
import threading
import numpy as np
from datetime import datetime, timedelta
from .qeredisdb import saveStatDataToDB, saveStatDataToDBReal, loadDBStatData, loadDBStatDataReal
from .qelogger import logger
from .qeredisdb import loadDBStatCurrent, loadDBStatCurrentReal, saveStatCurrentToDB, saveStatCurrentToDBReal
from .qeglobal import setTradingDaySaved

mutex = threading.Lock()

def getPrevTradingDay(curt):
    if curt.hour >= 19:
        return curt.strftime('%Y%m%d')
    wday = curt.weekday()
    if wday == 0:
        return (curt - timedelta(days=3)).strftime('%Y%m%d')
    else:
        return (curt - timedelta(days=1)).strftime('%Y%m%d')


class globalStatistics():
    def __init__(self):
        self.data = pd.DataFrame(columns=['daypnl','maxmarg',\
                                 'turnover','dayfee',\
                                 'balance','withdraw','deposit',\
                                 'winamount','wincount','lossamount','losscount'])
    
        self.runmode = ''
        self.user = ''
        self.token = ''
        #self.accounts = []
        self.tradingday = 0
        self.lastday = 0
        self.startbal = 0
        self.balance = 0
        self.pnl = 0
        self.fee = 0
        #self.ret = 0
        self.maxmarg = 0
        self.turnover = 0
        #self.highwater = 0
        #self.accret = 0
        #self.accpnl = 0
        #self.accfee = 0
        self.pnllist = []
        self.feelist = []
        self.ballist = []
        self.marglist = []
        self.tolist = []
        self.accnum = 1
        self.inited = []
        self.dplist = []
        self.wdlist = []
        self.withdraw = 0
        self.deposit = 0
        self.winamount = 0
        self.lossamount = 0
        self.wincount = 0
        self.losscount = 0
        self.walist = []
        self.mmlist = []
        self.wclist = []
        self.lalist = []
        self.lclist = []
        self.tradeids = []
        self.g_order_id = int('3'+datetime.now().strftime('%d%H%M'))*10000
    
    def setUserToken(self,user, token):
        self.user = user
        self.token = token
        accounts = token.split('_')
        self.accnum = len(accounts)
        if self.accnum > 1:
           for i in range(self.accnum):
               self.pnllist.append(0)
               self.feelist.append(0)
               self.ballist.append(0)
               self.marglist.append(0)
               self.tolist.append(0)
               self.inited.append(0)
               self.wdlist.append(0)
               self.dplist.append(0)
               self.walist.append(0)
               self.lalist.append(0)
               self.wclist.append(0)
               self.lclist.append(0)
               self.mmlist.append(0)
       
        
        
    def init(self, balance, tradingday, accid = 0):
        accnum = self.accnum
        logger.info("Statistics initialized")
        if accnum == 1:
            self.startbal = balance
            self.balance = balance
            #self.highwater = balance
            self.tradingday = tradingday
        elif accid in range(accnum):
            self.ballist[accid] = balance
            self.inited[accid] = 1
            if sum(self.inited) == accnum:
                self.balance = sum(self.ballist)
                #self.startbal = balance
                #self.highwater = balance
                self.tradingday = tradingday
    
    def getNewTradeID(self, curID):
        tmpID = curID
        while tmpID in self.tradeids:
            tmpID += 1
        self.tradeids.append(tmpID)
        return tmpID
            
    def getNewOrderID(self):
        mutex.acquire()
        self.g_order_id += 1
        mutex.release()
        return self.g_order_id
        
    def update(self, balance, pnl, fee, margin, turnover, \
               winamount,  lossamount, wincount, losscount, maxmarg, tradingday,\
               accid = 0,withdraw=0,deposit=0):
        #print("statistics update",maxmarg,self.accnum)
        self.tradingday = int(tradingday)
        
        if self.accnum == 1:
            self.balance = balance
            self.withdraw = withdraw
            self.deposit = deposit
            #netbal = self.balance - self.deposit + self.withdraw
            #if abs(self.startbal) > 0.01:
            #     self.ret = np.log(netbal/self.startbal)
            #else:
            #    self.ret = 0
            self.pnl = pnl
            self.fee = fee
            self.maxmarg = maxmarg
            self.turnover = turnover
            self.winamount = winamount
            self.lossamount = lossamount
            self.wincount = wincount
            self.losscount = losscount
        elif accid in range(self.accnum):
            self.pnllist[accid] = pnl
            self.ballist[accid] = balance
            self.feelist[accid] = fee
            self.tolist[accid] = turnover
            self.marglist[accid] = margin
            self.dplist[accid] = deposit
            self.wdlist[accid] = withdraw
            self.walist[accid] = winamount
            self.lalist[accid] = lossamount
            self.wclist[accid] = wincount
            self.lclist[accid] = losscount
            self.mmlist[accid] = maxmarg
            
            self.balance = sum(self.ballist)
            self.withdraw = sum(self.wdlist)
            self.deposit = sum(self.dplist)
            #netbal = self.balance - self.deposit + self.withdraw
            #if abs(self.startbal) > 0.01:
            #    self.ret = np.log(self.balance / self.startbal)
            #else:
            #    self.ret = 0
            self.pnl = sum(self.pnllist)
            self.fee = sum(self.feelist)
            self.maxmarg = sum(self.mmlist)
            self.turnover = sum(self.tolist)
            self.winamount = sum(self.walist)
            self.lossamount = sum(self.lalist)
            self.wincount = sum(self.wclist)
            self.losscount = sum(self.lclist)
        
        if self.startbal == 0 and self.balance != 0:
            self.startbal = self.balance
        d={}
        d['tradingday'] = self.tradingday
        d['pnl'] = self.pnl 
        d['fee'] = self.fee
        #d['ret'] = self.ret 
        d['maxmarg'] = self.maxmarg 
        d['turnover'] = self.turnover 
        d['deposit'] = self.deposit 
        d['winamount'] = self.winamount 
        d['lossamount'] = self.lossamount 
        d['wincount'] = self.wincount 
        d['losscount'] = self.losscount 
        d['withdraw'] = self.withdraw 
        #d['highwater'] = self.highwater
        #d['accret'] = self.accret
        #d['accpnl'] = self.accpnl
        #d['accfee'] = self.accfee
        d['balance'] = self.balance
        
        if self.runmode == 'simu':
            saveStatCurrentToDB(self.user, self.token, d)
        elif self.runmode == 'real':
            saveStatCurrentToDBReal(self.user, self.token, d)
        
    
    def crossday(self, tradingday):
        logger.info("Statistics crossday")
        tday = int(self.tradingday)
        self.g_order_id = int('3'+datetime.now().strftime('%d%H%M'))*10000
        #self.accret += self.ret
        #self.accpnl += self.pnl
        #self.accfee += self.fee
        #self.highwater = max(self.balance, self.highwater)
        #self.data.loc[tday, 'dayret' ] = self.ret
        #self.data.loc[tday, 'accret'] = self.accret
        self.data.loc[tday, 'daypnl'] = self.pnl
        #self.data.loc[tday, 'accpnl'] = self.accpnl
        self.data.loc[tday, 'dayfee'] = self.fee
        #self.data.loc[tday, 'accfee'] = self.accfee
        self.data.loc[tday, 'balance'] = self.balance
        self.data.loc[tday, 'turnover'] = self.turnover
        self.data.loc[tday, 'maxmarg'] = self.maxmarg
        self.data.loc[tday, 'withdraw'] = self.withdraw
        self.data.loc[tday, 'deposit'] = self.deposit
        #self.data.loc[tday, 'highwater'] = self.highwater
        self.data.loc[tday, 'winamount'] = self.winamount
        self.data.loc[tday, 'lossamount'] = self.lossamount
        self.data.loc[tday, 'wincount'] = self.wincount
        self.data.loc[tday, 'losscount'] = self.losscount
        
        #self.data.loc[tday, 'drawback'] = self.highwater - self.balance if self.highwater > self.balance else 0
        self.tradingday = tradingday
        self.pnl = 0
        self.fee = 0
        #self.ret = 0
        self.maxmarg = 0
        self.turnover = 0
        self.deposit = 0
        self.winamount = 0
        self.lossamount = 0
        self.wincount = 0
        self.losscount = 0
        self.withdraw = 0
        self.startbal = self.balance
        setTradingDaySaved(False)   
        self.data = self.data[self.data.balance != 0]
        self.saveDataToDB()

        
    def saveDataToDB(self):
        if self.runmode == 'simu':
            saveStatDataToDB(self.user, self.token, self.data)
        elif self.runmode == 'real':
            saveStatDataToDBReal(self.user, self.token, self.data)
        
    def loadFromDBSimu(self, tradingday):
        print('loadFromDBSimu')
        tradingday = int(tradingday) if tradingday != '' else 0
        self.runmode = 'simu'
        d = loadDBStatCurrent(self.user, self.token)
        if d:
            self.tradingday = d['tradingday']
            self.pnl = d['pnl']  
            self.fee = d['fee'] 
            #self.ret = d['ret'] 
            self.maxmarg = d['maxmarg']  
            self.turnover = d['turnover'] 
            self.deposit  = d['deposit'] 
            self.winamount = d['winamount']
            self.lossamount = d['lossamount']  
            self.wincount = d['wincount']  
            self.losscount = d['losscount'] 
            self.withdraw =  d['withdraw']
            #self.accfee = d['accfee']
            #self.accpnl = d['accpnl']
            #self.accret = d['accret']
            #self.highwater = d['highwater']
            self.balance = d['balance']
            res = loadDBStatData(self.user, self.token)
            if not res is None:
                self.data = res
            
            if self.tradingday != tradingday:
                self.crossday(tradingday)
            self.tradingday = tradingday
    
    def loadFromDBReal(self, tradingday):
        print('loadFromDBReal')
        tradingday = int(tradingday) if tradingday != '' else 0

        self.runmode = 'real'
        d = loadDBStatCurrentReal(self.user, self.token)
        if d:
            self.tradingday = d['tradingday']
            self.pnl = d['pnl']  
            self.fee = d['fee'] 
            #self.ret = d['ret'] 
            self.maxmarg = d['maxmarg']  
            self.turnover = d['turnover'] 
            self.deposit  = d['deposit'] 
            self.winamount = d['winamount']
            self.lossamount = d['lossamount']  
            self.wincount = d['wincount']  
            self.losscount = d['losscount'] 
            self.withdraw =  d['withdraw']
            #self.accfee = d['accfee']
            #self.accpnl = d['accpnl']
            #self.accret = d['accret']
            #self.highwater = d['highwater']
            self.balance = d['balance']
            res = loadDBStatDataReal(self.user, self.token)
            if not res is None:
                self.data = res
            if self.tradingday != tradingday:
                self.crossday(tradingday)
            self.tradingday = tradingday
        
    
    def updateData(self, balance, pnl, fee, margin, turnover, tradingday,\
                   winamount, lossamount, wincount, losscount, maxmarg, accid = 0,withdraw=0,deposit=0):
        tradingday = int(tradingday) if tradingday != '' else 0
        if self.runmode == "": 
            return
        elif self.tradingday == 0:
            if abs(balance) > 0:
                self.init(balance, tradingday, accid)
        elif self.tradingday != tradingday:
            print('updateData', self.tradingday, tradingday)
            self.crossday(tradingday)
        else:
            self.update(balance,pnl,fee,margin,turnover, winamount, lossamount, wincount, losscount,maxmarg, tradingday, accid,withdraw=withdraw, deposit=deposit)    
            

g_stat = globalStatistics()