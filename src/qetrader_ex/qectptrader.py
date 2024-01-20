#import pyctp.thosttraderapi as ctpapi
from pyctp.thosttraderapi import *
import time
import json
import os
from datetime import datetime,timedelta
from .qetype import qetype
from .qeredisdb import saveProcessToDB,saveTradeDatarealToDB,saveOrderDatarealToDB
#from .qeaccount import self.account
from .qelogger import logger
#from .qeriskctl import ctpriskctl
from multiprocessing import Queue
from .qectpmarket_wrap import checkMarketTime
from .qecontext import transInstID2Real,transInstID2Context,transExID2Context
import copy
from threading import Thread,Timer
#import qedata
from .qesimtrader import getCurTradingDay
from .qeglobal import instSetts, import_source, get_Instrument_volmult
from .qestatistics import g_stat
from .qeglobal import getExemode,setPositionLoaded

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
                
            #if not self.ordersload:
            #    self.tradespi.reqOrder()
            #    self.ordersload = True
            
            if not self.tradesload:
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
                self.account.saveOrders()
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
        self.account.setTradingDay(d['data']['tradingday'])
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
            print('ctp账户资金信息加载完毕',self.account.balance)
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
            print('ctp账户持仓信息加载完毕')
            logger.info('ctp账户持仓信息加载完毕')
            self.account.setLoadReady()
#         self.tradespi.position = self.account.position
#         print(self.account.position)
        return
def setGlobals(api):
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
    if getExemode():
        import pyctp.thosttraderapi as api
        #import pyctptest.thosttradertestapi as testapi
        #api = testapi if evalmode else ctpapi
    else:
        if evalmode:
            api = __import__('pyctp.thosttradertestapi',fromlist=['a'])
            #from pyctp.thosttraderapi import *
        else:
            api = __import__('pyctp.thosttraderapi',fromlist=['a'])
            #from pyctp.thosttradertestapi import *
            #from pyctp.thosttradertestapi import *
    setGlobals(api)

    class CTradeSpi(api.CThostFtdcTraderSpi):
        tapi=''
        def __init__(self,tapi):
            api.CThostFtdcTraderSpi.__init__(self)
            self.tapi=tapi
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
            return
        
        def reqTrade(self):
            logger.info("Query trades...")
            tradefield = api.CThostFtdcQryTradeField()
            tradefield.BrokerID = self.broker
            tradefield.InvestorID = self.investor
            ret = self.tapi.ReqQryTrade(tradefield, self.reqID)
            if ret != 0:
                logger.warning('reqQryTrade error='+str(ret))
            else:
                self.qryLock = True
                
            
            
        def reqOrder(self):
            logger.info("Query orders...")
            orderfield = api.CThostFtdcQryOrderField()
            orderfield.BrokerID = self.broker
            orderfield.InvestorID = self.investor
            ret = self.tapi.ReqQryOrder(orderfield, self.reqID)
            if ret != 0:
                logger.warning('reqQryOrder error='+str(ret))
            else:
                self.qryLock = True
             
        def reqInstrumentCommission(self, instid):
            logger.info("Query commission...")
            commfield = api.CThostFtdcQryInstrumentCommissionRateField ()
            commfield.BrokerID = self.broker
            commfield.InvestorID = self.investor
            commfield.InstrumentID = instid
            ret = self.tapi.ReqQryInstrumentCommissionRate(commfield, self.reqID)
            if ret != 0:
                logger.warning('reqInstrumentCommission error='+str(ret))
            else:
                self.qryLock = True

        
        def authenticate(self):
            logger.info("Authenticating...")
            authfield = api.CThostFtdcReqAuthenticateField()
            authfield.BrokerID = self.broker
            authfield.UserID = self.investor
            authfield.AppID = self.appid
            authfield.AuthCode = self.authcode
            self.tapi.ReqAuthenticate(authfield,self.reqID)
            
        def OnFrontConnected(self) -> "void":
            print("交易服务器连接成功。")
            now = datetime.now()
            if checkMarketTime(now):
                self.authenticate()
            else:
                self.waitAuth = True
                print('waiting for trading time to request authentication')
            return
        def OnFrontDisconnected(self,nReason:'int')-> "void":
            self.connectionStatus = False
            self.waitAuth = False
            return
        def logout():
            logoutfield = api.CThostFtdcUserLogoutField()
            logoutfield.BrokerID =self.broker
            logoutfield.UserID = self.investor
            self.tapi.ReqUserLogout(logoutfield, self.reqID)
            
        def OnRspAuthenticate(self, pRspAuthenticateField: 'CThostFtdcRspAuthenticateField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":	
    #         logger.info("OnRspAuthenticate")
            if pRspInfo.ErrorID == 0:
    #             logger.info("BrokerID="+str(pRspAuthenticateField.BrokerID))
                logger.info("UserID="+str(pRspAuthenticateField.UserID))
                print("UserID="+str(pRspAuthenticateField.UserID))
    #             logger.info("AppID="+str(pRspAuthenticateField.AppID))
    #             logger.info("AppType="+str(pRspAuthenticateField.AppType))
                self.reqID +=1
                loginfield = api.CThostFtdcReqUserLoginField()
                loginfield.BrokerID=self.broker
                loginfield.UserID=self.investor
                loginfield.Password=self.password
                loginfield.UserProductInfo="python dll"
                self.tapi.ReqUserLogin(loginfield,self.reqID)
                print ("鉴权成功")
            else:
                logger.error("Authenticate ErrorID="+str(pRspInfo.ErrorID))
                logger.error("Authenticate ErrorMsg="+str(pRspInfo.ErrorMsg))
            return
        def OnRspUserLogin(self, pRspUserLogin: 'CThostFtdcRspUserLoginField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
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
                    pSettlementInfoConfirm=api.CThostFtdcSettlementInfoConfirmField()
                    pSettlementInfoConfirm.BrokerID=self.broker
                    pSettlementInfoConfirm.InvestorID=self.investor
                    self.tapi.ReqSettlementInfoConfirm(pSettlementInfoConfirm,self.reqID)
                    #
    #             print("send ReqQrySettlementInfo ok")
            else:
                logger.error(" UserLogin ErrorID="+str(pRspInfo.ErrorID))
                logger.error(" UserLogin ErrorMsg="+str(pRspInfo.ErrorMsg))
            return
        def OnRspUserLogout(self,pUserLogout:'CThostFtdcUserLogoutField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
            self.connectionStatus = False
            logger.info("交易服务器已经登出")
            print("交易服务器已经登出")
            if pRspInfo.ErrorID != 0:
                logger.error("UserLogout ErrorID="+str(pRspInfo.ErrorID))
                logger.error("UserLogout ErrorMsg="+str(pRspInfo.ErrorMsg))
            return
            
        def OnRspQryOrder(self,pOrder:'CThostFtdcOrderField', pRspInfo:'CThostFtdcRspInfoField',  nRequestID:'int', bIsLast:'bool') -> "void":
            #print("OnRspQryOrder")
            if nRequestID != self.reqID:
                return
            try:
                if pOrder:
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
                    print("ctp查询委托订单表完成")
                    #self.reqTrade()
                    self.qryLock = False
            except Exception as e:
                logger.error(f'OnRspQryOrder:{e}')      

            
        def OnRspQryTrade(self, pTrade:'CThostFtdcTradeField', pRspInfo:'CThostFtdcRspInfoField', nRequestID:'int', bIsLast:'bool') -> "void":
            #print("OnRspQryOrder")
            if nRequestID != self.reqID:
                return
            try:
                if pTrade:
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
                    print("ctp查询成交表完成")
                    self.qryLock = False
            except Exception as e:
                logger.error(f'OnRspQryTrade:{e}')      
            
        def OnRspQryInstrumentCommissionRate(self, pInstrumentCommissionRate:'CThostFtdcInstrumentCommissionRateField', pRspInfo: 'CThostFtdcRspInfoField',nRequestID:'int', bIsLast:'bool') -> "void":
            pass
            
        def OnRspQrySettlementInfo(self, pSettlementInfo: 'CThostFtdcSettlementInfoField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
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
                self.tapi.ReqSettlementInfoConfirm(pSettlementInfoConfirm,self.reqID)
    #         print("send ReqSettlementInfoConfirm ok")
            return
        def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm: 'CThostFtdcSettlementInfoConfirmField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
    #         logger.info("OnRspSettlementInfoConfirm")
            #time.sleep(1)
            self.reqPosition()
            #self.connectionStatus = True

            if pRspInfo.ErrorID != 0:
                logger.error("ErrorID="+str(pRspInfo.ErrorID))
                logger.error("ErrorMsg="+str(pRspInfo.ErrorMsg))
            return
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
                
                orderfield=api.CThostFtdcInputOrderField()
                orderfield.BrokerID=self.broker
                orderfield.InstrumentID = instid_ex
                orderfield.UserID=self.investor
                orderfield.InvestorID=self.investor
                orderfield.LimitPrice = order_price
                orderfield.VolumeTotalOriginal = order['volume']
                orderfield.ContingentCondition = api.THOST_FTDC_CC_Immediately
                if order['timecond'] == 'FOK':
                    orderfield.TimeCondition = api.THOST_FTDC_TC_IOC
                    orderfield.VolumeCondition = api.THOST_FTDC_VC_CV
                elif order['timecond'] == 'FAK':
                    orderfield.TimeCondition = api.THOST_FTDC_TC_IOC
                    orderfield.VolumeCondition = api.THOST_FTDC_VC_AV
                else:
                    orderfield.TimeCondition = api.THOST_FTDC_TC_GFD
                    orderfield.VolumeCondition = api.THOST_FTDC_VC_AV
                orderfield.CombHedgeFlag = api.THOST_FTDC_HF_Speculation
    #             orderfield.GTDDate=""
                orderfield.OrderRef=str(orderid)
                orderfield.MinVolume = 1
                orderfield.ForceCloseReason = api.THOST_FTDC_FCC_NotForceClose
                orderfield.IsAutoSuspend = 0
                orderfield.OrderPriceType = api.THOST_FTDC_OPT_LimitPrice
                
    #             orderfield.ExchangeID = "SHFE"
    #             orderfield.Direction = api.THOST_FTDC_D_Buy
    #             orderfield.CombOffsetFlag = api.THOST_FTDC_OF_Open   
                orderfield.ExchangeID = exchangeMap.get(exID,'')
                orderfield.Direction = directionMapReverse.get(order['direction'],'')
                orderfield.CombOffsetFlag = offsetMapReverse.get(order_offset,'')
                ret = self.tapi.ReqOrderInsert(orderfield,self.reqID)
                if ret != 0:
                    logger.warning(f"ReqOrderInsert Failed:{ret}")
                    self.account.orders[orderid]['errorid']= ret
                
            except Exception as e:
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
                    orderfield=api.CThostFtdcInputOrderActionField()
                    orderfield.InstrumentID = instid_ex
                    # orderfield.MacAddress = '' 
                    orderfield.ExchangeID = exID
                    orderfield.ActionFlag = api.THOST_FTDC_AF_Delete
                    # orderfield.OrderActionRef = 0
                    orderfield.UserID = self.investor
                    # orderfield.LimitPrice = price
                    orderfield.OrderRef = str(d['orderid'])
                    
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
                    self.tapi.ReqOrderAction(orderfield,self.reqID)
                else:
                    logger.error('cancel order is not found')
            except Exception as e:
                logger.error(e)
            return
        def reqAccount(self):
            try:
                self.reqID += 1
                #logger.info("reqAccount")
                reqfield=api.CThostFtdcQryTradingAccountField()
                # reqfield.InvestorID = 1
                # reqfield.BrokerID = 2
                # reqfield.AccountID = 3
                ret = self.tapi.ReqQryTradingAccount(reqfield,self.reqID)
                if ret != 0:
                    logger.warning('reqQryTradingAccount error='+str(ret))
                else:
                    self.qryLock = True
            except Exception as e:
                logger.error(e)
            return
        def reqPosition(self):
            try:
                #logger.info("reqPosition")
                self.reqID += 1
                reqfield=api.CThostFtdcQryInvestorPositionField()
                reqfield.InvestorID = self.investor
                reqfield.BrokerID = self.broker
                ret = self.tapi.ReqQryInvestorPosition(reqfield,self.reqID)
                if ret != 0:
                    logger.warning('reqPosition error='+str(ret))
                else:
                    self.qryLock = True
            except Exception as e:
                logger.error(e)
            return 
        def OnRtnOrder(self, pOrder:'CThostFtdcOrderField') -> "void":
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
        def OnRspOrderInsert(self, pInputOrder: 'CThostFtdcInputOrderField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool') -> "void":
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
        def OnErrRtnOrderInsert(self, pInputOrder:'CThostFtdcInputOrderField', pRspInfo: 'CThostFtdcRspInfoField')-> "void":
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
        def OnErrRtnOrderAction(self,pOrderAction:'CThostFtdcOrderActionField', pRspInfo: 'CThostFtdcRspInfoField')-> "void":
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
        def OnRtnTrade(self, pTrade: 'CThostFtdcTradeField') -> "void":
            #global tqueue
    #         logger.info("OnRtnTrade")
            d = {}
            d['type'] = qetype.KEY_ON_TRADE
    #         d['instid'] = pTrade.InstrumentID
            exchange = exchangeMapReverse.get(pTrade.ExchangeID,"")
            d['instid'] = transInstID2Context(pTrade.InstrumentID,exchange)
            d['stratName'] = ''
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
        def OnRspQryTradingAccount(self,pTradingAccount:'CThostFtdcTradingAccountField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool')  -> "void":
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
                    self.qryLock = False
            except Exception as e:
                logger.error(e)
            return
        def OnRspQryInvestorPosition(self,pInvestorPosition:'CThostFtdcInvestorPositionField', pRspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool')  -> "void":
            if nRequestID != self.reqID:
                return
            #global tqueue
            #print('position', pInvestorPosition)
            try:
                if pInvestorPosition is not None and pInvestorPosition.InvestorID==self.investor and  pInvestorPosition.PositionCost != 0:
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
        def OnRspQryInvestorPositionDetail(self,pInvestorPositionDetail:'CThostFtdcInvestorPositionDetailField', RspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool')  -> "void":
            pass
        def OnRspQryInstrument(self,pInstrument:'CThostFtdcInstrumentField',  RspInfo: 'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool')  -> "void":
            pass
        def OnRspError(self,pRspInfo:'CThostFtdcRspInfoField', nRequestID: 'int', bIsLast: 'bool')  -> "void":
            logger.error("ErrorID="+str(pRspInfo.ErrorID))
            logger.error("ErrorMsg="+str(pRspInfo.ErrorMsg))
            return
    '''
    #def real_td_register_strategy(stratName, strat):
    #    global tstrats,feesmult
    #    if not stratName in tstrats:
    #        tstrats[stratName] = strat    
    #    for inst in strat.instid:    
    #        if not inst in instSetts:
    #            instSetts[inst] = qedata.get_instrument_setting(inst)
    #    return
    #def real_td_unregister_strategy(stratName):      
    #    global tstrats  
    #    if stratName in tstrats:
    #        #ID = tstrats[stratName].ID
    #        del tstrats[stratName]
    #        #del tstrats[ID]
    #    return
    '''

    #setGlobals()
    tradeapi=api.CThostFtdcTraderApi_CreateFtdcTraderApi()
    print(f"CTP API TD version = {api.CThostFtdcTraderApi_GetApiVersion()}")
    ctptrader.tradespi=CTradeSpi(tradeapi)
    ctptrader.tradespi.classname = ctptrader.classname
    ctptrader.tradespi.tqueue = ctptrader.tqueue
       
    ctptrader.tradespi.investor = ctptrader.investor
    ctptrader.tradespi.password = ctptrader.password
    ctptrader.tradespi.reqID = (int(ctptrader.investor) % 10000) + int(datetime.today().strftime('%m%d'))*10000
    ctptrader.tradespi.broker = ctptrader.broker
    ctptrader.tradespi.appid = ctptrader.appid
    ctptrader.tradespi.authcode = ctptrader.authcode
    ctptrader.tradespi.account = ctptrader.account
    ctptrader.tradespi.brokername = ctptrader.brokername
    
    print(f"trader connect to ctp {ctptrader.address}")        
    tradeapi.RegisterSpi(ctptrader.tradespi)
    ctptrader.tradespi.tapi.SubscribePrivateTopic(api.THOST_TERT_QUICK)
    ctptrader.tradespi.tapi.SubscribePublicTopic(api.THOST_TERT_QUICK)
    tradeapi.RegisterFront(ctptrader.address)
    ctptrader.tradespi.tapi.Init()
    ctptrader.evalmode = evalmode
    if evalmode:
        tday = getLocalTradingDay()
        ctptrader.account.setTradingDay (tday)
        ctptrader.account.loadFromDB(tday)
    ctptrader.callTimer()
    ctptrader.TraderProcess()
    ctptrader.tradespi.tapi.Join()

if __name__ == '__main__':
    runQERealTraderProcess('scott','888888',None)