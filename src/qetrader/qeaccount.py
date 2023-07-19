# -*- coding: utf-8 -*-
"""
Created on Sat Mar 19 13:07:37 2022

@author: ScottStation
"""

from .qeredisdb import saveAccountDatarealToDB, savePositionDatarealToDB,getDBAccountDetailReal
from .qeredisdb import delDBOrderDataReal, delDBTradeDataReal,getDBOrderDatareal,saveUnfinishedOrders,loadUnfinishedOrders
from datetime import datetime
from .qestatistics import g_stat
from .qeglobal import instSetts
from .qeriskctl import riskControl


class realAccountInfo:
    def __init__(self, user='unknown',token='',balance=0,accid=0):
        self.balance = balance
        self.avail = balance
        self.margin = 0
        self.frozenMarg = 0
        self.pendVolumes = {}
        self.position = {}
        self.closeProf = 0
        self.posProf = 0
        self.daypnl = 0
        self.maxmarg = 0
        self.accupnl = 0
        self.totalpnl = 0
        self.dayfees = 0
        self.accufees = 0
        self.totalfees = 0
        self.withdraw = 0
        self.deposit = 0
        self.winamount = 0
        self.lossamount = 0
        self.wincount = 0
        self.losscount = 0
        self.turnover = 0
        self.current_timedigit = 0
        self.tradingDay = ""
        self.name='ctp'
        self.user = user
        self.investorid = ''
        ### internal parameters
        self.dataSlide = {}
        self.orders = {}
        self.trades = {}
        self.token = token
        self.accid = accid
        self.riskctl = riskControl(self.riskctlCall,self.user, self.token,runmode='real')
        #self.g_order_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.g_trade_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.stgtable_load = False
        self.order_stg_table = {}
        self.loadReady = False

    def crossday(self):
        self.accupnl = self.totalpnl
        self.accufees = self.totalfees
        self.dayfees = 0
        self.daypnl = 0
        self.riskctl.crossDay()
        #self.g_order_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.g_trade_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.orders = {}
        self.trades = {}
        self.deposit = 0
        self.withdraw =  0
        self.turnover = 0
        self.maxmarg = 0
        self.winamount = 0
        self.lossamount = 0
        self.wincount = 0
        self.losscount = 0

        #self.pendVolumes = {}
        self.frozenMarg = 0
        for inst in self.position.keys():
            self.position[inst]['long']['yesvol'] = self.position[inst]['long']['volume']
            self.position[inst]['short']['yesvol'] = self.position[inst]['short']['volume']
        return

    def riskctlCall(self):
        instPrices = {}
        for oid in self.orders:
            order = self.orders[oid]
            if order['leftvol'] > 0 and order['ordertype'] == 'limit':
                field = 'longhigh' if order['direction'] > 0 else 'shortlow'
                instid = order['instid']
                price = order['price']
                if not instid in instPrices:
                    instPrices[instid] = {field:price}
                elif not field in  instPrices[instid]:
                    instPrices[instid][field] = price
                else:
                    if field == 'longhigh' and price > instPrices[instid][field]:
                        instPrices[instid][field] = price
                    elif field == 'shortlow' and price < instPrices[instid][field]:
                        instPrices[instid][field] = price     
        return instPrices                
    def calcFrozenVol(self, instid, direction):
        fvol = 0
        for oid in self.orders:
            order = self.orders[oid]
            if order['leftvol'] > 0 and order['action']=='close' and order['direction'] == direction:
                fvol += order['leftvol']
        return fvol
    
    def setLoadReady(self):
        self.loadReady = True

    def setTradingDay(self, tradingDay):
        self.tradingDay = tradingDay
        self.riskctl.setTradingDay(tradingDay)
    '''
    def getPosProf(self):
        posProf = 0
        for inst in self.position.keys():
            current = self.dataSlide[inst]['current']
            volMult = instSetts[inst]['volmult']
            if self.position[inst]['long']['volume'] > 0:
                posProf += volMult * (current - self.position[inst]['long']['poscost']) * \
                           self.position[inst]['long']['volume']
            if self.position[inst]['short']['volume'] > 0:
                posProf += volMult * (self.position[inst]['short']['poscost'] - current) * \
                           self.position[inst]['short']['volume']
        return posProf 
    '''

    def getCommission(self,  action, price, vol, closetype,instid, instSetts):
        if action == 'open':

            return instSetts[instid]['openfee'] * vol + instSetts[instid]['openfeerate'] * vol * price * \
                   instSetts[instid]['volmult']
        else:
            rate = instSetts[instid]['closetodayrate'] if closetype == 'closetoday' else 1
            return  rate * (instSetts[instid]['closefee'] * vol + \
                                                          instSetts[instid]['closefeerate'] * vol * price * instSetts[instid]['volmult'])
    
    def getCloseProf(self, poscost, dirstr, price, vol, instid, instSetts):
        volMult = instSetts[instid]['volmult']
        if dirstr == 'short':
            closeProf = volMult * vol * (poscost - price)
        else:
            closeProf = volMult * vol * (price - poscost)
        return closeProf
    
    
    def getPosition(self,instid, dirstr, field):
        if instid in self.position:
            if dirstr in self.position[instid]:
                if field in self.position[instid][dirstr]:
                    return self.position[instid][dirstr][field]
        return 0        
    
    def updatePosition(self, instid, direction, action, price, vol, closetype):
        if action == 'close':
            dirstr = 'short' if direction > 0 else 'long'
        else:
            dirstr = 'long' if direction > 0 else 'short'

        if instid in self.position:
            if dirstr in self.position[instid]:
                if action == 'open':
                    self.position[instid][dirstr]['volume'] += vol
                    self.position[instid][dirstr]['poscost'] = (self.position[instid][dirstr]['poscost'] * \
                                                                self.position[instid][dirstr]['volume'] + \
                                                                vol * price) / self.position[instid][dirstr]['volume']
                else:
                    self.position[instid][dirstr]['volume'] -= vol
                    if self.position[instid][dirstr]['volume'] <= 0:
                        self.position[instid][dirstr]['volume'] = 0
                        self.position[instid][dirstr]['poscost'] = 0
                    else:
                        self.position[instid][dirstr]['poscost'] = (self.position[instid][dirstr]['poscost'] * \
                                                                    self.position[instid][dirstr]['volume'] - \
                                                                    vol * price) / self.position[instid][dirstr]['volume']
                    if closetype == 'closeyesterday':
                        self.position[instid][dirstr]['yesvol'] -= vol
                    


    
    
    def updateWinLossParas(self, dirstr, price, vol, closetype, instid):
        poscost = self.getPosition(instid,dirstr,'poscost')
        tfee = self.getCommission('open', poscost, vol, closetype, instid, instSetts)
        tfee += self.getCommission('close', price, vol, closetype, instid, instSetts)
        tpnl = self.getCloseProf(poscost, dirstr, price, vol, instid, instSetts) - tfee
        if tpnl > 0:
            self.winamount += tpnl
            self.wincount += 1
        elif tpnl < 0:
            self.lossamount += tpnl
            self.losscount += 1
    
#     def updateMargin(self):
#         global g_dataSlide
#         marg = 0
#         for inst in self.position.keys():
#             current = g_dataSlide[inst]['current']
#             marg += self.getMargin(current, True, self.position[inst]['long']['volume'], inst)
#             marg += self.getMargin(current, False, self.position[inst]['short']['volume'], inst)
#         self.margin = marg
#         return    
#     def updateFrozenMarg(self):
#         global g_dataSlide
#         fm = 0
#         for inst in self.pendVolumes.keys():
#             current = g_dataSlide[inst]['current']
#             fm += self.getMargin(current, True, self.pendVolumes[inst]['long'], inst)
#             fm += self.getMargin(current, False, self.pendVolumes[inst]['short'], inst)
#         self.frozenMarg = fm
#         return
#     def updateCapital(self, closeProf, fee):
#         lastPosProf = self.posProf
#         self.posProf = self.getPosProf()
#         self.balance += closeProf - fee -lastPosProf + self.posProf
#         self.avail = self.balance -self.margin - self.frozenMarg
#         return
#     def getMargin(self, current, bLong, vol, instid):
#         marginrate = instSetts[instid]['marglong'] if bLong else instSetts[instid]['margshort']
#         return current * marginrate / 100 * vol * instSetts[instid]['volmult']
#     def getCommission(self,  action, price, vol, closetype,instid):
#         global instSetts   
#         if action == 'open':
#             return instSetts[instid]['openfee'] * vol + instSetts[instid]['openfeerate'] * vol * price * \
#                    instSetts[instid]['volmult']
#         else:
#             rate = instSetts[instid]['closetodayrate'] if closetype == 'closetoday' else 1
#             return  rate * (instSetts[instid]['closefee'] * vol + \
#                                                           instSetts[instid]['closefeerate'] * vol * price * instSetts[instid]['volmult'])
#         return
#     def readAndSetDB(self):
#         import math
#         try:
#             #load from db ,if not exist, write default value
#             bal =  getSimuInitCap(self.user)
#             if bal is None or math.isnan(float(bal)):
#                 updateInitCap(self.user, self.balance)
#             else:
#                 logger.info(f'load balance:{self.balance}')
#                 self.balance = float(bal)
#         except Exception as e:
#             logger.error(f"account.readAndSetDB error {e}",exc_info=True ) 
#         return
    def saveToDB(self):
        d = {}
        d['posProf'] = str(round(self.posProf,3))
        d['frozenMarg'] = str(round(self.frozenMarg,3))
        d['marg'] = str(round(self.margin,3))
        d['closeProf'] = str(round(self.closeProf,3))
        d['balance'] = str(round(self.balance,3))
        d['avail'] = str(round(self.avail,3))
        d['totalpnl'] = str(round(self.totalpnl,3))
        d['totalfee'] = str(round(self.totalfees,3))
        d['daypnl'] = str(round(self.daypnl,3))
        d['dayfee'] = str(round(self.dayfees,3))
        d['turnover'] = str(round(self.turnover,3))
        d['winamount'] = str(round(self.winamount,3))
        d['lossamount'] = str(round(self.lossamount,3))
        d['wincount'] = str(round(self.wincount,3))
        d['losscount'] = str(round(self.losscount,3))
        d['maxmarg'] = str(round(self.maxmarg,3))
       
        #print("Account save to DB")
        saveAccountDatarealToDB(self.user, self.investorid, self.tradingDay, d)
        savePositionDatarealToDB(self.user, self.investorid, self.position, self.tradingDay)
        g_stat.updateData(self.balance, self.daypnl, self.dayfees, self.margin, self.turnover, self.tradingDay,\
                          self.winamount, self.lossamount, self.wincount, self.losscount,self.maxmarg,\
                          accid=self.accid, withdraw=self.withdraw, deposit=self.deposit)

    def saveOrders(self):
        unfinished_orders = {}
        #print('saveOrders1',self.orders)
        for oid in self.orders:
            if self.orders[oid]['leftvol'] > 0:
                unfinished_orders[oid] = self.orders[oid].copy()
                if 'autoremake' in unfinished_orders[oid]:
                    del unfinished_orders[oid]['autoremake']
                if 'autocancel' in unfinished_orders[oid]:
                    del unfinished_orders[oid]['autocancel']    
        saveUnfinishedOrders(self.user, self.investorid, self.tradingDay, unfinished_orders)     
        #print('saveOrders2',self.orders)                 
#         updateInitCap(self.user, self.balance)
#         logger.info(f'saveToDB {self.balance}')
    

    def loadFromDB(self,tradingDay):
        res = getDBAccountDetailReal(self.user, self.investorid, str(tradingDay))
        if res:
            d = eval(res)
            self.winamount = float(d['winamount'])
            self.lossamount = float(d['winamount'])
            self.wincount = float(d['wincount'])
            self.losscount = float(d['losscount'])
            self.maxmarg = float(d['maxmarg'])
        g_stat.loadFromDBReal(int(tradingDay)) 
        orders = getDBOrderDatareal(self.user, self.investorid, tradingDay)
        for oid in orders:
            stgname = eval(orders[oid])['stratName']
            self.order_stg_table[oid] = stgname
        #print(self.order_stg_table)
        self.stgtable_load = True  
        delDBOrderDataReal(self.user, self.investorid, tradingDay)
        delDBTradeDataReal(self.user, self.investorid, tradingDay)
        self.riskctl.load(tradingDay)
        unfinished_orders = loadUnfinishedOrders(self.user, self.token, tradingDay)
        if unfinished_orders:
            for oid in unfinished_orders:
                self.orders[int(oid)] = unfinished_orders[oid]
    
        
#realaccount = realAccountInfo()

