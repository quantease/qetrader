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
from .qeglobal import  get_Instrument_volmult, g_dataSlide
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

# 价格类型映射
priceTypeMap = {}
priceTypeMapReverse ={}

# 方向类型映射
directionMap = {}
directionMapReverse = {}

# 交易所类型映射
exchangeMap = {}
exchangeMap["CCF"] = "CFFEX"
exchangeMap["SFE"] = "SHFE"
exchangeMap["ZCE"] = "CZCE"
exchangeMap["DCE"] = "DCE"
exchangeMap["SSE"] = "SSE"
exchangeMap["INE"] = "INE"
exchangeMap["unknown"] = ""
exchangeMapReverse = {v:k for k,v in exchangeMap.items()}

# 开平类型映射
offsetMap = {}
offsetMapReverse = {}
# 持仓类型映射
posiDirectionMap = {}
posiDirectionMapReverse={}

# 委托状态映射
statusMap = {}
statusMapReverse = {}


#tstrats={}
#instSetts = {}
#g_dataSlide = {}
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
        self.ordersload = True
        self.tradesload = True
        self.classname = ''
        self.accload = False
        self.posload = False
        self.tqueue = None
        self.strats = None
        self.lastts = 0 
        self.brokername = ''
        self.protectTime = datetime.now()
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
                        d = self.tqueue.get(block=True, timeout=1)
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
        elif d['type'] == qetype.KEY_ON_CROSS_DAY:
            self.update(d)
        elif d['type'] == qetype.KEY_ON_ORDER:
            self.onOrder(d)
        elif d['type'] == qetype.KEY_ON_TRADE:
            self.onTrade(d)              
        elif d['type'] == qetype.KEY_ON_ORDER_ERROR:
            self.onOrderError(d)
        elif d['type'] == qetype.KEY_ON_CANCEL_CONFIRM:
            self.onCancelConfirm(d)    
#         elif d['type'] == KEY_ON_TRADE_ERROR:
#             self.onTradeError(d)
        elif d['type'] == qetype.KEY_ON_POSITION:
            self.onPosition(d)
        elif d['type'] == qetype.KEY_ON_ACCOUNT:
            self.onAccount(d)
        elif d['type'] == qetype.KEY_TIMER:
            #if not self.accload  or not self.posload or not self.ordersload or not self.tradesload:
                #self.getStatistic()
            #if datetime.now() > self.protectTime:
            #    self.tradespi.qryLock = False
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
        
        self.protectTime = datetime.now()+timedelta(seconds=2)
        return
    def callback(self,d):
        #global tstrats
        #print('callback',d)
        if 'stratName' in d and d['stratName'].replace(' ','') != '' and d['stratName'] != 'algoex':
            #print('callback',d['stratName'],self.strats)
            if self.strats:
                stratQueue = self.strats.get(d['stratName'],None)
                if stratQueue:
                    print('callback',d['stratName'],d.get('leftvol',-1),d['type'])
                    stratQueue['queue'].put(d)
                else:
                    logger.error('callback '+str(d['stratName'])+' is not found')
        
    def sendOrder(self,d):
        #repeat = False
        tempinstid_ex,tempexID = transInstID2Real([d['instid']])
        instid_ex = tempinstid_ex[0]
        exID = tempexID[0]
        d['instid_ex'] = instid_ex
        d['exID'] = exID
        
        '''
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
        '''
        #print('sendOrder',d['stratName'])    
        self.tradespi.sendOrder(d)
        #if repeat:
        #    self.tradespi.sendOrder(d1)
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
        #print(self.account.stgtable_load, self.tradespi.qryLock, self.tradespi.connectionStatus, timeValid )
        try:
            if  self.account.stgtable_load and not self.tradespi.qryLock and self.tradespi.connectionStatus and timeValid :
                #if  not self.posload:
                #    self.tradespi.reqPosition()
                    #self.posload = True
                    
                #if not self.ordersload:
                #    self.tradespi.reqOrder()
                #    self.ordersload = True
                
                #if not self.tradesload:
                #    self.tradespi.reqTrade()
                #    self.tradesload = True
                
                if not self.accload or not self.posload or curts - self.lastts > 1 :
                    self.lastts = curts
                    if self.getAsk == True :
                        self.getAsk = False
                        ret = self.tradespi.reqAccount()
                        assert ret==0, f'reqAccount failed {ret}'
                    elif self.getAsk == False :
                        self.getAsk = True
                        ret = self.tradespi.reqPosition()
                        assert ret==0, f'reqPosition failed {ret}'

        except Exception as e:
            logger.error('getStatistic '+str(e))
            print("getStatistic error: ",e)

        if self.accload and self.posload and self.tradesload and self.ordersload:
            Timer_interval = 2
        
        if self.tradespi.waitAuth and isMarketTime:
            self.tradespi.waitAuth = False
            self.tradespi.authenticate()
        return
    def onOrder(self,d): 
        logger.info(f'onOrder callback {d["orderid"]} {d["status"]} {d["tradevol"]} {d["volume"]} {d["leftvol"]} {d["cancelvol"]}')
        saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, d )
        if d['from'] == 'RtnOrder':
            #print('onOrder callback',d)
            self.callback(d)
            self.account.saveOrders()
#             self.account.saveToDB()
    def onTrade(self,d):
#         print('onTrade')
        #global instSetts
        order = self.account.orders.get(d['orderid'],None)
        if order or d['from'] != 'RtnTrade':
            
            ## test only
            # order['tradevol'] += d['tradevol']
            # order['leftvol'] -= d['tradevol']
            # self.account.orders[d['orderid']] = order


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
                ## update position at once
                self.account.saveToDB()
                dirstr = 'long' if d['dir']>0 else 'short'
                self.account.updateWinLossParas(dirstr,  d['tradeprice'], d['tradevol'], d['closetype'], order['instid'])

            
#         else:
#             logger.info('rspTrade orderid is not found ')

    def onCancelConfirm(self,d):
        self.callback(d)
        saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, d )





    def onOrderError(self,d):
        self.callback(d)
        saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, d )
        #self.account.orders[d['orderid']] = order

    def update(self,d):
        #self.tradespi.dataSlide[d['instid']] = d['data']
        #self.account.dataSlide[d['instid']] = copy.copy(d['data'])
        # if self.account.tradingDay == '':
        #     self.account.loadFromDB(d['data']['tradingday'])
        self.crossday()
        self.account.setTradingDay( d['tradingday'])
        self.tradespi.curday = d['tradingday']
        
        # if d['data']['tradingday'] != self.tradespi.curday:
        #     if self.tradespi.curday != '':
        #         self.crossday()
        #     self.tradespi.curday = d['data']['tradingday']
        # self.account.current_timedigit = d['data']['timedigit']
        # self.account.setTradingDay( d['data']['tradingday'])
        # if self.tradespi.lasttime == 0:
        #     self.tradespi.lasttime = d['data']['timedigit']
        # elif abs(d['data']['timedigit'] - self.tradespi.lasttime) > 2500:
        #     self.tradespi.lasttime = d['data']['timedigit']
        #     self.account.saveToDB()
        # return
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
            print(f'ctp账户资金信息加载完毕 {self.account.balance}')
            logger.info(f'ctp账户资金信息加载完毕 {self.account.balance}')
            self.account.setLoadReady()
        
        
    def onPosition(self,d):
#         instid_list = d['data'].keys()
#         for instid in instid_list:
#             temp_instid = 1
        self.account.position = copy.copy(d['data'])
        #print('ctp update position',self.account.position.get('AU2312.SFE',{}))
        self.account.turnover += float(d['turnover'])
        if not self.posload:
            self.posload = True
            self.account.saveToDB()
            setPositionLoaded()
            print('ctp账户持仓信息加载完毕')
            logger.info('ctp账户持仓信息加载完毕')
            #self.account.setLoadReady() ## wait for account info ready
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
    statusMap[api.THOST_FTDC_OST_AllTraded] = qetype.KEY_STATUS_ALL_TRADED                 #全部成交, 0
    statusMap[api.THOST_FTDC_OST_PartTradedQueueing]  = qetype.KEY_STATUS_PART_TRADED      #部分成交还在队列中, 1
    statusMap[api.THOST_FTDC_OST_PartTradedNotQueueing] = qetype.KEY_STATUS_PTPC           #部分成交不在队列中, 2
    statusMap[api.THOST_FTDC_OST_NoTradeQueueing] = qetype.KEY_STATUS_PENDING              #未成交还在队列中, 3
    statusMap[api.THOST_FTDC_OST_NoTradeNotQueueing] = qetype.KEY_STATUS_REJECT                 #未成交不在队列中, 4
    statusMap[api.THOST_FTDC_OST_Canceled] = qetype.KEY_STATUS_CANCEL                       #撤单, 5
    statusMap[api.THOST_FTDC_OST_Unknown] =qetype.KEY_STATUS_UNKNOWN                      #未知, a
    statusMap[api.THOST_FTDC_OST_NotTouched] = "not_touch"                          #尚未触发, b
    statusMap[api.THOST_FTDC_OST_Touched] = "touch"                                 #已触发, c
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
        获取当前交易日
        :retrun 获取到的交易日
        @remark 只有登录成功后,才能得到正确的交易日
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
        self.locktimer = None
        logger.info('traderspi is ready')
    

    def lockTimer(self):
        self.qryLock = False
        #logger.info("Unlock on timer expired")


    def lockStart(self):
        self.qryLock = True
        if self.locktimer and not self.locktimer.finished:
            self.locktimer.cancel()
        self.locktimer = Timer(3, self.lockTimer)
        self.locktimer.start()

    def SubscribePrivateTopic(self, nResumeType: int) -> None:
        """
        订阅私有流。
        :param nResumeType: 私有流重传方式
                THOST_TERT_RESTART:0,从本交易日开始重传
                THOST_TERT_RESUME:1,从上次收到的续传
                THOST_TERT_QUICK:2,只传送登录后私有流的内容

        @remark 该方法要在Init方法前调用。若不调用则不会收到私有流的数据。
        """
        super(CTradeSpi, self).SubscribePrivateTopic(nResumeType)
    
    def SubscribePublicTopic(self, nResumeType: int) -> None:
        """
        订阅公共流。
        :param nResumeType: 公共流重传方式
                THOST_TERT_RESTART:0,从本交易日开始重传
                THOST_TERT_RESUME:1,从上次收到的续传
                THOST_TERT_QUICK:2只传送登录后公共流的内容
        该方法要在Init方法前调用。若不调用则不会收到公共流的数据。
        """
        super(CTradeSpi, self).SubscribePublicTopic(nResumeType)

    def RegisterFront(self, pszFrontAddress: str) -> None:
        """
        注册前置机网络地址
        @param pszFrontAddress：前置机网络地址。
        @remark 网络地址的格式为：“protocol:
        ipaddress:port”，如：”tcp:
        127.0.0.1:17001”。
        @remark “tcp”代表传输协议，“127.0.0.1”代表服务器地址。”17001”代表服务器端口号。
        """
        super(CTradeSpi, self).RegisterFront(pszFrontAddress.encode())

    def ReqAuthenticate(self, pReqAuthenticate: "ReqAuthenticateField", nRequestID: int) -> int:
        """
        客户端认证请求
        """
        return super(CTradeSpi, self).ReqAuthenticate(pReqAuthenticate, nRequestID)

    def ReqUserLogin(self, pReqUserLogin: "ReqUserLoginField", nRequestID: int) -> int:
        """
        用户登录请求
        """
        return super(CTradeSpi, self).ReqUserLogin(pReqUserLogin, nRequestID)

    def ReqUserLogout(self, pUserLogout: "UserLogoutField", nRequestID: int) -> int:
        """
        登出请求
        """
        return super(CTradeSpi, self).ReqUserLogout(pUserLogout, nRequestID)
    def ReqQryOrder(self, pQryOrder: "QryOrderField", nRequestID: int) -> int:
        """
        请求查询报单
        """
        return super(CTradeSpi, self).ReqQryOrder(pQryOrder, nRequestID)

    def ReqQryTrade(self, pQryTrade: "QryTradeField", nRequestID: int) -> int:
        """
        请求查询成交
        """
        return super(CTradeSpi, self).ReqQryTrade(pQryTrade, nRequestID)

    def ReqQryInstrumentCommissionRate(self, pQryInstrumentCommissionRate: "QryInstrumentCommissionRateField", nRequestID: int) -> int:
        """
        请求查询合约手续费率
        """
        return super(CTradeSpi, self).ReqQryInstrumentCommissionRate(pQryInstrumentCommissionRate, nRequestID)

    def ReqOrderAction(self, pInputOrderAction: "InputOrderActionField", nRequestID: int) -> int:
        """
        报单操作请求
        """
        return super(CTradeSpi, self).ReqOrderAction(pInputOrderAction, nRequestID)

    def ReqOrderInsert(self, pInputOrder: "InputOrderField", nRequestID: int) -> int:
        """
        报单录入请求
        """
        return super(CTradeSpi, self).ReqOrderInsert(pInputOrder, nRequestID)

    def ReqQryTradingAccount(self, pQryTradingAccount: "QryTradingAccountField", nRequestID: int) -> int:
        """
        请求查询资金账户
        """
        return super(CTradeSpi, self).ReqQryTradingAccount(pQryTradingAccount, nRequestID)

    def ReqQryInvestorPosition(self, pQryInvestorPosition: "QryInvestorPositionField", nRequestID: int) -> int:
        """
        请求查询投资者持仓
        """
        return super(CTradeSpi, self).ReqQryInvestorPosition(pQryInvestorPosition, nRequestID)

    def ReqSettlementInfoConfirm(self, pSettlementInfoConfirm: "SettlementInfoConfirmField", nRequestID: int) -> int:
        """
        投资者结算结果确认
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
            self.lockStart()

    
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
            if order['ordertype'] == "market":
                tick = g_dataSlide.get(order['instid'], None) #self.dataSlide[order['instid']]
                if tick:
                    if order['direction'] == 1:
                        order_price = tick['upperlimit']
                    else:
                        order_price = tick['lowerlimit']
                else:
                    #order_price = order['price']
                    logger.error('没有tick数据无法下市价单')    
                    return    
            else:
                order_price = order['price']
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
            #print("reqAccount")
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
                self.lockStart()
            return ret    
        except Exception as e:
            print( e.__traceback__.tb_lineno, e)
            logger.error(e)
            return -10
    def reqPosition(self):
        try:
            #logger.info("reqPosition")
            #print("reqPosition")
            self.reqID += 1
            reqfield=QryInvestorPositionField()
            reqfield.InvestorID = self.investor
            reqfield.BrokerID = self.broker
            ret = self.ReqQryInvestorPosition(reqfield,self.reqID)
            if ret != 0:
                logger.warning('reqPosition error='+str(ret))
            else:
                self.lockStart()
            return ret    
        except Exception as e:
            logger.error(e)
            return -10 
        
    def OnFrontConnected(self) -> None:
        print("交易服务器连接成功。")
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
            print ("鉴权成功")
        else:
            logger.error("Authenticate ErrorID="+str(pRspInfo.ErrorID))
            logger.error("Authenticate ErrorMsg="+str(pRspInfo.ErrorMsg))
        return
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast) -> None:
        # print("TradingDay=",pRspUserLogin.TradingDay)
        # print("SessionID=",pRspUserLogin.SessionID)   
        if pRspInfo.ErrorID == 0:
            logger.info("交易服务器登录成功")
            print("交易服务器登录成功")
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
        logger.info("交易服务器已经登出")
        print("交易服务器已经登出")
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

                d['status'] = statusMap.get(d['status_ctp'],'unknown')

                if d['status'] in [qetype.KEY_STATUS_CANCEL, qetype.KEY_STATUS_PTPC , qetype.KEY_STATUS_REJECT]:
                    d['cancelvol'] = d['volume'] - d['tradevol']
                    d['leftvol'] = 0  
                elif d['status'] == qetype.KEY_STATUS_ALL_TRADED :
                    d['cancelvol'] = 0
                    d['leftvol'] = 0
                else:
                    d['cancelvol'] = 0
                    d['leftvol'] = d['volume'] - d['tradevol']                  


                d['direction'] = directionMap.get(d['direction_ctp'],'unknown')
                offset = offsetMap.get(d['offset_ctp'],'auto')
                d['action'] = 'open' if offset =='open' else 'close'
                d['closetype'] = 'auto' if offset =='open' else offset
                d['offset'] = offset
                d['accid'] = self.account.accid
                self.account.orders[d['orderid']] = d
                d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
                d['time'] = d['orderTime']                
                #print("QryOrder:",d)
                self.tqueue.put(d)
            if bIsLast:
                print("ctp查询委托订单表完成")
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
                offset = offsetMap.get(d['offset_ctp'],'auto')
                d['action'] = 'open' if offset =='open' else 'close'
                d['closetype'] = 'auto' if offset =='open' else offset
                d['offset'] = offset
                d['dir'] = directionMap.get(d['direction_ctp'],'unknown')
                #d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
                d['timedigit'] = int((d['tradedate']+d['tradetime'].replace(':','')).replace(' ',''))

                #print("RspTrade:",d)
                self.tqueue.put(d)
            if bIsLast:
                print("ctp查询成交表完成")
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

        d['status'] = statusMap.get(d['status_ctp'],'unknown')
        d['direction'] = directionMap.get(d['direction_ctp'],'unknown')
        offset = offsetMap.get(d['offset_ctp'],'auto')
        d['action'] = 'open' if offset =='open' else 'close'
        d['closetype'] = 'auto' if offset =='open' else offset
        d['offset'] = offset
        d['leftvol'] = 0
        d['cancelvol'] = 0
        order = self.account.orders.get(d['orderid'],None)
        if order is not None:
            order['errorid'] = d['errorid']
            order['errormsg'] = d['errormsg']
            order['status'] = d['status']
            if d['status'] in [qetype.KEY_STATUS_CANCEL, qetype.KEY_STATUS_PTPC , qetype.KEY_STATUS_REJECT]:
                order['cancelvol'] = d['volume'] - d['tradevol']
                order['leftvol'] = 0  
            elif d['status'] == qetype.KEY_STATUS_ALL_TRADED :
                order['cancelvol'] = 0
                order['leftvol'] = 0
            else:
                order['cancelvol'] = 0
                order['leftvol'] = d['volume'] - d['tradevol']  
            order['tradevol'] = d['tradevol']
            self.account.orders[d['orderid']] = order                  
            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
            d['cancelvol'] = order['cancelvol']
            d['leftvol'] = order['leftvol']  
            d['accid'] = self.account.accid
            d['timecond'] = order['timecond']        
        d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
        d['time'] = d['orderTime']
        #print('OnRtnOrder order:',order, 'd:',d)
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
        d['accid'] = self.account.accid
        d['status'] = qetype.KEY_STATUS_REJECT
        d['direction'] = directionMap.get(d['direction_ctp'],'unknown')
        d['offset'] = offsetMap.get(d['offset_ctp'],'unknown')
        d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')   
        d['tradevol'] = 0    
        d['cancelvol'] = d['volume']
        d['leftvol'] = 0
        if d['errorid'] == 26: ## 全部已成交
            d['cancelvol'] = 0 # order['volume'] - order['tradevol']
            d['tradevol'] = d['volume']
            d['leftvol'] = 0
        if d['orderid'] in self.account.orders:
            order = self.account.orders[d['orderid']]
            order['errorid'] = d['errorid']
            order['errormsg'] = d['errormsg']
            order['status'] = qetype.KEY_STATUS_CANCEL_FAILED
            order['cancelvol'] = d['cancelvol']
            order['leftvol'] = d['leftvol']
            order['tradevol'] = d['tradevol']
            self.account.orders[d['orderid']] = order            
            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
            ## add keys            
            d['action'] = order['action']
            d['closetype'] = order['closetype']
            d['timecond'] = order['timecond']
        d['time'] = datetime.now().strftime("%H:%M:%S")
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

        d['accid'] = self.account.accid
        d['status'] = qetype.KEY_STATUS_REJECT
        d['direction'] = directionMap.get(d['direction_ctp'],'unknown')
        d['offset'] = offsetMap.get(d['offset_ctp'],'unknown')
        d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')   
        d['tradevol'] = 0    
        d['cancelvol'] = d['volume']
        d['leftvol'] = 0
        # if d['errorid'] == 26: ## 全部已成交
        #     d['cancelvol'] = 0 # order['volume'] - order['tradevol']
        #     d['tradevol'] = order['volume']
        #     d['leftvol'] = 0
        if d['orderid'] in self.account.orders:
            order = self.account.orders[d['orderid']]
            order['errorid'] = d['errorid']
            order['errormsg'] = d['errormsg']
            order['status'] = qetype.KEY_STATUS_CANCEL_FAILED
            order['cancelvol'] = d['cancelvol']
            order['leftvol'] = d['leftvol']
            order['tradevol'] = d['tradevol']
            self.account.orders[d['orderid']] = order

            ## add keys            
            d['action'] = order['action']
            d['closetype'] = order['closetype']
            d['timecond'] = order['timecond']
            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
        d['time'] = datetime.now().strftime("%H:%M:%S")


        self.tqueue.put(d)
        if pRspInfo.ErrorID == 0:
            logger.info(f"OnErrRtnOrderInsert orderref:{pInputOrder.OrderRef},instid:{pInputOrder.InstrumentID},dir:{pInputOrder.Direction}, vol:{pInputOrder.VolumeTotalOriginal}")
        else:
            logger.error(f"OnErrRtnOrderInsert Error:{pRspInfo.ErrorID}, Msg:{pRspInfo.ErrorMsg}, orderref:{pInputOrder.OrderRef},instid:{pInputOrder.InstrumentID}, dir:{pInputOrder.Direction}, vol:{pInputOrder.VolumeTotalOriginal}")
        
    def OnErrRtnOrderAction(self, pOrderAction, pRspInfo) -> None:
        d = {}
        d['type'] = qetype.KEY_ON_CANCEL_CONFIRM    
        d['orderid'] = int(pOrderAction.OrderRef)
        d['status'] = qetype.KEY_STATUS_CANCEL_FAILED
        #d['volume'] = pOrderAction.VolumeTotalOriginal
        #d['offset_ctp'] = pOrderAction.CombOffsetFlag
        # d['price'] = pOrderAction.LimitPrice
        d['errorid'] = pRspInfo.ErrorID
        d['errormsg'] = pRspInfo.ErrorMsg

        if self.account.orders.get(d['orderid'], None) :
            order = self.account.orders[d['orderid']]            
            if d['errorid'] == 26: ## 全部已成交
                d['cancelvol'] = 0 # order['volume'] - order['tradevol']
                d['tradevol'] = order['volume']
                d['leftvol'] = 0

                    ## add keys            
            else:
                d['cancelvol'] = 0
                d['tradevol'] = order['tradevol']
                d['leftvol'] = order['leftvol']
            order['status'] = qetype.KEY_STATUS_CANCEL_FAILED
            order['cancelvol'] = d['cancelvol']
            order['leftvol'] = d['leftvol']
            order['tradevol'] = d['tradevol']
            order['errorid'] = d['errorid']
            order['errormsg'] = d['errormsg']
            self.account.orders[d['orderid']] = order
            d['volume'] = order['volume']

            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
                #d['incoming_orderid'] = order['incoming_orderid']
            d['status'] = qetype.KEY_STATUS_CANCEL_FAILED
            d['direction'] = order ['direction']
            d['offset'] = order['action']
            d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')   
            d['tradevol'] = order['tradevol']  
            d['cancelvol'] = order['cancelvol']
            d['leftvol'] = order['leftvol']
            d['price'] = order['price']        
            d['action'] = order['action']
            d['closetype'] = order['closetype']
            d['accid'] = self.account.accid
            d['timecond'] = order['timecond']
            d['time'] = datetime.now().strftime("%H:%M:%S")

        self.tqueue.put(d)
#       print('CancelOrder failed ErrorID='+str(pRspInfo.ErrorID)+',ErrorMsg='+str(pRspInfo.ErrorMsg) )
        logger.error('CancelOrder failed orderID='+str(pOrderAction.OrderRef)+',ErrorID='+str(pRspInfo.ErrorID)+',ErrorMsg='+str(pRspInfo.ErrorMsg) )
        
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
        offset = offsetMap.get(d['offset_ctp'],'auto')
        d['action'] = 'open' if offset =='open' else 'close'
        d['closetype'] = 'auto' if offset =='open' else offset
        d['offset'] = offset
        d['dir'] = directionMap.get(d['direction_ctp'],'unknown')
        #d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
        d['timedigit'] = int((d['tradedate']+d['tradetime'].replace(':','')).replace(' ',''))
        if self.account.orders.get(d['orderid'], None) :
            order = self.account.orders[d['orderid']]    
            d['stratName'] = order['stratName']
            #d['instid'] = order['instid']
                #d['orderid'] = order['incoming_orderid']
            self.account.updatePosition(d['instid'], d['dir'], d['action'],d['tradeprice'], d['tradevol'], d['closetype'])
        self.tqueue.put(d)
        print(f"{d['action']} {d['dir']} succeed on  {d['instid']}, price: {d['tradeprice']}, vol: {d['tradevol']}, time: {d['tradetime']}, orderid: {d['orderid']}")
        logger.info(f"{d['action']} {d['dir']} succeed on  {d['instid']}, price: {d['tradeprice']}, vol: {d['tradevol']}, time: {d['tradetime']}, orderid: {d['orderid']}")

        return

    # 请求查询资金账户响应
   
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
                #print('qry account done, qryLock = False')
                
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
                # 针对上期所持仓的今昨分条返回（有昨仓、无今仓），读取昨仓数据
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
                    # 读取冻结
                    # if direction is "long": 
                    #     frozen += pInvestorPosition.LongFrozen
                    # else:
                    #     frozen += pInvestorPosition.ShortFrozen     
                    # 查询回报结束
                    self.posDict[instid] = pos
            if bIsLast:
                d = {}
                d['type'] = qetype.KEY_ON_POSITION
                d['data'] = copy.copy(self.posDict)
                d['turnover'] = self.turnover
#                 print(self.posDict.keys())
                self.posDict.clear()
                self.qryLock = False
                #print('qry position done, qryLock = False')
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
        注册名字服务器网络地址
        :param pszNsAddress：名字服务器网络地址。
        @remark 网络地址的格式为：“protocol:
        ipaddress:port”，如：”tcp:
        127.0.0.1:12001”。
        @remark “tcp”代表传输协议，“127.0.0.1”代表服务器地址。”12001”代表服务器端口号。
        @remark RegisterNameServer优先于RegisterFront
        """
        super(CTradeSpi, self).RegisterNameServer(pszNsAddress.encode())

    def RegisterFensUserInfo(self, pFensUserInfo: "FensUserInfoField") -> None:
        """
        注册名字服务器用户信息
        :param pFensUserInfo：用户信息。
        """
        super(CTradeSpi, self).RegisterFensUserInfo(pFensUserInfo)


    def RegisterUserSystemInfo(self, pUserSystemInfo: "UserSystemInfoField") -> None:
        """
        注册用户终端信息，用于中继服务器多连接模式
        需要在终端认证成功后，用户登录前调用该接口
        """
        super(CTradeSpi, self).RegisterUserSystemInfo(pUserSystemInfo)

    def SubmitUserSystemInfo(self, pUserSystemInfo: "UserSystemInfoField") -> None:
        """
        上报用户终端信息，用于中继服务器操作员登录模式
        操作员登录后，可以多次调用该接口上报客户信息
        """
        super(CTradeSpi, self).SubmitUserSystemInfo(pUserSystemInfo)

    def ReqUserAuthMethod(self, pReqUserAuthMethod: "ReqUserAuthMethod", nRequestID: int) -> int:
        """
        查询用户当前支持的认证模式
        """
        return super(CTradeSpi, self).ReqUserAuthMethod(pReqUserAuthMethod, nRequestID)

    def ReqGenUserCaptcha(self, pReqGenUserCaptcha: "ReqGenUserCaptchaField", nRequestID: int) -> int:
        """
        用户发出获取图形验证码请求
        """
        return super(CTradeSpi, self).ReqGenUserCaptcha(pReqGenUserCaptcha, nRequestID)

    def ReqGenUserText(self, pReqGenUserText: "ReqGenUserTextField", nRequestID: int) -> int:
        """
        用户发出获取短信验证码请求
        """
        return super(CTradeSpi, self).ReqGenUserText(pReqGenUserText, nRequestID)

    def ReqUserLoginWithCaptcha(self, pReqUserLoginWithCaptcha: "ReqUserLoginWithCaptchaField", nRequestID: int) -> int:
        """
        用户发出带有图片验证码的登陆请求
        """
        return super(CTradeSpi, self).ReqUserLoginWithCaptcha(pReqUserLoginWithCaptcha, nRequestID)

    def ReqUserLoginWithText(self, pReqUserLoginWithText: "ReqUserLoginWithTextField", nRequestID: int) -> int:
        """
        用户发出带有短信验证码的登陆请求
        """
        return super(CTradeSpi, self).ReqUserLoginWithText(pReqUserLoginWithText, nRequestID)

    def ReqUserLoginWithOTP(self, pReqUserLoginWithOTP: "ReqUserLoginWithOTPField", nRequestID: int) -> int:
        """
        用户发出带有动态口令的登陆请求
        """
        return super(CTradeSpi, self).ReqUserLoginWithOTP(pReqUserLoginWithOTP, nRequestID)


    def ReqUserPasswordUpdate(self, pUserPasswordUpdate: "UserPasswordUpdateField", nRequestID: int) -> int:
        """
        用户口令更新请求
        """
        return super(CTradeSpi, self).ReqUserPasswordUpdate(pUserPasswordUpdate, nRequestID)

    def ReqTradingAccountPasswordUpdate(self, pTradingAccountPasswordUpdate: "TradingAccountPasswordUpdateField", nRequestID: int) -> int:
        """
        资金账户口令更新请求
        """
        return super(CTradeSpi, self).ReqTradingAccountPasswordUpdate(pTradingAccountPasswordUpdate, nRequestID)


    def ReqParkedOrderInsert(self, pParkedOrder: "ParkedOrderField", nRequestID: int) -> int:
        """
        预埋单录入请求
        """
        return super(CTradeSpi, self).ReqParkedOrderInsert(pParkedOrder, nRequestID)

    def ReqParkedOrderAction(self, pParkedOrderAction: "ParkedOrderActionField", nRequestID: int) -> int:
        """
        预埋撤单录入请求
        """
        return super(CTradeSpi, self).ReqParkedOrderAction(pParkedOrderAction, nRequestID)


    def ReqQryMaxOrderVolume(self, pQryMaxOrderVolume: "QryMaxOrderVolumeField", nRequestID: int) -> int:
        """
        查询最大报单数量请求
        """
        return super(CTradeSpi, self).ReqQryMaxOrderVolume(pQryMaxOrderVolume, nRequestID)


    def ReqRemoveParkedOrder(self, pRemoveParkedOrder: "RemoveParkedOrderField", nRequestID: int) -> int:
        """
        请求删除预埋单
        """
        return super(CTradeSpi, self).ReqRemoveParkedOrder(pRemoveParkedOrder, nRequestID)

    def ReqRemoveParkedOrderAction(self, pRemoveParkedOrderAction: "RemoveParkedOrderActionField", nRequestID: int) -> int:
        """
        请求删除预埋撤单
        """
        return super(CTradeSpi, self).ReqRemoveParkedOrderAction(pRemoveParkedOrderAction, nRequestID)

    def ReqExecOrderInsert(self, pInputExecOrder: "InputExecOrderField", nRequestID: int) -> int:
        """
        执行宣告录入请求
        """
        return super(CTradeSpi, self).ReqExecOrderInsert(pInputExecOrder, nRequestID)

    def ReqExecOrderAction(self, pInputExecOrderAction: "InputExecOrderActionField", nRequestID: int) -> int:
        """
        执行宣告操作请求
        """
        return super(CTradeSpi, self).ReqExecOrderAction(pInputExecOrderAction, nRequestID)

    def ReqForQuoteInsert(self, pInputForQuote: "InputForQuoteField", nRequestID: int) -> int:
        """
        询价录入请求
        """
        return super(CTradeSpi, self).ReqForQuoteInsert(pInputForQuote, nRequestID)

    def ReqQuoteInsert(self, pInputQuote: "InputQuoteField", nRequestID: int) -> int:
        """
        报价录入请求
        """
        return super(CTradeSpi, self).ReqQuoteInsert(pInputQuote, nRequestID)

    def ReqQuoteAction(self, pInputQuoteAction: "InputQuoteActionField", nRequestID: int) -> int:
        """
        报价操作请求
        """
        return super(CTradeSpi, self).ReqQuoteAction(pInputQuoteAction, nRequestID)

    def ReqBatchOrderAction(self, pInputBatchOrderAction: "InputBatchOrderActionField", nRequestID: int) -> int:
        """
        批量报单操作请求
        :param pInputBatchOrderAction:
        :param nRequestID:
        :return:
        """
        return super(CTradeSpi, self).ReqBatchOrderAction(pInputBatchOrderAction, nRequestID)

    def ReqOptionSelfCloseInsert(self, pInputOptionSelfClose: "InputOptionSelfCloseField", nRequestID: int) -> int:
        """
        期权自对冲录入请求
        """
        return super(CTradeSpi, self).ReqOptionSelfCloseInsert(pInputOptionSelfClose, nRequestID)

    def ReqOptionSelfCloseAction(self, pInputOptionSelfCloseAction: "InputOptionSelfCloseActionField", nRequestID: int) -> int:
        """
        期权自对冲操作请求
        """
        return super(CTradeSpi, self).ReqOptionSelfCloseAction(pInputOptionSelfCloseAction, nRequestID)

    def ReqCombActionInsert(self, pInputCombAction: "InputCombActionField", nRequestID: int) -> int:
        """
        申请组合录入请求
        """
        return super(CTradeSpi, self).ReqCombActionInsert(pInputCombAction, nRequestID)



    def ReqQryInvestor(self, pQryInvestor: "QryInvestorField", nRequestID: int) -> int:
        """
        请求查询投资者
        """
        return super(CTradeSpi, self).ReqQryInvestor(pQryInvestor, nRequestID)

    def ReqQryTradingCode(self, pQryTradingCode: "QryTradingCodeField", nRequestID: int) -> int:
        """
        请求查询交易编码
        """
        return super(CTradeSpi, self).ReqQryTradingCode(pQryTradingCode, nRequestID)

    def ReqQryInstrumentMarginRate(self, pQryInstrumentMarginRate: "QryInstrumentMarginRateField", nRequestID: int) -> int:
        """
        请求查询合约保证金率
        """
        return super(CTradeSpi, self).ReqQryInstrumentMarginRate(pQryInstrumentMarginRate, nRequestID)


    def ReqQryExchange(self, pQryExchange: "QryExchangeField", nRequestID: int) -> int:
        """
        请求查询交易所
        """
        return super(CTradeSpi, self).ReqQryExchange(pQryExchange, nRequestID)

    def ReqQryProduct(self, pQryProduct: "QryProductField", nRequestID: int) -> int:
        """
        请求查询产品
        """
        return super(CTradeSpi, self).ReqQryProduct(pQryProduct, nRequestID)

    def ReqQryInstrument(self, pQryInstrument: "QryInstrumentField", nRequestID: int) -> int:
        """
        请求查询合约
        """
        return super(CTradeSpi, self).ReqQryInstrument(pQryInstrument, nRequestID)

    def ReqQryDepthMarketData(self, pQryDepthMarketData: "QryDepthMarketDataField", nRequestID: int) -> int:
        """
        请求查询行情
        """
        return super(CTradeSpi, self).ReqQryDepthMarketData(pQryDepthMarketData, nRequestID)

    def ReqQryTraderOffer(self, pQryTraderOffer: "QryTraderOfferField", nRequestID) -> int:
        return super(CTradeSpi, self).ReqQryTraderOffer(pQryTraderOffer, nRequestID)

    def ReqQrySettlementInfo(self, pQrySettlementInfo: "QrySettlementInfoField", nRequestID: int) -> int:
        """
        请求查询投资者结算结果
        """
        return super(CTradeSpi, self).ReqQrySettlementInfo(pQrySettlementInfo, nRequestID)

    def ReqQryTransferBank(self, pQryTransferBank: "QryTransferBankField", nRequestID: int) -> int:
        """
        请求查询转帐银行
        """
        return super(CTradeSpi, self).ReqQryTransferBank(pQryTransferBank, nRequestID)

    def ReqQryInvestorPositionDetail(self, pQryInvestorPositionDetail: "QryInvestorPositionDetailField", nRequestID: int) -> int:
        """
        请求查询投资者持仓明细
        """
        return super(CTradeSpi, self).ReqQryInvestorPositionDetail(pQryInvestorPositionDetail, nRequestID)

    def ReqQryNotice(self, pQryNotice: "QryNoticeField", nRequestID: int) -> int:
        """
        请求查询客户通知
        """
        return super(CTradeSpi, self).ReqQryNotice(pQryNotice, nRequestID)

    def ReqQrySettlementInfoConfirm(self, pQrySettlementInfoConfirm: "QrySettlementInfoConfirmField", nRequestID: int) -> int:
        """
        请求查询结算信息确认
        """
        return super(CTradeSpi, self).ReqQrySettlementInfoConfirm(pQrySettlementInfoConfirm, nRequestID)

    def ReqQryInvestorPositionCombineDetail(self, pQryInvestorPositionCombineDetail: "QryInvestorPositionCombineDetailField", nRequestID: int) -> int:
        """
        请求查询投资者持仓明细"""
        return super(CTradeSpi, self).ReqQryInvestorPositionCombineDetail(pQryInvestorPositionCombineDetail,
                                                                            nRequestID)

    def ReqQryCFMMCTradingAccountKey(self, pQryCFMMCTradingAccountKey: "QryCFMMCTradingAccountKeyField", nRequestID: int) -> int:
        """
        请求查询保证金监管系统经纪公司资金账户密钥
        """
        return super(CTradeSpi, self).ReqQryCFMMCTradingAccountKey(pQryCFMMCTradingAccountKey, nRequestID)

    def ReqQryEWarrantOffset(self, pQryEWarrantOffset: "QryEWarrantOffsetField", nRequestID: int) -> int:
        """
        请求查询仓单折抵信息
        """
        return super(CTradeSpi, self).ReqQryEWarrantOffset(pQryEWarrantOffset, nRequestID)

    def ReqQryInvestorProductGroupMargin(self, pQryInvestorProductGroupMargin: "QryInvestorProductGroupMarginField", nRequestID: int) -> int:
        """
        请求查询投资者品种/跨品种保证金
        """
        return super(CTradeSpi, self).ReqQryInvestorProductGroupMargin(pQryInvestorProductGroupMargin, nRequestID)

    def ReqQryExchangeMarginRate(self, pQryExchangeMarginRate: "QryExchangeMarginRateField", nRequestID: int) -> int:
        """
        请求查询交易所保证金率
        """
        return super(CTradeSpi, self).ReqQryExchangeMarginRate(pQryExchangeMarginRate, nRequestID)

    def ReqQryExchangeMarginRateAdjust(self, pQryExchangeMarginRateAdjust: "QryExchangeMarginRateAdjustField", nRequestID: int) -> int:
        """
        请求查询交易所调整保证金率
        """
        return super(CTradeSpi, self).ReqQryExchangeMarginRateAdjust(pQryExchangeMarginRateAdjust, nRequestID)

    def ReqQryExchangeRate(self, pQryExchangeRate: "QryExchangeRateField", nRequestID: int) -> int:
        """
        请求查询汇率
        """
        return super(CTradeSpi, self).ReqQryExchangeRate(pQryExchangeRate, nRequestID)

    def ReqQrySecAgentACIDMap(self, pQrySecAgentACIDMap: "QrySecAgentACIDMapField", nRequestID: int) -> int:
        """
        请求查询二级代理操作员银期权限
        """
        return super(CTradeSpi, self).ReqQrySecAgentACIDMap(pQrySecAgentACIDMap, nRequestID)

    def ReqQryProductExchRate(self, pQryProductExchRate: "QryProductExchRateField", nRequestID: int) -> int:
        """
        请求查询产品报价汇率
        """
        return super(CTradeSpi, self).ReqQryProductExchRate(pQryProductExchRate, nRequestID)

    def ReqQryProductGroup(self, pQryProductGroup: "QryProductGroupField", nRequestID: int) -> int:
        """
        请求查询产品组
        """
        return super(CTradeSpi, self).ReqQryProductGroup(pQryProductGroup, nRequestID)

    def ReqQryMMInstrumentCommissionRate(self, pQryMMInstrumentCommissionRate: "QryMMInstrumentCommissionRateField", nRequestID: int) -> int:
        """
        请求查询做市商合约手续费率
        """
        return super(CTradeSpi, self).ReqQryMMInstrumentCommissionRate(pQryMMInstrumentCommissionRate, nRequestID)

    def ReqQryMMOptionInstrCommRate(self, pQryMMOptionInstrCommRate: "QryMMOptionInstrCommRateField", nRequestID: int) -> int:
        """
        请求查询做市商期权合约手续费
        """
        return super(CTradeSpi, self).ReqQryMMOptionInstrCommRate(pQryMMOptionInstrCommRate, nRequestID)

    def ReqQryInstrumentOrderCommRate(self, pQryInstrumentOrderCommRate: "QryInstrumentOrderCommRateField", nRequestID: int) -> int:
        """
        请求查询报单手续费
        """
        return super(CTradeSpi, self).ReqQryInstrumentOrderCommRate(pQryInstrumentOrderCommRate, nRequestID)

    def ReqQrySecAgentTradingAccount(self, pQryTradingAccount: "QryTradingAccountField", nRequestID: int) -> int:
        """
        请求查询资金账户
        """
        return super(CTradeSpi, self).ReqQrySecAgentTradingAccount(pQryTradingAccount, nRequestID)

    def ReqQrySecAgentCheckMode(self, pQrySecAgentCheckMode: "QrySecAgentCheckModeField", nRequestID: int) -> int:
        """
        请求查询二级代理商资金校验模式
        """
        return super(CTradeSpi, self).ReqQrySecAgentCheckMode(pQrySecAgentCheckMode, nRequestID)

    def ReqQryOptionInstrTradeCost(self, pQryOptionInstrTradeCost: "QryOptionInstrTradeCostField", nRequestID: int) -> int:
        """
        请求查询期权交易成本
        """
        return super(CTradeSpi, self).ReqQryOptionInstrTradeCost(pQryOptionInstrTradeCost, nRequestID)

    def ReqQryOptionInstrCommRate(self, pQryOptionInstrCommRate: "QryOptionInstrCommRateField", nRequestID: int) -> int:
        """
        请求查询期权合约手续费
        """
        return super(CTradeSpi, self).ReqQryOptionInstrCommRate(pQryOptionInstrCommRate, nRequestID)

    def ReqQryExecOrder(self, pQryExecOrder: "QryExecOrderField", nRequestID: int) -> int:
        """
        请求查询执行宣告
        """
        return super(CTradeSpi, self).ReqQryExecOrder(pQryExecOrder, nRequestID)

    def ReqQryForQuote(self, pQryForQuote: "QryForQuoteField", nRequestID: int) -> int:
        """
        请求查询询价
        """
        return super(CTradeSpi, self).ReqQryForQuote(pQryForQuote, nRequestID)

    def ReqQryQuote(self, pQryQuote: "QryQuoteField", nRequestID: int) -> int:
        """
        请求查询报价
        """
        return super(CTradeSpi, self).ReqQryQuote(pQryQuote, nRequestID)

    def ReqQryOptionSelfClose(self, pQryOptionSelfClose: "QryOptionSelfCloseField", nRequestID: int) -> int:
        """
        请求查询期权自对冲
        """
        return super(CTradeSpi, self).ReqQryOptionSelfClose(pQryOptionSelfClose, nRequestID)

    def ReqQryInvestUnit(self, pQryInvestUnit: "QryInvestUnitField", nRequestID: int) -> int:
        """
        请求查询投资单元
        """
        return super(CTradeSpi, self).ReqQryInvestUnit(pQryInvestUnit, nRequestID)

    def ReqQryCombInstrumentGuard(self, pQryCombInstrumentGuard: "QryCombInstrumentGuardField", nRequestID: int) -> int:
        """
        请求查询组合合约安全系数
        """
        return super(CTradeSpi, self).ReqQryCombInstrumentGuard(pQryCombInstrumentGuard, nRequestID)

    def ReqQryCombAction(self, pQryCombAction: "QryCombActionField", nRequestID: int) -> int:
        """
        请求查询申请组合
        """
        return super(CTradeSpi, self).ReqQryCombAction(pQryCombAction, nRequestID)

    def ReqQryTransferSerial(self, pQryTransferSerial: "QryTransferSerialField", nRequestID: int) -> int:
        """
        请求查询转帐流水
        """
        return super(CTradeSpi, self).ReqQryTransferSerial(pQryTransferSerial, nRequestID)

    def ReqQryAccountregister(self, pQryAccountregister: "QryAccountregisterField", nRequestID: int) -> int:
        """
        请求查询银期签约关系
        """
        return super(CTradeSpi, self).ReqQryAccountregister(pQryAccountregister, nRequestID)

    def ReqQryContractBank(self, pQryContractBank: "QryContractBankField", nRequestID: int) -> int:
        """
        请求查询签约银行"""
        return super(CTradeSpi, self).ReqQryContractBank(pQryContractBank, nRequestID)

    def ReqQryParkedOrder(self, pQryParkedOrder: "QryParkedOrderField", nRequestID: int) -> int:
        """
        请求查询预埋单
        """
        return super(CTradeSpi, self).ReqQryParkedOrder(pQryParkedOrder, nRequestID)

    def ReqQryParkedOrderAction(self, pQryParkedOrderAction: "QryParkedOrderActionField", nRequestID: int) -> int:
        """
        请求查询预埋撤单"""
        return super(CTradeSpi, self).ReqQryParkedOrderAction(pQryParkedOrderAction, nRequestID)

    def ReqQryTradingNotice(self, pQryTradingNotice: "QryTradingNoticeField", nRequestID: int) -> int:
        """
        请求查询交易通知"""
        return super(CTradeSpi, self).ReqQryTradingNotice(pQryTradingNotice, nRequestID)

    def ReqQryBrokerTradingParams(self, pQryBrokerTradingParams: "QryBrokerTradingParamsField", nRequestID: int) -> int:
        """
        请求查询经纪公司交易参数
        """
        return super(CTradeSpi, self).ReqQryBrokerTradingParams(pQryBrokerTradingParams, nRequestID)

    def ReqQryBrokerTradingAlgos(self, pQryBrokerTradingAlgos: "QryBrokerTradingAlgosField", nRequestID: int) -> int:
        """
        请求查询经纪公司交易算法
        """
        return super(CTradeSpi, self).ReqQryBrokerTradingAlgos(pQryBrokerTradingAlgos, nRequestID)

    def ReqQueryCFMMCTradingAccountToken(self, pQueryCFMMCTradingAccountToken: "QueryCFMMCTradingAccountTokenField", nRequestID: int) -> int:
        """
        请求查询监控中心用户令牌
        """
        return super(CTradeSpi, self).ReqQueryCFMMCTradingAccountToken(pQueryCFMMCTradingAccountToken, nRequestID)

    def ReqFromBankToFutureByFuture(self, pReqTransfer: "ReqTransferField", nRequestID: int) -> int:
        """
        期货发起银行资金转期货请求
        """
        return super(CTradeSpi, self).ReqFromBankToFutureByFuture(pReqTransfer, nRequestID)

    def ReqFromFutureToBankByFuture(self, pReqTransfer: "ReqTransferField", nRequestID: int) -> int:
        """
        期货发起期货资金转银行请求
        """
        return super(CTradeSpi, self).ReqFromFutureToBankByFuture(pReqTransfer, nRequestID)

    def ReqQueryBankAccountMoneyByFuture(self, pReqQueryAccount: "ReqQueryAccountField", nRequestID: int) -> int:
        """
        期货发起查询银行余额请求
        """
        return super(CTradeSpi, self).ReqQueryBankAccountMoneyByFuture(pReqQueryAccount, nRequestID)

    def ReqQrySecAgentTradeInfo(self, pQrySecAgentTradeInfo: "QrySecAgentTradeInfoField", nRequestID: int) -> int:
        """
        请求查询二级代理商信息
        """
        return super(CTradeSpi, self).ReqQrySecAgentTradeInfo(pQrySecAgentTradeInfo, nRequestID)

    def ReqQryClassifiedInstrument(self, pQryClassifiedInstrument: "QryClassifiedInstrumentField", nRequestID: int) -> int:
        """
        请求查询分类合约
        """
        return super(CTradeSpi, self).ReqQryClassifiedInstrument(pQryClassifiedInstrument, nRequestID)

    def ReqQryCombPromotionParam(self, pQryCombPromotionParam: "QryCombPromotionParamField", nRequestID: int) -> int:
        """
        请求组合优惠比例
        """
        return super(CTradeSpi, self).ReqQryCombPromotionParam(pQryCombPromotionParam, nRequestID)

    def ReqQryRiskSettleInvstPosition(self, pQryRiskSettleInvstPosition: "QryRiskSettleInvstPositionField", nRequestID: int) -> int:
        """
        投资者风险结算持仓查询
        """
        return super(CTradeSpi, self).ReqQryRiskSettleInvstPosition(pQryRiskSettleInvstPosition, nRequestID)

    def ReqQryRiskSettleProductStatus(self, pQryRiskSettleProductStatus: "QryRiskSettleProductStatusField", nRequestID: int) -> int:
        """
        风险结算产品查询
        """
        return super(CTradeSpi, self).ReqQryRiskSettleProductStatus(pQryRiskSettleProductStatus, nRequestID)

    # SPBM期货合约参数查询
    def ReqQrySPBMFutureParameter(self, pQrySPBMFutureParameter: "QrySPBMFutureParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMFutureParameter(pQrySPBMFutureParameter, nRequestID)

    # SPBM期权合约参数查询
    def ReqQrySPBMOptionParameter(self, pQrySPBMOptionParameter: "QrySPBMOptionParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMOptionParameter(pQrySPBMOptionParameter, nRequestID)

    # SPBM品种内对锁仓折扣参数查询
    def ReqQrySPBMIntraParameter(self, pQrySPBMIntraParameter: "QrySPBMIntraParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMIntraParameter(pQrySPBMIntraParameter, nRequestID)

    # SPBM跨品种抵扣参数查询
    def ReqQrySPBMInterParameter(self, pQrySPBMInterParameter: "QrySPBMInterParameterField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMInterParameter(pQrySPBMInterParameter, nRequestID)

    # SPBM组合保证金套餐查询
    def ReqQrySPBMPortfDefinition(self, pQrySPBMPortfDefinition: "QrySPBMPortfDefinitionField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMPortfDefinition(pQrySPBMPortfDefinition, nRequestID)

    # 投资者SPBM套餐选择查询
    def ReqQrySPBMInvestorPortfDef(self, pQrySPBMInvestorPortfDef: "QrySPBMInvestorPortfDefField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQrySPBMInvestorPortfDef(pQrySPBMInvestorPortfDef, nRequestID)

    # 投资者新型组合保证金系数查询
    def ReqQryInvestorPortfMarginRatio(self, pQryInvestorPortfMarginRatio: "QryInvestorPortfMarginRatioField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQryInvestorPortfMarginRatio(pQryInvestorPortfMarginRatio, nRequestID)

    # 投资者产品SPBM明细查询
    def ReqQryInvestorProdSPBMDetail(self, pQryInvestorProdSPBMDetail: "QryInvestorProdSPBMDetailField", nRequestID: int) -> int:
        return super(CTradeSpi, self).ReqQryInvestorProdSPBMDetail(pQryInvestorProdSPBMDetail, nRequestID)

    # 心跳超时警告。当长时间未收到报文时，该方法被调用。
    # @param nTimeLapse 距离上次接收报文的时间
    def OnHeartBeatWarning(self, nTimeLapse) -> None:
        pass

    # 客户端认证响应

    # 用户口令更新请求响应
    def OnRspUserPasswordUpdate(self, pUserPasswordUpdate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 资金账户口令更新请求响应
    def OnRspTradingAccountPasswordUpdate(self, pTradingAccountPasswordUpdate, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 预埋单录入请求响应
    def OnRspParkedOrderInsert(self, pParkedOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 预埋撤单录入请求响应
    def OnRspParkedOrderAction(self, pParkedOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 报单操作请求响应
    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 查询最大报单数量响应
    def OnRspQryMaxOrderVolume(self, pQryMaxOrderVolume, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 删除预埋单响应
    def OnRspRemoveParkedOrder(self, pRemoveParkedOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 删除预埋撤单响应
    def OnRspRemoveParkedOrderAction(self, pRemoveParkedOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 执行宣告录入请求响应
    def OnRspExecOrderInsert(self, pInputExecOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 执行宣告操作请求响应
    def OnRspExecOrderAction(self, pInputExecOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 询价录入请求响应
    def OnRspForQuoteInsert(self, pInputForQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 报价录入请求响应
    def OnRspQuoteInsert(self, pInputQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 报价操作请求响应
    def OnRspQuoteAction(self, pInputQuoteAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 批量报单操作请求响应
    def OnRspBatchOrderAction(self, pInputBatchOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 申请组合录入请求响应
    def OnRspCombActionInsert(self, pInputCombAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 请求查询资金账户响应

    # 请求查询投资者响应
    def OnRspQryInvestor(self, pInvestor, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询交易编码响应
    def OnRspQryTradingCode(self, pTradingCode, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询合约保证金率响应
    def OnRspQryInstrumentMarginRate(self, pInstrumentMarginRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 请求查询交易所响应
    def OnRspQryExchange(self, pExchange, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询产品响应
    def OnRspQryProduct(self, pProduct, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 请求查询行情响应
    def OnRspQryDepthMarketData(self, pDepthMarketData, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 请求查询转帐银行响应
    def OnRspQryTransferBank(self, pTransferBank, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 请求查询客户通知响应
    def OnRspQryNotice(self, pNotice, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询结算信息确认响应
    def OnRspQrySettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询投资者持仓明细响应
    def OnRspQryInvestorPositionCombineDetail(self, pInvestorPositionCombineDetail, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 查询保证金监管系统经纪公司资金账户密钥响应
    def OnRspQryCFMMCTradingAccountKey(self, pCFMMCTradingAccountKey, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询仓单折抵信息响应
    def OnRspQryEWarrantOffset(self, pEWarrantOffset, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询投资者品种/跨品种保证金响应
    def OnRspQryInvestorProductGroupMargin(self, pInvestorProductGroupMargin, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询交易所保证金率响应
    def OnRspQryExchangeMarginRate(self, pExchangeMarginRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询交易所调整保证金率响应
    def OnRspQryExchangeMarginRateAdjust(self, pExchangeMarginRateAdjust, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询汇率响应
    def OnRspQryExchangeRate(self, pExchangeRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询二级代理操作员银期权限响应
    def OnRspQrySecAgentACIDMap(self, pSecAgentACIDMap, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询产品报价汇率
    def OnRspQryProductExchRate(self, pProductExchRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询产品组
    def OnRspQryProductGroup(self, pProductGroup, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询做市商合约手续费率响应
    def OnRspQryMMInstrumentCommissionRate(self, pMMInstrumentCommissionRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询做市商期权合约手续费响应
    def OnRspQryMMOptionInstrCommRate(self, pMMOptionInstrCommRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询报单手续费响应
    def OnRspQryInstrumentOrderCommRate(self, pInstrumentOrderCommRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询期权交易成本响应
    def OnRspQryOptionInstrTradeCost(self, pOptionInstrTradeCost, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询期权合约手续费响应
    def OnRspQryOptionInstrCommRate(self, pOptionInstrCommRate, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询执行宣告响应
    def OnRspQryExecOrder(self, pExecOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询询价响应
    def OnRspQryForQuote(self, pForQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询报价响应
    def OnRspQryQuote(self, pQuote, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询组合合约安全系数响应
    def OnRspQryCombInstrumentGuard(self, pCombInstrumentGuard, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询申请组合响应
    def OnRspQryCombAction(self, pCombAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询转帐流水响应
    def OnRspQryTransferSerial(self, pTransferSerial, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询银期签约关系响应
    def OnRspQryAccountregister(self, pAccountregister, pRspInfo, nRequestID, bIsLast) -> None:
        pass


    # 合约交易状态通知
    def OnRtnInstrumentStatus(self, pInstrumentStatus) -> None:
        pass

    # 交易所公告通知
    def OnRtnBulletin(self, pBulletin) -> None:
        pass

    # 交易通知
    def OnRtnTradingNotice(self, pTradingNoticeInfo) -> None:
        pass

    # 提示条件单校验错误
    def OnRtnErrorConditionalOrder(self, pErrorConditionalOrder) -> None:
        pass

    # 执行宣告通知
    def OnRtnExecOrder(self, pExecOrder) -> None:
        pass

    # 执行宣告录入错误回报
    def OnErrRtnExecOrderInsert(self, pInputExecOrder, pRspInfo) -> None:
        pass

    # 执行宣告操作错误回报
    def OnErrRtnExecOrderAction(self, pExecOrderAction, pRspInfo) -> None:
        pass

    # 询价录入错误回报
    def OnErrRtnForQuoteInsert(self, pInputForQuote, pRspInfo) -> None:
        pass

    # 报价通知
    def OnRtnQuote(self, pQuote) -> None:
        pass

    # 报价录入错误回报
    def OnErrRtnQuoteInsert(self, pInputQuote, pRspInfo) -> None:
        pass

    # 报价操作错误回报
    def OnErrRtnQuoteAction(self, pQuoteAction, pRspInfo) -> None:
        pass

    # 询价通知
    def OnRtnForQuoteRsp(self, pForQuoteRsp) -> None:
        pass

    # 保证金监控中心用户令牌
    def OnRtnCFMMCTradingAccountToken(self, pCFMMCTradingAccountToken) -> None:
        pass

    # 批量报单操作错误回报
    def OnErrRtnBatchOrderAction(self, pBatchOrderAction, pRspInfo) -> None:
        pass

    # 申请组合通知
    def OnRtnCombAction(self, pCombAction) -> None:
        pass

    # 申请组合录入错误回报
    def OnErrRtnCombActionInsert(self, pInputCombAction, pRspInfo) -> None:
        pass

    # 请求查询签约银行响应
    def OnRspQryContractBank(self, pContractBank, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询预埋单响应
    def OnRspQryParkedOrder(self, pParkedOrder, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询预埋撤单响应
    def OnRspQryParkedOrderAction(self, pParkedOrderAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询交易通知响应
    def OnRspQryTradingNotice(self, pTradingNotice, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询经纪公司交易参数响应
    def OnRspQryBrokerTradingParams(self, pBrokerTradingParams, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询经纪公司交易算法响应
    def OnRspQryBrokerTradingAlgos(self, pBrokerTradingAlgos, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询监控中心用户令牌
    def OnRspQueryCFMMCTradingAccountToken(self, pQueryCFMMCTradingAccountToken, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 银行发起银行资金转期货通知
    def OnRtnFromBankToFutureByBank(self, pRspTransfer) -> None:
        pass

    # 银行发起期货资金转银行通知
    def OnRtnFromFutureToBankByBank(self, pRspTransfer) -> None:
        pass

    # 银行发起冲正银行转期货通知
    def OnRtnRepealFromBankToFutureByBank(self, pRspRepeal) -> None:
        pass

    # 银行发起冲正期货转银行通知
    def OnRtnRepealFromFutureToBankByBank(self, pRspRepeal) -> None:
        pass

    # 期货发起银行资金转期货通知
    def OnRtnFromBankToFutureByFuture(self, pRspTransfer) -> None:
        pass

    # 期货发起期货资金转银行通知
    def OnRtnFromFutureToBankByFuture(self, pRspTransfer) -> None:
        pass

    # 系统运行时期货端手工发起冲正银行转期货请求，银行处理完毕后报盘发回的通知
    def OnRtnRepealFromBankToFutureByFutureManual(self, pRspRepeal) -> None:
        pass

    # 系统运行时期货端手工发起冲正期货转银行请求，银行处理完毕后报盘发回的通知
    def OnRtnRepealFromFutureToBankByFutureManual(self, pRspRepeal) -> None:
        pass

    # 期货发起查询银行余额通知
    def OnRtnQueryBankBalanceByFuture(self, pNotifyQueryAccount) -> None:
        pass

    # 期货发起银行资金转期货错误回报
    def OnErrRtnBankToFutureByFuture(self, pReqTransfer, pRspInfo) -> None:
        pass

    # 期货发起期货资金转银行错误回报
    def OnErrRtnFutureToBankByFuture(self, pReqTransfer, pRspInfo) -> None:
        pass

    # 系统运行时期货端手工发起冲正银行转期货错误回报
    def OnErrRtnRepealBankToFutureByFutureManual(self, pReqRepeal, pRspInfo) -> None:
        pass

    # 系统运行时期货端手工发起冲正期货转银行错误回报
    def OnErrRtnRepealFutureToBankByFutureManual(self, pReqRepeal, pRspInfo) -> None:
        pass

    # 期货发起查询银行余额错误回报
    def OnErrRtnQueryBankBalanceByFuture(self, pReqQueryAccount, pRspInfo) -> None:
        pass

    # 期货发起冲正银行转期货请求，银行处理完毕后报盘发回的通知
    def OnRtnRepealFromBankToFutureByFuture(self, pRspRepeal) -> None:
        pass

    # 期货发起冲正期货转银行请求，银行处理完毕后报盘发回的通知
    def OnRtnRepealFromFutureToBankByFuture(self, pRspRepeal) -> None:
        pass

    # 期货发起银行资金转期货应答
    def OnRspFromBankToFutureByFuture(self, pReqTransfer, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 期货发起期货资金转银行应答
    def OnRspFromFutureToBankByFuture(self, pReqTransfer, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 期货发起查询银行余额应答
    def OnRspQueryBankAccountMoneyByFuture(self, pReqQueryAccount, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 银行发起银期开户通知
    def OnRtnOpenAccountByBank(self, pOpenAccount) -> None:
        pass

    # 银行发起银期销户通知
    def OnRtnCancelAccountByBank(self, pCancelAccount) -> None:
        pass

    # 银行发起变更银行账号通知
    def OnRtnChangeAccountByBank(self, pChangeAccount) -> None:
        pass

    # 期权自对冲录入请求响应
    def OnRspOptionSelfCloseInsert(self, pInputOptionSelfClose, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 期权自对冲操作请求响应
    def OnRspOptionSelfCloseAction(self, pInputOptionSelfCloseAction, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询资金账户响应
    def OnRspQrySecAgentTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询二级代理商资金校验模式响应
    def OnRspQrySecAgentCheckMode(self, pSecAgentCheckMode, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询期权自对冲响应
    def OnRspQryOptionSelfClose(self, pOptionSelfClose, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询投资单元响应
    def OnRspQryInvestUnit(self, pInvestUnit, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 期权自对冲通知
    def OnRtnOptionSelfClose(self, pOptionSelfClose) -> None:
        pass

    # 期权自对冲录入错误回报
    def OnErrRtnOptionSelfCloseInsert(self, pInputOptionSelfClose, pRspInfo) -> None:
        pass

    # 期权自对冲操作错误回报
    def OnErrRtnOptionSelfCloseAction(self, pOptionSelfCloseAction, pRspInfo) -> None:
        pass

    # 查询用户当前支持的认证模式的回复
    def OnRspUserAuthMethod(self, pRspUserAuthMethod, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 获取图形验证码请求的回复
    def OnRspGenUserCaptcha(self, pRspGenUserCaptcha, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 获取短信验证码请求的回复
    def OnRspGenUserText(self, pRspGenUserText, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询二级代理商信息响应
    def OnRspQrySecAgentTradeInfo(self, pSecAgentTradeInfo, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询分类合约响应
    def OnRspQryClassifiedInstrument(self, pInstrument, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求组合优惠比例响应
    def OnRspQryCombPromotionParam(self, pCombPromotionParam, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 投资者风险结算持仓查询响应
    def OnRspQryRiskSettleInvstPosition(self, pRiskSettleInvstPosition, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 风险结算产品查询响应
    def OnRspQryRiskSettleProductStatus(self, pRiskSettleProductStatus, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 请求查询交易员报盘机响应
    def OnRspQryTraderOffer(self, pTraderOffer, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM期权合约参数查询响应
    def OnRspQrySPBMOptionParameter(self, pSPBMOptionParameter, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM品种内对锁仓折扣参数查询响应
    def OnRspQrySPBMIntraParameter(self, pSPBMIntraParameter, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM跨品种抵扣参数查询响应
    def OnRspQrySPBMInterParameter(self, pSPBMInterParameter, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # SPBM组合保证金套餐查询响应
    def OnRspQrySPBMPortfDefinition(self, pSPBMPortfDefinition, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 投资者SPBM套餐选择查询响应
    def OnRspQrySPBMInvestorPortfDef(self, pSPBMInvestorPortfDef, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 投资者新型组合保证金系数查询响应
    def OnRspQryInvestorPortfMarginRatio(self, pInvestorPortfMarginRatio, pRspInfo, nRequestID, bIsLast) -> None:
        pass

    # 投资者产品SPBM明细查询响应
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
    '''以下是7*24小时环境'''   
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
    #if evalmode:
    tday = getLocalTradingDay()
    ctptrader.account.setTradingDay(tday)
    ctptrader.account.loadFromDB(tday)
    ctptrader.callTimer()
    ctptrader.TraderProcess()
    ctptrader.tradespi.Join()

if __name__ == '__main__':
    runQERealTraderProcess('scott','888888',None)