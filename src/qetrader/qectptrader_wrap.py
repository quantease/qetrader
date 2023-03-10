#import pyctp.thosttraderapi as ctpapi
#from pyctp.thosttraderapi import *
import time
#import json
#import os
from datetime import datetime,timedelta
from .qetype import qetype
from .qeredisdb import saveProcessToDB,saveTradeDatarealToDB,saveOrderDatarealToDB
#from .qeaccount import self.account
from .qelogger import logger
#from .qeriskctl import ctpriskctl
#from multiprocessing import Queue
from .qectpmarket_wrap import checkMarketTime
from .qecontext import transInstID2Real,transInstID2Context,transExID2Context
import copy
from threading import Timer
from .qeglobal import  get_Instrument_volmult
from .qestatistics import g_stat
from .qeglobal import setPositionLoaded

from typing import Optional

from ctpwrapper.ApiStructure import (
    FensUserInfoField, UserSystemInfoField,
    ReqAuthenticateField, ReqGenUserCaptchaField,
    ReqGenUserTextField, ReqQueryAccountField,
    ReqTransferField, QueryCFMMCTradingAccountTokenField,
    QryBrokerTradingAlgosField, QryBrokerTradingParamsField,
    QryTradingNoticeField, UserLogoutField,
    QryParkedOrderActionField, QryParkedOrderField,
    QryContractBankField, QryAccountregisterField,
    QryTransferSerialField, QryCombActionField,
    QryCombInstrumentGuardField, QryInvestUnitField,
    QryOptionSelfCloseField, QryQuoteField,
    QryForQuoteField, QryExecOrderField,
    QryOptionInstrCommRateField, QryOptionInstrTradeCostField,
    QrySecAgentTradeInfoField, QrySecAgentCheckModeField,
    QryInstrumentOrderCommRateField, QryMMOptionInstrCommRateField,
    QryMMInstrumentCommissionRateField, QryProductGroupField,
    QryProductExchRateField, QrySecAgentACIDMapField,
    QryExchangeMarginRateAdjustField, ReqUserLoginField,
    InputOrderField, ParkedOrderField,
    ParkedOrderActionField, InputOrderActionField,
    QryMaxOrderVolumeField, SettlementInfoConfirmField,
    RemoveParkedOrderField, RemoveParkedOrderActionField,
    InputExecOrderField, InputExecOrderActionField,
    InputForQuoteField, InputQuoteField,
    InputQuoteActionField, InputBatchOrderActionField,
    InputOptionSelfCloseField, InputOptionSelfCloseActionField,
    InputCombActionField, ReqUserLoginWithCaptchaField,
    ReqUserLoginWithTextField, ReqUserLoginWithOTPField,
    UserPasswordUpdateField, TradingAccountPasswordUpdateField,
    QryOrderField, QryTradeField,
    QryInvestorPositionField, QryTradingAccountField,
    QryInvestorField, QryTradingCodeField,
    QryInstrumentCommissionRateField,
    QryExchangeField, QryProductField,
    QryInstrumentField, QryDepthMarketDataField,
    QrySettlementInfoField, QryTransferBankField,
    QryInvestorPositionDetailField, QryNoticeField,
    QrySettlementInfoConfirmField, QryInvestorPositionCombineDetailField,
    QryCFMMCTradingAccountKeyField, QryEWarrantOffsetField,
    QryInvestorProductGroupMarginField, QryExchangeMarginRateField,
    QryExchangeRateField, QryInstrumentMarginRateField,
    QryClassifiedInstrumentField, QryCombPromotionParamField,
    QryTraderOfferField, QryRiskSettleInvstPositionField,
    QryRiskSettleProductStatusField, QrySPBMFutureParameterField,
    QrySPBMInterParameterField, QrySPBMPortfDefinitionField,
    QrySPBMOptionParameterField, QrySPBMIntraParameterField,
    QrySPBMInvestorPortfDefField, QryInvestorPortfMarginRatioField,
    QryInvestorProdSPBMDetailField
)
from ctpwrapper.TraderApi import TraderApiWrapper
from .qectpconst_wrap import TThostEnumValues


api = TThostEnumValues()
str2bytes = lambda x: bytes(x,'utf-8')
BROKERID_CTP ="9999"
CTP_AppID="simnow_client_test"
CTP_AuthCode="0000000000000000"
FrontAddr="tcp://180.168.146.187:10101" 
g_mode_724 = False

# ??????????????????
priceTypeMap = {}
priceTypeMapReverse ={}

# ??????????????????
directionMap = {}
directionMapReverse = {}

# ?????????????????????
exchangeMap = {}
exchangeMap["CCF"] = "CFFEX"
exchangeMap["SFE"] = "SHFE"
exchangeMap["ZCE"] = "CZCE"
exchangeMap["DCE"] = "DCE"
exchangeMap["SSE"] = "SSE"
exchangeMap["INE"] = "INE"
exchangeMap["unknown"] = ""
exchangeMapReverse = {v:k for k,v in exchangeMap.items()}

# ??????????????????
offsetMap = {}
offsetMapReverse = {}
# ??????????????????
posiDirectionMap = {}
posiDirectionMapReverse={}

# ??????????????????
statusMap = {}
statusMapReverse = {}


#tstrats={}
#instSetts = {}
g_dataSlide = {}
feesmult = 1.0
#tradespi = None
#tqueue = None
g_USERID= "143523"         # "195456"
g_PASSWORD= "asd!1234567"           #   "123456_a"
Timer_interval = 1

def getPreviousTradingDay():
    now = datetime.now()
    if now.hour > 16:
        tday = now
    elif now.weekday()== 0:
        tday = now - timedelta(days=3)
    else:
        tday = now - timedelta(days=1)
    return tday.strftime("%Y%m%d")

def getLocalTradingDay():
    tday = datetime.now()
    if tday.hour > 18:
        days = 1 if tday.weekday() < 4 else 3
        tday += timedelta(days=days)
    elif tday.hour < 8 and tday.weekday()==5:
        tday += timedelta(days=2)
    return tday.strftime('%Y%m%d')



class qeCtpTrader(object):
    def __init__(self):
        self.tradespi = None
        
        self.user = 'unknown'
#         self.investor = g_USERID
#         self.password = g_PASSWORD
#         self.broker = BROKERID_CTP
#         self.appid = CTP_AppID
#         self.authcode = CTP_AuthCode
#         self.address = FrontAddr
        self.getAsk = False
        self.ordersload = False
        self.tradesload = False
        self.classname = ''
        self.accload = False
        self.posload = False
        self.tqueue = None
        self.strats = None
        self.lastts = 0 
        self.brokername = ''
        return
    def connect(self):
        return
    def callTimer(self):     
        global  Timer_interval
        timer = Timer(Timer_interval,self.callTimer)
        d = {}
        d['type'] = qetype.KEY_TIMER
#         logger.info('timer '+str(datetime.now()))
        if self.tqueue:
            self.tqueue.put(d)
            #self.heartBeat(True)
            #self.getStatistic()
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
         
    def TraderProcess(self):   
        #global tqueue
        logger.info(u"start Trader") 
        print("start Trader")
        if self.tqueue:
            logger.info('tqueue is ready')
            while True:
                try:
                    while not self.tqueue.empty():
#                         print('.')
                        d = self.tqueue.get(block = True, timeout = 1)
                        self.process(d)
                    time.sleep(0.001)
                except Exception as e:
                    logger.error(f"ctptrader tqueue error {e}",exc_info=True )            
        return
    def process(self,d):
        #print(d['type'],self.tradespi.frontConnected)
        if d['type'] == qetype.KEY_SEND_ORDER:
            self.sendOrder(d)
        elif d['type'] == qetype.KEY_CANCEL_ORDER:
            self.cancelOrder(d)
        elif d['type'] == qetype.KEY_MARKET_DATA:
            self.update(d)
        elif d['type'] == qetype.KEY_ON_ORDER:
            self.onOrder(d)
        elif d['type'] == qetype.KEY_ON_TRADE:
            self.onTrade(d)              
        elif d['type'] == qetype.KEY_ON_ORDER_ERROR:
            self.onOrderError(d)
#         elif d['type'] == KEY_ON_TRADE_ERROR:
#             self.onTradeError(d)
        elif d['type'] == qetype.KEY_ON_POSITION:
            self.onPosition(d)
        elif d['type'] == qetype.KEY_ON_ACCOUNT:
            self.onAccount(d)
        elif d['type'] == qetype.KEY_TIMER:
            self.getStatistic()
            #self.heartBeat(True)
#         elif d['type'] == KEY_ON_INSTRUMENT:
#             self.onInstrument(d)
#         elif d['type'] == KEY_ON_POSITION_DETAIL:
#             self.onPositionDetail(d)
        elif d['type'] == qetype.KEY_USER_LOGOUT:
            self.tradespi.logout()
        else:
            logger.error('incorrect type given as type is '+str(d['type']))
        return
    def callback(self,d):
        #global tstrats
        if d['stratName'].replace(' ','') != '':
            if self.strats:
                stratQueue = self.strats.get(d['stratName'],None)
                if stratQueue:
                    stratQueue['queue'].put(d)
                else:
                    logger.error('callback '+str(d['stratName'])+' is not found')
        
    def sendOrder(self,d):
        repeat = False
        tempinstid_ex,tempexID = transInstID2Real([d['instid']])
        instid_ex = tempinstid_ex[0]
        exID = tempexID[0]
        d['instid_ex'] = instid_ex
        d['exID'] = exID
        
        if d['action'] == 'close':
            
            if d['closetype'] == 'auto':
                
                if exID != 'SFE' and exID != 'INE':
                    d['closetype'] = "close"
                else:

                    tempinstid = self.account.position.get(d['instid'],'-1')
                    if tempinstid == '-1':
                        logger.error('No position to close at '+str(d['instid']))
                        return
                    else:
                        
                        if d['direction'] == 1:
                            direction1 = 'short'
                        else:
                            direction1 = 'long'
                        if self.account.position[d['instid']][direction1]['yesvol'] >= 1:
                            
                            if self.account.position[d['instid']][direction1]['yesvol'] >= d['volume']:
                                d['closetype'] = "closeyesterday"
                            else:
                                #d1 = copy.copy(d)
                                tempvolume = self.account.position[d['instid']][direction1]['yesvol']
                                volume1 = d['volume'] - tempvolume
                                d['closetype'] = "closeyesterday"
                                d['volume'] = tempvolume
                                #d1['closetype'] = "closetoday"                 
                                #d1['volume'] = volume1                     
                                #repeat = True                       
                        else:
                            d['closetype'] = "closetoday"
            elif d['closetype'] == 'all':
                if exID != 'SFE' and exID != 'INE':
                    d['closetype'] = "close"
                    tempvolume = self.account.position[d['instid']][direction1]['volume']
                else:

                    if d['direction'] == 1:
                        direction1 = 'short'
                    else:
                        direction1 = 'long'
                    if self.account.position[d['instid']][direction1]['yesvol'] >= 1:
                        if self.account.position[d['instid']][direction1]['yesvol'] >= d['volume']:
                            d['closetype'] = "closeyesterday"
                        else:
                            d1 = copy.copy(d)
                            tempvolume = self.account.position[d['instid']][direction1]['yesvol']
                            volume1 = d['volume'] - tempvolume
                            d['closetype'] = "closeyesterday"
                            d['volume'] = tempvolume
                            d1['closetype'] = "closetoday"                 
                            d1['volume'] = volume1                     
                            repeat = True                       
                    else:
                        d['closetype'] = "closetoday"
            elif exID != 'SFE' and exID != 'INE':
                    d['closetype'] = "close"
        #print('sendOrder',d['stratName'])    
        self.tradespi.sendOrder(d)
        if repeat:
            self.tradespi.sendOrder(d1)
        return
    def cancelOrder(self,d):
        self.tradespi.cancelOrder(d)
    def getStatistic(self):
        global g_mode_724, Timer_interval
        temptime = datetime.now()
        curts = temptime.timestamp()
        isMarketTime = checkMarketTime(temptime)
        isNoon = False #(temptime.hour == 11 and temptime.minute > 30) or (temptime.hour ==12)
        timeValid = g_mode_724 or (isMarketTime and not isNoon)
        
        if  self.account.stgtable_load and not self.tradespi.qryLock and self.tradespi.connectionStatus and timeValid :
            #if  not self.posload:
            #    self.tradespi.reqPosition()
                #self.posload = True
                
            if not self.ordersload:
                self.tradespi.reqOrder()
                self.ordersload = True
            
            elif not self.tradesload:
                self.tradespi.reqTrade()
                self.tradesload = True
            
            elif not self.accload or not self.posload or curts - self.lastts > 1 :
                self.lastts = curts
                if self.getAsk == True :
                    self.getAsk = False
                    self.tradespi.reqAccount()
                elif self.getAsk == False :
                    self.getAsk = True
                    self.tradespi.reqPosition()
        
        if self.accload and self.posload and self.tradesload and self.ordersload:
            Timer_interval = 2
        
        if self.tradespi.waitAuth and isMarketTime:
            self.tradespi.waitAuth = False
            self.tradespi.authenticate()
        return
    def onOrder(self,d): 
#         print('onOrder '+str(d['status_ctp']))
#         print(d['orderid'])
        order = self.account.orders.get(d['orderid'],None)
        if order:
            d['status'] = statusMap.get(d['status_ctp'],'unknown')
            d['direction'] = directionMap.get(d['direction_ctp'],'unknown')
            offset = offsetMap.get(d['offset_ctp'],'auto')
            d['action'] = 'open' if offset =='open' else 'close'
            d['closetype'] = 'auto' if offset =='open' else offset
            d['offset'] = offset
            d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
            #time = str(d['timedigit'])
            #d['time'] = time[:8]+' '+time[8:10]+':'+time[10:12]+':'+time[12:14]+"."+time[14:]
            d['time'] = d['orderTime']
            if d['from'] == 'RtnOrder':
                #d['errorid'] = order['errorid']
                #d['errormsg'] = order['errormsg']
                d['stratName'] = order['stratName']
                d['instid'] = order['instid']
                #d['incoming_orderid'] = order['incoming_orderid']
                #d['incoming_orderid'] = d['orderid']
            
           # if d['status'] == KEY_STATUS_CANCEL :
            #     print('pass '+str(d['volume'])+'-'+str(d['tradevol'])+'-'+str(d['leftvol']))
            #     d['cancelvol'] = d['volume'] - d['tradevol']
            #     d['leftvol'] = 0
            # elif d['status'] == KEY_STATUS_REJECT :
            #     d['cancelvol'] = d['volume']
            #     d['leftvol'] = 0
            # else:
            #     print('pass '+str(d['volume'])+'-'+str(d['tradevol'])+'-'+str(d['leftvol']))
            #     d['cancelvol'] = max(d['volume'] - d['tradevol'],0)
            
            if d['status'] in [qetype.KEY_STATUS_CANCEL, qetype.KEY_STATUS_PTPC , qetype.KEY_STATUS_REJECT]:
                order['cancelvol'] = d['volume'] - d['tradevol']
                order['leftvol'] = 0  
            elif d['status'] == qetype.KEY_STATUS_ALL_TRADED :
                order['cancelvol'] = 0
                order['leftvol'] = 0
            else:
                order['cancelvol'] = 0
                order['leftvol'] = d['volume'] - d['tradevol']
            d['cancelvol'] = order['cancelvol']
            d['leftvol'] = order['leftvol']  
            #if d['stratName'] == '':
            #    print('unresolved order', d['orderid'])
            d['accid'] = self.account.accid
            d['timecond'] = order['timecond']
            #d['sessionid'] = order['sessionid']
            #print('errormsg',d.keys())
            saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, d )
            self.account.orders[d['orderid']] = d
            if d['from'] == 'RtnOrder':
                self.callback(d)
#             self.account.saveToDB()
        else:
            logger.info('rspOrder orderid is not found '+str(d['orderid']))
        return
    def onTrade(self,d):
#         print('onTrade')
        #global instSetts
        order = self.account.orders.get(d['orderid'],None)
        if order or d['from'] != 'RtnTrade':
            offset = offsetMap.get(d['offset_ctp'],'auto')
            d['action'] = 'open' if offset =='open' else 'close'
            d['closetype'] = 'auto' if offset =='open' else offset
            d['offset'] = offset
            d['dir'] = directionMap.get(d['direction_ctp'],'unknown')
            #d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
            d['timedigit'] = int((d['tradedate']+d['tradetime'].replace(':','')).replace(' ',''))
            if order and d['from'] == 'RtnTrade':
                d['stratName'] = order['stratName']
                d['instid'] = order['instid']
                #d['orderid'] = order['incoming_orderid']
            
            trade = {}
            trade['instid'] = d['instid']
            trade['action'] = d['action']
            trade['dir'] = d['dir']
            trade['orderid'] = d['orderid']
            trade['tradevol'] = d['tradevol']
            trade['tradeprice'] = d['tradeprice']
            trade['stratName'] = d['stratName']
            trade['timedigit'] = d['timedigit']
            trade['closetype'] = d['closetype']
            trade['date'] = d['tradedate']
            trade['time'] = d['tradetime']
            
            tradeid = g_stat.getNewTradeID(int(str(d['timedigit'])[2:]+'00'))
            #while  tradeid in self.account.trades:
            #    tradeid += 1
            trade['tradeid'] = tradeid
            self.account.trades[tradeid] = trade
            #if d['stratName'] == '':
            #    print('unresolved trade', d['orderid'])
            trade['accid'] = self.account.accid
            saveTradeDatarealToDB(self.account.user, self.account.token, self.account.tradingDay, trade )
            if d['from'] == 'RtnTrade':
                self.callback(d)
                self.account.saveToDB()
                dirstr = 'long' if d['dir']>0 else 'short'
                self.account.updateWinLossParas(dirstr,  d['tradeprice'], d['tradevol'], d['closetype'], order['instid'])

            
#         else:
#             logger.info('rspTrade orderid is not found ')
        return
    def onOrderError(self,d):
        order = self.account.orders.get(d['orderid'],None)
        if order:
            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
            #d['incoming_orderid'] = order['incoming_orderid']      
            d['status'] = qetype.KEY_STATUS_REJECT
            d['direction'] = directionMap.get(d['direction_ctp'],'unknown')
            d['offset'] = offsetMap.get(d['offset_ctp'],'unknown')
            d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')   
            d['tradevol'] = 0    
            d['cancelvol'] = d['volume']
            d['leftvol'] = 0
            ## add keys            
            d['action'] = order['action']
            d['closetype'] = order['closetype']
            d['accid'] = self.account.accid
            d['timecond'] = order['timecond']
            d['time'] = datetime.now().strftime("%H:%M:%S")
            
            
            
            self.callback(d)
            order['errorid'] = d['errorid']
            order['errormsg'] = d['errormsg']
            order['status'] = qetype.KEY_STATUS_REJECT
            order['tradevol']  = 0
            order['cancelvol'] = d['volume']
            order['leftvol'] = 0  
            #print('error errormsg',order.keys(),d.keys())
            saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, d )
            self.account.orders[d['orderid']] = order
            
            
        else:
            logger.info('rspOrderErr orderid is not found '+str(d['orderid']))
        return
    def update(self,d):
        self.tradespi.dataSlide[d['instid']] = d['data']
        self.account.dataSlide[d['instid']] = copy.copy(d['data'])
        if self.account.tradingDay == '':
            self.account.loadFromDB(d['data']['tradingday'])
        
        
        if d['data']['tradingday'] != self.tradespi.curday:
            if self.tradespi.curday != '':
                self.crossday()
            self.tradespi.curday = d['data']['tradingday']
        self.account.current_timedigit = d['data']['timedigit']
        self.account.tradingDay = d['data']['tradingday']
        if self.tradespi.lasttime == 0:
            self.tradespi.lasttime = d['data']['timedigit']
        elif abs(d['data']['timedigit'] - self.tradespi.lasttime) > 2500:
            self.tradespi.lasttime = d['data']['timedigit']
            self.account.saveToDB()
        return
    def crossday(self):
        #self.tradespi.g_order_id = int(datetime.now().strftime('%H%M%S'))*100000
        #self.account.orders = {}
        self.tradespi.mapTable = {}     
        #self.tradespi.g_trade_id = int(datetime.now().strftime('%H%M%S'))*100000
        self.tradespi.reqID = 0
        self.account.crossday()
        #ctpriskctl.crossday()
        return
    def onAccount(self,d):
#         print('balance is '+str(d['balance']))
        self.account.balance = d['balance']
        self.account.avail = d['available'] 
        self.account.dayfees = d['commission'] 
        self.account.margin = d['margin'] 
        self.account.closeProf = d['closeProfit'] 
        self.account.posProf = d['positionProfit']
        self.account.frozenMarg = d['frozenMarg']
        self.account.daypnl = d['closeProfit'] #+ d['positionProfit']
        self.account.totalpnl = self.account.accupnl + self.account.daypnl
        self.account.totalfees = self.account.accufees + self.account.dayfees
        self.account.maxmarg = max(self.account.margin, self.account.maxmarg)
        
        if not self.accload:
            self.accload = True
            self.account.saveToDB()
            print('ctp??????????????????????????????',self.account.balance)
            self.account.setLoadReady()
        
        
    def onPosition(self,d):
#         instid_list = d['data'].keys()
#         for instid in instid_list:
#             temp_instid = 1
        self.account.position = copy.copy(d['data'])
        self.account.turnover += float(d['turnover'])
        if not self.posload:
            self.posload = True
            self.account.saveToDB()
            setPositionLoaded()
            print('ctp??????????????????????????????')
            logger.info('ctp??????????????????????????????')
            self.account.setLoadReady()
#         self.tradespi.position = self.account.position
#         print(self.account.position)
        return
def setGlobals():
    global priceTypeMap,priceTypeMapReverse,directionMap, directionMapReverse,offsetMap,offsetMapReverse,posiDirectionMap, posiDirectionMapReverse, statusMap,statusMapReverse
    priceTypeMap[api.THOST_FTDC_OPT_LimitPrice] = "limit"
    priceTypeMap[api.THOST_FTDC_OPT_AnyPrice] = "market"
    priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()} 
    directionMap[api.THOST_FTDC_D_Buy] = 1
    directionMap[api.THOST_FTDC_D_Sell] = -1
    directionMapReverse = {v: k for k, v in directionMap.items()}
    offsetMap[api.THOST_FTDC_OF_Open] = "open"
    offsetMap[api.THOST_FTDC_OF_Close] = "close"
    offsetMap[api.THOST_FTDC_OF_CloseToday] = "closetoday"
    offsetMap[api.THOST_FTDC_OF_CloseYesterday] = "closeyesterday"
    offsetMapReverse = {v:k for k,v in offsetMap.items()}
    posiDirectionMap[api.THOST_FTDC_PD_Net] = "net"
    posiDirectionMap[api.THOST_FTDC_PD_Long] = "long"
    posiDirectionMap[api.THOST_FTDC_PD_Short] = "short"
    posiDirectionMapReverse = {v:k for k,v in posiDirectionMap.items()}
    statusMap[api.THOST_FTDC_OST_AllTraded] = qetype.KEY_STATUS_ALL_TRADED                 #????????????, 0
    statusMap[api.THOST_FTDC_OST_PartTradedQueueing]  = qetype.KEY_STATUS_PART_TRADED      #???????????????????????????, 1
    statusMap[api.THOST_FTDC_OST_PartTradedNotQueueing] = qetype.KEY_STATUS_PTPC           #???????????????????????????, 2
    statusMap[api.THOST_FTDC_OST_NoTradeQueueing] = qetype.KEY_STATUS_PENDING              #????????????????????????, 3
    statusMap[api.THOST_FTDC_OST_NoTradeNotQueueing] = qetype.KEY_STATUS_REJECT                 #????????????????????????, 4
    statusMap[api.THOST_FTDC_OST_Canceled] = qetype.KEY_STATUS_CANCEL                       #??????, 5
    statusMap[api.THOST_FTDC_OST_Unknown] =qetype.KEY_STATUS_UNKNOWN                      #??????, a
    statusMap[api.THOST_FTDC_OST_NotTouched] = "not_touch"                          #????????????, b
    statusMap[api.THOST_FTDC_OST_Touched] = "touch"                                 #?????????, c
    statusMapReverse = {v:k for k,v in statusMap.items()}


class CTradeSpi(TraderApiWrapper):
    #tapi=''
    def Create(self, pszFlowPath: Optional[str] = "") -> None:
        super(CTradeSpi, self).Create(pszFlowPath.encode())

    def Release(self) -> None:
        super(CTradeSpi, self).Release()

    def Init(self) -> None:
        super(CTradeSpi, self).Init()
        time.sleep(1)  # wait for c++ init

    def Join(self) -> int:
        return super(CTradeSpi, self).Join()
    
    def GetTradingDay(self) -> str:
        """
        ?????????????????????
        :retrun ?????????????????????
        @remark ?????????????????????,??????????????????????????????
        """
        day = super(CTradeSpi, self).GetTradingDay()
        return day.decode()

    def __init__(self):
        #api.CThostFtdcTraderSpi.__init__(self)
        #self.tapi=tapi
        #self.g_orders = {}
        #self.g_trades = {}
        #self.g_order_id = int(datetime.now().strftime('%H%M%S'))*100000
        #self.g_trade_id = int(datetime.now().strftime('%H%M%S'))*100000
        self.investor = ""
        self.password = ""
        self.broker = ""
        self.appid = ""
        self.authcode = ""
#         self.investor = "195456"
#         self.password = "123456_a"
#         self.broker = "9999"
#         self.appid = "simnow_client_test"
#         self.authcode = "0000000000000000"
        self.reqID = 0
        #self.g_benchmark = self.g_order_id
        self.curday = '' 
        self.instVolume={}
        self.lasttime = 0
        self.posDict = {}
        self.turnover = 0
        self.dataSlide = {}
        self.frontID = 0
        self.sessionID = 0
        self.mapTable = {}   
        self.exchangeDict = {}
        self.accountPosition = {}
        self.connectionStatus = False
        self.waitAuth = False
        self.qryLock = False
        self.lastTDay = getPreviousTradingDay()
        logger.info('traderspi is ready')
    
    def SubscribePrivateTopic(self, nResumeType: int) -> None:
        """
        ??????????????????
        :param nResumeType: ?????????????????????
                THOST_TERT_RESTART:0,???????????????????????????
                THOST_TERT_RESUME:1,????????????????????????
                THOST_TERT_QUICK:2,????????????????????????????????????

        @remark ???????????????Init??????????????????????????????????????????????????????????????????
        """
        super(CTradeSpi, self).SubscribePrivateTopic(nResumeType)
    
    def SubscribePublicTopic(self, nResumeType: int) -> None:
        """
        ??????????????????
        :param nResumeType: ?????????????????????
                THOST_TERT_RESTART:0,???????????????????????????
                THOST_TERT_RESUME:1,????????????????????????
                THOST_TERT_QUICK:2????????????????????????????????????
        ???????????????Init??????????????????????????????????????????????????????????????????
        """
        super(CTradeSpi, self).SubscribePublicTopic(nResumeType)

    def RegisterFront(self, pszFrontAddress: str) -> None:
        """
        ???????????????????????????
        @param pszFrontAddress???????????????????????????
        @remark ??????????????????????????????protocol:
        ipaddress:port???????????????tcp:
        127.0.0.1:17001??????
        @remark ???tcp???????????????????????????127.0.0.1??????????????????????????????17001??????????????????????????????
        """
        super(CTradeSpi, self).RegisterFront(pszFrontAddress.encode())

    def ReqAuthenticate(self, pReqAuthenticate: "ReqAuthenticateField", nRequestID: int) -> int:
        """
        ?????????????????????
        """
        return super(CTradeSpi, self).ReqAuthenticate(pReqAuthenticate, nRequestID)

    def ReqUserLogin(self, pReqUserLogin: "ReqUserLoginField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqUserLogin(pReqUserLogin, nRequestID)

    def ReqUserLogout(self, pUserLogout: "UserLogoutField", nRequestID: int) -> int:
        """
        ????????????
        """
        return super(CTradeSpi, self).ReqUserLogout(pUserLogout, nRequestID)
    def ReqQryOrder(self, pQryOrder: "QryOrderField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryOrder(pQryOrder, nRequestID)

    def ReqQryTrade(self, pQryTrade: "QryTradeField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryTrade(pQryTrade, nRequestID)

    def ReqQryInstrumentCommissionRate(self, pQryInstrumentCommissionRate: "QryInstrumentCommissionRateField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryInstrumentCommissionRate(pQryInstrumentCommissionRate, nRequestID)

    def ReqOrderAction(self, pInputOrderAction: "InputOrderActionField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqOrderAction(pInputOrderAction, nRequestID)

    def ReqOrderInsert(self, pInputOrder: "InputOrderField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqOrderInsert(pInputOrder, nRequestID)

    def ReqQryTradingAccount(self, pQryTradingAccount: "QryTradingAccountField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryTradingAccount(pQryTradingAccount, nRequestID)

    def ReqQryInvestorPosition(self, pQryInvestorPosition: "QryInvestorPositionField", nRequestID: int) -> int:
        """
        ???????????????????????????
        """
        return super(CTradeSpi, self).ReqQryInvestorPosition(pQryInvestorPosition, nRequestID)

    def ReqSettlementInfoConfirm(self, pSettlementInfoConfirm: "SettlementInfoConfirmField", nRequestID: int) -> int:
        """
        ???????????????????????????
        """
        return super(CTradeSpi, self).ReqSettlementInfoConfirm(pSettlementInfoConfirm, nRequestID)

    def logout(self):
        logoutfield = UserLogoutField()
        logoutfield.BrokerID =self.broker
        logoutfield.UserID = self.investor
        self.ReqUserLogout(logoutfield, self.reqID)
    
    def reqTrade(self):
        logger.info("Query trades...")
        tradefield = QryTradeField()
        tradefield.BrokerID = self.broker
        tradefield.InvestorID = self.investor
        ret = self.ReqQryTrade(tradefield, self.reqID)
        if ret != 0:
            logger.warning('reqQryTrade error='+str(ret))
        else:
            self.qryLock = True
            
        
        
    def reqOrder(self):
        logger.info("Query orders...")
        orderfield = QryOrderField()
        orderfield.BrokerID = self.broker
        orderfield.InvestorID = self.investor
        ret = self.ReqQryOrder(orderfield, self.reqID)
        if ret != 0:
            logger.warning('reqQryOrder error='+str(ret))
        else:
            self.qryLock = True
         
    def reqInstrumentCommission(self, instid):
        logger.info("Query commission...")
        commfield = QryInstrumentCommissionRateField ()
        commfield.BrokerID = self.broker
        commfield.InvestorID = self.investor
        commfield.InstrumentID = instid
        ret = self.ReqQryInstrumentCommissionRate(commfield, self.reqID)
        if ret != 0:
            logger.warning('reqInstrumentCommission error='+str(ret))
        else:
            self.qryLock = True

    
    def authenticate(self):
        logger.info("Authenticating...")
        authfield = ReqAuthenticateField()
        authfield.BrokerID = self.broker
        authfield.UserID = self.investor
        authfield.AppID = self.appid
        authfield.AuthCode = self.authcode
        self.ReqAuthenticate(authfield,self.reqID)

    def sendOrder(self,order):
#         logger.info('trader sendorder')
        try:
            #self.account.g_order_id += 1
            #self.mapTable[self.account.g_order_id] = order['incoming_orderid']
            #self.mapTable[order['incoming_orderid']] = self.account.g_order_id
            #order['orderid'] = self.account.g_order_id
            orderid = order['orderid']
            self.account.orders[orderid] = order
            self.reqID += 1
            instid_ex = order['instid_ex']
            exID = order['exID']
#             tempinstid_ex,tempexID = transInstID2Real([order['instid']])
#             instid_ex = tempinstid_ex[0]
#             exID = tempexID[0]
#             self.exchangeDict[instid_ex] = exID
#             print(order['action'])
            if order['action'] == 'close':
                
                if order['closetype'] == 'close':
                    order_offset = "close"
                elif order['closetype'] == 'closetoday':
                    order_offset = "closetoday"
                elif order['closetype'] == 'closeyesterday':
                    order_offset = 'closeyesterday'
#                 else:
#                     order_offset = "close"
                    
            else:
                order_offset = 'open'
#             print(order['closetype'])
#             print('price '+str(type(order['price']))+' volume '+str(type(order['volume'])))
#             print('1'+str(exchangeMap.get(exID,''))+'2'+str(priceTypeMapReverse.get(order['ordertype'],'')))
#             print(str(offsetMapReverse.get(order_offset,''))+str(directionMapReverse.get(order['direction'],'')))
#             print(self.g_order_id)
            if order['ordertype'] == "market":
                tick = self.dataSlide[order['instid']]
                if order['direction'] == 1:
                    order_price = tick['upperlimit']
                else:
                    order_price = tick['lowerlimit']
            else:
                order_price = order['price']
            
            orderfield= InputOrderField(ContingentCondition = api.THOST_FTDC_CC_Immediately,TimeCondition = api.THOST_FTDC_TC_GFD,VolumeCondition = api.THOST_FTDC_VC_AV,OrderPriceType = api.THOST_FTDC_OPT_LimitPrice,Direction = api.THOST_FTDC_D_Buy,ForceCloseReason = api.THOST_FTDC_FCC_NotForceClose)
            orderfield.BrokerID=self.broker
            orderfield.InstrumentID = str2bytes(instid_ex)
            orderfield.UserID=self.investor
            orderfield.InvestorID=self.investor
            orderfield.LimitPrice = order_price
            orderfield.VolumeTotalOriginal = order['volume']
            #orderfield.ContingentCondition = str2bytes(api.THOST_FTDC_CC_Immediately)
            if order['timecond'] == 'FOK':
                orderfield.TimeCondition = str2bytes(api.THOST_FTDC_TC_IOC)
                orderfield.VolumeCondition = str2bytes(api.THOST_FTDC_VC_CV)
            elif order['timecond'] == 'FAK':
                orderfield.TimeCondition = str2bytes(api.THOST_FTDC_TC_IOC)
                orderfield.VolumeCondition = str2bytes(api.THOST_FTDC_VC_AV)
            else:
                orderfield.TimeCondition = str2bytes(api.THOST_FTDC_TC_GFD)
                orderfield.VolumeCondition = str2bytes(api.THOST_FTDC_VC_AV)
            orderfield.CombHedgeFlag = str2bytes(api.THOST_FTDC_HF_Speculation)
#             orderfield.GTDDate=""
            orderfield.OrderRef=str2bytes(str(orderid))
            orderfield.MinVolume = 1
            #orderfield.ForceCloseReason = str2bytes(api.THOST_FTDC_FCC_NotForceClose)
            orderfield.IsAutoSuspend = 0
            #orderfield.OrderPriceType = str2bytes(api.THOST_FTDC_OPT_LimitPrice)
            
#             orderfield.ExchangeID = "SHFE"
#             orderfield.Direction = api.THOST_FTDC_D_Buy
#             orderfield.CombOffsetFlag = api.THOST_FTDC_OF_Open   
            orderfield.ExchangeID = str2bytes(exchangeMap.get(exID,''))
            orderfield.Direction = str2bytes(directionMapReverse.get(order['direction'],''))
            orderfield.CombOffsetFlag = str2bytes(offsetMapReverse.get(order_offset,''))
            ret = self.ReqOrderInsert(orderfield,self.reqID)
            if ret != 0:
                logger.warning(f"ReqOrderInsert Failed:{ret}")
                self.account.orders[orderid]['errorid']= ret
            
        except Exception as e:
            print(e.__traceback__.tb_lineno,e)
            logger.error(e)      
        return
    def cancelOrder(self,d):
#         logger.info('trader cancelorder')
        try:
            order = self.account.orders.get(d['orderid'],None)
            if order:
                tempinstid_ex,tempexID = transInstID2Real([order['instid']])
                instid_ex = tempinstid_ex[0]
                exID = tempexID[0]
                
                self.reqID += 1
                orderfield=InputOrderActionField(ActionFlag = api.THOST_FTDC_AF_Delete, OrderRef=str(d['orderid']))
                orderfield.InstrumentID = str2bytes(instid_ex)
                # orderfield.MacAddress = '' 
                orderfield.ExchangeID = str2bytes(exID)
                #orderfield.ActionFlag = str2bytes(api.THOST_FTDC_AF_Delete)
                # orderfield.OrderActionRef = 0
                orderfield.UserID = self.investor
                # orderfield.LimitPrice = price
                
                orderfield.InvestorID = self.investor
                orderfield.SessionID = order.get('sessionid', self.sessionID)# 0
                # orderfield.VolumeChange = 0
                orderfield.BrokerID = self.broker
                # orderfield.RequestID = 0
                # orderfield.OrderSysID = ''
                orderfield.FrontID = order.get('frontid',self.frontID) # 0
                # orderfieldq.InvestUnitID = ''
                # orderfield.IPAddress = ''
                #print('ctp cancelorder', order['sessionid'], order['frontid'],d['orderid'])
                self.ReqOrderAction(orderfield,self.reqID)
            else:
                logger.error('cancel order is not found')
        except Exception as e:
            print(e.__traceback__.tb_lineno,e)
            logger.error(e)
        return
    def reqAccount(self):
        try:
            self.reqID += 1
            #logger.info("reqAccount")
            reqfield=QryTradingAccountField(BizType='1')
            reqfield.InvestorID = self.investor
            reqfield.BrokerID = self.broker
            # reqfield.InvestorID = 1
            # reqfield.BrokerID = 2
            # reqfield.AccountID = 3
            ret = self.ReqQryTradingAccount(reqfield,self.reqID)
            if ret != 0:
                logger.warning('reqQryTradingAccount error='+str(ret))
            else:
                self.qryLock = True
        except Exception as e:
            print( e.__traceback__.tb_lineno, e)
            logger.error(e)
        return
    def reqPosition(self):
        try:
            #logger.info("reqPosition")
            self.reqID += 1
            reqfield=QryInvestorPositionField()
            reqfield.InvestorID = self.investor
            reqfield.BrokerID = self.broker
            ret = self.ReqQryInvestorPosition(reqfield,self.reqID)
            if ret != 0:
                logger.warning('reqPosition error='+str(ret))
            else:
                self.qryLock = True
        except Exception as e:
            logger.error(e)
        return 
        
    def OnFrontConnected(self) -> None:
        print("??????????????????????????????")
        now = datetime.now()
        if checkMarketTime(now):
            self.authenticate()
        else:
            self.waitAuth = True
            print('waiting for trading time to request authentication')
        return
    def OnFrontDisconnected(self, nReason) -> None:
        self.connectionStatus = False
        self.waitAuth = False
        return
        
    def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast) -> None:
#         logger.info("OnRspAuthenticate")
        if pRspInfo.ErrorID == 0:
#             logger.info("BrokerID="+str(pRspAuthenticateField.BrokerID))
            logger.info("UserID="+str(pRspAuthenticateField.UserID))
            print("UserID="+str(pRspAuthenticateField.UserID))
#             logger.info("AppID="+str(pRspAuthenticateField.AppID))
#             logger.info("AppType="+str(pRspAuthenticateField.AppType))
            self.reqID +=1
            loginfield = ReqUserLoginField()
            loginfield.BrokerID=self.broker
            loginfield.UserID=self.investor
            loginfield.Password=self.password
            loginfield.UserProductInfo=str2bytes("python dll")
            self.ReqUserLogin(loginfield,self.reqID)
            print ("????????????")
        else:
            logger.error("Authenticate ErrorID="+str(pRspInfo.ErrorID))
            logger.error("Authenticate ErrorMsg="+str(pRspInfo.ErrorMsg))
        return
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast) -> None:
        # print("TradingDay=",pRspUserLogin.TradingDay)
        # print("SessionID=",pRspUserLogin.SessionID)   
        if pRspInfo.ErrorID == 0:
            logger.info("???????????????????????????")
            print("???????????????????????????")
            self.frontID = pRspUserLogin.FrontID
            self.sessionID = pRspUserLogin.SessionID
            #self.connectionStatus = True
            #self.reqID += 1
            #qryinfofield = api.CThostFtdcQrySettlementInfoField()
            #qryinfofield.BrokerID=self.broker
            #qryinfofield.InvestorID=self.investor
            #qryinfofield.TradingDay=self.lastTDay #pRspUserLogin.TradingDay
            #self.tapi.ReqQrySettlementInfo(qryinfofield,self.reqID)
            if self.brokername: #and self.brokername == 'simnow':
                self.reqID += 1
                pSettlementInfoConfirm=SettlementInfoConfirmField()
                pSettlementInfoConfirm.BrokerID=self.broker
                pSettlementInfoConfirm.InvestorID=self.investor
                self.ReqSettlementInfoConfirm(pSettlementInfoConfirm,self.reqID)
                #
#             print("send ReqQrySettlementInfo ok")
        else:
            logger.error(" UserLogin ErrorID="+str(pRspInfo.ErrorID))
            logger.error(" UserLogin ErrorMsg="+str(pRspInfo.ErrorMsg))
        return
    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast) -> None:
        self.connectionStatus = False
        logger.info("???????????????????????????")
        print("???????????????????????????")
        if pRspInfo.ErrorID != 0:
            logger.error("UserLogout ErrorID="+str(pRspInfo.ErrorID))
            logger.error("UserLogout ErrorMsg="+str(pRspInfo.ErrorMsg))
        return
        
    def OnRspQryOrder(self, pOrder, pRspInfo, nRequestID, bIsLast) -> None:
        #print("OnRspQryOrder")
        if nRequestID != self.reqID:
            return
        try:
            if pOrder and not int(pOrder.OrderRef) in self.account.orders:
                d = {}
                d['type'] = qetype.KEY_ON_ORDER
                instid = pOrder.InstrumentID
                exid = transExID2Context(pOrder.ExchangeID)
                d['instid'] = transInstID2Context(instid, exid)
                d['status_ctp'] = pOrder.OrderStatus
                d['submit_status'] = pOrder.OrderSubmitStatus
                d['orderid'] = int(pOrder.OrderRef)
                d['direction_ctp'] = pOrder.Direction
                d['volume'] = pOrder.VolumeTotalOriginal
                d['tradevol'] = pOrder.VolumeTraded
                #d['leftvol'] = pOrder.VolumeTotal
                d['offset_ctp'] = pOrder.CombOffsetFlag
                d['price'] = pOrder.LimitPrice
                d['orderTime'] = pOrder.InsertTime
                d['cancelTime'] = pOrder.CancelTime
                d['date'] = pOrder.InsertDate
                d['torderid'] = pOrder.OrderSysID
                d['frontid'] = pOrder.FrontID
                d['sessionid'] = pOrder.SessionID
                d['from'] = 'QryOrder'
                d['stratName'] = self.account.order_stg_table.get(str(d['orderid']),'')
                d['errorid'] = 0
                if d['status_ctp'] == api.THOST_FTDC_OST_Canceled and d['submit_status'] == api.THOST_FTDC_OSS_InsertRejected:
                    d['errormsg'] = pOrder.StatusMsg
                    d['errorid'] = -9
                else:
                    d['errormsg'] = ''
                    d['errorid'] = 0
                if pOrder.TimeCondition == api.THOST_FTDC_TC_IOC:
                    if pOrder.VolumeCondition == api.THOST_FTDC_VC_CV:
                        d['timecond'] = 'FOK'
                    else:
                        d['timecond'] = 'FAK'
                else:
                    d['timecond'] = 'GFD'

                self.account.orders[d['orderid']] = d
                #print("QryOrder:",d)
                self.tqueue.put(d)
            if bIsLast:
                print("ctp???????????????????????????")
                #self.reqTrade()
                self.qryLock = False
        except Exception as e:
            logger.error(f'OnRspQryOrder:{e}')      

        
    def OnRspQryTrade(self, pTrade, pRspInfo, nRequestID, bIsLast) -> None:
        #print("OnRspQryOrder")
        if nRequestID != self.reqID:
            return
        try:
            if pTrade and not int(pTrade.OrderRef) in self.account.orders:
                d = {}
                d['type'] = qetype.KEY_ON_TRADE
        #         d['instid'] = pTrade.InstrumentID
                instid = pTrade.InstrumentID
                exid = transExID2Context(pTrade.ExchangeID)
                d['instid'] = transInstID2Context(instid, exid)
                d['orderid'] = int(pTrade.OrderRef)
                d['direction_ctp'] = pTrade.Direction
                d['tradevol'] = pTrade.Volume
                d['offset_ctp'] = pTrade.OffsetFlag
                d['tradeprice'] = pTrade.Price
                d['tradeid'] = pTrade.TradeID
                d['sysid'] = pTrade.OrderSysID
                d['tradetime'] = pTrade.TradeTime
                d['tradedate'] = pTrade.TradeDate
                d['from'] = 'QryTrade'
                d['stratName'] = self.account.order_stg_table.get(str(d['orderid']),'')
                #print("RspTrade:",d)
                self.tqueue.put(d)
            if bIsLast:
                print("ctp?????????????????????")
                self.qryLock = False
        except Exception as e:
            logger.error(f'OnRspQryTrade:{e}')      
        
    def OnRspQryInstrumentCommissionRate(self, pInstrumentCommissionRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass
        
    def OnRspQrySettlementInfo(self, pSettlementInfo, pRspInfo, nRequestID, bIsLast) -> None:
        if bIsLast:
            print (f"OnRspQrySettlementInfo: {pSettlementInfo.SettlementID}")
             # if  pSettlementInfo is not None :
            #     print("content:",pSettlementInfo.Content)
            # else :
            #     print("content null")
            self.reqID += 1
            pSettlementInfoConfirm=api.CThostFtdcSettlementInfoConfirmField()
            pSettlementInfoConfirm.BrokerID=self.broker
            pSettlementInfoConfirm.InvestorID=self.investor
            pSettlementInfoConfirm.SettlementID = pSettlementInfo.SettlementID
            pSettlementInfoConfirm.AccountID = pSettlementInfo.AccountID
            pSettlementInfoConfirm.CurrencyID = pSettlementInfo.CurrencyID
            self.ReqSettlementInfoConfirm(pSettlementInfoConfirm,self.reqID)
#         print("send ReqSettlementInfoConfirm ok")
        return
    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast) -> None:
#         logger.info("OnRspSettlementInfoConfirm")
        #time.sleep(1)
        self.reqPosition()
        #self.connectionStatus = True

        if pRspInfo.ErrorID != 0:
            logger.error("ErrorID="+str(pRspInfo.ErrorID))
            logger.error("ErrorMsg="+str(pRspInfo.ErrorMsg))
        return
    def OnRtnOrder(self, pOrder) -> None:
        #global tqueue
#         logger.info("OnRtnOrder")
        # print ("OrderStatus=",pOrder.OrderStatus)
        # print ("StatusMsg=",pOrder.StatusMsg)
        # print ("LimitPrice=",pOrder.LimitPrice)
        d = {}
        d['type'] = qetype.KEY_ON_ORDER
#         d['instid'] = pOrder.InstrumentID
        d['status_ctp'] = pOrder.OrderStatus
        d['submit_status'] = pOrder.OrderSubmitStatus
        #d['ordertype'] = 'limit' if pOrder.OrderPriceType == '2' else 'market'
        d['orderid'] = int(pOrder.OrderRef)
        d['direction_ctp'] = pOrder.Direction
        d['volume'] = pOrder.VolumeTotalOriginal
        d['tradevol'] = pOrder.VolumeTraded
        #d['leftvol'] = pOrder.VolumeTotal
        d['offset_ctp'] = pOrder.CombOffsetFlag
        d['price'] = pOrder.LimitPrice
        d['orderTime'] = pOrder.InsertTime
        d['cancelTime'] = pOrder.CancelTime
        d['date'] = pOrder.InsertDate
        d['torderid'] = pOrder.OrderSysID
        d['frontid'] = pOrder.FrontID
        d['sessionid'] = pOrder.SessionID
        d['from'] = 'RtnOrder'
        
        if d['status_ctp'] == api.THOST_FTDC_OST_Canceled and d['submit_status'] == api.THOST_FTDC_OSS_InsertRejected:
            logger.warning(f'OnRtnOrder canceled by exchange: {pOrder.InstrumentID}, {pOrder.OrderRef}, {pOrder.StatusMsg}') 
            d['errormsg'] = pOrder.StatusMsg
            d['errorid'] = -9
        else:
            d['errormsg'] = ''
            d['errorid'] = 0
    
        #print('rtnOrder', d['frontid'], d['sessionid'],d['orderid'])
        self.tqueue.put(d)
        return
    def OnRspOrderInsert(self, pInputOrder, pRspInfo, nRequestID, bIsLast) -> None:
        if nRequestID != self.reqID:
            return
        #global tqueue
        logger.error("OnRspOrderInsert")
        print ("ErrorID=",pRspInfo.ErrorID)
        # print ("ErrorMsg=",pRspInfo.ErrorMsg)

        d = {}
        d['type'] = qetype.KEY_ON_ORDER_ERROR
#         d['instid'] = pInputOrder.InstrumentID
        d['orderid'] = int(pInputOrder.OrderRef)
        d['direction_ctp'] = pInputOrder.Direction
        d['volume'] = pInputOrder.VolumeTotalOriginal
        d['offset_ctp'] = pInputOrder.CombOffsetFlag
        d['price'] = pInputOrder.LimitPrice
        d['errorid'] = pRspInfo.ErrorID
        d['errormsg'] = pRspInfo.ErrorMsg
        
        ## add keys
        d['status_ctp'] = ''
        d['orderTime'] = ''
        d['cancelTime'] = ''
        d['date'] = ''
        d['torderid'] = ''
        d['from'] = 'OnRspOrderInsert'
        
        self.tqueue.put(d)
        if pRspInfo.ErrorID == 0:
            logger.info(f"OnRspOrderInsert orderref:{pInputOrder.OrderRef},instid:{pInputOrder.InstrumentID},dir:{pInputOrder.Direction}, vol:{pInputOrder.VolumeTotalOriginal}")
        else:
            logger.error(f"OnRspOrderInsert Error:{pRspInfo.ErrorID}, Msg:{pRspInfo.ErrorMsg}, orderref:{pInputOrder.OrderRef},instid:{pInputOrder.InstrumentID}, dir:{pInputOrder.Direction}, vol:{pInputOrder.VolumeTotalOriginal}")
        return
    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo) -> None:
        #global tqueue
        logger.error("OnErrRtnOrderInsert")
        d = {}
        d['type'] = qetype.KEY_ON_ORDER_ERROR
#         d['instid'] = pInputOrder.InstrumentID
        d['orderid'] = int(pInputOrder.OrderRef)
        d['direction_ctp'] = pInputOrder.Direction
        d['volume'] = pInputOrder.VolumeTotalOriginal
        d['offset_ctp'] = pInputOrder.CombOffsetFlag
        d['price'] = pInputOrder.LimitPrice
        d['errorid'] = pRspInfo.ErrorID
        d['errormsg'] = pRspInfo.ErrorMsg
        ## add keys
        d['status_ctp'] = ''
        d['orderTime'] = ''
        d['cancelTime'] = ''
        d['date'] = ''
        d['torderid'] = ''
        d['from'] = 'OnErrRtnOrderInsert'
        self.tqueue.put(d)
        if pRspInfo.ErrorID == 0:
            logger.info(f"OnErrRtnOrderInsert orderref:{pInputOrder.OrderRef},instid:{pInputOrder.InstrumentID},dir:{pInputOrder.Direction}, vol:{pInputOrder.VolumeTotalOriginal}")
        else:
            logger.error(f"OnErrRtnOrderInsert Error:{pRspInfo.ErrorID}, Msg:{pRspInfo.ErrorMsg}, orderref:{pInputOrder.OrderRef},instid:{pInputOrder.InstrumentID}, dir:{pInputOrder.Direction}, vol:{pInputOrder.VolumeTotalOriginal}")
        return
    def OnErrRtnOrderAction(self, pOrderAction, pRspInfo) -> None:
        # d = {}
        # d['type'] = KEY_ON_ORDER_ERROR     
        # d['instid'] = pOrderAction.InstrumentID
        # d['orderid'] = int(pOrderAction.OrderRef)
        # d['direction_ctp'] = pOrderAction.Direction
        # d['volume'] = pOrderAction.VolumeTotalOriginal
        # d['offset_ctp'] = pOrderAction.CombOffsetFlag
        # d['price'] = pOrderAction.LimitPrice
        # d['errorid'] = pRspInfo.ErrorID
        # d['erromsg'] = pRspInfo.ErrorMsg
        # self.tqueue.put(d)
#         print('CancelOrder failed ErrorID='+str(pRspInfo.ErrorID)+',ErrorMsg='+str(pRspInfo.ErrorMsg) )
        logger.error('CancelOrder failed ErrorID='+str(pRspInfo.ErrorID)+',ErrorMsg='+str(pRspInfo.ErrorMsg) )
        return
    def OnRtnTrade(self, pTrade) -> None:
        #global tqueue
#         logger.info("OnRtnTrade")
        d = {}
        d['type'] = qetype.KEY_ON_TRADE
#         d['instid'] = pTrade.InstrumentID
        exchange = exchangeMapReverse.get(pTrade.ExchangeID,"")
        d['instid'] = transInstID2Context(pTrade.InstrumentID,exchange)
        #d['stratName'] = ''
        d['orderid'] = int(pTrade.OrderRef)
        d['direction_ctp'] = pTrade.Direction
        d['tradevol'] = pTrade.Volume
        d['offset_ctp'] = pTrade.OffsetFlag
        d['tradeprice'] = pTrade.Price
        d['tradeid'] = pTrade.TradeID
        d['sysid'] = pTrade.OrderSysID
        d['tradetime'] = pTrade.TradeTime
        d['tradedate'] = pTrade.TradeDate
        d['from'] = 'RtnTrade'
        self.tqueue.put(d)
        return

    # ??????????????????????????????
   
    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast) -> None:
        if nRequestID != self.reqID:
            return
        #global tqueue
        #print("account",pTradingAccount)
#         print('account')
        try:
            d = {}
            d['type'] = qetype.KEY_ON_ACCOUNT
            # d.accountID = pTradingAccount.AccountID
            # account.preBalance = pTradingAccount.PreBalance
            d['available'] = pTradingAccount.Available
            d['commission'] = pTradingAccount.Commission
            d['margin'] = pTradingAccount.CurrMargin
            d['closeProfit'] = pTradingAccount.CloseProfit
            d['positionProfit'] = pTradingAccount.PositionProfit
            d['frozenMarg'] = pTradingAccount.FrozenMargin
            d['balance'] = pTradingAccount.Balance
            d['deposit'] = pTradingAccount.Deposit
            d['withdraw'] = pTradingAccount.Withdraw
            
            if bIsLast:
                self.tqueue.put(d)
                if not self.connectionStatus:
                    self.connectionStatus = True
                    time.sleep(1)
                self.qryLock = False
                
        except Exception as e:
            logger.error(e)
        return
    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast) -> None:
        if nRequestID != self.reqID:
            return
        #global tqueue
        #print('position', pInvestorPosition)
        try:
            if pInvestorPosition is not None and pInvestorPosition.InvestorID==self.investor.decode('utf-8') and  pInvestorPosition.PositionCost != 0:
#                 print('exchange at '+str(pInvestorPosition.ExchangeID))
#                 tempinstid = pInvestorPosition.InstrumentID
#                 tempex = pInvestorPosition.ExchangeID
                exchange = exchangeMapReverse.get(pInvestorPosition.ExchangeID,"")
                instid = transInstID2Context(pInvestorPosition.InstrumentID,exchange)
#                 print(instid)
#                 instid = str(pInvestorPosition.InstrumentID)+'.'+str(tempex1)
                if instid in self.posDict:
                    pos = self.posDict[instid]
                else:
                    pos = {'long': {'volume': 0, 'poscost': 0, 'yesvol': 0},'short': {'volume': 0, 'poscost': 0, 'yesvol': 0}}
                    self.posDict[instid] = pos
                direction = posiDirectionMap.get(pInvestorPosition.PosiDirection, 'net')
                if direction != 'net':
                    cost = 0
                    self.turnover += pInvestorPosition.OpenAmount + pInvestorPosition.CloseAmount
                # ??????????????????????????????????????????????????????????????????????????????????????????
                    volmult = get_Instrument_volmult(instid)
                    #volmult = tempdict.get('volmult',1)
#                     exchange = tempex1
                    if pInvestorPosition.PositionDate == '2' and (exchange == 'SFE' or exchange == 'INE' ):
                        pos[str(direction)]['yesvol'] = pInvestorPosition.Position
                    elif exchange != 'SFE' and exchange != 'INE':
                        pos[str(direction)]['yesvol'] = pInvestorPosition.Position - pInvestorPosition.TodayPosition
                    cost = pos[str(direction)]['poscost'] * pos[str(direction)]['volume'] *volmult
                    pos[str(direction)]['volume'] += pInvestorPosition.Position
                    # positionProfit += pInvestorPosition.PositionProfit
                    if pos[str(direction)]['volume'] >= 1 :
                        cost += pInvestorPosition.PositionCost
                        pos[str(direction)]['poscost'] = cost / (pos[str(direction)]['volume']*volmult)
#                         pos[str(direction)]['poscost'] = (cost + pInvestorPosition.PositionCost) / (pos[str(direction)]['volume']*volmult)
                    # ????????????
                    # if direction is "long": 
                    #     frozen += pInvestorPosition.LongFrozen
                    # else:
                    #     frozen += pInvestorPosition.ShortFrozen     
                    # ??????????????????
            if bIsLast:
                d = {}
                d['type'] = qetype.KEY_ON_POSITION
                d['data'] = copy.copy(self.posDict)
                d['turnover'] = self.turnover
#                 print(self.posDict.keys())
                self.posDict.clear()
                self.qryLock = False
                self.turnover = 0
                if not self.connectionStatus:
                    time.sleep(1)
                    self.reqAccount()
                #self.connectionStatus = True
                self.tqueue.put(d)
        except Exception as e:
            logger.error(e)
        return
    def OnRspQryInvestorPositionDetail(self,pInvestorPositionDetail, RspInfo, nRequestID, bIsLast)  -> None:
        pass
    def OnRspQryInstrument(self,pInstrument,  RspInfo, nRequestID, bIsLast)  -> None:
        pass
    def OnRspError(self,pRspInfo, nRequestID, bIsLast)  -> None:
        logger.error("ErrorID="+str(pRspInfo.ErrorID))
        logger.error("ErrorMsg="+str(pRspInfo.ErrorMsg))
        return
    def RegisterNameServer(self, pszNsAddress: str) -> None:
        """
        ?????????????????????????????????
        :param pszNsAddress?????????????????????????????????
        @remark ??????????????????????????????protocol:
        ipaddress:port???????????????tcp:
        127.0.0.1:12001??????
        @remark ???tcp???????????????????????????127.0.0.1??????????????????????????????12001??????????????????????????????
        @remark RegisterNameServer?????????RegisterFront
        """
        super(CTradeSpi, self).RegisterNameServer(pszNsAddress.encode())

    def RegisterFensUserInfo(self, pFensUserInfo: "FensUserInfoField") -> None:
        """
        ?????????????????????????????????
        :param pFensUserInfo??????????????????
        """
        super(CTradeSpi, self).RegisterFensUserInfo(pFensUserInfo)


    def RegisterUserSystemInfo(self, pUserSystemInfo: "UserSystemInfoField") -> None:
        """
        ???????????????????????????????????????????????????????????????
        ???????????????????????????????????????????????????????????????
        """
        super(CTradeSpi, self).RegisterUserSystemInfo(pUserSystemInfo)

    def SubmitUserSystemInfo(self, pUserSystemInfo: "UserSystemInfoField") -> None:
        """
        ?????????????????????????????????????????????????????????????????????
        ??????????????????????????????????????????????????????????????????
        """
        super(CTradeSpi, self).SubmitUserSystemInfo(pUserSystemInfo)

    def ReqUserAuthMethod(self, pReqUserAuthMethod: "ReqUserAuthMethod", nRequestID: int) -> int:
        """
        ???????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqUserAuthMethod(pReqUserAuthMethod, nRequestID)

    def ReqGenUserCaptcha(self, pReqGenUserCaptcha: "ReqGenUserCaptchaField", nRequestID: int) -> int:
        """
        ???????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqGenUserCaptcha(pReqGenUserCaptcha, nRequestID)

    def ReqGenUserText(self, pReqGenUserText: "ReqGenUserTextField", nRequestID: int) -> int:
        """
        ???????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqGenUserText(pReqGenUserText, nRequestID)

    def ReqUserLoginWithCaptcha(self, pReqUserLoginWithCaptcha: "ReqUserLoginWithCaptchaField", nRequestID: int) -> int:
        """
        ????????????????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqUserLoginWithCaptcha(pReqUserLoginWithCaptcha, nRequestID)

    def ReqUserLoginWithText(self, pReqUserLoginWithText: "ReqUserLoginWithTextField", nRequestID: int) -> int:
        """
        ????????????????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqUserLoginWithText(pReqUserLoginWithText, nRequestID)

    def ReqUserLoginWithOTP(self, pReqUserLoginWithOTP: "ReqUserLoginWithOTPField", nRequestID: int) -> int:
        """
        ?????????????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqUserLoginWithOTP(pReqUserLoginWithOTP, nRequestID)


    def ReqUserPasswordUpdate(self, pUserPasswordUpdate: "UserPasswordUpdateField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqUserPasswordUpdate(pUserPasswordUpdate, nRequestID)

    def ReqTradingAccountPasswordUpdate(self, pTradingAccountPasswordUpdate: "TradingAccountPasswordUpdateField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqTradingAccountPasswordUpdate(pTradingAccountPasswordUpdate, nRequestID)


    def ReqParkedOrderInsert(self, pParkedOrder: "ParkedOrderField", nRequestID: int) -> int:
        """
        ?????????????????????
        """
        return super(CTradeSpi, self).ReqParkedOrderInsert(pParkedOrder, nRequestID)

    def ReqParkedOrderAction(self, pParkedOrderAction: "ParkedOrderActionField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqParkedOrderAction(pParkedOrderAction, nRequestID)


    def ReqQryMaxOrderVolume(self, pQryMaxOrderVolume: "QryMaxOrderVolumeField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryMaxOrderVolume(pQryMaxOrderVolume, nRequestID)


    def ReqRemoveParkedOrder(self, pRemoveParkedOrder: "RemoveParkedOrderField", nRequestID: int) -> int:
        """
        ?????????????????????
        """
        return super(CTradeSpi, self).ReqRemoveParkedOrder(pRemoveParkedOrder, nRequestID)

    def ReqRemoveParkedOrderAction(self, pRemoveParkedOrderAction: "RemoveParkedOrderActionField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqRemoveParkedOrderAction(pRemoveParkedOrderAction, nRequestID)

    def ReqExecOrderInsert(self, pInputExecOrder: "InputExecOrderField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqExecOrderInsert(pInputExecOrder, nRequestID)

    def ReqExecOrderAction(self, pInputExecOrderAction: "InputExecOrderActionField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqExecOrderAction(pInputExecOrderAction, nRequestID)

    def ReqForQuoteInsert(self, pInputForQuote: "InputForQuoteField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqForQuoteInsert(pInputForQuote, nRequestID)

    def ReqQuoteInsert(self, pInputQuote: "InputQuoteField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQuoteInsert(pInputQuote, nRequestID)

    def ReqQuoteAction(self, pInputQuoteAction: "InputQuoteActionField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQuoteAction(pInputQuoteAction, nRequestID)

    def ReqBatchOrderAction(self, pInputBatchOrderAction: "InputBatchOrderActionField", nRequestID: int) -> int:
        """
        ????????????????????????
        :param pInputBatchOrderAction:
        :param nRequestID:
        :return:
        """
        return super(CTradeSpi, self).ReqBatchOrderAction(pInputBatchOrderAction, nRequestID)

    def ReqOptionSelfCloseInsert(self, pInputOptionSelfClose: "InputOptionSelfCloseField", nRequestID: int) -> int:
        """
        ???????????????????????????
        """
        return super(CTradeSpi, self).ReqOptionSelfCloseInsert(pInputOptionSelfClose, nRequestID)

    def ReqOptionSelfCloseAction(self, pInputOptionSelfCloseAction: "InputOptionSelfCloseActionField", nRequestID: int) -> int:
        """
        ???????????????????????????
        """
        return super(CTradeSpi, self).ReqOptionSelfCloseAction(pInputOptionSelfCloseAction, nRequestID)

    def ReqCombActionInsert(self, pInputCombAction: "InputCombActionField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqCombActionInsert(pInputCombAction, nRequestID)



    def ReqQryInvestor(self, pQryInvestor: "QryInvestorField", nRequestID: int) -> int:
        """
        ?????????????????????
        """
        return super(CTradeSpi, self).ReqQryInvestor(pQryInvestor, nRequestID)

    def ReqQryTradingCode(self, pQryTradingCode: "QryTradingCodeField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryTradingCode(pQryTradingCode, nRequestID)

    def ReqQryInstrumentMarginRate(self, pQryInstrumentMarginRate: "QryInstrumentMarginRateField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryInstrumentMarginRate(pQryInstrumentMarginRate, nRequestID)


    def ReqQryExchange(self, pQryExchange: "QryExchangeField", nRequestID: int) -> int:
        """
        ?????????????????????
        """
        return super(CTradeSpi, self).ReqQryExchange(pQryExchange, nRequestID)

    def ReqQryProduct(self, pQryProduct: "QryProductField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryProduct(pQryProduct, nRequestID)

    def ReqQryInstrument(self, pQryInstrument: "QryInstrumentField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryInstrument(pQryInstrument, nRequestID)

    def ReqQryDepthMarketData(self, pQryDepthMarketData: "QryDepthMarketDataField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryDepthMarketData(pQryDepthMarketData, nRequestID)

    def ReqQryTraderOffer(self, pQryTraderOffer: "QryTraderOfferField", nRequestID) -> int:
        return super(CTradeSpi, self).ReqQryTraderOffer(pQryTraderOffer, nRequestID)

    def ReqQrySettlementInfo(self, pQrySettlementInfo: "QrySettlementInfoField", nRequestID: int) -> int:
        """
        ?????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQrySettlementInfo(pQrySettlementInfo, nRequestID)

    def ReqQryTransferBank(self, pQryTransferBank: "QryTransferBankField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryTransferBank(pQryTransferBank, nRequestID)

    def ReqQryInvestorPositionDetail(self, pQryInvestorPositionDetail: "QryInvestorPositionDetailField", nRequestID: int) -> int:
        """
        ?????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryInvestorPositionDetail(pQryInvestorPositionDetail, nRequestID)

    def ReqQryNotice(self, pQryNotice: "QryNoticeField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryNotice(pQryNotice, nRequestID)

    def ReqQrySettlementInfoConfirm(self, pQrySettlementInfoConfirm: "QrySettlementInfoConfirmField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQrySettlementInfoConfirm(pQrySettlementInfoConfirm, nRequestID)

    def ReqQryInvestorPositionCombineDetail(self, pQryInvestorPositionCombineDetail: "QryInvestorPositionCombineDetailField", nRequestID: int) -> int:
        """
        ?????????????????????????????????"""
        return super(CTradeSpi, self).ReqQryInvestorPositionCombineDetail(pQryInvestorPositionCombineDetail,
                                                                            nRequestID)

    def ReqQryCFMMCTradingAccountKey(self, pQryCFMMCTradingAccountKey: "QryCFMMCTradingAccountKeyField", nRequestID: int) -> int:
        """
        ???????????????????????????????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryCFMMCTradingAccountKey(pQryCFMMCTradingAccountKey, nRequestID)

    def ReqQryEWarrantOffset(self, pQryEWarrantOffset: "QryEWarrantOffsetField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryEWarrantOffset(pQryEWarrantOffset, nRequestID)

    def ReqQryInvestorProductGroupMargin(self, pQryInvestorProductGroupMargin: "QryInvestorProductGroupMarginField", nRequestID: int) -> int:
        """
        ???????????????????????????/??????????????????
        """
        return super(CTradeSpi, self).ReqQryInvestorProductGroupMargin(pQryInvestorProductGroupMargin, nRequestID)

    def ReqQryExchangeMarginRate(self, pQryExchangeMarginRate: "QryExchangeMarginRateField", nRequestID: int) -> int:
        """
        ?????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryExchangeMarginRate(pQryExchangeMarginRate, nRequestID)

    def ReqQryExchangeMarginRateAdjust(self, pQryExchangeMarginRateAdjust: "QryExchangeMarginRateAdjustField", nRequestID: int) -> int:
        """
        ???????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryExchangeMarginRateAdjust(pQryExchangeMarginRateAdjust, nRequestID)

    def ReqQryExchangeRate(self, pQryExchangeRate: "QryExchangeRateField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryExchangeRate(pQryExchangeRate, nRequestID)

    def ReqQrySecAgentACIDMap(self, pQrySecAgentACIDMap: "QrySecAgentACIDMapField", nRequestID: int) -> int:
        """
        ?????????????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQrySecAgentACIDMap(pQrySecAgentACIDMap, nRequestID)

    def ReqQryProductExchRate(self, pQryProductExchRate: "QryProductExchRateField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryProductExchRate(pQryProductExchRate, nRequestID)

    def ReqQryProductGroup(self, pQryProductGroup: "QryProductGroupField", nRequestID: int) -> int:
        """
        ?????????????????????
        """
        return super(CTradeSpi, self).ReqQryProductGroup(pQryProductGroup, nRequestID)

    def ReqQryMMInstrumentCommissionRate(self, pQryMMInstrumentCommissionRate: "QryMMInstrumentCommissionRateField", nRequestID: int) -> int:
        """
        ???????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryMMInstrumentCommissionRate(pQryMMInstrumentCommissionRate, nRequestID)

    def ReqQryMMOptionInstrCommRate(self, pQryMMOptionInstrCommRate: "QryMMOptionInstrCommRateField", nRequestID: int) -> int:
        """
        ??????????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryMMOptionInstrCommRate(pQryMMOptionInstrCommRate, nRequestID)

    def ReqQryInstrumentOrderCommRate(self, pQryInstrumentOrderCommRate: "QryInstrumentOrderCommRateField", nRequestID: int) -> int:
        """
        ???????????????????????????
        """
        return super(CTradeSpi, self).ReqQryInstrumentOrderCommRate(pQryInstrumentOrderCommRate, nRequestID)

    def ReqQrySecAgentTradingAccount(self, pQryTradingAccount: "QryTradingAccountField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQrySecAgentTradingAccount(pQryTradingAccount, nRequestID)

    def ReqQrySecAgentCheckMode(self, pQrySecAgentCheckMode: "QrySecAgentCheckModeField", nRequestID: int) -> int:
        """
        ?????????????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQrySecAgentCheckMode(pQrySecAgentCheckMode, nRequestID)

    def ReqQryOptionInstrTradeCost(self, pQryOptionInstrTradeCost: "QryOptionInstrTradeCostField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryOptionInstrTradeCost(pQryOptionInstrTradeCost, nRequestID)

    def ReqQryOptionInstrCommRate(self, pQryOptionInstrCommRate: "QryOptionInstrCommRateField", nRequestID: int) -> int:
        """
        ?????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryOptionInstrCommRate(pQryOptionInstrCommRate, nRequestID)

    def ReqQryExecOrder(self, pQryExecOrder: "QryExecOrderField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryExecOrder(pQryExecOrder, nRequestID)

    def ReqQryForQuote(self, pQryForQuote: "QryForQuoteField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryForQuote(pQryForQuote, nRequestID)

    def ReqQryQuote(self, pQryQuote: "QryQuoteField", nRequestID: int) -> int:
        """
        ??????????????????
        """
        return super(CTradeSpi, self).ReqQryQuote(pQryQuote, nRequestID)

    def ReqQryOptionSelfClose(self, pQryOptionSelfClose: "QryOptionSelfCloseField", nRequestID: int) -> int:
        """
        ???????????????????????????
        """
        return super(CTradeSpi, self).ReqQryOptionSelfClose(pQryOptionSelfClose, nRequestID)

    def ReqQryInvestUnit(self, pQryInvestUnit: "QryInvestUnitField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryInvestUnit(pQryInvestUnit, nRequestID)

    def ReqQryCombInstrumentGuard(self, pQryCombInstrumentGuard: "QryCombInstrumentGuardField", nRequestID: int) -> int:
        """
        ????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryCombInstrumentGuard(pQryCombInstrumentGuard, nRequestID)

    def ReqQryCombAction(self, pQryCombAction: "QryCombActionField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryCombAction(pQryCombAction, nRequestID)

    def ReqQryTransferSerial(self, pQryTransferSerial: "QryTransferSerialField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryTransferSerial(pQryTransferSerial, nRequestID)

    def ReqQryAccountregister(self, pQryAccountregister: "QryAccountregisterField", nRequestID: int) -> int:
        """
        ??????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryAccountregister(pQryAccountregister, nRequestID)

    def ReqQryContractBank(self, pQryContractBank: "QryContractBankField", nRequestID: int) -> int:
        """
        ????????????????????????"""
        return super(CTradeSpi, self).ReqQryContractBank(pQryContractBank, nRequestID)

    def ReqQryParkedOrder(self, pQryParkedOrder: "QryParkedOrderField", nRequestID: int) -> int:
        """
        ?????????????????????
        """
        return super(CTradeSpi, self).ReqQryParkedOrder(pQryParkedOrder, nRequestID)

    def ReqQryParkedOrderAction(self, pQryParkedOrderAction: "QryParkedOrderActionField", nRequestID: int) -> int:
        """
        ????????????????????????"""
        return super(CTradeSpi, self).ReqQryParkedOrderAction(pQryParkedOrderAction, nRequestID)

    def ReqQryTradingNotice(self, pQryTradingNotice: "QryTradingNoticeField", nRequestID: int) -> int:
        """
        ????????????????????????"""
        return super(CTradeSpi, self).ReqQryTradingNotice(pQryTradingNotice, nRequestID)

    def ReqQryBrokerTradingParams(self, pQryBrokerTradingParams: "QryBrokerTradingParamsField", nRequestID: int) -> int:
        """
        ????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryBrokerTradingParams(pQryBrokerTradingParams, nRequestID)

    def ReqQryBrokerTradingAlgos(self, pQryBrokerTradingAlgos: "QryBrokerTradingAlgosField", nRequestID: int) -> int:
        """
        ????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryBrokerTradingAlgos(pQryBrokerTradingAlgos, nRequestID)

    def ReqQueryCFMMCTradingAccountToken(self, pQueryCFMMCTradingAccountToken: "QueryCFMMCTradingAccountTokenField", nRequestID: int) -> int:
        """
        ????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQueryCFMMCTradingAccountToken(pQueryCFMMCTradingAccountToken, nRequestID)

    def ReqFromBankToFutureByFuture(self, pReqTransfer: "ReqTransferField", nRequestID: int) -> int:
        """
        ???????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqFromBankToFutureByFuture(pReqTransfer, nRequestID)

    def ReqFromFutureToBankByFuture(self, pReqTransfer: "ReqTransferField", nRequestID: int) -> int:
        """
        ???????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqFromFutureToBankByFuture(pReqTransfer, nRequestID)

    def ReqQueryBankAccountMoneyByFuture(self, pReqQueryAccount: "ReqQueryAccountField", nRequestID: int) -> int:
        """
        ????????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQueryBankAccountMoneyByFuture(pReqQueryAccount, nRequestID)

    def ReqQrySecAgentTradeInfo(self, pQrySecAgentTradeInfo: "QrySecAgentTradeInfoField", nRequestID: int) -> int:
        """
        ?????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQrySecAgentTradeInfo(pQrySecAgentTradeInfo, nRequestID)

    def ReqQryClassifiedInstrument(self, pQryClassifiedInstrument: "QryClassifiedInstrumentField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryClassifiedInstrument(pQryClassifiedInstrument, nRequestID)

    def ReqQryCombPromotionParam(self, pQryCombPromotionParam: "QryCombPromotionParamField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryCombPromotionParam(pQryCombPromotionParam, nRequestID)

    def ReqQryRiskSettleInvstPosition(self, pQryRiskSettleInvstPosition: "QryRiskSettleInvstPositionField", nRequestID: int) -> int:
        """
        ?????????????????????????????????
        """
        return super(CTradeSpi, self).ReqQryRiskSettleInvstPosition(pQryRiskSettleInvstPosition, nRequestID)

    def ReqQryRiskSettleProductStatus(self, pQryRiskSettleProductStatus: "QryRiskSettleProductStatusField", nRequestID: int) -> int:
        """
        ????????????????????????
        """
        return super(CTradeSpi, self).ReqQryRiskSettleProductStatus(pQryRiskSettleProductStatus, nRequestID)

    # SPBM????????????????????????
    def ReqQrySPBMFutureParameter(self, pQrySPBMFutureParameter: "QrySPBMFutureParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMFutureParameter(pQrySPBMFutureParameter, nRequestID)

    # SPBM????????????????????????
    def ReqQrySPBMOptionParameter(self, pQrySPBMOptionParameter: "QrySPBMOptionParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMOptionParameter(pQrySPBMOptionParameter, nRequestID)

    # SPBM????????????????????????????????????
    def ReqQrySPBMIntraParameter(self, pQrySPBMIntraParameter: "QrySPBMIntraParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMIntraParameter(pQrySPBMIntraParameter, nRequestID)

    # SPBM???????????????????????????
    def ReqQrySPBMInterParameter(self, pQrySPBMInterParameter: "QrySPBMInterParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMInterParameter(pQrySPBMInterParameter, nRequestID)

    # SPBM???????????????????????????
    def ReqQrySPBMPortfDefinition(self, pQrySPBMPortfDefinition: "QrySPBMPortfDefinitionField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMPortfDefinition(pQrySPBMPortfDefinition, nRequestID)

    # ?????????SPBM??????????????????
    def ReqQrySPBMInvestorPortfDef(self, pQrySPBMInvestorPortfDef: "QrySPBMInvestorPortfDefField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMInvestorPortfDef(pQrySPBMInvestorPortfDef, nRequestID)

    # ??????????????????????????????????????????
    def ReqQryInvestorPortfMarginRatio(self, pQryInvestorPortfMarginRatio: "QryInvestorPortfMarginRatioField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQryInvestorPortfMarginRatio(pQryInvestorPortfMarginRatio, nRequestID)

    # ???????????????SPBM????????????
    def ReqQryInvestorProdSPBMDetail(self, pQryInvestorProdSPBMDetail: "QryInvestorProdSPBMDetailField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQryInvestorProdSPBMDetail(pQryInvestorProdSPBMDetail, nRequestID)

    # ???????????????????????????????????????????????????????????????????????????
    # @param nTimeLapse ?????????????????????????????????
    def OnHeartBeatWarning(self, nTimeLapse) -> None:
        pass

    # ?????????????????????

    # ??????????????????????????????
    def OnRspUserPasswordUpdate(self, pUserPasswordUpdate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspTradingAccountPasswordUpdate(self, pTradingAccountPasswordUpdate, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ???????????????????????????
    def OnRspParkedOrderInsert(self, pParkedOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspParkedOrderAction(self, pParkedOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryMaxOrderVolume(self, pQryMaxOrderVolume, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ?????????????????????
    def OnRspRemoveParkedOrder(self, pRemoveParkedOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspRemoveParkedOrderAction(self, pRemoveParkedOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspExecOrderInsert(self, pInputExecOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspExecOrderAction(self, pInputExecOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspForQuoteInsert(self, pInputForQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspQuoteInsert(self, pInputQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspQuoteAction(self, pInputQuoteAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspBatchOrderAction(self, pInputBatchOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspCombActionInsert(self, pInputCombAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ??????????????????????????????

    # ???????????????????????????
    def OnRspQryInvestor(self, pInvestor, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryTradingCode(self, pTradingCode, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQryInstrumentMarginRate(self, pInstrumentMarginRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ???????????????????????????
    def OnRspQryExchange(self, pExchange, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspQryProduct(self, pProduct, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ????????????????????????
    def OnRspQryDepthMarketData(self, pDepthMarketData, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ??????????????????????????????
    def OnRspQryTransferBank(self, pTransferBank, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ??????????????????????????????
    def OnRspQryNotice(self, pNotice, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQrySettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????
    def OnRspQryInvestorPositionCombineDetail(self, pInvestorPositionCombineDetail, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????????????????????????????
    def OnRspQryCFMMCTradingAccountKey(self, pCFMMCTradingAccountKey, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQryEWarrantOffset(self, pEWarrantOffset, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????/????????????????????????
    def OnRspQryInvestorProductGroupMargin(self, pInvestorProductGroupMargin, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????
    def OnRspQryExchangeMarginRate(self, pExchangeMarginRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????????????????????????????????????????
    def OnRspQryExchangeMarginRateAdjust(self, pExchangeMarginRateAdjust, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspQryExchangeRate(self, pExchangeRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????????????????
    def OnRspQrySecAgentACIDMap(self, pSecAgentACIDMap, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryProductExchRate(self, pProductExchRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????????????????
    def OnRspQryProductGroup(self, pProductGroup, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????????????????????????????????????????
    def OnRspQryMMInstrumentCommissionRate(self, pMMInstrumentCommissionRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????????????????
    def OnRspQryMMOptionInstrCommRate(self, pMMOptionInstrCommRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????????????????????????????
    def OnRspQryInstrumentOrderCommRate(self, pInstrumentOrderCommRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQryOptionInstrTradeCost(self, pOptionInstrTradeCost, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????
    def OnRspQryOptionInstrCommRate(self, pOptionInstrCommRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryExecOrder(self, pExecOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspQryForQuote(self, pForQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????
    def OnRspQryQuote(self, pQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????????????????
    def OnRspQryCombInstrumentGuard(self, pCombInstrumentGuard, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryCombAction(self, pCombAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryTransferSerial(self, pTransferSerial, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQryAccountregister(self, pAccountregister, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # ????????????????????????
    def OnRtnInstrumentStatus(self, pInstrumentStatus) -> None:
        pass

    # ?????????????????????
    def OnRtnBulletin(self, pBulletin) -> None:
        pass

    # ????????????
    def OnRtnTradingNotice(self, pTradingNoticeInfo) -> None:
        pass

    # ???????????????????????????
    def OnRtnErrorConditionalOrder(self, pErrorConditionalOrder) -> None:
        pass

    # ??????????????????
    def OnRtnExecOrder(self, pExecOrder) -> None:
        pass

    # ??????????????????????????????
    def OnErrRtnExecOrderInsert(self, pInputExecOrder, pRspInfo) -> None:
        pass

    # ??????????????????????????????
    def OnErrRtnExecOrderAction(self, pExecOrderAction, pRspInfo) -> None:
        pass

    # ????????????????????????
    def OnErrRtnForQuoteInsert(self, pInputForQuote, pRspInfo) -> None:
        pass

    # ????????????
    def OnRtnQuote(self, pQuote) -> None:
        pass

    # ????????????????????????
    def OnErrRtnQuoteInsert(self, pInputQuote, pRspInfo) -> None:
        pass

    # ????????????????????????
    def OnErrRtnQuoteAction(self, pQuoteAction, pRspInfo) -> None:
        pass

    # ????????????
    def OnRtnForQuoteRsp(self, pForQuoteRsp) -> None:
        pass

    # ?????????????????????????????????
    def OnRtnCFMMCTradingAccountToken(self, pCFMMCTradingAccountToken) -> None:
        pass

    # ??????????????????????????????
    def OnErrRtnBatchOrderAction(self, pBatchOrderAction, pRspInfo) -> None:
        pass

    # ??????????????????
    def OnRtnCombAction(self, pCombAction) -> None:
        pass

    # ??????????????????????????????
    def OnErrRtnCombActionInsert(self, pInputCombAction, pRspInfo) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryContractBank(self, pContractBank, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????
    def OnRspQryParkedOrder(self, pParkedOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryParkedOrderAction(self, pParkedOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryTradingNotice(self, pTradingNotice, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????????????????
    def OnRspQryBrokerTradingParams(self, pBrokerTradingParams, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????????????????
    def OnRspQryBrokerTradingAlgos(self, pBrokerTradingAlgos, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQueryCFMMCTradingAccountToken(self, pQueryCFMMCTradingAccountToken, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????
    def OnRtnFromBankToFutureByBank(self, pRspTransfer) -> None:
        pass

    # ???????????????????????????????????????
    def OnRtnFromFutureToBankByBank(self, pRspTransfer) -> None:
        pass

    # ???????????????????????????????????????
    def OnRtnRepealFromBankToFutureByBank(self, pRspRepeal) -> None:
        pass

    # ???????????????????????????????????????
    def OnRtnRepealFromFutureToBankByBank(self, pRspRepeal) -> None:
        pass

    # ???????????????????????????????????????
    def OnRtnFromBankToFutureByFuture(self, pRspTransfer) -> None:
        pass

    # ???????????????????????????????????????
    def OnRtnFromFutureToBankByFuture(self, pRspTransfer) -> None:
        pass

    # ????????????????????????????????????????????????????????????????????????????????????????????????????????????
    def OnRtnRepealFromBankToFutureByFutureManual(self, pRspRepeal) -> None:
        pass

    # ????????????????????????????????????????????????????????????????????????????????????????????????????????????
    def OnRtnRepealFromFutureToBankByFutureManual(self, pRspRepeal) -> None:
        pass

    # ????????????????????????????????????
    def OnRtnQueryBankBalanceByFuture(self, pNotifyQueryAccount) -> None:
        pass

    # ?????????????????????????????????????????????
    def OnErrRtnBankToFutureByFuture(self, pReqTransfer, pRspInfo) -> None:
        pass

    # ?????????????????????????????????????????????
    def OnErrRtnFutureToBankByFuture(self, pReqTransfer, pRspInfo) -> None:
        pass

    # ?????????????????????????????????????????????????????????????????????
    def OnErrRtnRepealBankToFutureByFutureManual(self, pReqRepeal, pRspInfo) -> None:
        pass

    # ?????????????????????????????????????????????????????????????????????
    def OnErrRtnRepealFutureToBankByFutureManual(self, pReqRepeal, pRspInfo) -> None:
        pass

    # ??????????????????????????????????????????
    def OnErrRtnQueryBankBalanceByFuture(self, pReqQueryAccount, pRspInfo) -> None:
        pass

    # ????????????????????????????????????????????????????????????????????????????????????
    def OnRtnRepealFromBankToFutureByFuture(self, pRspRepeal) -> None:
        pass

    # ????????????????????????????????????????????????????????????????????????????????????
    def OnRtnRepealFromFutureToBankByFuture(self, pRspRepeal) -> None:
        pass

    # ???????????????????????????????????????
    def OnRspFromBankToFutureByFuture(self, pReqTransfer, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????
    def OnRspFromFutureToBankByFuture(self, pReqTransfer, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQueryBankAccountMoneyByFuture(self, pReqQueryAccount, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRtnOpenAccountByBank(self, pOpenAccount) -> None:
        pass

    # ??????????????????????????????
    def OnRtnCancelAccountByBank(self, pCancelAccount) -> None:
        pass

    # ????????????????????????????????????
    def OnRtnChangeAccountByBank(self, pChangeAccount) -> None:
        pass

    # ?????????????????????????????????
    def OnRspOptionSelfCloseInsert(self, pInputOptionSelfClose, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????????????????????????????
    def OnRspOptionSelfCloseAction(self, pInputOptionSelfCloseAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQrySecAgentTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????????????????
    def OnRspQrySecAgentCheckMode(self, pSecAgentCheckMode, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????????????????????????????
    def OnRspQryOptionSelfClose(self, pOptionSelfClose, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryInvestUnit(self, pInvestUnit, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????????????????
    def OnRtnOptionSelfClose(self, pOptionSelfClose) -> None:
        pass

    # ?????????????????????????????????
    def OnErrRtnOptionSelfCloseInsert(self, pInputOptionSelfClose, pRspInfo) -> None:
        pass

    # ?????????????????????????????????
    def OnErrRtnOptionSelfCloseAction(self, pOptionSelfCloseAction, pRspInfo) -> None:
        pass

    # ????????????????????????????????????????????????
    def OnRspUserAuthMethod(self, pRspUserAuthMethod, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspGenUserCaptcha(self, pRspGenUserCaptcha, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspGenUserText(self, pRspGenUserText, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????
    def OnRspQrySecAgentTradeInfo(self, pSecAgentTradeInfo, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryClassifiedInstrument(self, pInstrument, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryCombPromotionParam(self, pCombPromotionParam, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????????????????????????????
    def OnRspQryRiskSettleInvstPosition(self, pRiskSettleInvstPosition, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ??????????????????????????????
    def OnRspQryRiskSettleProductStatus(self, pRiskSettleProductStatus, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????
    def OnRspQryTraderOffer(self, pTraderOffer, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM??????????????????????????????
    def OnRspQrySPBMOptionParameter(self, pSPBMOptionParameter, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM??????????????????????????????????????????
    def OnRspQrySPBMIntraParameter(self, pSPBMIntraParameter, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM?????????????????????????????????
    def OnRspQrySPBMInterParameter(self, pSPBMInterParameter, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM?????????????????????????????????
    def OnRspQrySPBMPortfDefinition(self, pSPBMPortfDefinition, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ?????????SPBM????????????????????????
    def OnRspQrySPBMInvestorPortfDef(self, pSPBMInvestorPortfDef, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ????????????????????????????????????????????????
    def OnRspQryInvestorPortfMarginRatio(self, pInvestorPortfMarginRatio, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # ???????????????SPBM??????????????????
    def OnRspQryInvestorProdSPBMDetail(self, pInvestorProdSPBMDetail, pRspInfo, nRequestID, bIsLast) -> None:
        pass
def runQERealTraderProcess(user,account, classname,strats,traderqueue,user_setting,mode_724):
    global g_mode_724 #, tradespi,FrontAddr, 
    # if os.path.exists('tduser.pid'):
    #     with open("tduser.pid",'r') as f:
    #         os.system('kill - 9 '+f.read())
    # with open("tduser.pid",'w') as f:
    #     f.write(str(os.getpid())+'\n')
    #     print('pid:',os.getpid() )
    # now = datetime.now()
    # if not checkMarketTime(now):
    #     print("Market is not opened yet. Please check the time:",now)
    #     return
        #FrontAddr = "tcp://101.230.209.178:53313"
    '''?????????7*24????????????'''   
    ctptrader = qeCtpTrader()
    ctptrader.tqueue = traderqueue
    ctptrader.strats = strats
    ctptrader.user = user
    ctptrader.investor = user_setting['investorid']
    ctptrader.password = user_setting['password']
    ctptrader.broker = user_setting['brokerid']
    ctptrader.appid = user_setting['appid']
    ctptrader.authcode = user_setting['authcode']
    ctptrader.address = user_setting['tdaddress']
    ctptrader.classname = classname
    ctptrader.brokername = user_setting['broker']
    ctptrader.account = account
    ctptrader.account.user = user
    ctptrader.account.investorid = ctptrader.investor
    #self.account.loadFromDB(getCurTradingDay())
    g_mode_724 = mode_724
    #callTimer()   
    #ctptrader.connect()
    evalmode =  user_setting['api'] == 'ctptest'
    setGlobals()
 
 
    #setGlobals()
    #tradeapi=api.CThostFtdcTraderApi_CreateFtdcTraderApi()
    ctptrader.tradespi=CTradeSpi()
    ctptrader.tradespi.Create("./")
    ctptrader.tradespi.classname = ctptrader.classname
    ctptrader.tradespi.tqueue = ctptrader.tqueue
       
    ctptrader.tradespi.investor = str2bytes(ctptrader.investor)
    ctptrader.tradespi.password = str2bytes(ctptrader.password)
    ctptrader.tradespi.reqID = (int(ctptrader.investor) % 10000) + int(datetime.today().strftime('%m%d'))*10000
    ctptrader.tradespi.broker = str2bytes(ctptrader.broker)
    ctptrader.tradespi.appid = str2bytes(ctptrader.appid)
    ctptrader.tradespi.authcode = str2bytes(ctptrader.authcode)
    ctptrader.tradespi.account = ctptrader.account
    ctptrader.tradespi.brokername = ctptrader.brokername
    
    print(f"trader connect to ctp {ctptrader.address}")        
    #tradeapi.RegisterSpi(ctptrader.tradespi)
    ctptrader.tradespi.SubscribePrivateTopic(api.THOST_TERT_QUICK)
    ctptrader.tradespi.SubscribePublicTopic(api.THOST_TERT_QUICK)
    ctptrader.tradespi.RegisterFront(ctptrader.address)
    ctptrader.tradespi.Init()
    print(f"CTP API TD version = {ctptrader.tradespi.GetApiVersion()}")
    ctptrader.evalmode = evalmode
    if evalmode:
        tday = getLocalTradingDay()
        ctptrader.account.tradingDay = tday
        ctptrader.account.loadFromDB(tday)
    ctptrader.callTimer()
    ctptrader.TraderProcess()
    ctptrader.tradespi.Join()

if __name__ == '__main__':
    runQERealTraderProcess('scott','888888',None)