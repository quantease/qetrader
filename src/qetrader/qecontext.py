# -*- coding: utf-8 -*-
"""
Created on Tue Oct 12 20:03:20 2021

@author: ScottStation
"""


import pandas as pd
import numpy as np
#import qedata
from qesdk import is_valid_trade_time
from .qelogger import logger
import datetime
from .qeglobal import getInstAccID,instSetts


#import matplotlib.pyplot as plt



def transInstID2Real(instids):
    instIDs = []
    
    exID_list = []
    for instid in instids:
        exID = instid[-3:]
        instID = instid[:-4]
        if exID == 'SFE' or exID == 'INE' or exID == 'DCE':
            instID = instID.lower()
        else:
            instID = instID.upper()
        if exID == 'ZCE':
            instID = instID[:2] + instID[3:]
        instIDs.append(instID)    
        exID_list.append(exID)
    return instIDs,exID_list

def transInstID2Context(instID, exID):
    if exID == 'ZCE':
        return instID[:2]+'2'+instID[2:]+'.'+exID
    else:
        return instID.upper()+'.'+exID

def transExID2Context(exID):
    if exID == "SHFE":
        return "SFE"
    elif exID == "CZCE":
        return "ZCE"
    elif exID == "CFFEX":
        return 'CCF'
    elif exID == 'GFEX':
        return "GFE"
    else:
        return exID

class qeDataSet:

    def __init__(self,data=None):      
        self.data = {}
        if data:
            for k in data:
                self.data[k] = data[k]

    def add(self,instid,data):

        LT = len(instid)
        if LT != len(data):
            logger.info('Length of instrument is inconsistent to that of data')
        else:

            for i in range(LT):
                self.data[instid[i]] = data[i]
    
    def indexing(self,i):
        d = {}
        for k in self.data:
            df = self.data[k]
            d[k] = df.iloc[i,:] # .to_dict()
        
        data = qeDataSet(d)
        return data
    
    def label(self,header):
        d = {}
        for k in self.data:
            df = self.data[k]
            d[k] = df[header] # .to_dict()
        
        data = qeDataSet(d)
        return data



class qeStratStatistics:
    accret = 0.0
    balance = 0.0
    avail = 0.0
    lastPosProf = 0.0
    dayfees = 0.0
    totalfees = 0.0
    daypnl = 0.0
    totalpnl = 0.0
    opens = {'long': {'price': np.nan, 'vol': 0}, 'short': {'price': np.nan, 'vol': 0}}
    closes = {'long': {'price': np.nan, 'vol': 0}, 'short': {'price': np.nan, 'vol': 0}}
    dayorders = 0
    daycancels = 0
    dayopens = 0
    daycloses = 0
    totalpos = {}

    def __init__(self, initCap):
        self.balance = initCap
        self.avail = initCap
        self.opens = {'long': {'price': np.nan, 'vol': 0}, 'short': {'price': np.nan, 'vol': 0}}
        self.closes = {'long': {'price': np.nan, 'vol': 0}, 'short': {'price': np.nan, 'vol': 0}}
        self.accret = 0.0
        self.totalfees = 0.0
        self.totalpnl = 0.0
        self.daypnl = 0
        self.dayopens = 0
        self.daycloses = 0
        self.dayfees = 0
        self.dayorders = 0
        self.daycancels = 0
        self.lastPosProf = 0
        self.totalpos = {}

    def crossDay(self):
        self.daypnl = 0
        self.dayopens = 0
        self.daycloses = 0
        self.dayfees = 0
        self.dayorders = 0
        self.daycancels = 0





def getProd(instid):
    if instid[1].isdigit():
        return instid[0]
    else:
        return instid[:2]


class qeContextBase(object):

    def __init__(self,instid):   
                        # list

        self.instid = instid     
        self.position = {}  #position = [{'long':{'volume':0,'poscost':0,'yesvol':0}, 'short':{'volume':0,'poscost':0,'yesvol':0}}]
        self.dataslide = {}
        #self.exchangeID = exchangeID
        self.exID = {}
        self.instsett = {}
        self.initCapital = 10000000   
        self.stat = qeStratStatistics(self.initCapital)
        self.orders = {}
        self.trades = {}  
        self.datamode = ''
        self.traderate = 1
        self.feesMult = 1.0      
        self.ROrders = {}
        self.Cancels = {}    
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
        self.tradingday = ''
        self.lasttday=''
        self.lastvol = {}
        self.curvol = {}
        self.orderid = 0
        self.tradeid = 0
        self.maxpos = {}
        self.curpnl = 0
        self.printlog = True
        self.flippage = 0
        self.lastclose = {}
        self.current = {}
        self.position = {}
        self.prodMaxMarg = {}
        self.prodTurnover= {}
        self.instClosePnl = {}
        self.longpendvol = {}
        self.shortpendvol = {}
        self.openPrice = {}
        self.algoorders={}
        self.algoid = 0
        self.maxmarg = 0
        self.fcDict = {}
        self.bDataRead = False
        self.addNewInsts(instid)        
        self.recmode = False
        self.presett = {}
        self.instsett = instSetts 


    def addNewInsts(self, instid):
        for i in range(len(instid)):
            self.lastclose[instid[i]] = 0
            self.lastvol[instid[i]] = 0
            self.curvol[instid[i]] = 0
            self.exID[instid[i]] = instid[i][-3:]
            if not instid[i] in self.position:
                self.position[instid[i]] = {'long': {'volume': 0, 'poscost': 0, 'yesvol': 0},
                                           'short': {'volume': 0, 'poscost': 0, 'yesvol': 0}}
            #temp_instid_full = self.instid[i]+'.'+self.exchangeID[i]
            #self.instsett[instid[i]] = get_instrument_setting(instid[i])
            self.longpendvol[instid[i]] = {'volume':0,'poscost':0}
            self.shortpendvol[instid[i]] = {'volume':0,'poscost':0}
            self.openPrice[instid[i]] = 0
            self.maxpos[instid[i]] = 0
       

    def updateTradingday(self, tradingday):
        
        self.lasttday = self.tradingday
        self.tradingday = tradingday.replace('-','')
        
        
    def getCurrent(self,instid):
        if instid in self.dataslide:
           if self.dataslide[instid]['current'] > 0 :
               return self.dataslide[instid]['current']
        return 0

    def getDataSlide(self, instid, field):
        if instid in self.dataslide:
            if field in self.dataslide[instid]:
                return self.dataslide[instid][field]
            else:
                logger.warning("Invalide field name",field)

        return 0    
    def getDayStart(self):
        days = 1
        if self.curtime.hour >= 19:
            days = 0
        elif self.curtime.weekday() == 0:
            days = 3
        return (self.curtime - datetime.timedelta(days=days)).strftime("%Y-%m-%d 19:00:00")    
    
    def getPosition(self, instid, direction, field):
        if instid in self.position:
            if direction in self.position[instid]:
                if field in self.position[instid][direction]:
                    return self.position[instid][direction][field]
                else:
                     logger.warning("Invalide field name",field)
                   
        return 0

    def getAccountPosition(self, instid, direction, field, accid=-1):     
        if self.recmode:
            return self.getPosition(instid,direction,field)
        accid = getInstAccID(instid)[0] if accid < 0 else accid
        if accid == 0:
            if instid in self.account.position:
                if direction in self.account.position[instid]:
                    if field in self.account.position[instid][direction]:
                        return self.account.position[instid][direction][field]
                    else:
                        logger.warning("Invalide field name",field)
        elif accid < len(self.accounts):
            if instid in self.accounts[accid].position:
                if direction in self.accounts[accid].position[instid]:
                    if field in self.accounts[accid].position[instid][direction]:
                        return self.accounts[accid].position[instid][direction][field]
            
        
        return 0
    
       
        
    def getMargin(self, price, bLong, vol,instid):
        if vol == 0:
            return 0
        tempdata = self.instsett.get(instid,"NULL")
        if tempdata != "NULL":
            if isinstance(tempdata['marglong'],str):
                marginrate = 200 if not bLong else 0 ## tempory code for options
            else:    
                marginrate = tempdata['marglong'] if bLong else tempdata['margshort']
            return price * marginrate/100 * vol * tempdata['volmult']
        else:
            logger.warning(f"incorrect inst for getMargin {instid}")
            #traceback.print_exc()
            return 0
    
    def getCommission(self, action, price, vol, yesvol,instid):
        ## Calculate commission by Different Exchange
        ## commissionByMoney and ByVolume, closeToday and closeYesterday
        ## fees multiple
        if vol == 0:
            return 0
        tempdata = self.instsett.get(instid,"NULL")
        if tempdata != "NULL":

            if action == 'open':
                return tempdata['openfee']*vol + tempdata['openfeerate']*vol*price* tempdata['volmult']
            else:
                yesrate = yesvol / vol
                totalrate = tempdata['closetodayrate'] * (1 - yesrate) + yesrate
                return totalrate *( tempdata['closefee']*vol + tempdata['closefeerate'] *vol*price*tempdata['volmult'])
        else:
            logger.warning("incorrect inst for getCommission")
            return 0
            
    def updateData(self):
        mm = 0
        # print(1)
        prodMM = {}
        for i in range(len(self.instid)):

            instid = self.instid[i]
            p = getProd(instid)
            
            high =  self.getDataSlide(instid,'high')
            if high > 0:
                marg = high * (self.instsett[instid]['marglong']*self.getPosition(instid,'long','volume') + \
                        self.instsett[instid]['margshort']*self.getPosition(instid,'short','volume'))/100 * \
                        self.instsett[instid]['volmult']
                mm += marg
                if p in prodMM:
                    prodMM[p] += marg
                else:
                    prodMM[p] = marg
                    
            
            # 最大保证金额
        # print(1)
        if mm > self.maxmarg:  # 如果账户的最大保证金大于规定的最大保证金
            self.maxmarg = mm
        
        for p in prodMM:
            if not p in self.prodMaxMarg :
                self.prodMaxMarg[p] = prodMM[p]
            elif self.prodMaxMarg[p] < prodMM[p]:
                self.prodMaxMarg[p] = prodMM[p]

        self.posProf = self.getPosProf()
        # print(1)
        #lastcap = self.stat.balance
        self.stat.balance += self.curpnl + self.posProf - self.stat.lastPosProf
        # print(1)
        self.stat.lastPosProf = self.posProf
        #self.logret = np.log(self.stat.balance / lastcap)
        self.stat.accret += self.logret
        self.stat.avail = self.stat.balance - self.marg - self.frozenMarg
    

    def crossDay(self):
        self.frozenMarg = 0
        self.longpendvol = {}
        self.shortpendvol = {}
        self.orders = {}
        self.algoorders  = {}
        # self.trades = {}
        self.orderid = 0
        self.lastvol = {}
        self.stat.crossDay()
        for prod in self.prodMaxMarg:
            self.prodMaxMarg[prod]  = 0
        for prod in self.prodTurnover:
            self.prodTurnover[prod] = 0
        for inst in self.instClosePnl:
            self.instClosePnl[inst] =  0

        ## on trades
        #for i in range(len(self.instid)):
        for inst in self.instid:
            if inst in self.position:
                self.position[inst]['long']['yesvol'] = self.position[inst]['long']['volume']
                self.position[inst]['short']['yesvol'] = self.position[inst]['short']['volume']
            else:
                self.position[inst] = {'long':{'yesvol':0,'volume':0,'poscost':0},'short':{'yesvol':0,'volume':0,'poscost':0}}
            self.longpendvol[inst] = {'volume':0,'poscost':0}
            self.shortpendvol[inst] = {'volume':0,'poscost':0}
            self.lastvol[inst] = 0
            
        self.updateMarg()
        #if self.runmode == 'simu':
        #    self.checkforceclose()

    def checkCrossDay(self):
        if not self.lasttime:
            return False
        if self.lasttday != '' and self.tradingday != self.lasttday:
            return True
        elif (self.lasttime.hour == 14 or self.lasttime.hour == 15) and self.curtime.hour != 14 and self.curtime.hour != 15:
            return True
        return False

    def dayStatistics(self):
        logger.info(f'{self.stratName}{self.curday}: orders-{self.stat.dayorders},cancels-{self.stat.daycancels},opens-{self.stat.dayopens},closes-{self.stat.daycloses}')
        logger.info(f"{self.stratName}: totalpnl-"+str(round(self.stat.totalpnl, 2))+",totalfees-"+str(round(self.stat.totalfees, 2))+\
              ',balance-'+ str(round(self.stat.balance, 2)) +',accumlated return-'+str(round(100 * self.stat.accret, 2)) + '%')

    def totalStatistics(self):
        logger.info(f"Total statistics of {self.stratName}:") 
        logger.info(f"{self.stratName} totalpnl-"+str(round(self.stat.totalpnl, 2))+ ",totalfees-"+str(round(self.stat.totalfees, 2),)+',maxmargin-'+\
              str(round(self.maxmarg, 2)) + \
              ',balance-'+str(round(self.stat.balance, 2)) + ',accumlated return-' + \
              str(round(100 * self.stat.accret, 2)) + '%')
    
    def clearExpirePosition(self):
        return 
        '''
        getymstr = lambda x : x[1:5] if x[1].isdigit() else x[2:6]
        for key in list(self.position):
            ymstr = '20'+getymstr(key) + '31'
            try:
            if int(self.tradingday) >= int(ymstr):
                ## Expired
                self.position.pop(key)
            except:
                continue
        '''
        
    def getPositionVol(self,instid):
        totalL = self.getPosition(instid, 'long', 'volume')
        totalS = self.getPosition(instid, 'short', 'volume')
        yesL = self.getPosition(instid, 'long','yesvol')
        yesS = self.getPosition(instid, 'short', 'yesvol')
        return totalL - yesL , yesL, totalS - yesS, yesS

    def updateMarg(self):
        self.marg = 0
        for instid in self.position.keys():
            tL, yL, tS, yS = self.getPositionVol(instid)
            margL = self.getMargin(self.getPosition(instid, 'long', 'poscost'), True, tL, instid) 
            if yL > 0:
                margL += self.getMargin(self.getDataSlide(instid,'presett'), True, yL, instid)
            margS = self.getMargin(self.getPosition(instid, 'short', 'poscost'),False, tS, instid)
            if yS > 0:
                margS += self.getMargin(self.getDataSlide(instid,'presett'), False, yS, instid)
            self.marg += margL + margS
            #marg = self.getMargin(self.position[instid]['long']['poscost'],             self.marg += self.getMargin(self.getPosition(instid,'long','poscost'), True, self.getPosition(instid,'long','volume'), instid)
            #self.marg += self.getMargin(self.getPosition(instid,'short','poscost'), False, self.getPosition(instid,'short','volume'), instid)
        #print('context margin', self.marg, self.position)
        

    def updateFrozenMarg(self):
        self.frozenMarg = 0
        
        for i in range(len(self.instid)):
            if self.longpendvol.get(self.instid[i]) and self.shortpendvol.get(self.instid[i]):
                self.frozenMarg += self.getMargin(self.longpendvol[self.instid[i]]['poscost'], True,  self.longpendvol[self.instid[i]]['volume'], self.instid[i]) + self.getMargin(
                    self.shortpendvol[self.instid[i]]['poscost'],False,
                    self.shortpendvol[self.instid[i]]['volume'], self.instid[i])

    def addTrade(self, instid, direction, price, volume, volMult, action, closetype='auto'):
        def getAvgCost(oldp, oldv, newp, newv):
            return (oldp*oldv + newp*newv) /(oldv+newv)
        try:
            result = {}
            if direction > 0:
                #self.longpendvol[instid]['volume'] -= volume
                #if self.longpendvol[instid]['volume'] <= 0:
                #    self.longpendvol[instid]={'volume':0,'poscost':0}
                if action != 'open' and self.position[instid]['short']['volume'] > 0:
                    tradevol = volume if volume <= self.position[instid]['short']['volume'] else \
                        self.position[instid]['short']['volume']
                    self.position[instid]['short']['volume'] -= tradevol
                    tradeyesvol = tradevol if tradevol <= self.position[instid]['short']['yesvol'] else \
                        self.position[instid]['short']['yesvol']
                    todayvol = self.position[instid]['short']['volume'] - self.position[instid]['short']['yesvol']
                    if closetype == 'auto' or closetype == 'closeyesterday':
                        self.position[instid]['short']['yesvol'] -= tradeyesvol
                    elif todayvol < tradevol:
                        ## if today volume is not enough , close some yesterday volume
                        self.position[instid]['short']['yesvol'] -= tradevol - todayvol

                    closeProf = volMult * tradevol * (self.position[instid]['short']['poscost'] - price)
                    result["close"] = {'direction': -1, 'price': price,
                                       'poscost': self.position[instid]['short']['poscost'],
                                       'volume': tradevol, 'closeyesvol': tradeyesvol,
                                       'closeProf': closeProf}
                    if self.position[instid]['short']['volume'] <= 0:
                        self.position[instid]['short'] = {'volume': 0, 'poscost': 0, 'yesvol': 0}
                    volume -= tradevol
                if volume > 0 and action != 'close':
                    if self.position[instid]['long']['volume'] == 0:
                        self.position[instid]['long'] = {'poscost': price, 'volume': volume, 'posProf': 0,
                                                         'yesvol': 0}
                    else:
                        self.position[instid]['long']['poscost'] = getAvgCost( self.position[instid]['long']['poscost'], \
                                                                              self.position[instid]['long']['volume'],price, volume)
                        self.position[instid]['long']['volume'] += volume
                    result['open'] = {'direction': 1, 'poscost': price, 'volume': volume}
            else:
                #self.shortpendvol[instid]['volume'] -= volume
                #if self.shortpendvol[instid]['volume'] <= 0:
                #    self.shortpendvol[instid] ={'volume':0,'poscost':0}
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
                    closeProf = volMult * tradevol * (price - self.position[instid]['long']['poscost'])
                    result["close"] = {'direction': 1, 'price': price,
                                       'poscost': self.position[instid]['long']['poscost'],
                                       'volume': tradevol, 'closeyesvol': tradeyesvol, 'closeProf': closeProf}
                    if self.position[instid]['long']['volume'] == 0:
                        self.position[instid]['long'] = {'volume': 0, 'poscost': 0, 'yesvol': 0}
                    volume -= tradevol
                if volume > 0 and action != 'close':
                    if self.position[instid]['short']['volume'] == 0:
                        self.position[instid]['short'] = {'poscost': price, 'volume': volume, 'posProf': 0,
                                                          'yesvol': 0}
                    else:
                        self.position[instid]['short']['poscost'] = getAvgCost(self.position[instid]['short']['poscost'], \
                                                                     self.position[instid]['short']['volume'], price, volume)
                        self.position[instid]['short']['volume'] += volume
                    result['open'] = {'direction': -1, 'poscost': price, 'volume': volume}
            self.updateFrozenMarg()
            return result
        except Exception as e:
            logger.error(f"Add trade fail on {e}",exc_info=True)
            return None

    def getPosProf(self):
        posProf = 0
        for i in range(len(self.instid)):

            instid = self.instid[i]
            # print(instid)
            volMult = self.instsett[instid]['volmult']
            # print(volMult)
            current = self.getCurrent(instid)

            if self.getPosition(instid,'long','volume') != 0:
                # position['long']['posProf'] = volMult * (current - position['long']['poscost']) * position['long']['volume']
                posProf += volMult * (current - self.position[instid]['long']['poscost']) * \
                           self.position[instid]['long']['volume']
            if self.getPosition(instid,'short','volume') != 0:
                posProf += volMult * (self.position[instid]['short']['poscost'] - current) * \
                           self.position[instid]['short']['volume']
                # posProf += position['short']['posProf']
        return posProf
    '''
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
            for i in range(len(self.instid)):
                self.stat.opens[self.instid[i]] = {'long': {'price': np.nan, 'vol': 0},
                                                  'short': {'price': np.nan, 'vol': 0}}
                self.stat.closes[self.instid[i]] = {'long': {'price': np.nan, 'vol': 0},
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
                # print('1',tradeinstid)
                #current = self.getCurrent(tradeinstid)
                # print(self.current)
                self.orders[id]['tradevol'] += tradevol
                self.orders[id]['leftvol'] -= tradevol
                res = self.addTrade(tradeinstid, self.orders[id]['direction'], tradeprice,
                                    tradevol, self.instsett[tradeinstid]['volmult'],
                                    self.orders[id]['action'], self.orders[id]['closetype'])
                # print(res.keys())
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
                    marg = self.getMargin(dirstr == 'long', res['open']['volume'], tradeinstid)
                    self.marg += marg
                    self.stat.dayopens += res['open']['volume']
                    if dirstr == 'long':
                        statAddTrade(self.stat.opens[tradeinstid]['long'], tradeprice, tradevol)
                    else:
                        statAddTrade(self.stat.opens[tradeinstid]['short'], tradeprice, tradevol)
                    fees += self.feesMult * self.getCommission( 'open', tradeprice, tradevol, 0,tradeinstid)
                    self.tradeid += 1
                    self.posProf = self.getPosProf()
                    self.trades[self.tradeid] = {'time': self.curtime, 'action': 'open', 'dir': dirstr,
                                                 'price': self.orders[id]['price'], 'instid': tradeinstid,
                                                 'tradeprice': tradeprice, 'vol': int(tradevol), 'orderid': id,
                                                 'poscostl': self.position[tradeinstid]['long']['poscost'],
                                                 'poscostS': self.position[tradeinstid]['short']['poscost'],
                                                 'current': self.getCurrent(tradeinstid),
                                                 'posProf': self.posProf, 'closeProf': self.closeProf}
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
                    marg = self.getMargin(dirstr == 'long', res['close']['volume'], tradeinstid)
                    self.marg -= marg
                    fees += self.feesMult * self.getCommission( 'close', tradeprice,
                                                               res['close']['volume'], res['close']['closeyesvol'],tradeinstid)
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
                                                 'posProf': self.posProf, 'closeProf': self.closeProf}
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
            print("context Check Trades on line", e.__traceback__.tb_lineno, e)
    '''
    def updateTime(self, time):
        # print("time",time)
        if self.curtime == 0 or time > self.curtime:
            self.lasttime = self.curtime
            self.curtime = time
            self.curday = time.strftime('%Y-%m-%d')
        # print('curday',self.curday)
        if self.lasttime:
            # print('lasttime',self.lasttime)
            self.lastday = self.lasttime.strftime('%Y-%m-%d')
            # print('lastday', self.lastday)

    def getDailyData(self, instid):
        curday = self.curtime.strftime('%Y-%m-%d 00:00:00')
        if self.getDataSlide(instid, 'current') != 0:
            d = {curday:{'open':self.dataslide[instid]['open'],
                 'close':self.dataslide[instid]['current'],
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
                 

    def updateOpenPrice(self, instid):
        pass
        
        #if 'open' in self.dataslide[instid].keys() and self.dataslide[instid]['open'] and self.dataslide[instid][
        #    'open'] > 0:
        #    self.openPrice[instid] = self.dataslide[instid]['open']
        #else:
        #    self.openPrice[instid] = self.getCurrent(instid)

    def isTradeTime(self):
        return is_valid_trade_time(self.instid[0], self.curtime)  # all the contracts trades on the same time
    
        
    def getCloseProf(self, instid, price, dirstr, vol):
        volMult = self.instsett[instid]['volmult']
        #logger.info(f'closeProf: {volMult}, {self.position[instid]}, {dirstr}, {vol}')
        if dirstr == 'long':
            return volMult * vol * (price - self.position[instid][dirstr]['poscost'])
        else:
            return volMult * vol * (self.position[instid][dirstr]['poscost'] - price)
        
    def getRelativeClosePnl(self, instid, price, dirstr, vol, isToday, presett):
        volMult = self.instsett[instid]['volmult']
        poscost = self.position[instid][dirstr]['poscost'] if isToday else max(presett,self.presett.get(instid, 0))
        if self.recmode:
           logger.info(f'closeProf: {volMult}, {self.position[instid]}, {dirstr},{price}, {vol}, {poscost} {self.stratName}')
        if dirstr == 'long':
            return volMult * vol * (price - poscost)
        else:
            return volMult * vol * (poscost - price)
      
    
    def simuTrade(self, trade):
        ## Close yesterday first
        def updatePos(poscost, posvol, price, vol):
            if vol + posvol > 0:
                cost2 = (poscost*posvol + price*vol)/(vol+posvol)
            else:
                cost2 = 0
            vol2 = vol + posvol
            return cost2,vol2
            

        try:
           

            closeProf = 0
            fees = 0
            # tradeprice = trade['tradeprice']
            # tradevol = trade['tradevol']

            tradeinstid = trade['instid']
            prod = getProd(tradeinstid)
            tradeprice = trade['tradeprice']
            tradevol = trade['tradevol']
            action = trade['action']
            closetype = trade['closetype']
            direction = trade['dir']
            oid = trade['orderid']
            
#             print('trade action'+str(action))
            if action == 'open':
                # print(20)
                #if direction > 0:
                #    self.longpendvol[tradeinstid]['volume'] = max(self.longpendvol[tradeinstid]['volume']  - tradevol, 0)
                #    if self.longpendvol[tradeinstid]['volume'] <= 0:
                #        self.longpendvol[tradeinstid]={'volume':0,'poscost':0}
                #else:
                #    self.shortpendvol[tradeinstid]['volume']  = max(self.shortpendvol[tradeinstid]['volume']  - tradevol, 0)
                #    if self.shortpendvol[tradeinstid]['volume'] <= 0:
                #        self.shortpendvol[tradeinstid]={'volume':0,'poscost':0}
                self.updateFrozenMarg()    
                # print(res['open']['direction'])
                dirstr = 'long' if direction > 0 else 'short'
                odirstr = 'long' if dirstr =='short' else 'short'
                #print('before',self.position, dirstr,odirstr, tradevol, tradeprice)
                if tradeinstid in self.position:
                    if dirstr in self.position[tradeinstid]:
                        #print(1)
                        self.position[tradeinstid][dirstr]['poscost'],self.position[tradeinstid][dirstr]['volume'] = \
                            updatePos(self.position[tradeinstid][dirstr]['poscost'],self.position[tradeinstid][dirstr]['volume'],\
                                      tradeprice, tradevol)
                    else:
                        #print(2)
                        self.position[tradeinstid][dirstr] = {'poscost':tradeprice, 'volume': tradevol, 'yesvol':0}
                        self.position[tradeinstid][odirstr] = {'poscost':0, 'volume': 0, 'yesvol':0}
                else:
                    #print(3)
                    pos ={}
                    pos [dirstr] = {'poscost':tradeprice, 'volume': tradevol, 'yesvol':0}
                    pos [odirstr] = {'poscost':0, 'volume': 0, 'yesvol':0}
                    self.position[tradeinstid] = pos
                    #print('pos0',pos, self.position)
                        
                        
                
                
                
                if self.printlog:
                    print(str(self.curtime), "Open", dirstr, ", vol",
                            int(tradevol), \
                            "price(O/T)", tradeprice, "cur position(L/S)", \
                            int(self.getAccountPosition(tradeinstid,'long','volume')),
                            int(self.getAccountPosition(tradeinstid,'short','volume')),
                            tradeinstid)
                self.updateMarg()
                self.stat.dayopens += tradevol
                openfee = self.feesMult * self.getCommission( 'open', tradeprice, tradevol, 0,tradeinstid)
                fees += openfee
                if tradeinstid in self.instClosePnl:
                    self.instClosePnl[tradeinstid] -= openfee
                else:
                    self.instClosePnl[tradeinstid] = - openfee
                self.tradeid += 1
                self.posProf = self.getPosProf()
                self.trades[self.tradeid] = {'time': self.curtime, 'action': 'open', 'dir': dirstr,
                                                'instid': tradeinstid,
                                                'tradeprice': tradeprice, 'vol': int(tradevol), 'orderid': oid,
                                                'poscostl': self.position[tradeinstid]['long']['poscost'],
                                                'poscostS': self.position[tradeinstid]['short']['poscost'],
                                                'current': self.getCurrent(tradeinstid),
                                                'posProf': self.posProf, 'closeProf': self.closeProf}

            elif action == 'close':
                dirstr = 'long' if direction < 0 else 'short'
                
                closeProf = self.getCloseProf(tradeinstid, tradeprice, dirstr, tradevol)
                self.closeProf += closeProf
                
                (tvol, yvol) = (tradevol, 0) if closetype=='closetoday' else (tradevol, tradevol)
                closePnl = self.getRelativeClosePnl(tradeinstid, tradeprice, dirstr, tvol-yvol, True, trade.get('presett',0))
                closePnl += self.getRelativeClosePnl(tradeinstid, tradeprice, dirstr, yvol, False,trade.get('presett',0))
                    
                
                
                if tradeinstid in self.position:
                    if dirstr in self.position[tradeinstid]:
                        self.position[tradeinstid][dirstr]['volume'] -= tradevol
                        if closetype == 'closeyesterday':
                            self.position[tradeinstid][dirstr]['yesvol'] -=tradevol
                        if self.position[tradeinstid][dirstr]['volume'] <= 0:
                            self.position[tradeinstid][dirstr] = {'poscost':0,'volume':0,'yesvol':0}
                    else:
                        self.position[tradeinstid][dirstr] = {'poscost':0,'volume':0,'yesvol':0}
                else:
                    self.position[tradeinstid] =    {'long': {'volume': 0, 'poscost': 0, 'yesvol': 0},
                                       'short': {'volume': 0, 'poscost': 0, 'yesvol': 0}}                    
    
                
                if self.printlog:
                    print(str(self.curtime), closetype , dirstr, "vol",
                            tradevol, \
                            "price(C/T)", 
                            tradeprice, \
                            "cur position(L/S)", int(self.getAccountPosition(tradeinstid, 'long','volume')),
                            int(self.getAccountPosition(tradeinstid,'short','volume')), \
                            tradeinstid)

                self.updateMarg()
                closefee = self.feesMult * self.getCommission( 'close', tradeprice,tvol,yvol ,tradeinstid)
                fees += closefee
                #tfee = closefee + self.feesMult * self.getCommission( 'open', tradeprice,tvol,0 ,tradeinstid)
                
                
                if tradeinstid in self.instClosePnl:
                    self.instClosePnl[tradeinstid] += closePnl - closefee
                else:
                    self.instClosePnl[tradeinstid] = closePnl - closefee
                self.stat.daycloses += tradevol
                self.tradeid += 1
                self.posProf = self.getPosProf()
                self.trades[self.tradeid] = {'time': self.curtime, 'action': 'close', 'dir': dirstr,
                                                'instid': tradeinstid,
                                                'tradeprice': tradeprice, 'vol': int(tradevol), 'orderid': oid,
                                                'poscostl': self.position[tradeinstid]['long']['poscost'],
                                                'poscostS': self.position[tradeinstid]['short']['poscost'],
                                                'current': self.getCurrent(tradeinstid),
                                                'posProf': self.posProf, 'closeProf': self.closeProf}
            else:
                logger.error('Invalid action in context.simTrade')
                return
            # self.stat.totalfees += fees
            turnover = tradeprice * tradevol * self.instsett[tradeinstid]['volmult']
            if prod in self.prodTurnover:
                self.prodTurnover[prod] += turnover
            else:
                self.prodTurnover[prod] = turnover

            self.stat.daypnl += closeProf
            self.stat.totalpnl += closeProf
            self.stat.dayfees += fees
                # print(closeProf, self.closeProf,self.stat.totalpnl)
            self.stat.totalfees += fees

            self.curpnl = closeProf - fees

        except Exception as e:
            logger.error(f"context simuTrade {e}",exc_info=True)


