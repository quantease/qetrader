# -*- coding: utf-8 -*-
"""
Created on Wed Nov  3 17:39:15 2021

@author: ScottStation
"""
import time
import json
from datetime import datetime, timedelta
from .qetype import qetype
from qesdk import is_valid_trade_time
from .qeredisdb import getDBPositionData,getDBOrderData,getDBTradeData,saveTradeDataToDB,saveOrderDataToDB
from .qeredisdb import saveNewAccountToDB, loadSimuAccounts,removeDBSimuAccounts,getDBAccountData
from .qeredisdb import getSimuInitCap,updateInitCap,saveAccountDataToDB,savePositionDataToDB
from .qelogger import logger
from .qestatistics import g_stat
from .qeglobal import instSetts
from .qeriskctl import riskControl
import numpy as np
#import collections


#tstrats = {}
#instSetts = {}
from .qeglobal import g_dataSlide
feesmult = 1.0

from threading import Timer

def getMixPrice(oldp, oldv, newp, newv):
    return(oldp*oldv + newp*newv)/(oldv+newv)

def getCurTradingDay():
    now = datetime.now()
    wday = now.weekday()
    if now.hour >= 19:
        if wday < 5:
            now += timedelta(days=1)
        else:    
            now += timedelta(days=3)
            
    elif now.hour < 8 and wday == 5:
        now += timedelta(days=2)
    return int(now.strftime('%Y%m%d'))            


class accountInfo():
    def __init__(self,user='unknown',token=''):
        self.balance = 10000000
        self.avail = self.balance
        self.margin = 0
        self.maxmarg = 0
        self.frozenMarg = 0
        self.pendVolumes = {}
        self.frozenVol = {}
        self.position = {}
        self.trades = {}
        self.orders = {}
        
        #self.g_order_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.g_trade_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.closeProf = 0
        self.posProf = 0
        self.daypnl = 0
        self.totalpnl = 0
        self.dayfees = 0
        self.totalfees = 0
        self.winamount = 0
        self.lossamount = 0
        self.wincount = 0
        self.losscount = 0
        self.turnover = 0
        self.current_timedigit = 0
        self.tradingDay = ""
        self.user = user
        self.token = token
        self.curtime = datetime.now()
        self.riskctl = riskControl(self.riskctlCall,user=user,token=token,runmode='simu')
        self.loadReady = False
        self.loadPosition = True
        self.stratCross = {}
        self.callback = None
        
   
    def crossday(self):
        logger.info('simuaccount.crossday')
        self.dayfees = 0
        self.daypnl = 0
        self.trades = {}
        self.orders = {}
        #self.g_order_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.g_trade_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        self.pendVolumes = {}
        self.frozenMarg = 0
        self.winamount = 0
        self.lossamount = 0
        self.wincount = 0
        self.maxmarg = 0
        self.losscount = 0
        self.turnover = 0
        self.riskctl.crossDay()
        for inst in self.position.keys():
            self.position[inst]['long']['yesvol'] = self.position[inst]['long']['volume']
            self.position[inst]['short']['yesvol'] = self.position[inst]['short']['volume']
        self.checkforceclose()
    def setTradingDay(self, tradingDay):
        self.tradingDay = tradingDay
        self.riskctl.setTradingDay(tradingDay)
    
    def setLoadReady(self):
        self.loadReady = True
        
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
    
    def getPosProf(self):
        global g_dataSlide
        posProf = 0
        position = self.position.copy()
        for inst in position.keys():
            if inst in g_dataSlide:# and inst in instSetts:
                current = g_dataSlide[inst]['current']
                volMult = instSetts[inst]['volmult']
                if self.position[inst]['long']['volume'] > 0:
                    posProf += volMult * (current - self.position[inst]['long']['poscost']) * \
                               self.position[inst]['long']['volume']
                if self.position[inst]['short']['volume'] > 0:
                    posProf += volMult * (self.position[inst]['short']['poscost'] - current) * \
                               self.position[inst]['short']['volume']
        return posProf                   
    
    def getPositionVol(self,instid):
        totalL = self.getPosition(instid, 'long', 'volume')
        totalS = self.getPosition(instid, 'short', 'volume')
        yesL = self.getPosition(instid, 'long','yesvol')
        yesS = self.getPosition(instid, 'short', 'yesvol')
        return totalL - yesL , yesL, totalS - yesS, yesS    
    
    def updateMargin(self):
        global g_dataSlide
        marg = 0
        position = self.position.copy()
        for instid in position.keys():
            #current = g_dataSlide[inst]['current']
            tL, yL, tS, yS = self.getPositionVol(instid)
            margL = self.getMargin(self.getPosition(instid, 'long', 'poscost'), True, tL, instid) 
            if yL > 0:
                margL += self.getMargin(g_dataSlide[instid]['presett'], True, yL, instid)
            margS = self.getMargin(self.getPosition(instid, 'short', 'poscost'),False, tS, instid)
            if yS > 0:
                margS += self.getMargin(g_dataSlide[instid]['presett'], False, yS, instid)
            marg += margL + margS
            #marg += self.getMargin(self.position[inst]['long']['poscost'], True, self.position[inst]['long']['volume'], inst)
            #marg += self.getMargin(self.position[inst]['short']['poscost'], False, self.position[inst]['short']['volume'], inst)
        self.margin = marg
        self.maxmarg = max(marg, self.maxmarg)
        #print("account margin",self.margin, self.position)
        
    def updateFrozenMarg(self):
        global g_dataSlide
        fm = 0
        for oid in self.orders:
            order = self.orders[oid]
            if order['leftvol'] >0 and order['action'] == 'open':
                inst = order['instid']
                odir = order['direction']
                if order['ordertype'] == 'market':
                    current = g_dataSlide[inst]['current'] if inst in g_dataSlide else 0
                else:
                    current = order['price']
                if current > 0:
                    fm += self.getMargin(current, odir > 0, order['leftvol'], inst)
        self.frozenMarg = fm        
    
    #def updateFrozenMarg(self):
    #    global g_dataSlide
    #    fm = 0
    #    for inst in self.pendVolumes.keys():
    #        #current = g_dataSlide[inst]['current']
    #        fm += self.getMargin(self.pendVolumes[inst]['long']['poscost'], True, self.pendVolumes[inst]['long']['volume'], inst)
    #        fm += self.getMargin(self.pendVolumes[inst]['short']['poscost'], False, self.pendVolumes[inst]['short']['volume'], inst)
    #    self.frozenMarg = fm
    def updateStratPostion(self, pos):
        def mixPosition(cost1, vol1, cost2, vol2):
            cost  =  (cost1*vol1 + cost2*vol2)/(vol1+vol2) if vol1+vol2 > 0 else 0
            vol = vol1 + vol2
            return {'volume': vol, 'poscost': cost, 'yesvol': 0}
            
            
        for inst in pos:
            if inst in self.position:
                for dirstr in pos[inst]:
                    if dirstr in self.position[inst]:
                        self.position[inst][dirstr] = mixPosition( self.position[inst][dirstr]['poscost'], self.position[inst][dirstr]['volume'], pos[inst][dirstr]['poscost'], pos[inst][dirstr]['volume'] )
                    else:
                        self.position[inst][dirstr] = pos[inst][dirstr]
                    
            else:
                self.position[inst] = pos[inst]
        
        
        
    def updateCapital(self, closeProf, fee):
        lastPosProf = self.posProf
        self.posProf = self.getPosProf()
        #print(type(closeProf), type(fee), type(lastPosProf), type(self.posProf))
        self.balance += closeProf - fee -lastPosProf + self.posProf
        self.avail = self.balance -self.margin - self.frozenMarg
    
    def getMargin(self, current, bLong, vol, instid):
        marginrate = instSetts[instid]['marglong'] if bLong else instSetts[instid]['margshort']
        return current * marginrate / 100 * vol * instSetts[instid]['volmult']

    def getCommission(self,  action, price, vol, closetype,instid):
        #global instSetts
        
        if action == 'open':

            return instSetts[instid]['openfee'] * vol + instSetts[instid]['openfeerate'] * vol * price * \
                   instSetts[instid]['volmult']
        else:
            rate = instSetts[instid]['closetodayrate'] if closetype == 'closetoday' else 1
            return  rate * (instSetts[instid]['closefee'] * vol + \
                                                          instSetts[instid]['closefeerate'] * vol * price * instSetts[instid]['volmult'])

    def readAndSetDB(self):
        import math
        try:
            #load from db ,if not exist, write default value
            bal =  getSimuInitCap(self.user)
            if bal is None or math.isnan(float(bal)):
                updateInitCap(self.user, self.balance)
            else:
#                 logger.info(f'load balance:{self.balance}')
                self.balance = float(bal)
        except Exception as e:
            logger.error(f"account.readAndSetDB error {e}",exc_info=True ) 
          
    
    def saveToDB(self):
        d = {}
        # d['tradingday'] = self.tradingDay 
        # d['timedigit'] = self.current_timedigit 
#         d['initcapital'] = account.initCapital
#         d['curpnl'] = account.curpnl
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
        d['tradingDay'] = str(self.tradingDay)
        d['winamount'] = str(round(self.winamount, 3))
        d['lossamount'] = str(round(self.lossamount, 3))
        d['wincount'] = str(round(self.wincount, 3))
        d['losscount'] = str(round(self.losscount, 3))
        d['turnover'] = str(round(self.turnover, 3))
        d['maxmarg'] = str(round(self.maxmarg, 3))
        
        saveAccountDataToDB(self.user, self.token,  d)
        savePositionDataToDB(self.user, self.token, self.position)
        
        g_stat.updateData(self.balance, self.daypnl, self.dayfees, self.margin, self.turnover, self.tradingDay,\
                          self.winamount, self.lossamount, self.wincount, self.losscount,self.maxmarg)
        #updateInitCap(self.user, self.balance)
        #logger.info(f'saveToDB {self.balance}')
    
    def getPosition(self, instid, dirstr,feild='volume'):
         if instid in self.position:
            if dirstr in self.position[instid]:
                if feild in self.position[instid][dirstr]:
                    return self.position[instid][dirstr][feild]
         return 0
       
    '''
    def getFrozenVol(self, instid, dirstr):
        if instid in self.frozenVol:
            if dirstr in self.frozenVol[instid]:
                return self.frozenVol[instid][dirstr]
        return 0
    '''
    
    def calcFrozenVol(self, instid, direction):
        fvol = 0
        for oid in self.orders:
            order = self.orders[oid]
            if order['instid'] == instid and order['leftvol'] > 0 and order['action']=='close' and order['direction'] == direction:
                fvol += order['leftvol']
        return fvol
        
    def makeOrder(self, action, direction, price, vol, instid):
        margin = self.getMargin(price, direction>0, vol, instid)
        if action == 'open' and self.avail <= margin:
            return -1
        elif action == 'open':
            pass
            '''
            if direction > 0:
                if instid in self.pendVolumes:
                    self.pendVolumes[instid]['long']['poscost'] = getMixPrice(self.pendVolumes[instid]['long']['poscost'],self.pendVolumes[instid]['long']['volume'],price,vol)
                    self.pendVolumes[instid]['long']['volume'] += vol
                else:
                    self.pendVolumes[instid]={'long':{'volume':vol,'poscost':price}, "short":{'volume':0,"poscost":0}}
            else:
                if instid in self.pendVolumes:
                    self.pendVolumes[instid]['short']['poscost'] = getMixPrice(self.pendVolumes[instid]['short']['poscost'],self.pendVolumes[instid]['short']['volume'],price,vol)
                    self.pendVolumes[instid]['short']['volume'] += vol
                else:
                    self.pendVolumes[instid]={'long':{'volume':0,"poscost":0}, "short":{'volume':vol,'poscost':price}}
            '''
        elif action == 'close':
            dirstr = 'short' if direction > 0 else 'long'
            pend = self.calcFrozenVol(instid, direction)
            #fvol = self.getFrozenVol(instid, dirstr)
            pos = self.getPosition(instid, dirstr)
            leftvol = pos - pend
            if vol > leftvol:
                print(f'Position is not enough: vol{vol}, pos {pos}, pend {pend}, left {leftvol}')
                logger.warning(f'Position is not enough: vol{vol},  pos {pos}, pend {pend}, left {leftvol}')
                return -2
            #else:
            #    if not instid in self.frozenVol:
            #        self.frozenVol[instid] = {"long":0, "short":0}
            #    self.frozenVol[instid][dirstr] += vol
                
              
                
                
        if instid[-3:]=='CCF':
            self.dayfees += 1
            self.totalfees += 1
        self.updateFrozenMarg()  
        self.avail =self.balance - self.margin - self.frozenMarg
        self.saveToDB()
        return 0    
        
        
    def cancelOrder(self, vol, direction, instid, action, saveDB=True):
        if action =='open':
            dirstr = 'long' if direction > 0 else 'short'
            #self.pendVolumes[instid][dirstr]['volume'] = max(self.pendVolumes[instid][dirstr]['volume']-vol,0)
            #if self.pendVolumes[instid][dirstr]['volume'] == 0:
            #    self.pendVolumes[instid][dirstr]['poscost'] = 0
                
            self.updateFrozenMarg()
            self.avail =self.balance - self.margin - self.frozenMarg

        #elif action =='close':
        #    dirstr = 'short' if direction > 0 else 'long'
            #self.frozenVol[instid][dirstr] = max(self.frozenVol[instid][dirstr] - vol, 0)
         
        
        if instid[-3:]=='CCF':
            self.dayfees += 1
            self.totalfees += 1
        if saveDB:
            self.saveToDB()    
        
        
    def  onTrade(self, instid, action, blong,  price, vol, closetype,feesmult=1.0):
        global g_dataSlide   #,  tstrats
        
        def updatePos(poscost, posvol, price, vol):
            if vol + posvol > 0:
                poscost = (poscost*posvol + price*vol)/(vol+posvol)
            else:
                poscost = 0
            posvol = vol + posvol
            return poscost, posvol
        try:
            
            dirstr = 'long' if blong else 'short'
            closeProf = 0
            if action=='open':
                ## update position
                if not instid in self.position:
                    if blong:
                        self.position[instid] = {'long':{'poscost':price,'volume':vol, 'yesvol':0}, \
                                                 'short':{'poscost':0,'volume':0, 'yesvol': 0}}
                    else:
                        self.position[instid] = {'short':{'poscost':price,'volume':vol, 'yesvol':0}, \
                                                 'long':{'poscost':0,'volume':0, 'yesvol':0}}
                else:

                    self.position[instid][dirstr]['poscost'],self.position[instid][dirstr]['volume'] = updatePos(self.position[instid][dirstr]['poscost'],self.position[instid][dirstr]['volume'], price, vol)
                #print('OnTrade', price, vol, self.position)

            elif action=='close':   
                volMult = instSetts[instid]['volmult']
                if dirstr == 'short':
                    closeProf = volMult * vol * (self.position[instid][dirstr]['poscost'] - price)
                else:
                    closeProf = volMult * vol * (price - self.position[instid][dirstr]['poscost'])

                self.daypnl += closeProf
                self.totalpnl += closeProf
                self.position[instid][dirstr]['volume'] -= vol
                #self.frozenVol[instid][dirstr] = max(self.frozenVol[instid][dirstr]-vol, 0)
                if closetype == 'closeyesterday':
                    self.position[instid][dirstr]['yesvol'] -= vol
                if self.position[instid][dirstr]['volume'] <= 0:
                    self.position[instid][dirstr] = {'poscost':0,'volume':0,'yesvol':0}
                    
                tfee = feesmult *self.getCommission("open",self.position[instid][dirstr]['poscost'] , vol, closetype, instid)
                tfee += feesmult * self.getCommission(action,price,vol, closetype,instid)
                tpnl = closeProf -tfee
                if tpnl > 0:
                    simuaccount.wincount += 1
                    simuaccount.winamount += tpnl
                elif tpnl < 0:
                    simuaccount.losscount += 1
                    simuaccount.lossamount += tpnl
                   
                
            ##update pendVolume
            '''
            if action == 'open':
                self.pendVolumes[instid][dirstr]['volume'] = max(self.pendVolumes[instid][dirstr]['volume'] -  vol, 0)
                if self.pendVolumes[instid][dirstr]['volume'] == 0:
                    self.pendVolumes[instid][dirstr] = {'poscost':0,'volume':0}
            '''
            
            self.turnover += price * vol * instSetts[instid]['volmult']
            self.updateFrozenMarg()
            self.updateMargin()
            fee = feesmult * self.getCommission(action,price,vol, closetype,instid)
            self.totalfees += fee
            self.dayfees += fee
            

            self.updateCapital(closeProf, fee)
            self.saveToDB()
        except Exception as e:
            logger.error(f"account.onTrade error {e}",exc_info=True ) 
    
        
    def autoAction(self, instid, blong, vol):
        checkdir = 'short' if blong else 'long'
        if self.position[instid][checkdir]['volume'] > 0:
            tvol = min(self.position[instid][checkdir]['volume'], vol)
            return 'close', tvol
        else:
            return 'open', vol
        
        
    
    def checkCloseToday(self, instid, blong, closetype, vol):
        dirstr = 'long' if blong else 'short'
        yesvol = self.getPosition(instid,dirstr,'yesvol')
        dayvol = self.getPosition(instid,dirstr,'volume') - self.getPosition(instid,dirstr,'yesvol')
        #print(closetype,self.position, instid, dirstr,  yesvol, dayvol, vol)
        if closetype == 'closeyesterday':
            return min(yesvol,vol), closetype
        elif closetype == 'closetoday':
            return min(dayvol,vol),closetype
        elif yesvol > 0:
            return min(yesvol, vol), 'closeyesterday'
        else:
            return min(dayvol, vol), 'closetoday'
    
    #def noticeCrossDay(self, name):
    #    if name in self.stratCross:
    #        self.stratCross[name] = 1
    #    if sum(self.stratCross.values()) == len(self.stratCross):
    #        self.checkForceClose()
    #        for name in self.stratCross:
    #            self.stratCross = 0
    def getFCVol(self, isToday, price, bLong, cost, presett, instid):
        volmult = instSetts[instid]['volmult']
        closetype = 'closetoday' if isToday else 'closeyesterday'
        factor1 = self.getMargin(price, bLong, 1, instid)
        cost = presett if not isToday else cost
        priceDiff = price - cost if bLong else cost - price 
        factor2 = priceDiff * volmult - self.getCommission('close',price, 1,closetype,instid)
        return factor1, factor2
        #return np.ceil((marg - balance) / (factor1 + factor2) )
                
    def calcForceClose(self, instid, marg, balance):
        global g_dataSlide
        A = marg
        B = balance
        tL, yL, tS, yS = self.getPositionVol(instid)
        ps = g_dataSlide[instid]['presett']
        costL, costS = self.getPosition(instid, 'long', 'poscost'), self.getPosition(instid, 'short', 'poscost'), 
        price = g_dataSlide[instid]['current']
        finished = False
        fclist = [0,0,0,0]
        if yL > 0:
            f1, f2 = self.getFCVol(False, price, True, costL, ps, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),yL)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[0] = fcvol
            finished = A < B
        if not finished and yS > 0:
            f1, f2 = self.getFCVol(False, price, False, costS, ps, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),yS)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[1] = fcvol
            finished = A < B
        if not finished and tL > 0:
            f1, f2 = self.getFCVol(True, price, True, costL, ps, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),tL)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[2] = fcvol
            finished = A < B
        if not finished and tS > 0:
            f1, f2 = self.getFCVol(True, price, False, costS, ps, instid)
            fcvol = min(np.ceil((A-B) /(f1+f2)),tS)
            A -= f1 * fcvol
            B += f2 * fcvol
            fclist[3] = fcvol
            finished = A < B
        return finished, A, B, fclist
          
    
    
    def checkforceclose(self):
        if self.balance <  self.margin:
            ## touch force close
            ## get max marg instid
            A = self.margin
            B = self.balance
            fcDict = {}
            position = self.position.copy()
            for instid in position:
                finished, A, B, fclist = self.calcForceClose(instid, A, B)
                fcDict[instid] = fclist
                if finished:
                    break
            print('权益低于保证金，触发平台强平操作')
            
            if self.callback:
                self.callback(fcDict)
            #force_close(self, fcDict)
    
simuaccount = accountInfo()           

def createSimuAccount(user, initCap=10000000):
    '''
    

    Parameters
    ----------
    user : str
        username.
    initCap : float, optional
        initial capital. The default is 10000000.

    Returns
    -------
    token : str
        token of new simulation account.

    '''
    import uuid
    token = str(uuid.uuid1()).replace('-', '')
    
    simuacc = accountInfo()
    simuacc.user = user
    simuacc.token = token
    simuacc.balance = initCap
    saveNewAccountToDB(user, token)
    simuacc.saveToDB()
    
    return token
    
def removeSimuAccountData(user, tokens=None, excepts=None):
    tlist = []
    if tokens:
         tlist = tokens
    else:
         tlist = loadSimuAccounts(user)
         if excepts:
             tlist = [t for t in tlist if not t in excepts]
    return removeDBSimuAccounts(user, tlist)         


def listSimuAccounts(user):
    ret = loadSimuAccounts(user)
    if ret:
        return ret
    else:
        return []             

def setSimuAccountCapital(user, token, capital):
    try:
        acc = getDBAccountData(user, token)
        if acc:
            d = json.loads(acc)
            d['balance'] = float(capital)
            saveAccountDataToDB(user,token,d)
            print(f'Change account capital to {capital} successfully.')
        else:
            print('Query account information failed')
    except Exception as e:
        print(f'Error:{e}')
        
class QEsimtrader(object):

    def __init__(self):
        
        self.tqueue = None
        self.strats = None
        self.curday = ''
        self.instVolume={}
        #self.g_orders = {}
        #self.g_trades = {}
        #self.g_order_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        #self.g_trade_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        
        #self.account = accountInfo()
        #simuaccount.balance=0
        
        #self.g_benchmark = self.g_order_id
        self.lasttime = 0
        self.user = 'unknown'
        self.Timer_interval = 60
        self.mapTable = {}     
    
    def callTimer(self): 
#         global tqueue
        timer = Timer(self.Timer_interval,self.callTimer)
        d = {}
        d['type'] = qetype.KEY_TIMER_SIMU
#         logger.info('timer '+str(datetime.now()))
        
        if self.tqueue:
            self.tqueue.put(d)
        else:
            logger.info('Timer is pending')
        timer.start()
        return
    def heartBeat(self,realTrade):
        pass
        '''
        d = {}
        d['time'] = datetime.now().strftime('%Y%m%d%H%M%S')
        if realTrade:
            d['type'] = 'real'
        else:
            d['type'] = 'simu'
#         print('heartbeat '+str(d['time']))
        saveProcessToDB(self.user,d)
        '''
    
    
    def loadFromDB(self, tradingDay):
        #tradingDay = getCurTradingDay()
        acc = getDBAccountData(self.user, self.token)
        simuaccount.user = self.user
        simuaccount.token = self.token
        logger.info(f'simuaccount.loadFromDB {tradingDay}')
        if acc:
            d = json.loads(acc)
            simuaccount.posProf = float(d['posProf'])
            simuaccount.frozenMarg = 0
            simuaccount.margin =   float(d['marg']) 
            simuaccount.closeProf =  float(d['closeProf'])
            simuaccount.balance = float(d['balance'])
            simuaccount.avail =  float(d['avail'])
            simuaccount.totalpnl = float(d['totalpnl'])
            simuaccount.totalfees = float(d['totalfee']) 
            simuaccount.daypnl = float(d['daypnl']) 
            simuaccount.dayfees = float(d['dayfee']) 
            simuaccount.winamount = float(d['winamount'])
            simuaccount.lossamount = float(d['lossamount'])
            simuaccount.wincount = float(d['wincount'])
            simuaccount.losscount = float(d['losscount'])
            simuaccount.turnover = float(d['turnover'])
            simuaccount.maxmarg = float(d['maxmarg'])
            
            #print(tradingDay, d)
            if d['tradingDay'] != '' and int(d['tradingDay']) < int(tradingDay):
                simuaccount.crossday()
            simuaccount.tradingDay = tradingDay
        else:
            logger.warn(f"读取模拟账户数据失败, user:{self.user},token:{self.token}.")
        
        if simuaccount.loadPosition:     
            pos = getDBPositionData(self.user, self.token)
            if pos:
                simuaccount.position = json.loads(pos)
        #else:
        #    logger.warn(f"读取模拟账户持仓数据失败, user:{self.user},token:{self.token}.")
        
        orders = getDBOrderData(self.user, self.token, tradingDay)
        for oid in orders:
            content = eval(orders[oid])
            simuaccount.orders[oid] = content
        
        trades = getDBTradeData(self.user,self.token, tradingDay)
        for tid in trades:
            content = eval(trades[tid])
            simuaccount.trades[tid] = content
        
        #print("load",simuaccount.position, simuaccount.margin, simuaccount.balance)
        ###Deal with unfinished orders
        
        for oid in simuaccount.orders:
            #print(oid)
            #print(simuaccount.orders[oid])
            #print(type(simuaccount.orders[oid]))
            if simuaccount.orders[oid]['leftvol'] > 0:
                simuaccount.orders[oid]['status'] = qetype.KEY_STATUS_PTPC if simuaccount.orders[oid]['tradevol'] > 0 else qetype.KEY_STATUS_CANCEL
                simuaccount.orders[oid]['cancelvol'] += simuaccount.orders[oid]['leftvol']
                simuaccount.orders[oid]['leftvol'] = 0
        g_stat.loadFromDBSimu(int(tradingDay))
        simuaccount.setLoadReady()
        simuaccount.riskctl.load(tradingDay)
    
    def sendForceCloseOrder(self, instid, direction, price, volume, ordertype="limit", action="open", closetype='auto'):
        now = datetime.now()
        orderid = g_stat.getNewOrderID()
        temporder = {'instid': instid,
                     'price': price,
                     'direction': direction,
                     'ordertype': ordertype,
                     'closetype': closetype,
                     'volume': volume,
                     'leftvol': volume,
                     'tradevol': 0,
                     'cancelvol': 0,
                     'pendvol': 0,
                     'status': 'committed',
                     'errorid': 0,
                     'errormsg': '',
                     'action': action,
                     'timecond': 'GFD',
                     'autoremake':[0,0,0,0,now,'wait'],
                     'autocancel': [0,0,0,0,now,'wait'],
                     'father': 0,
                     'accid': 0}

        temporder['type'] = qetype.KEY_SEND_ORDER
        temporder['stratName'] = 'force_close'
        temporder['orderid'] = orderid
        
        self.tqueue.put(temporder)
    
    
    
    def accountCallback(self, fcDict):
        global g_dataSlide
        for inst in fcDict:
            current = g_dataSlide[inst]['current']
            fclist = fcDict[inst]
            if fclist[0] > 0:
                self.sendForceCloseOrder(inst, -1, current,fclist[0],'market', 'close', 'closeyesterday')
            if fclist[1] > 0:
                self.sendForceCloseOrder(inst, 1, current,fclist[1],'market', 'close', 'closeyesterday')
            if fclist[2] > 0:    
                self.sendForceCloseOrder(inst, -1, current,fclist[2],'market', 'close', 'closetoday')
            if fclist[3] > 0:
                self.sendForceCloseOrder(inst, 1, current,fclist[3],'market', 'close', 'closetoday')
        
    
    
    def simTraderProcess(self):      
        logger.info(u"模拟器启动")
        print(u"模拟器启动")
        #simuaccount.feesmult = feesMult
        
        simuaccount.user = self.user
        #simuaccount.stratCross = {key : 0 for key in self.strats}
        simuaccount.callback = self.accountCallback
        #simuaccount.readAndSetDB()
        self.callTimer()
    
        if self.tqueue:
            #print('simtrader tqueue is ready')
            while True:
                
                while not self.tqueue.empty():
                    try:
                        d = self.tqueue.get(block = True, timeout = 1)
                        self.process(d)
                        
                    except Exception as e:
                        logger.error(f"simtrader tqueue error {e}",exc_info=True ) 
                          
                time.sleep(0.001)
            

    def process(self,d):
       
        if d['type'] == qetype.KEY_SEND_ORDER:
            self.sendOrder(d)
        elif d['type'] == qetype.KEY_CANCEL_ORDER:
            self.cancelOrder(d)
        elif d['type'] == qetype.KEY_MARKET_DATA:
            #print('trader mdata')
            self.update(d,d['instid'])
        elif d['type'] == qetype.KEY_ON_CROSS_DAY:
            self.crossday(d)    
        elif d['type'] == qetype.KEY_MARKET_MULTIDATA:
            self.update(d['data'][0],d['instid'])    
        elif d['type'] == qetype.KEY_TIMER_SIMU:
            #orderlen = len(simuaccount.orders)
            #logger.debug(f'simtrader.onTimer {orderlen}')
            simuaccount.updateCapital(0,0)
            simuaccount.saveToDB()
            
            #self.heartBeat(False)

    def callback(self,d):
        if self.strats:
            if self.strats['async']:
	            if d['stratName'] != 'force_close':
	                self.strats['queue'].put(d)
            else:
	            stratSett = self.strats.get(d['stratName'],None)
	            if stratSett:
	                stratSett['queue'].put(d)
	            elif d['stratName'] != 'force_close':
	                logger.error('callback '+str(d['stratName'])+' is not found')

    def crossday(self,d):
        #self.g_order_id = self.g_benchmark
        logger.info('simTrader.crossday')
        self.instVolume = {}
        self.mapTable = {}     
        #self.g_order_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        #self.g_trade_id = int('3'+datetime.now().strftime('%Y%m%d')[2:])*100000
        simuaccount.crossday()
        simuaccount.setTradingDay(d['tradingDay'])
        self.curday = d['tradingDay']
       
        
        
    def update(self,d,instid):
        global g_dataSlide
        try:
            
            #g_dataSlide[d['instid']] = d['data']
            self.curtime = datetime.strptime(str(d['data']['timedigit'])[:14],"%Y%m%d%H%M%S")
            #if not self.mode_724 and not is_valid_trade_time(d['instid'],curtime):
                #print("Invalid data time",curtime, d['instid'])
            #    return
            if d['data']['tradingday'] != self.curday:
                #if self.curday != '':
                #    self.crossday()
                self.curday = d['data']['tradingday']
            #print("update to matchTrade")
            self.matchTrade(instid)
            
            simuaccount.current_timedigit = d['data']['timedigit']
            if simuaccount.tradingDay == '':
                self.loadFromDB(d['data']['tradingday'])
            
            simuaccount.setTradingDay (d['data']['tradingday'])
            
            if self.lasttime == 0 :
                #print('first update')
                self.lasttime = d['data']['timedigit']
                simuaccount.updateCapital(0, 0)
                simuaccount.saveToDB()
                
            elif abs(d['data']['timedigit'] - self.lasttime) > 2500:
                
                ##every above 2.5 second, update capital
                self.lasttime = d['data']['timedigit']
                simuaccount.updateCapital(0, 0)
                simuaccount.saveToDB()
            
        except Exception as e:
            logger.error(f"update error {e}",exc_info=True ) 
    
    def sendOrder(self,order):
        global g_dataSlide
        try:
            #if str(g_dataSlide[order['instid']]['timedigit'])[8:12] == '1015':
            #    order['status'] =  qetype.KEY_STATUS_REJECT
            #    order['cancelvol'] = order['leftvol']
            #    order['leftvol'] = 0
            #    order['errorid'] = 1
            #    order['errormsg'] =  'Not trade time.'
            #    #logger.warning(f'Warning: not trade time: {g_dataSlide[order['instid']]['timedigit']} ')                                   
            destprice = order['price'] if order['ordertype'] == 'limit' else g_dataSlide[order['instid']]['current']
            res = simuaccount.makeOrder(order['action'],order['direction'], destprice , order['volume'], order['instid'])
            
            if res != 0 :
                order['status'] =  'failed'
                order['cancelvol'] = order['leftvol']
                order['leftvol'] = 0
                order['errorid'] = abs(res)
                if res == -1:
                    order['errormsg'] =  '资金不足' 
                    logger.warning(f'Warning: 资金不足。剩余可用权益: {simuaccount.avail} ') 
                else:
                    order['errormsg'] =  "可平持仓不足"
                    instid = order['instid']
                    longpos = simuaccount.getPosition(instid,'long')
                    shortpos = simuaccount.getPosition(instid,'short')
                    logger.warning(f'Warning: 可平持仓不足。目前多仓 {longpos}, 空仓 {shortpos}') 
                    
#             else:
#                 logger.debug("pass account makeorder")

            #simuaccount.g_order_id += 1
            #self.mapTable[simuaccount.g_order_id] = order['incoming_orderid']
            #self.mapTable[order['incoming_orderid']] = simuaccount.g_order_id
            #order['orderid'] = simuaccount.g_order_id
            
            if order['status'] == 'committed':
                order['status'] = qetype.KEY_STATUS_PENDING
            elif order['status'] == 'failed':
                order['status'] =qetype.KEY_STATUS_REJECT
            else:
                order['status'] = qetype.KEY_STATUS_UNKNOWN
                
            simuaccount.orders[order['orderid']] = order
            #print(simuaccount.g_order_id, len(simuaccount.orders))
            self.rtnOrder(order)

            #self.matchTrade(instid)
        except Exception as e:
            logger.error(f"sendorder error {e}",exc_info=True ) 

            
    def cancelOrder(self,d):
        def docancel(order):
            if order['tradevol'] > 0:
                order['status'] = qetype.KEY_STATUS_PTPC
            else:    
                order['status'] = qetype.KEY_STATUS_CANCEL
            order['cancelvol'] = order['leftvol']
            order['leftvol'] = 0
            
        try:
            if d['orderid'] == 0:
                for id in simuaccount.orders.keys():
                    order = simuaccount.orders[id]
                    if order['stratName'] == d['stratName']:
                        if order['status'] == qetype.KEY_STATUS_PENDING or order['status'] == qetype.KEY_STATUS_PART_TRADED:
                            docancel(order)
                            simuaccount.cancelOrder( order['volume'], order['direction'], order['instid'],order['action'],saveDB=False)
                            self.rtnOrder(order)
                simuaccount.saveToDB()        
            else:
                order = simuaccount.orders.get(d['orderid'],None)
                if order:
                        if order['status'] == qetype.KEY_STATUS_PENDING or order['status'] == qetype.KEY_STATUS_PART_TRADED:
    #                         print('cancel order')
                            docancel(order)
                            self.rtnOrder(order)
                            simuaccount.cancelOrder( order['volume'], order['direction'], order['instid'],order['action'])
                        else:
                            logger.error('cancel order failed')

                else:
                        logger.error('cancel order is not found')

 
        except Exception as e:
            logger.error(f"cancelorder error {e}",exc_info=True ) 

    def rtnOrder(self,order):
        #global g_orders,g_order_id,mapTable
        #print('rtnOrder', order['status'])
        content = simuaccount.orders.get(order['orderid'],-1)
        if content != -1:
            #stratID = int(str(incoming_orderid)[:5])
            
            # copy order update d
            d = {key:value for key,value in content.items()}
            d['type'] = qetype.KEY_ON_ORDER
            
            temp_time = order.get('timedigit',-1)
            if temp_time != -1:
                d['timedigit'] = temp_time
            else:
                d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
            
            time = str(d['timedigit'])
            d['time'] = time[:8]+' '+time[8:10]+':'+time[10:12]+':'+time[12:14]+"."+time[14:]
            order['time'] = d['time']
            order['timedigit'] = d['timedigit']
            
            simuaccount.orders[d['orderid']] = order
            sorder = order.copy()
            del sorder['autocancel']
            del sorder['autoremake']
            sorder['accid'] = 0
            saveOrderDataToDB(self.user,self.token, simuaccount.tradingDay, sorder )
            
            self.callback(d)
        else:
            logger.error('rsp order id is not found')

    def rtnTrade(self,trade):
        #global g_orders
        trade['type'] = qetype.KEY_ON_TRADE 
        inst = trade['instid']
        trade['presett'] = g_dataSlide[inst]['presett']
        self.callback(trade)
            
             
        
#             print('rsp trade id is not found')

    # def getStratName(self,data):
    #     tempdata = data.split("#")   # string is '',strateName,orderid
    #     return (tempdata[-2], tempdata[-1]) 
        

    def matchTrade(self,instid):
        global g_dataSlide
        
        tradeprice = 0.0
        tradevol = 0
        #debug_flag = False
        
        
        #print("matchTrade", self.g_order_id,self.g_benchmark)
        #return
        #print('matchTrade', len(simuaccount.orders), instid)
        if len(simuaccount.orders) > 0:
            try:
                for key,order in simuaccount.orders.items():
                    #for instid in instids:
                        #print('key',key, 'order',order['leftvol'],order['volume'],order['direction'],order['action'],instid,order['instid'])
                        if order['leftvol'] > 0 and instid == order['instid']:
    #                         print('orderid '+str(order['incoming_orderid']))
                            #instid = order['instid']
                            #if order['status'] == qetype.KEY_STATUS_PART_TRADED:
                            #print("check again:",order['status'], instid, order['leftvol'], order['volume'], order['direction'], order['action'])
                            if not self.mode_724 and not is_valid_trade_time(instid,self.curtime):
                                print("MatchTrade failed on invalid data time",self.curtime, instid)
                                logger.info(f"MatchTrade failed on invalid data time:{self.curtime}, intid:{instid}")
                                continue
                            if g_dataSlide.get(instid, None) is None:
                                logger.info(f"MatchTrade failed on g_dataslide have no data on such {instid}" )
                                continue
                            if g_dataSlide[instid].get('presett',0) == 0:
                                logger.info(f"MatchTrade failed on presettle price is zero on such {instid}" )
                                continue
                                
                            stratName = order['stratName']
                             
                            found = False
                            if self.strats: 
                                if self.strats['async']:
                                    for strat in self.strats['strat']:
                                        if strat.name == stratName:
                                            found = True                                   
                                            flippage = strat.flippage
                                            traderate = strat.traderate
                                            feesmult = strat.feesmult
                                            break
                                    if not found:
                                        flippage = 0
                                        traderate = 1
                                        feesmult = 1
                                else:
                                    if stratName in self.strats:
                                        strat = self.strats[stratName]['strat']
                                        flippage = strat.flippage
                                        traderate = strat.traderate
                                        feesmult = strat.feesmult
                                    else:
                                        flippage = 0
                                        traderate = 1
                                        feesmult = 1                            
                            ticksize = instSetts[instid]['ticksize']

                            tick = g_dataSlide[instid]
                            #print('matchTrade volume', instid, self.instVolume,tick['volume'])
                            opvol = tick['a1_v'] if order['direction'] > 0 else tick['b1_v']
                            
                            if instid in self.instVolume and tick['volume'] >= self.instVolume[instid]:
                                    curvol = tick['volume'] - self.instVolume[instid]
                                    self.instVolume[instid] = tick['volume']
                            else:
                                self.instVolume[instid] = tick['volume']
                                curvol = 0
                            
                            curvol = max(curvol, opvol)    
    #                         logger.debug('curvol location '+str(curvol)+';')
                            
    #                         if debug_flag:
    #                             logger.debug('tick a='+str(tick['a1_p'])+', b='+str(tick['b1_p']))
    #                             logger.debug('order left '+str(order['leftvol'])+' type '+str(order['ordertype'])+' type '+str(order['direction']))
                                    
                            if order['ordertype'] == 'market':
    #                             if debug_flag:
    #                                 logger.debug('going to market')
                                if order['direction'] > 0:
                                    
                                    #tradeprice = tick['current'] if tick['current'] >= tick['a1_p'] else tick['a1_p']
                                    #trade_able_count = tick['a1_v']
                                    # waiting for next phase to address trade condition
                                    tradeprice = tick['a1_p'] + flippage *ticksize if flippage > 0 and tradeprice < tick['a1_p'] + flippage*ticksize else tick['a1_p']
                                else:
                                    #tradeprice = tick['current'] if tick['current'] <= tick['b1_p'] else tick['b1_p']
                                    #trade_able_count = tick['b1_v']
                                    # waiting for next phase to address trade condition
                                    tradeprice = tick['b1_p'] - flippage *ticksize if flippage > 0 and tradeprice > tick['b1_p'] - flippage *ticksize else tick['b1_p']

                                #tradevol = max(int(curvol * traderate), 1)       
                                tradevol = order['leftvol']
                                #tradevol = order['leftvol']  if order['leftvol']  < tradevol else tradevol
    #                             logger.debug('tradevol '+str(tradevol)+';')
                            elif order['ordertype'] == 'limit':
    #                             if debug_flag:
    #                                 logger.debug('going to limit')
                                tradeprice = order['price']
                                if (order['direction'] > 0 and tick['current'] > order['price'] ) or(order['direction'] < 0 and tick['current'] < order['price'] ):
                                    tradevol = 0
                                    #continue
                                elif tick['current'] == order['price']:
                                    tradevol = curvol - order['pendvol'] if curvol >= order['pendvol'] else 0
                                    order['pendvol'] -= order['pendvol'] if curvol > order['pendvol'] else curvol
                                    if tradevol > 0:
                                        tradevol = order['leftvol']  if order['leftvol']  < tradevol else tradevol
                                else:
                                    tradevol = max(int(curvol * traderate),1)
                                    tradevol = order['leftvol']  if order['leftvol']  < tradevol else tradevol
                                    
                                if (order['timecond'] =='FOK' and tradevol < order['leftvol']) or (order['timecond'] =='FAK' and tradevol == 0):
                                    order['status'] = qetype.KEY_STATUS_CANCEL
                                    order['tradevol'] = 0
                                    order['cancelvol'] = order['volume']
                                    order['leftvol'] = 0
                                    order['timedigit'] = tick['timedigit']
                                    self.rtnOrder(order)
                                    tradevol = 0
                                '''   
                                elif (order['direction'] > 0 and tick['a1_p'] == order['price'] ) or(order['direction'] < 0 and tick['b1_p'] == order['price'] ):
                                    tempvolume = tick['a1_v'] if order['direction'] > 0 else  tick['b1_v']
                                    tradevol = order['leftvol'] if order['leftvol'] <= tempvolume else tempvolume
                                elif (order['direction'] > 0 and tick['a1_p'] < order['price'] ) or(order['direction'] < 0 and tick['b1_p'] > order['price'] ):
                                    tradevol = order['leftvol'] # waiting for next phase to address liquidation
                                '''    

                            if tradevol > 0:
    #                             print('matchTrade tradevol')
                                ##add closeYesterday codes
                                #if order['action'] == 'auto':
                                #    order['action'], tradevol = simuaccount.autoAction(instid, order['direction']>0, tradevol)
    #                             logger.debug('autoaction tradevol '+str(tradevol))
                                closetype = order['closetype']
                                if order['action'] == 'close':
                                    tradevol, closetype = simuaccount.checkCloseToday(instid, order['direction']<0, closetype, tradevol)
    #                                 logger.debug('checkclosetoday tradevol '+str(tradevol))
                                    if tradevol == 0:
                                        if order['timecond'] == 'FAK' or order['timecond'] == 'FOK':
                                            order['status'] = qetype.KEY_STATUS_CANCEL
                                            order['tradevol'] = 0
                                            order['cancelvol'] = order['volume']
                                            order['leftvol'] = 0
                                            order['timedigit'] = tick['timedigit']
                                            self.rtnOrder(order)
    #                                     try:
    #                                         print(simuaccount.position[instid]['long'])
    #                                     except Exception as e:
    #                                         print("print account position ",e.__traceback__.tb_lineno, e ) 
    #                                     logger.debug('hit')
                                        #logger.warning(f'matchTrade invalid closetype {closetype}')
                                        continue
                                blong = order['direction']>0 if order['action']=='open' else order['direction']<0   
                                simuaccount.onTrade(instid, order['action'], blong, tradeprice, tradevol, closetype,feesmult)
                                
                                simuaccount.g_trade_id += 1
                                order['tradevol'] += int(tradevol)
                                order['leftvol'] = max(order['leftvol'] - int(tradevol),0)
                                order['timedigit'] = tick['timedigit']

                                if order['timecond'] == 'FAK':
                                    order['status'] = qetype.KEY_STATUS_PTPC if order['leftvol'] > 0 else qetype.KEY_STATUS_ALL_TRADED
                                    order['cancelvol'] = order['leftvol']
                                    order['leftvol'] = 0
                                else:
                                    if order['leftvol'] == 0:
                                        order['status'] = qetype.KEY_STATUS_ALL_TRADED
                                    else:
                                        order['status'] = qetype.KEY_STATUS_PART_TRADED
                                    
                                trade = {}

                                trade['instid'] = instid
                                trade['orderid'] = order['orderid']
                                trade['stratName'] = order['stratName']
                                trade['tradeid'] = simuaccount.g_trade_id                         
                                trade['tradevol'] = int(tradevol)
                                trade['tradeprice'] = tradeprice
                                trade['timedigit'] = tick['timedigit']
                                trade['date'] = tick['time'][:8]
                                trade['time'] = tick['time'][9:]
                                trade['action'] = order['action']
                                trade['dir'] = order['direction'] 
                                trade['closetype'] = closetype
                                logger.info(f"OnTrade:instid {instid},orderid {trade['orderid']},price {trade['tradeprice']},\
                                            vol {trade['tradevol']}, action {trade['action']},dir {trade['dir']}, closetype {trade['closetype']}")
                                trade['accid'] = 0
                                saveTradeDataToDB(self.user, self.token, simuaccount.tradingDay, trade )

                                if trade['stratName'] == 'force_close':
                                    print(f"{tick['time']} Force Closed price:{trade['tradeprice']}, vol:{trade['tradevol']}, intid:{trade['instid']}, direction:{trade['dir']}, orderid: {trade['orderid']}, closetype:{trade['closetype']}")
                                    
    #                             tradedata = {}
                                                      
    #                             tradedata['timedigit'] = tick['timedigit']
    #                             tradedata['time'] = tick['time']
    #                             tradedata['action'] = order['action']
    #                             tradedata['dir'] = order['direction']     
    #                             tradedata['tradeprice'] = tradeprice
    #                             tradedata['vol'] = int(tradevol)
    #                             tradedata['closetype'] = closetype
    #                             trade['data'] = tradedata

                                simuaccount.trades[simuaccount.g_trade_id] = trade

                                self.rtnOrder(order)
                                self.rtnTrade(trade)

            except Exception as e:
                logger.error(f"matchTrade {e}",exc_info=True ) 
                        
                
        
        return





        
        
def runQETraderProcess(user, token, strats,traderqueue, mode_724):
    logger.info('start trader process')
    qesimtrader = QEsimtrader()
    #simuaccount.balance=balance
    #print('balance',self.balance)
    qesimtrader.user = user
    qesimtrader.token = token
    qesimtrader.strats = strats
    qesimtrader.tqueue = traderqueue
    #qesimtrader.loadFromDB()
    qesimtrader.mode_724 = mode_724
    #qesimtrader.master_orders = master_orders
    qesimtrader.simTraderProcess()






if __name__ == '__main__':
    #from multiprocessing import Queue
    #runQETraderProcess('scott','888888',Queue(),balance)
    pass









