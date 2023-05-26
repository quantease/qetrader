# -*- coding: utf-8 -*-
"""
Created on Mon Mar 21 11:04:10 2022

@author: ScottStation
"""
from  datetime import datetime, timedelta
import traceback

#MAX_SEC_RISK_CTL_MAX = 10
#class soptRiskControlModel:
#    def __init__(self):
#        self.dailyMax = 10000
#        self.secMax = 10
#        self.dailyCount = 0
#        self.lastts = 0    
#        self.intervals = []
#        self.delayorders = {'curtime':None, 'orderlist':[]}
#    def setDailyMax(self, dailyMax):
#        self.dailyMax = dailyMax
#        
#    def setSecMax(self, secMax):
#        self.secMax = min(secMax, MAX_SEC_RISK_CTL_MAX)
# 
#    def getRetryOrders(self):
#        if len(self.delayorders['orderlist']) > 0:
#            curts = int(datetime.now().timestamp()*1000)
#            if curts - self.delayorders['curtime'] > 1000:
#                  num = min(len(self.delayorders['orderlist']), int(self.secMax / 2))
#                  tmplist = self.delayorders['orderlist'][:num]
#                  self.delayorders['orderlist'] = self.delayorders['orderlist'][num:]
#                  return  tmplist
#                  
#        return None
#    
#    def putRetryOrders(self, curtime, orderids):
#        if len(orderids) > 0:
#            self.delayorders['curtime'] = curtime
#            self.delayorders['orderlist'] += orderids
#    
#    def newCount(self, num=1, orderids=[]):
#        curts = int(datetime.now().timestamp()*1000)
#        if self.dailyCount + num <= self.dailyMax:
#            self.dailyCount += num
#        else:
#            return -1;
#        
#        
#        
#        if num > self.secMax:
#            self.putRetryOrders(curts, orderids)
#            return -2
#        
#        
#        elif self.lastts > 0:
#            tmpsum = num - 1
#            
#            interval = curts - self.lastts
#            if tmpsum + interval > 1000:
#                self.intervals = []
#                for i in range(1,num):
#                    self.intervals.append(1)
#            else:
#                savedints = self.intervals       
#                tmpints = [interval]
#                for i in range (1, num):
#                    tmpints.append(1)
#                failed = False
#                for  i in range(len(self.intervals)-1, -1, -1 ):
#                    if self.intervals[i] + sum(tmpints) <= 1000:
#                        if len(tmpints) + 1 <= self.dailyMax:
#                            tmpints =  [self.intervals[i]] + tmpints
#                        else:
#                            failed = True
#                            break
#                    else:
#                        break
#                if not failed:
#                    self.intervals = tmpints
#                else:
#                    self.intervals = savedints
#                    self.putRetryOrders(curts, orderids)
#                    return -2
#
#        else:
#            for i in range(1, num):
#                self.intervals.append(1)
#
#                
#        self.lastts = curts
#        return 0
#    
#    def crossday(self):
#        self.dailyCount = 0
#        self.intervals = []   
#        
#soptriskctl = soptRiskControlModel()   


#class ctpRiskControlModel:
#    def __init__(self):
#        self.dailyMax = 400
#        self.dailyCount = 0
#
#    def setCancelDailyMax(self, dailyMax):
#        self.dailyMax = dailyMax
#        
# 
#    def cancelCount(self,num=1):
#        if self.dailyCount + num <= self.dailyMax:
#            self.dailyCount += num
#            return 0;
#        else:
#            return -1;
#    
#    def crossday(self):
#        self.dailyCount = 0
# 
#ctpriskctl = ctpRiskControlModel()        


######################## New design ###########################################

class riskControl(object):
    def __init__(self, callback):
        ## maxcancels
        self.modules = {'maxcancels':False,'daymaxacts':False, 'secmaxacts':False, 'selftrade':False}
        self.maxcancels = 380
        self.daycancles = 0
        self.daymaxacts = 10000
        self.maxselftrades = 4
        self.dayselftrades = 0
        self.dayacts = 0
        self.secmaxacts = 10
        self.secacts = []
        self.callback = callback
    
    def active(self, module,paras=None):
        try:
            if paras and not isinstance(paras, list):
                paras = [paras]
            if module =='maxcancels':
                if not paras is None:
                    self.maxcancels = paras[0]
                print('Successfully active maxcancels risk control')
                    
            elif module =='daymaxacts':
                if not paras is None:
                    self.daymaxacts = paras[0]
                print('Successfully active daymaxacts risk control')
            elif module =='secmaxacts':
                if not paras is None:
                    self.secmaxacts = paras[0]
                print('Successfully active secmaxacts risk control')
            elif module =='selftrade':
                if not paras is None:
                    self.maxselftrades = paras[0]
                print('Successfully active selftrade risk control')
            else:
                print('Invalid risk control module name.')
                return
            self.modules[module] = True
                    
                    
        except:
            traceback.print_exc()
                
        
    def make_order(self, context, num=1,instid=None, limitprice=None, direction=0):
        if self.modules['daymaxacts']:
            if self.dayacts + num > self.daymaxacts:
                return -3
            self.dayacts += num
        
        if self.modules['secmaxacts']:
            self.secacts = [ ct for ct in self.secacts if (context.curtime-ct).seconds < 1] 
            if len(self.secacts) + num > self.secmaxacts:
                return -4
            for i in range(num):
                self.secacts.append(context.curtime)
        
        if self.modules['selftrade'] and limitprice and instid and direction != 0:
            instPrices = self.callback()
            checkfield = 'longhigh' if direction < 0 else 'shortlow'
            if instid in instPrices and checkfield in instPrices[instid]:
                price = instPrices[instid][checkfield]
                if direction > 0 and limitprice > price:
                    self.dayselftrades += 1
                elif direction < 0 and limitprice < price:
                    self.dayselftrades += 1
            if self.dayselftrades > self.maxselftrades:
                return -5
        
        return 0
    
    def cancel_order(self, context, num=1):
        if self.modules['maxcancels']:
            if self.daycancles + num > self.maxcancels:
                return -2
            elif self.daycancles + num >= 0.85 * self.maxcancels:
                print('Warning: 撤单次数达到最大撤单次数的85%以上.')
                logger.info('Warning: 撤单次数达到最大撤单次数的85%以上.')    
            self.daycancles += num 
        
        if self.modules['daymaxacts']:
            if self.dayacts + num > self.daymaxacts:
                return -3
            self.dayacts += num
            
        if self.modules['secmaxacts']:
            self.secacts = [ ct for ct in self.secacts if (context.curtime-ct).seconds < 1] 
            if len(self.secacts) + num > self.secmaxacts:
                return -4
            for i in range(num):
                self.secacts.append(context.curtime)
        
        
        return 0
    
    def crossDay(self):
        self.dailyCount = 0
        self.dayacts = 0
        self.secacts = []
        self.dayselftrades = 0



















