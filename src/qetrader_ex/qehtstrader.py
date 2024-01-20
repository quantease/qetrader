#import ctypes
import json
import time
#import argparse
from .secitpdk.secitpdk_dict import (JYLB_SALE,JYLB_BUY,SORT_TYPE_AES,DDLX_XJWT,JYLB_JJRG,
    DDLX_SZSB_QECJCX, DDLX_SZSB_SYCX, DDLX_XJWT, DDLX_SHHB_DSFZYJ,DDLX_SHHB_ZYWDSYZXJ,JYLB_JJSG,
    DDLX_SZSB_DSFZYJ, DDLX_SHHB_BFZYJ, DDLX_SZSB_BFZYJ,DDLX_SZSB_ZYWDSYCX,
    SBJG_WAITING,SBJG_SENDING,SBJG_CONFIRM,SBJG_INVALID,DDLX_SHHB_ZYWDSYCX,
    SBJG_FUNDREQ,SBJG_PARTTRADE,SBJG_COMPLETE,SBJG_PTADPWTD,SBJG_WTDFAIL,SBJG_WITHDRAW,SBJG_MANUAL,
    NOTIFY_PUSH_ORDER,NOTIFY_PUSH_MATCH,NOTIFY_PUSH_INVALID,NOTIFY_PUSH_WITHDRAW,JYLB_ETFSG)
from .secitpdk.secitpdk_struct import (ITPDK_BatchOrder)
from .secitpdk.secitpdk import SECITPDK, cont
from .qelogger import logger
import os
import copy
from threading import Timer
from .qestatistics import g_stat
from .qetype import qetype
from .qeglobal import setPositionLoaded
from .qeredisdb import saveTradeDatarealToDB,saveOrderDatarealToDB
Timer_interval = 2

curHtsTrader = None
class HtsTrader(object):
    def __init__(self, user,account,classname,strats,queue,khh):
        self.tqueue = queue
        self.account = account
        self.account.user = user
        self.account.investorid = khh
        self.strats = strats
        self.user = user
        self.classname = classname
        self.is_connected = False
        self.khh = khh
        self.posLoad = False
        self.accLoad = False
        self.accinfoLoad = False
        ### save for today
        self.updatetime = 0
        self.curday = ''
        self.turnover = 0
        self.posDict = {}
        
    def updateTime(self):
        self.sysday = SECITPDK.GetSystemDate()
        self.tradingday = SECITPDK.GetTradeDate()
        self.timestr = SECITPDK.GetReviseTime()
        self.timedigit = SECITPDK.GetReviseTimeAsLong()
        
        
        if self.account.tradingDay == '':
            self.account.loadFromDB(self.tradingday)
        self.account.current_timedigit = self.timedigit
        self.account.setTradingDay ( self.tradingday  )      
        
        if self.tradingday != self.curday:
            if self.curday != '':
                self.crossday()
            self.curday = self.tradingday

        if self.timedigit - self.updatetime > 3:
            self.updatetime = self.timedigit
            self.account.saveToDB()        

    def TraderProcess(self):
        logger.info(u"start Trader") 
        print("start Trader")
        self.updateTime()
        self.qryAccInfo()
        self.qryAccount()
        self.qryPosition()
        self.callTimer()
        if self.tqueue and self.posLoad and self.accLoad and self.accinfoLoad:
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
        else:
            logger.info('tqueue is not ready')
                    
    def process(self, d):
        ##处理queue信息
        if d['type'] == qetype.KEY_SEND_ORDER:
            self.sendOrder(d)
        elif d['type'] == qetype.KEY_CANCEL_ORDER:
            self.cancelOrder(d)
        
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
        elif d['type'] == qetype.KEY_TIMER:
            self.getStatistic()
            #self.heartBeat(True)
#         elif d['type'] == KEY_ON_INSTRUMENT:
#             self.onInstrument(d)
#         elif d['type'] == KEY_ON_POSITION_DETAIL:
#             self.onPositionDetail(d)
        else:
            logger.error('incorrect type given as type is '+str(d['type']))


    def sendOrder(self,d):
        ## 下单
        self.entrustOrder(d)
        
    def cancelOrder(self,d):
        ## 撤单
        self.orderWithdraw(d['orderid'])
        
    def onOrder(self,d):
        order = self.account.orders.get(d['orderid'],None)
        if order:
            order['status'] = d['status']

            d['direction'] = order['direction']
            d['action'] = order['action']
            d['closetype'] = 'auto' 
            d['timedigit'] = order['timedigit']
            #time = str(d['timedigit'])
            #d['time'] = time[:8]+' '+time[8:10]+':'+time[10:12]+':'+time[12:14]+"."+time[14:]
            d['time'] = order['time']
            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
            d['type'] = qetype.KEY_ON_ORDER
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
            saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, order )
            self.account.orders[d['orderid']] = order
            self.callback(d)
#             self.account.saveToDB()
        else:
            logger.info('rspOrder orderid is not found '+str(d['orderid']))

    def onTrade(self,d):
        ## 订单成交
        order = self.account.orders.get(d['orderid'],None)
        if order or d['from'] != 'RtnTrade':
            d['action'] = 'open' 
            d['closetype'] = 'auto' 
            d['direction'] = order['direction']
            #d['timedigit'] = int(datetime.now().strftime("%Y%m%d%H%M%S")+'001')
            d['timedigit'] = SECITPDK.GetReviseTimeAsLong()
            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
            d['type'] = qetype.KEY_ON_TRADE

            order['status'] = d['status']
            order['tradevol'] += d['tradevol']
            if d['status'] in [qetype.KEY_STATUS_CANCEL, qetype.KEY_STATUS_PTPC , qetype.KEY_STATUS_REJECT]:
                order['cancelvol'] = d['volume'] - d['tradevol']
                order['leftvol'] = 0  
            elif d['status'] == qetype.KEY_STATUS_ALL_TRADED :
                order['cancelvol'] = 0
                order['leftvol'] = 0
            else:
                order['cancelvol'] = 0
                order['leftvol'] = d['volume'] - d['tradevol']
            self.account.orders[d['orderid']] = order
            saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, order)

            trade = {}
            trade['instid'] = d['instid']
            trade['action'] = d['action']
            trade['dir'] = d['direction']
            trade['orderid'] = d['orderid']
            trade['tradevol'] = d['tradevol']
            trade['tradeprice'] = d['tradeprice']
            trade['stratName'] = d['stratName']
            trade['timedigit'] = d['timedigit']
            trade['closetype'] = d['closetype']
            trade['date'] = SECITPDK.GetTradeDate()
            trade['time'] = SECITPDK.GetReviseTime()
            
            tradeid = g_stat.getNewTradeID(int(str(d['timedigit'])[2:]+'00'))
            #while  tradeid in self.account.trades:
            #    tradeid += 1
            trade['tradeid'] = tradeid
            self.account.trades[tradeid] = trade
            #if d['stratName'] == '':
            #    print('unresolved trade', d['orderid'])
            trade['accid'] = self.account.accid
            saveTradeDatarealToDB(self.account.user, self.account.token, self.account.tradingDay, trade )
            self.callback(d)
            self.account.saveToDB()
            dirstr = 'long' if d['dir']>0 else 'short'
            self.account.updateWinLossParas(dirstr,  d['tradeprice'], d['tradevol'], order['closetype'], order['instid'])
        
    def onOrderError(self,d):
        ## 订单失败
        order = self.account.orders.get(d['orderid'],None)
        if order:
            d['stratName'] = order['stratName']
            d['instid'] = order['instid']
            #d['incoming_orderid'] = order['incoming_orderid']      
            d['status'] = qetype.KEY_STATUS_REJECT
            d['direction'] = order['direction']
            d['timedigit'] = order['timedigit']   
            d['tradevol'] = 0    
            d['cancelvol'] = d['volume']
            d['leftvol'] = 0
            ## add keys            
            d['action'] = order['action']
            d['closetype'] = order['closetype']
            d['accid'] = self.account.accid
            d['timecond'] = order['timecond']
            d['time'] = order['time']
            d['type'] = qetype.KEY_ON_ORDER_ERROR
            
            self.callback(d)
            order['errorid'] = d['errorid']
            order['errormsg'] = d['errormsg']
            order['status'] = qetype.KEY_STATUS_REJECT
            order['tradevol']  = 0
            order['cancelvol'] = d['volume']
            order['leftvol'] = 0  
            #print('error errormsg',order.keys(),d.keys())
            saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, order )
            self.account.orders[d['orderid']] = order

    def onCancelConfirm(self,d):
        ## 撤单回报
        order = self.account.orders.get(d['orderid'],None)
        if order:
            order['errorid'] = d['errorid']
            order['errormsg'] = d['errormsg']
            order['status'] = d['status']
            if d['status'] == qetype.KEY_STATUS_CANCEL:
                order['cancelvol'] = order['volume'] - order['tradevol']
                order['leftvol'] = 0
            else:
                order['cancelvol'] = 0
                order['leftvol'] = order['volume'] - order['tradevol']
            saveOrderDatarealToDB(self.account.user,self.account.token, self.account.tradingDay, order )
            self.account.orders[d['orderid']] = order    
            d = copy.deepcopy(order)
            d['type'] = qetype.KEY_ON_CANCEL_CONFIRM
            self.callback(d)

    def callback(self, d):
        ## 回调strat接口，返回策略订单信息
        if d['stratName'].replace(' ','') != '':
            if self.strats:
                stratQueue = self.strats.get(d['stratName'],None)
                if stratQueue:
                    stratQueue['queue'].put(d)
                else:
                    logger.error('callback '+str(d['stratName'])+' is not found')

    def callTimer(self):
        ## 定时器
        global  Timer_interval
        timer = Timer(Timer_interval,self.callTimer)
        d = {}
        d['type'] = qetype.KEY_TIMER
#         logger.info('timer '+str(datetime.now()))
        if self.tqueue:
            self.tqueue.put(d)
        else:
            logger.info('Timer is pending')
        timer.start()       
        
    def getStatistic(self):
        ## 获取统计数据
        self.qryAccount()
        self.qryPosition()

        self.updateTime()
        
    def crossDay(self):
        ## 跨天
        self.turnover = 0
        self.posDict = {}
    
    def onAccount(self,d):
        ## 账户回报
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
        
        if not self.accLoad:
            self.accLoad = True
            self.account.saveToDB()
            print('ctp账户资金信息加载完毕',self.account.balance)
            self.account.setLoadReady()        
        
        
    def onPosition(self,d):
        ## 仓位回报
        self.account.position = copy.copy(d['data'])
        self.account.turnover += float(d['turnover'])
        if not self.posLoad:
            self.posLoad = True
            self.account.saveToDB()
            setPositionLoaded()
            print('ctp账户持仓信息加载完毕')
            logger.info('ctp账户持仓信息加载完毕')
            ##self.account.setLoadReady() ##wait for account load ready
            
    #############################
    ## 以下为HTS独有
    def getTradableQty(self, stcode, exid ,orderdir, price, ordertype):
        ## 获取可交易标的
        gdh = self.shgdh if exid == 'SH' else self.szgdh
        kmsl = SECITPDK.TradableQty(self.khh, stcode, exid, orderdir, price, ordertype, gdh)
        if kmsl >= 0:
            print ("Tradeable qty =", kmsl)
            return kmsl
        else:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("TradableQty failed, {}: {}".format(retcode, retmsg))
            return 0

    def entrustOrder(self, order):
        try:
            orderdir = JYLB_BUY if order['dir'] > 0  else JYLB_SALE 
            stock = order['instid'].split('.')
            stcode = stock[0]
            exid = stock[1] if len(stock) > 1 else ''
            assert exid in ['SSE',"SZE"], "exchange id error"
            exid = 'SH' if exid == 'SSE' else 'SZ'
            ordertype = order['ordertype']
            timecond = order['timecond']
            if ordertype == 'limit':
                if timecond == 'FOK' :
                    if exid == 'SZ':
                        htsorder = DDLX_SZSB_QECJCX
                    else:
                        raise ValueError('limit FOK order not supported for SH')    
                elif timecond == 'FAK':
                    if exid == 'SZ':
                        htsorder = DDLX_SZSB_SYCX
                    else:
                        raise ValueError('limit FAK order not supported for SH')    
                else:
                    htsorder = DDLX_XJWT

            elif ordertype == 'opponent':
                htsorder = DDLX_SHHB_DSFZYJ if exid == 'SH' else DDLX_SZSB_DSFZYJ
            elif ordertype == 'quote':
                htsorder = DDLX_SHHB_BFZYJ if exid == 'SH' else DDLX_SZSB_BFZYJ
            elif ordertype == 'market':
                if timecond == 'FAK':
                    htsorder = DDLX_SHHB_ZYWDSYCX if exid == 'SH' else DDLX_SZSB_ZYWDSYCX
                elif timecond == 'FOK':
                    raise ValueError('market FOK order not supported')
                elif timecond == 'FAL':
                    if exid == 'SH':
                        htsorder = DDLX_SHHB_ZYWDSYZXJ
                    else:
                        raise ValueError('market FAL order not supported for SZ')          
            
            qty = self.getTradableQty(stcode, exid ,orderdir, order['price'], htsorder)
            if qty == 0:
                msg = '下单失败: 可委托数量为0'
                cont.error(msg)
                logger.error(msg)
                order['errorid'] = -1
                order['errormsg']=msg
                self.onOrderError(order)
            elif order['volume'] > qty:
                msg = '下单失败: 下单数量大于可委托数量'
                cont.error(msg)
                logger.error(msg)
                order['errorid'] = -2
                order['errormsg']=msg
                self.onOrderError(order)
            else:
                gdh = self.shgdh if exid == 'SH' else self.szgdh

                wth = SECITPDK.OrderEntrust(self.khh, exid, stcode, orderdir, order['volume'], order['price'], htsorder, gdh)
                if wth > 0:
                    print ("下单成功, wth=", wth)
                    orderid = wth
                    order['orderid'] = wth
                    order['time'] = SECITPDK.GetReviseTime()
                    order['timedigit'] = SECITPDK.GetReviseTimeAsLong()
                    self.account.orders[orderid] = order

                else:
                    retcode, retmsg = SECITPDK.GetLastError()
                    cont.error("下单失败, {}: {}".format(retcode, retmsg))  
                    order['errorid'] = retcode
                    order['errormsg']=retmsg
                    self.onOrderError(order)
        except Exception as e:
            cont.error('entrustOrder error: '+str(e))
            logger.error('下单失败: '+str(e))

    def qryAccount(self):
        """ 查询资金 """
        khh = self.khh
        print ("=========== queryfundinfo_example ============")
        size, arZjzh = SECITPDK.QueryFundInfo(khh)
        if size < 0:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("Query fund info failed, {}: {}".format(retcode, retmsg))
        else:
            print ("Query fund info success, result num:", size)
            d = {}
            d['type'] = qetype.KEY_ON_ACCOUNT
            for i in range(size):
                d['available'] = arZjzh[i].FundAvl
                d['commission'] = 0 ## unsupported
                d['margin'] = arZjzh[i].MarketValue
                d['closeProfit'] = arZjzh[i].DateProfit - arZjzh[i].UnclearProfit
                d['positionProfit'] = arZjzh[i].UnclearProfit
                d['frozenMarg'] = arZjzh[i].FrozenBalance
                d['balance'] = arZjzh[i].TotalAsset
                d['deposit'] = 0 ## unsupported
                d['withdraw'] = 0 ## unsupported               
                print ("AccountId: {}, FundAccount: {}, MoneyType:{}, OrgCode:{}, MasterFlag:{}, AccountType:{}, LastBalance:{}, CurrentBalance: {}, FrozenBalance:{}, FundAvl: {}, TotalAsset:{}, MarketValue:{}, UncomeBalance:{}, FetchBalance:{}, UpdateTime:{}, SettleBalance:{}".format(arZjzh[i].AccountId, arZjzh[i].FundAccount, arZjzh[i].MoneyType, arZjzh[i].OrgCode, arZjzh[i].MasterFlag, arZjzh[i].AccountType, arZjzh[i].LastBalance, arZjzh[i].CurrentBalance, arZjzh[i].FrozenBalance, arZjzh[i].FundAvl, arZjzh[i].TotalAsset, arZjzh[i].MarketValue, arZjzh[i].UncomeBalance, arZjzh[i].FetchBalance, arZjzh[i].UpdateTime, arZjzh[i].SettleBalance))
                break
            self.onAccount(d)

    def qryPosition(self):    
        """ 查询持仓 """
        #print ("=========== queryzqgl_example ============")
        khh =self.khh
        size, arZQGL = SECITPDK.QueryPositions(khh, SORT_TYPE_AES, 0, 0, "", "", "", 1)
        if size < 0:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("查询持仓失败, {}: {}".format(retcode, retmsg))
        else:
            print ("Query zqgl success, result num:", size)

            self.posDict = {}
            self.turnover = 0
            for i in range(size):
                pos = {'long': {'volume': 0, 'poscost': 0, 'yesvol': 0},'short': {'volume': 0, 'poscost': 0, 'yesvol': 0}}
                inst = arZQGL[i].StockCode
                pos['long']['volume'] = arZQGL[i].CurrentQty + arZQGL[i].PreQty
                pos['long']['poscost'] = arZQGL[i].CostPrice
                pos['long']['yesvol'] = arZQGL[i].PreQty
                self.posDict[inst] = pos
                self.turnover += arZQGL[i].RealBuyBalance + arZQGL[i].RealSellBalance
                #print ("AccountId: {}, SecuAccount: {}, StockCode: {}, CurrentQty: {}, MarketValue: {}, CostPrice: {}, DiluteCostPrice: {}, KeepCostPrice: {}, QtyAvl: {}".format(arZQGL[i].AccountId, arZQGL[i].SecuAccount, arZQGL[i].StockCode, arZQGL[i].CurrentQty, arZQGL[i].MarketValue, arZQGL[i].CostPrice, arZQGL[i].DiluteCostPrice, arZQGL[i].KeepCostPrice, arZQGL[i].QtyAvl))
        d = {}
        d['type'] = qetype.KEY_ON_POSITION
        d['data'] = copy.copy(self.posDict)
        d['turnover'] = self.turnover
        self.onPosition(d)

    def qryAccInfo(self):
        ## 查询交易所账户信息
        szgdh = ""
        shgdh = ""
        print ("=========== queryaccinfo_example ============")
        size, arGdh = SECITPDK.QueryAccInfo(self.khh)
        if size < 0:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("Query account info failed, {}: {}".format(retcode, retmsg))
        else:
            print ("Query account info success, result num:", size)
            for i in range(size):
                print ("AccountId: {}, Market: {}, SecuAccount: {}, HolderName:{}, FundAccount: {}, OrgCode:{}, MoneyType:{}, TradeAccess: {}, HolderType:{}".format(arGdh[i].AccountId, arGdh[i].Market, arGdh[i].SecuAccount, arGdh[i].HolderName, arGdh[i].FundAccount, arGdh[i].OrgCode, arGdh[i].MoneyType, arGdh[i].TradeAccess, arGdh[i].HolderType))

                if "SH" == arGdh[i].Market:
                    shgdh = arGdh[i].SecuAccount
                if "SZ" == arGdh[i].Market:
                    szgdh = arGdh[i].SecuAccount
            self.accinfoLoad = True
            self.szgdh = szgdh
            self.shgdh = shgdh        
    def orderWithdraw(self, orderid):
        cdwth = SECITPDK.OrderWithdraw(self.khh, "SZ", orderid)
        if cdwth > 0:
            print ("撤单成功, 订单号=", cdwth)
        else:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("撤单失败, {}: {}".format(retcode, retmsg))
            logger.error("撤单失败, {}: {}".format(retcode, retmsg))

        
    def qryOrder(self):
        pass
    
    def qryTrade(self):
        pass
    
    def processStatus(self,statusstr):
        mapdict ={SBJG_WAITING:qetype.KEY_STATUS_UNKNOWN,
                    SBJG_SENDING:qetype.KEY_STATUS_UNKNOWN,
                    SBJG_CONFIRM:qetype.KEY_STATUS_PENDING,
                    SBJG_INVALID:qetype.KEY_STATUS_REJECTED,
                    SBJG_FUNDREQ:qetype.KEY_STATUS_PENDING,
                    SBJG_PARTTRADE:qetype.KEY_STATUS_PART_TRADED,
                    SBJG_COMPLETE:qetype.KEY_STATUS_ALL_TRADED,
                    SBJG_PTADPWTD:qetype.KEY_STATUS_PTPC,
                    SBJG_WITHDRAW:qetype.KEY_STATUS_CANCELLED,
                    SBJG_WTDFAIL:qetype.KEY_STATUS_CANCELL_FAILED,
                    SBJG_MANUAL:qetype.KEY_STATUS_UNKNOWN}
        return mapdict[statusstr]

    def on_msg_call_back(self,stime, smsg, ntype):
        """ 交易所确认、废单、成交消息推送回调 """
        msg = smsg.decode("gb2312", "strict")
        data = json.loads(msg)
        d = {}
        if NOTIFY_PUSH_ORDER == ntype:
            d['type'] = qetype.KEY_ON_ORDER
            d['orderid'] = data["WTH"]
            d['status'] = self.processStatus(data["SBJG"])
            d['errormsg'] = data['JGSM']
            print ("Receive order confrim msg -- KFSBDBH: {}, WTH: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["SBJG"], data["JGSM"]))
        if NOTIFY_PUSH_WITHDRAW == ntype:
            d['type'] = qetype.KEY_ON_CANCEL_CONFIRM
            d['orderid'] = data["WTH"]
            d['status'] = self.proceeStatus(data["SBJG"])
            d['errormsg'] = data['JGSM'].split(':')[1]
            d['errorid'] = data['JGSM'].split(':')[0]
            print ("Receive withdraw confirm msg -- KFSBDBH: {}, WTH: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["SBJG"], data["JGSM"]))
        if NOTIFY_PUSH_MATCH == ntype:
            d['type'] = qetype.KEY_ON_TRADE
            d['orderid'] = data["WTH"]
            d['status'] = self.processStatus(data["SBJG"])
            d['tradeprice'] = data["CJJG"]
            d['tradevol'] = data["CJSL"]
            d['errormsg'] = data['JGSM']
            print ("Receive order report msg -- KFSBDBH: {}, WTH: {}, CJJG: {}, CJSL: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["CJJG"], data["CJSL"], data["SBJG"], data["JGSM"]))
        if NOTIFY_PUSH_INVALID == ntype:
            d['type'] = qetype.KEY_ON_ORDER_ERROR
            d['orderid'] = data["WTH"]
            d['status'] = self.processStatus(data["SBJG"])
            d['errormsg'] = data['JGSM'].split(':')[1]
            d['errorid'] = data['JGSM'].split(':')[0]
            print ("Receive order failed msg -- KFSBDBH: {}, WTH: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["SBJG"], data["JGSM"]))
        if self.tqueue:
            self.tqueue.put(d)


    def on_connevent_call_back(self, skhh, sconnkey, nevent, data):
        """ 服务连接事件回调 """
        print ("Receive conn evetn -- KHH: {}, Key: {}, Event: {}".format(skhh, sconnkey, nevent))
        
    def on_func_call_back(self,stime, smsg, ntype):
        """ 异步接口回调 """
        msg = smsg.decode("gb2312", "strict")
        data = json.loads(msg)
        print ("Async func call back -- KFSBDBH: {}, RETCODE: {}, RETNOTE:{}".format(data["KFSBDBH"], data["RETCODE"], data["RETNOTE"]))


def on_func_call_back(stime, smsg, ntype):
    """ 异步接口回调 """
    # print "on_func_call_back"
    msg = smsg.decode("gb2312", "strict")
    data = json.loads(msg)
    print ("Async func call back -- KFSBDBH: {}, RETCODE: {}, RETNOTE:{}".format(data["KFSBDBH"], data["RETCODE"], data["RETNOTE"]))


def on_msg_call_back(stime, smsg, ntype):
    """ 交易所确认、废单、成交消息推送回调 """
    msg = smsg.decode("gb2312", "strict")
    data = json.loads(msg)

    if NOTIFY_PUSH_ORDER == ntype:
        print ("Receive order confrim msg -- KFSBDBH: {}, WTH: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["SBJG"], data["JGSM"]))
    if NOTIFY_PUSH_WITHDRAW == ntype:
        print ("Receive withdraw confirm msg -- KFSBDBH: {}, WTH: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["SBJG"], data["JGSM"]))
    if NOTIFY_PUSH_MATCH == ntype:
        print ("Receive order report msg -- KFSBDBH: {}, WTH: {}, CJJG: {}, CJSL: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["CJJG"], data["CJSL"], data["SBJG"], data["JGSM"]))
    if NOTIFY_PUSH_INVALID == ntype:
        print ("Receive order failed msg -- KFSBDBH: {}, WTH: {}, SBJG:{}, JGSM:{}".format(data["KFSBDBH"], data["WTH"], data["SBJG"], data["JGSM"]))


def on_connevent_call_back(skhh, sconnkey, nevent, data):
    """ 服务连接事件回调 """
    print ("Receive conn evetn -- KHH: {}, Key: {}, Event: {}".format(skhh, sconnkey, nevent))


def callback_example():
    SECITPDK.SetFuncCallback(on_func_call_back)
    SECITPDK.SetMsgCallback(on_msg_call_back)
    SECITPDK.SetConnEventCallback(on_connevent_call_back)


def login_example(key, khh, pwd, wtfs):
    """ 登录 """
    print ("=========== login_example ============")
    SECITPDK.SetWTFS(wtfs)
    SECITPDK.SetNode("pysecitpdk")
    token = SECITPDK.TradeLogin(key, khh, pwd)
    if token > 0:
        print ("Login success, token:", token)
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Login error, {}: {}".format(retcode, retmsg))


def time_example():
    """ 获取服务端交易日期、系统日期 """
    print ("=========== time_example ============")
    print ("Server system date:", SECITPDK.GetSystemDate())
    print ("Server trade date:", SECITPDK.GetTradeDate())
    print ("Revise date:", SECITPDK.GetReviseTime())

def querynodeinfo_example(key, khh):
    """ 查询客户节点信息 """
    global szgdh, shgdh
    print ("=========== querynodeinfo_example ============")
    size, arKhjd = SECITPDK.QueryCusNodeinfo(key, khh)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query fund info failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query fund info success, result num:", size)
        for i in range(size):
            print ("AccountId: {}, SystemType: {}, Market:{}, NodeID: {}".format(arKhjd[i].AccountId, arKhjd[i].SystemType, arKhjd[i].Market, arKhjd[i].NodeID))


def queryfundinfo_example(khh):
    """ 查询资金 """
    print ("=========== queryfundinfo_example ============")
    size, arZjzh = SECITPDK.QueryFundInfo(khh)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query fund info failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query fund info success, result num:", size)
        for i in range(size):
            print ("AccountId: {}, FundAccount: {}, MoneyType:{}, OrgCode:{}, MasterFlag:{}, AccountType:{}, LastBalance:{}, CurrentBalance: {}, FrozenBalance:{}, FundAvl: {}, TotalAsset:{}, MarketValue:{}, UncomeBalance:{}, FetchBalance:{}, UpdateTime:{}, SettleBalance:{}".format(arZjzh[i].AccountId, arZjzh[i].FundAccount, arZjzh[i].MoneyType, arZjzh[i].OrgCode, arZjzh[i].MasterFlag, arZjzh[i].AccountType, arZjzh[i].LastBalance, arZjzh[i].CurrentBalance, arZjzh[i].FrozenBalance, arZjzh[i].FundAvl, arZjzh[i].TotalAsset, arZjzh[i].MarketValue, arZjzh[i].UncomeBalance, arZjzh[i].FetchBalance, arZjzh[i].UpdateTime, arZjzh[i].SettleBalance))


def queryaccinfo_example(khh):
    """ 查询股东信息 """
    szgdh = ""
    shgdh = ""
    print ("=========== queryaccinfo_example ============")
    size, arGdh = SECITPDK.QueryAccInfo(khh)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query account info failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query account info success, result num:", size)
        for i in range(size):
            print ("AccountId: {}, Market: {}, SecuAccount: {}, HolderName:{}, FundAccount: {}, OrgCode:{}, MoneyType:{}, TradeAccess: {}, HolderType:{}".format(arGdh[i].AccountId, arGdh[i].Market, arGdh[i].SecuAccount, arGdh[i].HolderName, arGdh[i].FundAccount, arGdh[i].OrgCode, arGdh[i].MoneyType, arGdh[i].TradeAccess, arGdh[i].HolderType))

            if "SH" == arGdh[i].Market:
                shgdh = arGdh[i].SecuAccount
            if "SZ" == arGdh[i].Market:
                szgdh = arGdh[i].SecuAccount
    return szgdh, shgdh


def querydrwt_example(khh):
    """ 查询当日委托 """
    print ("=========== querydrwt_example ============")
    size, arDrwt = SECITPDK.QueryOrders(khh, 0, SORT_TYPE_AES, 0, 0, "", "", 0)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query drwt failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query drwt success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, OrderId: {}, CXOrderId:{}, SBWTH:{}, KFSBDBH: {}, Market:{}, StockCode: {}, StockType:{}, EntrustType:{}, OrderPrice: {}, OrderQty: {}, MatchPrice: {}, MatchQty: {}, SecuAccount:{}, OrderStatus:{}, ResultInfo: {}, BrowIndex:{}".format(arDrwt[i].AccountId, arDrwt[i].OrderId, arDrwt[i].CXOrderId, arDrwt[i].SBWTH, arDrwt[i].KFSBDBH, arDrwt[i].Market, arDrwt[i].StockCode, arDrwt[i].StockType, arDrwt[i].EntrustType, arDrwt[i].OrderPrice, arDrwt[i].OrderQty, arDrwt[i].MatchPrice, arDrwt[i].MatchQty, arDrwt[i].SecuAccount, arDrwt[i].OrderStatus, arDrwt[i].ResultInfo, arDrwt[i].BrowIndex))


def querysscj_example(khh):
    """ 查询实时成交 """
    print ("=========== querysscj_example ============")
    size, arSSCJ = SECITPDK.QueryMatchs(khh, 0, SORT_TYPE_AES, 0, 0, "", "", 0)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query sscj failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query sscj success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, Market:{}, SecuAccount:{}, EntrustType:{}, OrderId: {}, KFSBDBH: {}, MatchSerialNo: {}, StockCode: {}, MatchTime: {}, MatchPrice: {}, MatchQty: {}, ClearBalance: {}, BrowIndex:{}".format(arSSCJ[i].AccountId, arSSCJ[i].Market, arSSCJ[i].SecuAccount, arSSCJ[i].EntrustType, arSSCJ[i].OrderId, arSSCJ[i].KFSBDBH, arSSCJ[i].MatchSerialNo, arSSCJ[i].StockCode, arSSCJ[i].MatchTime, arSSCJ[i].MatchPrice, arSSCJ[i].MatchQty, arSSCJ[i].ClearBalance, arSSCJ[i].BrowIndex))


def queryzqgl(khh):
    """ 查询持仓 """
    #print ("=========== queryzqgl_example ============")
    size, arZQGL = SECITPDK.QueryPositions(khh, SORT_TYPE_AES, 0, 0, "", "", "", 1)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("查询持仓失败, {}: {}".format(retcode, retmsg))
    else:
        print ("Query zqgl success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, SecuAccount: {}, StockCode: {}, CurrentQty: {}, MarketValue: {}, CostPrice: {}, DiluteCostPrice: {}, KeepCostPrice: {}, QtyAvl: {}".format(arZQGL[i].AccountId, arZQGL[i].SecuAccount, arZQGL[i].StockCode, arZQGL[i].CurrentQty, arZQGL[i].MarketValue, arZQGL[i].CostPrice, arZQGL[i].DiluteCostPrice, arZQGL[i].KeepCostPrice, arZQGL[i].QtyAvl))

def QueryFreezeDetails_example(khh):
    """ 查询资金冻结 """
    print ("=========== QueryFreezeDetails_example ============")
    size, arZJLS = SECITPDK.QueryFreezeDetails(khh, khh, 0, 0, 0)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query ZJLS failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query ZJLS success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, FundAccount: {}, SerialNo: {}, MoneyType: {}, OccurDate: {}, FrozenType: {}, FrozenBalance: {}, ApplyTime: {}, Summary: {}".format(arZJLS[i].AccountId, arZJLS[i].FundAccount, arZJLS[i].SerialNo, arZJLS[i].MoneyType, arZJLS[i].OccurDate, arZJLS[i].FrozenType, arZJLS[i].FrozenBalance, arZJLS[i].ApplyTime, arZJLS[i].Summary))

def FundTransDetail_example(khh,pwd):
    """ 查询柜台资金流水 """
    print ("=========== FundTransDetail_example ============")
    size, arGTZJLS = SECITPDK.FundTransDetail(khh, pwd, "", 0, "")
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query FundTransDetail failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query FundTransDetail success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, FundAccount: {}, MoneyType: {}, ApplyTime: {}, FrozenBalance:{}, Summary: {}, BrowIndex: {}".format(arGTZJLS[i].AccountId, arGTZJLS[i].FundAccount, arGTZJLS[i].MoneyType, arGTZJLS[i].ApplyTime, arGTZJLS[i].FrozenBalance, arGTZJLS[i].Summary, arGTZJLS[i].BrowIndex))

def QueryZJHBCL_example(khh,pwd):
    """ 查询资金划拨策略 """
    print ("=========== QueryZJHBCL_example ============")
    size, arZJHBCL = SECITPDK.QueryZJHBCL(khh, pwd, khh)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query QueryZJHBCL failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query QueryZJHBCL success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, FundAccount: {}, MoneyType: {}, NodeId: {}, Market:{}, Rate: {}".format(arZJHBCL[i].AccountId, arZJHBCL[i].FundAccount, arZJHBCL[i].MoneyType, arZJHBCL[i].NodeId, arZJHBCL[i].Market, arZJHBCL[i].Rate))

def QueryJDJZJHBMX_example(khh,pwd):
    """ 查询节点间资金划拨明细 """
    print ("=========== QueryJDJZJHBMX_example ============")
    size, arJDJZJHBMX = SECITPDK.QueryJDJZJHBMX(khh, pwd, "", 0, "")
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query QueryJDJZJHBMX failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query QueryJDJZJHBMX success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, FundAccount: {}, MoneyType: {}, NodeId1: {}, NodeId2:{}, TradeDate:{}, TransDate:{}, Summary: {}, ApplyTime:{}, OccurAmt:{}, BrowIndex: {}".format(arJDJZJHBMX[i].AccountId, arJDJZJHBMX[i].FundAccount, arJDJZJHBMX[i].MoneyType, arJDJZJHBMX[i].NodeId1, arJDJZJHBMX[i].NodeId2, arJDJZJHBMX[i].TradeDate, arJDJZJHBMX[i].TransDate, arJDJZJHBMX[i].ApplyTime, arJDJZJHBMX[i].OccurAmt, arJDJZJHBMX[i].Summary, arJDJZJHBMX[i].BrowIndex))

def querypsqy_example(khh):
    """ 查询配售权益 """
    print ("=========== querypsqy_example ============")
    size, arPSQY = SECITPDK.QueryPSQY(khh, "", "")
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query psqy failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query psqy success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("AccountId: {}, SecuAccount: {}, Market: {}, BallotQty: {}, StartQty: {}".format(arPSQY[i].AccountId, arPSQY[i].SecuAccount, arPSQY[i].Market, arPSQY[i].BallotQty, arPSQY[i].StartQty))

def queryZQDM_example(khh):
    """ 查询证券代码 """
    print ("=========== queryZQDM_example ============")
    size, arZQDM = SECITPDK.QueryZQDMInfo(khh, 0, "", "SZ", "", "", 0)
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query ZQDM failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query ZQDM success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("StockCode: {}, StockName: {}, StockType:{}, Market: {}, MaxTradeAmt:{}, MinTradeAmt:{}".format(arZQDM[i].StockCode, arZQDM[i].StockName, arZQDM[i].StockType, arZQDM[i].Market, arZQDM[i].MaxTradeAmt, arZQDM[i].MinTradeAmt))

def queryTPXX_example(khh):
    """ 查询网络投票信息 """
    print ("=========== queryTPXX_example ============")
    size, arTPXX = SECITPDK.QueryTPXX(khh, 0, 0, "", "")
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query TPXX failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query TPXX success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("Market: {}, StockCode: {}, StockType: {}, CompanyCode: {}, MeetingCode:{}, MeetingName: {}, MotionCode:{}, MotionName:{}, MotionType:{}, BrowIndex: {}".format(arTPXX[i].Market, arTPXX[i].StockCode, arTPXX[i].StockType, arTPXX[i].CompanyCode, arTPXX[i].MeetingCode, arTPXX[i].MeetingName, arTPXX[i].MotionCode, arTPXX[i].MotionName, arTPXX[i].MotionType, arTPXX[i].BrowIndex))

def queryetfmx_example(khh):
    """ 查询ETTF成分股信息 """
    print ("=========== queryetfmx_example ============")
    size, arEtfmx = SECITPDK.QueryETFShare(khh, "510050")
    if size < 0:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Query etfmx failed, {}: {}".format(retcode, retmsg))
    else:
        print ("Query etfmx success, result num:", size)
        for i in range(size):
            if i > 2:
                break
            print ("FundCode: {}, Market: {}, StockCode: {}, ComponentQty: {}, PremiumRatio: {}, CashSubstitute: {}, SubstituteFlag: {}".format(arEtfmx[i].FundCode, arEtfmx[i].Market, arEtfmx[i].StockCode, arEtfmx[i].ComponentQty, arEtfmx[i].PremiumRatio, arEtfmx[i].CashSubstitute, arEtfmx[i].SubstituteFlag))


def orderenstrust_example(khh, szgdh, shgdh):
    """ 普通买卖 """
    print ("=========== orderenstrust_example ============")
    kmsl = SECITPDK.TradableQty(khh, "SZ", "000001", JYLB_BUY, 10.1, DDLX_XJWT, szgdh)
    if kmsl >= 0:
        print ("Tradeable qty =", kmsl)
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("TradableQty failed, {}: {}".format(retcode, retmsg))

    wth = SECITPDK.OrderEntrust(khh, "SZ", "000001", JYLB_BUY, 2000, 10.1, DDLX_XJWT, szgdh)
    if wth > 0:
        print ("Order orderenstrust success, wth=", wth)
        # 撤单
        cdwth = SECITPDK.OrderWithdraw(khh, "SZ", wth)
        if cdwth > 0:
            print ("Order withdraw success, wth=", wth)
        else:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("Order withdraw failed, {}: {}".format(retcode, retmsg))
        # 撤单（异步）
        # ret = SECITPDK.OrderWithdraw_ASync(khh, "SZ", wth)
        # if ret > 0:
        #     print "Order withdraw async success, kfsbdbh=", ret
        # else:
        #     retcode, retmsg = SECITPDK.GetLastError()
        #     cont.error("Order withdraw async failed, {}: {}".format(retcode, retmsg))
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Order failed, {}: {}".format(retcode, retmsg))


def orderenstrust_async_example(khh, szgdh, shgdh):
    """ 异步普通买卖 """
    print ("=========== orderenstrust_async_example ============")
    kfsbdbh = SECITPDK.OrderEntrust_ASync(khh, "SZ", "000001", JYLB_BUY, 100, 10.1, DDLX_XJWT, szgdh)
    if kfsbdbh > 0:
        print ("Order orderenstrust async success, kfsbdbh=", kfsbdbh)
        # 根据开发商本地编号撤单
        cdwth = SECITPDK.OrderWithdrawByKFSBDBH(khh, "SZ", kfsbdbh)
        if cdwth > 0:
            print ("Order withdraw by kfsbdbh success, wth=", cdwth)
        else:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("Order withdraw by kfsbdbh failed, {}: {}".format(retcode, retmsg))
        # 根据开发商本地编号撤单（异步）
        # ret = SECITPDK.OrderWithdrawByKFSBDBH_ASync(khh, "SZ", kfsbdbh)
        # if ret > 0:
        #     print "Order withdraw by kfsbdbh async success, kfsbdbh=", ret
        # else:
        #     retcode, retmsg = SECITPDK.GetLastError()
        #     cont.error("Order withdraw by kfsbdbh async failed, {}: {}".format(retcode, retmsg))
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Order failed, {}: {}".format(retcode, retmsg))


def batchorderenstrust_example(khh, szgdh, shgdh):
    """ 普通买卖批量委托 """
    print ("=========== batchorderenstrust_example ============")
    batchorder = (ITPDK_BatchOrder*3)()
    for i in range(len(batchorder)):
        batchorder[i].Market = "SZ"
        if 0 == i:
            batchorder[i].StockCode = "000001"
        else:
            batchorder[i].StockCode = "000002"
        batchorder[i].EntrustType = JYLB_BUY
        batchorder[i].OrderPrice = 10.1
        batchorder[i].OrderQty = 100
        batchorder[i].OrderType = DDLX_XJWT
        batchorder[i].SecuAccount = szgdh

    ret = SECITPDK.BatchOrderEntrust(khh, batchorder, 1)
    if ret >= 0:
        print ("Batch order success {}/{}".format(len(batchorder)-ret, len(batchorder)))
        for i in range(len(batchorder)):
            print ("No.{} -- WTH: {}, RETMESSAGE: {}".format(i+1, batchorder[i].OrderId, batchorder[i].RetMessage))
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Batch order failed, {}: {}".format(retcode, retmsg))


def batchorderenstrust_async_example(khh, szgdh, shgdh):
    """ 异步普通买卖批量委托 """
    print ("=========== batchorderenstrust_async_example ============")
    batchorder = (ITPDK_BatchOrder*3)()
    for i in range(len(batchorder)):
        batchorder[i].Market = "SZ"
        batchorder[i].StockCode = "000001"
        batchorder[i].EntrustType = JYLB_BUY
        batchorder[i].OrderPrice = 10.1
        batchorder[i].OrderQty = 100
        batchorder[i].OrderType = DDLX_XJWT
        batchorder[i].SecuAccount = szgdh

    ret = SECITPDK.BatchOrderEntrust_ASync(khh, batchorder, 1)
    if ret >= 0:
        print ("Batch order async success")
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Batch order async failed, {}: {}".format(retcode, retmsg))


def etfenstrust_example(khh, szgdh, shgdh):
    """ ETF申赎 """
    print ("=========== etfenstrust_example ============")
    kmsl = SECITPDK.ETFTradableQty(khh, "SZ", "159001", JYLB_ETFSG, szgdh)
    if kmsl >= 0:
        print ("ETFTradeable qty =", kmsl)
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("ETFTradableQty failed, {}: {}".format(retcode, retmsg))

    wth = SECITPDK.ETFEntrust(khh, "SZ", "159001", JYLB_ETFSG, 100, szgdh)
    if wth > 0:
        print ("Order etfenstrust success, wth=", wth)
        # 撤单
        cdwth = SECITPDK.ETFWithdraw(khh, "SZ", wth)
        if cdwth > 0:
            print ("Order withdraw success, wth=", wth)
        else:
            retcode, retmsg = SECITPDK.GetLastError()
            cont.error("Order withdraw failed, {}: {}".format(retcode, retmsg))
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Order failed, {}: {}".format(retcode, retmsg))


def etfenstrust_async_example(khh, szgdh, shgdh):
    """ ETF申赎 """
    print ("=========== etfenstrust_async_example ============")
    kfsbdbh = SECITPDK.ETFEntrust_ASync(khh, "SZ", "159001", JYLB_ETFSG, 100, szgdh)
    if kfsbdbh > 0:
        print ("Order etfenstrust success, kfsbdbh=", kfsbdbh)
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Order failed, {}: {}".format(retcode, retmsg))


def lofenstrust_example(khh, szgdh, shgdh):
    """ LOF基金 """
    print ("=========== lofenstrust_example ============")
    kmsl = SECITPDK.LOFTradableQty(khh, "SH", "501093", JYLB_JJRG, 10.1, DDLX_XJWT, shgdh)
    if kmsl >= 0:
        print ("LOFTradeable qty =", kmsl)
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("LOFTradableQty failed, {}: {}".format(retcode, retmsg))

    wth = SECITPDK.LOFEntrust(khh, "SH", "501093", JYLB_JJRG, 10000, 10.1, DDLX_XJWT, shgdh)
    if wth > 0:
        print ("Order lofenstrust success, wth=", wth)
        # # 撤单
        # cdwth = SECITPDK.ETFWithdraw(khh, "SZ", wth)
        # if cdwth > 0:
        #     print "Order withdraw success, wth=", wth
        # else:
        #     retcode, retmsg = SECITPDK.GetLastError()
        #     cont.error("Order withdraw failed, {}: {}".format(retcode, retmsg))
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Order failed, {}: {}".format(retcode, retmsg))

def shjjtenstrust_example(khh, szgdh, shgdh):
    """ 上海基金通 """
    wth = SECITPDK.SHJJT(khh, "SH", "519001", JYLB_JJSG, 100, 10.1, DDLX_XJWT, 0, "", shgdh)
    if wth > 0:
        print ("Order shjjtenstrust success, wth=", wth)
        # # 撤单
        # cdwth = SECITPDK.ETFWithdraw(khh, "SZ", wth)
        # if cdwth > 0:
        #     print "Order withdraw success, wth=", wth
        # else:
        #     retcode, retmsg = SECITPDK.GetLastError()
        #     cont.error("Order withdraw failed, {}: {}".format(retcode, retmsg))
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Order failed, {}: {}".format(retcode, retmsg))





def runHtsRealTraderProcess(user, account, classname, strats,traderqueue,user_setting):
    '''
    运行实盘交易进程
    :param user: 用户名
    :param account: 账户名
    :param classname: 现货/期权/两融
    :param strats: 策略实例
    :param traderqueue: 交易队列
    :param user_setting: 用户设置
        investorid:投资者代码
        password:密码
        brokerid:经纪商代码key
    :return:
    '''
    global curHtsTrader

    # python .\secdemo.py -key A5_RS_115 -khh 221188943404 -pwd 000783
    # python .\secdemo.py -key A5_RS_93 -khh 221188943403 -pwd 123123
    # python .\secdemo.py -key A5_RS_156 -khh 000001 -pwd 000783
    # python .\secdemo.py -key A5_RS_199 -khh 200900138524 -pwd 000783
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("-key", "--key",     help="login key.",  type=str, default="")
    parser.add_argument("-khh", "--khh",     help="khh.",  type=str, default="")
    parser.add_argument("-pwd", "--pwd",       help="pwd.",  type=str, default="")
    parser.add_argument("-wtfs", "--wtfs",     help="wtfs.",  type=str, default="32")
    args = parser.parse_args()
    '''

    try:
        key = user_setting['brokerid']
        khh = user_setting['investorid']
        pwd = user_setting['password']
        wtfs = "32"
    except Exception as e:
        print (e)
        return
    curdir = os.path.dirname(os.path.abspath(__file__))
    SECITPDK.SetLogPath("")
    print('profile dir',curdir)
    SECITPDK.SetProfilePath(curdir+'/secitpdk/')

    # init
    SECITPDK.Init()
    SECITPDK.SetWriteLog(True)
    SECITPDK.SetFixWriteLog(False)

    curHtsTrader = HtsTrader(user,account,classname,strats,traderqueue,khh)
    
    ## Set callback functions
    SECITPDK.SetFuncCallback(curHtsTrader.on_func_call_back)
    SECITPDK.SetMsgCallback(curHtsTrader.on_msg_call_back)
    SECITPDK.SetConnEventCallback(curHtsTrader.on_connevent_call_back)
    
    
    ## Login to server
    SECITPDK.SetWTFS(wtfs)
    SECITPDK.SetNode("pysecitpdk")
    token = SECITPDK.TradeLogin(key, khh, pwd)
    if token > 0:
        print ("Login success, token:", token)
        curHtsTrader.TraderProcess()
    else:
        retcode, retmsg = SECITPDK.GetLastError()
        cont.error("Login error, {}: {}".format(retcode, retmsg))

def test_trader(khh):
    # query
    # queryfundinfo_example(khh)
    # QueryFreezeDetails_example(khh)
    # queryZQDM_example(khh)
    queryTPXX_example(khh)
    # FundTransDetail_example(khh)
    # QueryZJHBCL_example(khh)
    # QueryJDJZJHBMX_example(khh)
    szgdh, shgdh = queryaccinfo_example(khh)
    # querynodeinfo_example(key,khh)
    # querydrwt_example(khh)
    # querysscj_example(khh)
    # queryzqgl_example(khh)
    # querypsqy_example(khh)
    # queryetfmx_example(khh)

    # trade
    orderenstrust_example(khh, szgdh, shgdh)
    # orderenstrust_async_example(khh, szgdh, shgdh)
    # batchorderenstrust_example(khh, szgdh, shgdh)
    # batchorderenstrust_async_example(khh, szgdh, shgdh)
    # etfenstrust_example(khh, szgdh, shgdh)
    # etfenstrust_async_example(khh, szgdh, shgdh)
    # lofenstrust_example(khh, szgdh, shgdh)
    # shjjtenstrust_example(khh, szgdh, shgdh)

    # wth = []
    # for i in range(2):
    #     ret = SECITPDK.OrderEntrust(khh, "SH", "600000", JYLB_BUY, 101300, 16, DDLX_XJWT, shgdh)
    #     if ret < 0:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Order by kfsbdbh async failed, {}: {}".format(retcode, retmsg))
    #     else:
    #         cont.ok("Order success, wth={}".format(ret))
    #         wth.append(ret)

    # time.sleep(20)
    # for i in wth:
    #     ret = SECITPDK.OrderWithdraw(khh, " ", i)
    #     if ret < 0:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Order withdraw by kfsbdbh async failed, {}: {}".format(retcode, retmsg))
    #     else:
    #         cont.ok("Order withdraw success, wth={}".format(ret))
    #         wth.append(ret)


        

    # for j in range(200):
    #     for i in range(5000):
    #         ret = SECITPDK.OrderEntrust_ASync(khh, "SZ", "000001", JYLB_BUY, 200, 14, DDLX_XJWT, szgdh)
    #         if ret < 0:
    #             retcode, retmsg = SECITPDK.GetLastError()
    #             cont.error("Order withdraw by kfsbdbh async failed, {}: {}".format(retcode, retmsg))
    #     time.sleep(1)

    # for i in range(100000):
    #     size, arSSCJ = SECITPDK.QueryMatchs(khh, 0, SORT_TYPE_AES, 0, 0, "", "", 0)
    #     if size < 0:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Query sscj failed, {}: {}".format(retcode, retmsg))

    # for i in range(100000):
    #     size, arDrwt = SECITPDK.QueryOrders(khh, 0, SORT_TYPE_DESC, 0, 0, "", "", 0)
    #     if size < 0:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Query drwt failed, {}: {}".format(retcode, retmsg))


    # for i in range(20):
    #     wth = SECITPDK.ETFEntrust(khh, "SH", "511651", JYLB_ETFSG, 1000000, shgdh)
    #     if wth > 0:
    #         print "Order etfenstrust success, wth=", wth
    #         # 撤单
    #         # cdwth = SECITPDK.ETFWithdraw(khh, "SZ", wth)
    #         # if cdwth > 0:
    #         #     print "Order withdraw success, wth=", wth
    #         # else:
    #         #     retcode, retmsg = SECITPDK.GetLastError()
    #         #     cont.error("Order withdraw failed, {}: {}".format(retcode, retmsg))
    #     else:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Order failed, {}: {}".format(retcode, retmsg))


    # test
    # for i in range(1):
    #     for j in range(300):
    #         # orderenstrust_async_example()
    #         ret = SECITPDK.OrderEntrust(khh, "SH", "600000", JYLB_BUY, 200, 10.1, DDLX_XJWT, shgdh)
    #         if ret < 0:
    #             retcode, retmsg = SECITPDK.GetLastError()
    #             cont.error("Order withdraw by kfsbdbh async failed, {}: {}".format(retcode, retmsg))

    #     time.sleep(1)
    # for i in range(100):
    #     size, arDrwt = SECITPDK.QueryOrders(khh, 0, SORT_TYPE_DESC, 0, 0, "", "", 0)
    #     if size < 0:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Query drwt failed, {}: {}".format(retcode, retmsg))
    #     else:
    #         for i in range(size):
    #             if i > 2:
    #                 break
    #             print "AccountId: {}, OrderId: {}, KFSBDBH: {}, StockCode: {}, OrderPrice: {}, OrderQty: {}, MatchPrice: {}, MatchQty: {}, ResultInfo: {}".format(arDrwt[i].AccountId, arDrwt[i].OrderId, arDrwt[i].KFSBDBH, arDrwt[i].StockCode, arDrwt[i].OrderPrice, arDrwt[i].OrderQty, arDrwt[i].MatchPrice, arDrwt[i].MatchQty, arDrwt[i].ResultInfo)
    # for i in range(100):
    #     size, arSSCJ = SECITPDK.QueryMatchs(khh, 0, SORT_TYPE_AES, 0, 0, "SZ", "000001", 0)
    #     if size < 0:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Query drwt failed, {}: {}".format(retcode, retmsg))
    #     else:
    #         for i in range(size):
    #             if i > 2:
    #                 break
    #             print "AccountId: {}, OrderId: {}, KFSBDBH: {}, StockCode: {}, MatchPrice: {}, MatchQty: {}, BrowIndex: {}".format(arSSCJ[i].AccountId, arSSCJ[i].OrderId, arSSCJ[i].KFSBDBH, arSSCJ[i].StockCode, arSSCJ[i].MatchPrice, arSSCJ[i].MatchQty, arSSCJ[i].BrowIndex)
    
    # for i in range(31):
    #     size, arZQGL = SECITPDK.QueryPositions(khh, SORT_TYPE_AES, 0, 0, "", "", "", 0)
    #     if size < 0:
    #         retcode, retmsg = SECITPDK.GetLastError()
    #         cont.error("Query zqgl failed, {}: {}".format(retcode, retmsg))


    # wth = SECITPDK.LOFEntrust(khh, "SZ", "160224", JYLB_JJFC, 100, 10.1, DDLX_XJWT, szgdh)
    # if wth > 0:
    #     print "Order lofenstrust success, wth=", wth
    # else:
    #     retcode, retmsg = SECITPDK.GetLastError()
    #     cont.error("Order failed, {}: {}".format(retcode, retmsg))

    # exit
    time.sleep(30)
    SECITPDK.Exit()
    cont.ok("Test complete!")

def testHTSTrader():
    from multiprocessing import Queue
    user = 'test'
    from .qeaccount import realAccountInfo

    account = realAccountInfo()
    classname = 'stock'
    strats = ['test']
    traderqueue = Queue()
    user_setting = {'investorid':"2005255",'password':"202123", 'brokerid':"A5_RS_156_1"}
    runHtsRealTraderProcess(user, account, classname, strats, traderqueue, user_setting)