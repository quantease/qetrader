# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 21:11:45 2022

@author: ScottStation
"""
from .qelogger import logger
#from .qeriskctl import soptriskctl, ctpriskctl
from .qetype import qetype
from .qeredisdb import saveHedgePointToDB, saveHedgePointrealToDB, get_bar_data
from multiprocessing import Queue
import pandas as pd
import numpy as np
#import datetime
from .qesimtrader import getMixPrice
from .qestatistics import g_stat
from .qeglobal import getAccidTraderQueue, getInstTraderQueue, getInstClass, getInstAccID, getClassAccID
from datetime import datetime, timedelta
import traceback
import random
import asyncio


simuqueue = Queue()

class qeStratBase:
    flippage = 0
    traderate = 1.0
    formula = None
    wait_all=False
    freq=0
    instid = None
    datamode ='tick'
    rfrate = 0.00
    
    feesmult = 1.0
    recordinsts = None
    direction_index = 0
    dailyminutes = 5
    
    _runmode = 'simu'
    _start_date = None
    _end_date = None
    _append_mode = False
    
    @classmethod
    def setMode(cls, runmode, start_date=None, end_date=None):
        cls._runmode = runmode
        cls._start_date = start_date
        cls._end_date = end_date

 
    def handleData(self, context):
        pass
    
    def onBar(self,context):
        pass

    def crossDay(self, context):
        pass
    
    def handleOrder(self,order, context):
        pass

    def handleOrderError(self,order, context):
        pass
    
    def handleTrade(self,trade,context):
        pass

    async def aio_onBar(self,context):
        pass
    
    async def aio_crossDay(self,context):
        pass

    def matchTrade(self, context, datamode):
        try:
            # trades = {'id':{'tradeprice}}
            tradeprice = 0.0
            tradevol = 0
            orderinstid = ''
            trades = {}
            flippage = self.flippage
            traderate = self.traderate
            # print(context.orders)
            for oid in context.orders:
                orderinstid = context.orders[oid]['instid']
                if context.orders[oid]['leftvol'] == 0:
                    continue
                ## dataslide trade process
                elif datamode == 'tick':
                    current = context.dataslide[orderinstid]['current']
                    if context.orders[oid]['ordertype'] == 'market':
                        if context.orders[oid]['direction'] > 0:
                            tradeprice = current if current >= context.dataslide[orderinstid]['a1_p'] else \
                                context.dataslide[orderinstid]['a1_p']
                            tradeprice = context.dataslide[orderinstid]['a1_p'] + flippage * \
                                         context.instsett[orderinstid][
                                             'ticksize'] if flippage > 0 and tradeprice < \
                                                            context.dataslide[orderinstid][
                                                                'a1_p'] + flippage * context.instsett[orderinstid][
                                                                'ticksize'] else tradeprice
                        else:
                            tradeprice = current if current <= context.dataslide[orderinstid]['b1_p'] else \
                                context.dataslide[orderinstid]['b1_p']
                            tradeprice = context.dataslide[orderinstid]['b1_p'] - flippage * \
                                         context.instsett[orderinstid][
                                             'ticksize'] if flippage > 0 and tradeprice > \
                                                            context.dataslide[orderinstid][
                                                                'b1_p'] - flippage * context.instsett[orderinstid][
                                                                'ticksize'] else tradeprice
                        #tradevol = max(int(context.curvol[orderinstid] * traderate), 1)
                        #tradevol = context.orders[oid]['leftvol'] if context.orders[oid][
                        #                                                'leftvol'] < tradevol else tradevol
                        tradevol =  context.orders[oid]['leftvol']

                    elif context.orders[oid]['ordertype'] == 'limit':
                        tradeprice = context.orders[oid]['price']
                        if (context.orders[oid]['direction'] > 0 and current > context.orders[oid]['price']) or (
                                context.orders[oid]['direction'] < 0 and current < context.orders[oid]['price']):
                            tradevol = 0
                            continue
                        elif current == context.orders[oid]['price']:
                            tradevol = context.curvol[orderinstid] - context.orders[oid]['pendvol'] if context.curvol[
                                                                                                          orderinstid] >= \
                                                                                                      context.orders[
                                                                                                          oid][
                                                                                                          'pendvol'] else 0
                            context.orders[oid]['pendvol'] -= context.orders[oid]['pendvol'] if context.curvol[
                                                                                                  orderinstid] > \
                                                                                              context.orders[oid][
                                                                                                  'pendvol'] else \
                                context.curvol[orderinstid]
                            if tradevol == 0:
                                continue
                            else:
                                tradevol = context.orders[oid]['leftvol'] if context.orders[oid][
                                                                                'leftvol'] < tradevol else tradevol
                        else:
                            tradevol = max(int(context.curvol[orderinstid] * traderate), 1)
                            tradevol = context.orders[oid]['leftvol'] if context.orders[oid][
                                                                            'leftvol'] < tradevol else tradevol

                ## minu data trade process

                elif datamode == 'minute':
                    
                    current = context.dataslide[orderinstid]['close']
                    if context.orders[oid]['ordertype'] == 'market':
                        if context.orders[oid]['direction'] > 0:
                            tradeprice = current + flippage * context.instsett[orderinstid]['ticksize']
                        else:
                            tradeprice = current - flippage * context.instsett[orderinstid]['ticksize']
#                         print(type(context.curvol[orderinstid]))
#                         print(type(traderate))
                        #tradevol = max(1,int(context.curvol[orderinstid] * traderate))
                        tradevol = context.orders[oid]['leftvol']

                    elif context.orders[oid]['ordertype'] == 'limit':
                        tradeprice = context.orders[oid]['price']
                        # spread = 2 * context.instsett[orderinstid]['ticksize']
                        if (context.orders[oid]['direction'] > 0 and context.dataslide[orderinstid]['close'] >
                            context.orders[oid]['price']) or (
                                context.orders[oid]['direction'] < 0 and context.dataslide[orderinstid]['close'] <
                                context.orders[oid]['price']):
                            tradevol = 0
                            continue
                        else:
                            tradevol = max(1, int(context.curvol[orderinstid] * traderate))
                    tradevol = context.orders[oid]['leftvol'] if context.orders[oid]['leftvol'] < tradevol else tradevol

                ##minute and daily trade
                else:
                    current = context.dataslide[orderinstid]['close']
                    if context.orders[oid]['ordertype'] == 'market':
                        if context.orders[oid]['direction'] > 0:
                            tradeprice = current + flippage * context.instsett[orderinstid]['ticksize']
                        else:
                            tradeprice = current - flippage * context.instsett[orderinstid]['ticksize']
                        #tradevol = max(1,int(context.curvol[orderinstid] * traderate))
                        tradevol = context.orders[oid]['leftvol']

                    elif context.orders[oid]['ordertype'] == 'limit':
                        tradeprice = context.orders[oid]['price']
                        if (context.orders[oid]['direction'] > 0 and context.dataslide[orderinstid]['close'] >
                            context.orders[oid]['price']) or (
                                context.orders[oid]['direction'] < 0 and context.dataslide[orderinstid]['close'] <
                                context.orders[oid]['price']):
                            tradevol = 0
                            continue
                        else:
                            tradevol = max(1,int(context.curvol[orderinstid] * traderate))
                    tradevol = context.orders[oid]['leftvol'] if context.orders[oid]['leftvol'] < tradevol else tradevol
                if (context.orders[oid]['timecond']== 'FAK' and tradevol == 0) or \
                   (context.orders[oid]['timecond']== 'FOK' and tradevol < context.orders[oid]['volume']):
                    tradevol = 0
                    context.orders[oid]['cancelvol'] = context.ordere[oid]['leftvol']
                    context.orders[oid]['leftvol'] = 0
                    context.orders[oid]['status'] = 'canceled'

                if tradevol > 0:
                    # print(context.curtime,orderinstid,oid)
                    # tradeinstid = orderinstid
                    trades[oid] = {'tradeprice': tradeprice, 'tradevol': int(tradevol), 'instid': orderinstid}
        except Exception as e:
            print("Failed on matchTrade: ", e.__traceback__.tb_lineno, e)

        return trades

def real_make_order(context, instid, direction, price, volume, ordertype="limit", action="open", closetype='auto',timecond='GFD', autoremake=[0,0,0,0], autocancel=[0,0],accid=-1,father=0):
    '''
    Call this function to make an order
    Paramters
    --------
    context: object
        Context data of this backtest
    direction: int
        Long 1, short -1
    price: float
        The price of this order (except market order)
    volume: int
        The volume of this order
    ordertype: string
        Only support following types: "market" for market orders and "limit" for limit orders.
    action: string
        Only support "open" for open only, "close" for close only.
    closetype: string
        default: 'auto ' for automatic choice
        also could be 'closetoday' or 'closeyesterday' 
    Returns
    -------
    -1 if failed, otherwisa return order oid (>0).

    '''
    #global traderqueue
    #traderqueue = getInstTraderQueue(instid) if context.runmode=='real' else simuqueue
    validtypes = ['limit', 'market']
    validtimeconds = ['GFD', 'FAK', 'FOK']
    validclosetypes = ['auto', 'closetoday', 'closeyesterday']
    validaction = ['open', 'close']  # ['auto','open','close']
    try:
        direction = int(direction)
        volume = int(volume)
    except Exception as e:
        logger.warning("volume/direction must be digits." + str(direction) + '/' + str(volume), e)
        return -1,[]
    if not ordertype in validtypes:
        logger.warning("ordettype must be one of " + str(validtypes) + ",your ordertype:" + str(ordertype))
        return -1,[]
    if not closetype in validclosetypes:
        logger.warning("closetype must be one of " + str(validclosetypes) + ',your closetype:' + str(closetype))
        return -1,[]
    if not timecond in validtimeconds:
        logger.warning("closetype must be one of " + str(validclosetypes) + ',your closetype:' + str(closetype))
        return -1,[]
    if not action in validaction:
        logger.warning("action must be one of " + str(validaction) + ',your action:' + str(action))
        return -1,[]

    if direction == 0:
        logger.warning("Direction can not be zero. your direction: " + str(direction))
        return -1,[]
    if ordertype =='market' and price == 0:
        price = context.getCurrent(instid)
    if volume <= 0 or price <= 0:
        logger.warning("price and volume must be positive . current price:" + str(price) + ',volume:' + str(volume))
        return -1,[]
    if autoremake[0] == 1 and timecond != 'FAK':
        logger.warning(f"FAK track mode 1 must set timecond to FAK but current is {timecond}")
        return -1,[]
    if autoremake[0] == 2 and timecond != 'GFD':
        logger.warning(f"FAK track mode 2 must set timecond to GFD but current is {timecond}")
        return -1,[]

    #if action == 'close' and closetype == 'none':
    #    logger.warning('closetype at close must be close,closetoday or closeyesterday')
    #    return -1

    #if action == 'close' and closetype == 'close':

    #    if instid[-3:] == 'SFE' or instid[-3:] == 'INE':
    #        logger.warning('closetype must be closetoday or closeyesterday for instrument in SFE or INE')
    #        return -1

    classname = getInstClass(instid)
    accid = getInstAccID(instid)[0] if accid < 0 else accid
    if accid >= len(context.accounts):
        accid = len(context.accounts)-1
    traderqueue = getAccidTraderQueue(accid) if context.runmode=='real' else simuqueue    
    #    if soptriskctl.newCount() == -1:
    #        logger.warning("Risk Control: order numbers exceed maxium of a day.")
    #        return -2
    #    elif soptriskctl.newCount() == -2:
    #        logger.warning('Risk Control: order numbers exceed maxium of a second, try later.')
    #        return -3 
        
        
    try:

        status = 'committed'
        errorid = 0
        errormsg = ''
        #leftvol = volume
        cancelvol = 0
        #destprice = price if ordertype == 'limit' else context.getCurrent(instid)
        autoremake += [datetime.now(), 'wait'] 
        autocancel += [datetime.now(), 'wait']
        
        if True: # not context.realTrade:
            ''' #move to simtrader
            margin = context.getMargin(direction>0,volume,instid)
            #print(margin, context.stat.avail, context.stat.balance)
            if context.stat.avail <= margin:
                    status = 'failed'
                    errorid  = 1
                    errormsg = 'Not enough margin.'
                    leftvol = 0
                    cancelvol = volume
                    print("Warning: not enough capital for new order. Current availiable:", context.stat.avail, 'margin:',margin)
            
            if status == 'committed' and action == 'open':
                if direction > 0:
                    context.longpendvol[instid]['poscost'] = getMixPrice(context.longpendvol[instid]['poscost'],context.longpendvol[instid]['volume'],destprice, volume)
                    context.longpendvol[instid]['volume'] +=  volume
                else:
                    context.shortpendvol[instid]['poscost'] = getMixPrice(context.shortpendvol[instid]['poscost'],context.shortpendvol[instid]['volume'],destprice, volume)                            
                    context.shortpendvol[instid]['volume'] += volume
                context.updateFrozenMarg()
'''
        pendvol = 0
        if ordertype == 'limit':
            pendvol = context.getDataSlide(instid,'a1_v') if direction < 0 else context.getDataSlide(instid,'b1_v')
        
        if instid[-3:] == 'CCF':
                ## CCFX order commission
                context.stat.dayfees += 1
                context.stat.totalfees += 1
        context.stat.avail = context.stat.balance - context.marg - context.frozenMarg
        context.stat.dayorders += 1
        
        orderids = []
        if action == 'close' and closetype=='auto':
            dirstr = 'long' if  direction < 0 else 'short'
            yesvol = context.getAccountPosition(instid, dirstr, 'yesvol')
            tvol = context.getAccountPosition(instid, dirstr, 'volume')
            if yesvol > 0:
                if volume > yesvol:
                    closevol = [ min(volume - yesvol, tvol - yesvol), yesvol]
                else:
                    closevol = [ 0, volume]
            else:
                closevol = [min(volume, tvol - yesvol), 0]
            
            ordernum = 2 if closevol[0] != 0 and closevol[1] != 0 else 1
            if ordernum == 1:
                rc = context.accounts[accid].riskctl.make_order(context, volume, instid, price, direction)
                if rc < 0:
                    logger.warning(f"风控模块阻止下单: error code {rc} on {instid} {action} {direction}")
                    return rc,[]
            else:    
                rc = context.accounts[accid].riskctl.make_order(context, closevol[0], instid, price, direction)
                if rc < 0:
                    logger.warning(f"风控模块阻止下单平今: error code {rc} on {instid} {action} {direction}")
                    return rc,[]
            #rc = context.accounts[accid].riskctl.make_order(context, ordernum)
            
            success = 0
            rc = 0
            for i in range(len(closevol)):
                if closevol[i] > 0:
                    rc = context.accounts[accid].riskctl.make_order(context, closevol[i], instid, price, direction)
                    if rc < 0:
                        ctstr = '平今' if i == 0 else '平昨'
                        logger.warning(f"风控模块阻止下单: error code {rc} on {instid} {action} {direction} {ctstr} {closevol[i]}")
                        continue
                    success += 1
                    context.orderid = g_stat.getNewOrderID()
                    closetype = 'closetoday' if i ==0 else 'closeyesterday'
                    temporder = {'instid': instid,
                                 'price': price,
                                 'direction': direction,
                                 'ordertype': ordertype,
                                 'closetype': closetype,
                                 'volume': closevol[i],
                                 'leftvol': closevol[i],
                                 'tradevol': 0,
                                 'cancelvol': cancelvol,
                                 'pendvol': pendvol,
                                 'status': status,
                                 'errorid': errorid,
                                 'errormsg': errormsg,
                                 'action': action,
                                 'timecond': timecond,
                                 'autoremake':autoremake,
                                 'autocancel': autocancel,
                                 'father': father,
                                 'accid':accid}
            
                    context.orders[context.orderid] = temporder
                    temporder['type'] = qetype.KEY_SEND_ORDER
                    temporder['stratName'] = context.stratName
                    temporder['orderid'] = context.orderid
                    orderids.append(context.orderid)
                    traderqueue.put(temporder)
            if success == 0:
                return rc, []
        else:            
            rc = context.accounts[accid].riskctl.make_order(context, volume, instid, price, direction)
            #rc = context.account.riskctl.make_order(context)
            if rc < 0:
                logger.warning(f"风控模块阻止下单: error code {rc} on {instid} {action} {direction}")
                return rc,[]
            context.orderid = g_stat.getNewOrderID()
            temporder = {'instid': instid,
                         'price': price,
                         'direction': direction,
                         'ordertype': ordertype,
                         'closetype': closetype,
                         'volume': volume,
                         'leftvol': volume,
                         'tradevol': 0,
                         'cancelvol': cancelvol,
                         'pendvol': pendvol,
                         'status': status,
                         'errorid': errorid,
                         'errormsg': errormsg,
                         'action': action,
                         'timecond': timecond,
                         'autoremake':autoremake,
                         'autocancel': autocancel,
                         'father': father,
                         'accid':accid}
    
            context.orders[context.orderid] = temporder
            temporder['type'] = qetype.KEY_SEND_ORDER
            temporder['stratName'] = context.stratName
            temporder['orderid'] = context.orderid
            orderids.append(context.orderid)
            traderqueue.put(temporder)
    
        return 0, orderids
    except Exception as e:
        logger.error("Failed on make order: " + str(e), exc_info=True)
        return -1,[]


def real_cancel_order(context, orderid):
    '''
    Paramters
    --------
    context: object
        Context data of this backtest
    orderid: int
        The order oid. if 0 means cancel all orders.
    Returns
    -------
    -1 failed to find orderid
    0 successed

    '''
    #global traderqueue
    traderqueue = None 
   
    try:
        ret = -1
        if orderid == 0:
            #totals = {}
            totalnum = 0
            ret = 0
            context.frozenMarg = 0
            accids = set()
            for oid, order in context.orders.items():
                #for oid in context.orders:
                if context.orders[oid]['leftvol'] > 0:
                    accid = context.orders[oid]['accid']
                    instid = order['instid']
                    totalnum += 1
                    rc = context.accounts[accid].riskctl.cancel_order(context, oid)
                    if rc < 0:
                        ret += rc
                        dirstr = 'long' if context.orders[oid]['direction']>0 else 'short'
                        instid = context.orders[oid]['instid']
                        price = context.orders[oid]['price']
                        logger.warning(f'风控模块阻止撤单: {oid} {instid}')
                        fmarg = context.getMargin(price, dirstr, context.orders[oid]['leftvol'], instid)
                        context.frozenMarg += fmarg
                        continue
                    else:
                        context.orders[oid]['autoremake'][3] = 0 
                        accids.add(accid)
                        if instid[-3:] == 'CCF':
                            ## CCFX cancel commission
                            context.stat.dayfees += 1
                            context.stat.totalfees += 1
                        temporder = {}
                        temporder['type'] = qetype.KEY_CANCEL_ORDER
                        temporder['stratName'] = context.stratName
                        temporder['orderid'] = orderid
                        if context.runmode == 'real':
                                    getAccidTraderQueue(accid).put(temporder)
                        else:
                                    simuqueue.put(temporder)
                        ## set the remake count to zero
            print(context.curtime, 'cancel all order')
            logger.info('cancel all order')
            context.stat.avail = context.stat.balance - context.marg - context.frozenMarg

        else:
            

            if orderid in context.orders.keys():
                instid = context.orders[orderid]['instid']
                accid = context.orders[orderid]['accid']
                rc = context.accounts[accid].riskctl.cancel_order(context, orderid)
                if rc  < 0:
                    logger.warning(f'风控模块阻止撤单 {orderid}: error code:{rc}')
                    return rc
                #if True : #not context.realTrade:
                traderqueue = getAccidTraderQueue(accid)
                #if classname == 'stockoption':
                #    if soptriskctl.newCount() == -1:
                #        logger.warning("Risk Control: order numbers exceed maxium of a day.")
                #        return -2
                #    elif soptriskctl.newCount(1, [orderid]) == -2:
                #        logger.warning('Risk Control: order numbers exceed maxium of a second, try later.')
                #        return -3 
                #elif classname == 'future':
                #    if ctpriskctl.cancelCount() < 0:
                #        logger.warning('Risk Control: cancel numbers exceeed maxium of a day.')
                #        return -2
                
                '''
                if context.orders[orderid]['action'] == 'open':
                    if context.orders[orderid]['direction'] > 0:
                        context.longpendvol[instid]['volume'] = max(
                            context.longpendvol[instid]['volume'] - context.orders[orderid]['leftvol'], 0)
                        if context.longpendvol[instid]['volume'] <= 0:
                            context.longpendvol[instid] = {'volume':0,'poscost':0}
                    else:
                        context.shortpendvol[instid]['volume'] = max(
                            context.shortpendvol[instid]['volume'] - context.orders[orderid]['leftvol'], 0)
                        if context.shortpendvol[instid]['volume'] <= 0:
                            context.shortpendvol[instid] = {'volume':0,'poscost':0}
                    context.updateFrozenMarg()
                '''    
                if not context.realTrade:    
                    context.orders[orderid]['status'] = "canceled" if context.orders[orderid][
                                                                          'status'] != "parttraded" else "ptpc"
                    # part traded part canceled
                    context.orders[orderid]['cancelvol'] = context.orders[orderid]['leftvol']
                    context.orders[orderid]['leftvol'] = 0
                if instid[-3:] == 'CCF':
                    ## CCFX order commission
                    context.stat.dayfees += 1
                    context.stat.totalfees += 1
                context.stat.daycancels += 1
                ret = 0
            if ret == 0 and traderqueue:
                context.stat.avail = context.stat.balance - context.marg - context.frozenMarg
                # context.Cancels[context.curtime] = [orderid, context.stat.daycancels]
                # print(context.Cancels[context.curtime])
                
                ## set the remake count to zero
                #context.orders[orderid]['autoremake'][3] = 0 
                logger.info(f'{ context.orders[orderid]["instid"]} Cancel order:{orderid}')
                print(f'{context.curtime} { context.orders[orderid]["instid"]} Cancel order:{orderid}')
                temporder = {}
                temporder['type'] = qetype.KEY_CANCEL_ORDER
                temporder['stratName'] = context.stratName
                temporder['orderid'] = orderid
                if context.runmode =='real':
                    traderqueue.put(temporder)
                else:
                    simuqueue.put(temporder)
        return ret
    except Exception as e:
        logger.error("Failed on cancel order: ", e.__traceback__.tb_lineno, e)
        return -1


def calculatemul(context):
    letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',\
                 'v', 'w', 'x', 'y', 'z']
    mapDict = {}
    for i in range(len(context.instid)):
        mapDict[letters[i]] = context.getCurrent(context.instid[i])
    # print(context.formula)
    multiresult = eval(context.formula, mapDict)
    # print(multiresult)
    return multiresult

def real_record_hedge_point(context, action, dirstr, volume):
    validaction = ['open', 'close']  # ['auto','open','close']
    valid_direction = ['long', 'short']

    if not action in validaction:
        logger.error("action must be one of " + str(validaction) + ',your action:' + str(action))
        return

    if not dirstr in valid_direction:
        logger.error("action must be one of " + str(valid_direction) + ',your direction:' + str(valid_direction))
        return

    if context.hedgemodel == False:
        return

    d = {}
    d['action'] = action
    d['direction'] = dirstr
    d['volume'] = volume
    d['time'] = context.timedigit
    d['stratName'] = context.stratName
    d['price'] = calculatemul(context)
    #if context.realTrade:
    #    saveHedgePointrealToDB(context.user, context.token, context.stratName, context.timedigit, d)
    #    logger.info('write hedge point to DB')

    #else:
    saveHedgePointToDB(context.user, context.token, context.stratName, context.timedigit, d)
    logger.info('write hedge point to DB')
    return




def test_make_order(context, instid, direction, price, volume, ordertype="limit", action="open", closetype='auto', timecond = 'GFD'):
    '''
    Call this function to make an order
    Paramters
    --------
    context: object
        Context data of this backtest
    direction: int
        Long 1, short -1
    price: float
        The price of this order (except market order)
    volume: int
        The volume of this order
    ordertype: string
        Only support following types: "market" for market orders and "limit" for limit orders.
    action: string
        Only support "open" for open only, "close" for close only.
    closetype: string
        default: 'auto' for automatic match
        also could be 'closetoday' or 'closeyesterday'
    Returns
    -------
    -1 if failed, otherwisa return order oid (>0).

    '''
    # print(1)
    validtypes = ['limit', 'market']
    validclosetypes = ['auto', 'closetoday', 'closeyesterday'] 
    validtimeconds = ['GFD', 'FAK', 'FOK']
    validaction = ['open', 'close']
    

    try:
        direction = int(direction)
        volume = int(volume)
        # print(direction,volume)
        # print(instid)
    except Exception as e:
        logger.error(f"volume/direction must be digits.,{direction},{volume}, {e}")
        return -1,[]
    if not ordertype in validtypes:
        logger.warning(f"ordettype must be one of {validtypes}, your ordertype:{ordertype}")
        return -1,[]
    if not action in validaction:
        logger.warning(f"action must be one of {validaction},your action:{ action}")
        return -1,[]
    if not closetype in validclosetypes:
        logger.warning(f"action must be one of {validclosetypes},your action:{ closetype}")
        return -1,[]
    if not timecond in validtimeconds:
        logger.warning("closetype must be one of " + str(validclosetypes) + ',your closetype:' + str(closetype))
        return -1,[]
    if direction == 0:
        logger.warning(f"Direction can not be zero. your direction: {direction}")
        return -1,[]
    if ordertype =='market' and price == 0:
        price = context.getCurrent(instid)
    if volume <= 0 or price <= 0:
        logger.warning(f"price and volume must be positive . current price:{price}, volume:{volume},instid:{instid}")
        return -1,[]
    
    #if action == 'close' and closetype=='none':
    #        logger.warning('closetype must be close,closetoday or closeyesterday if action=close')
    #        return -1
        
    #if action == 'close' and closetype=='close':
        
    #    if instid[-3:] == 'SFE' or instid[-3:] == 'INE':
    #        logger.warning('closetype must be closetoday or closeyesterday for instrument in SFE or INE')      
    #        return -1
        

    try:
        status = 'committed'
        errorid = 0
        errormsg = ''
        leftvol = volume
        cancelvol = 0
        destprice = price if ordertype=="limit" else context.getCurrent(instid)
        if action == "open":
            
            margin = context.getMargin(destprice, direction > 0, volume, instid)
            # print(margin, context.stat.avail, context.stat.balance)
            if context.stat.avail <= margin:
                status = 'failed'
                errorid = 1
                errormsg = '资金不足.'
                leftvol = 0
                cancelvol = volume
                logger.warning(f"Warning: 资金不足，目前可用权益:{context.stat.avail}, 需要保证金:{margin}")
            
        elif action == "close":
            dirstr = 'short' if  direction > 0 else 'long'
            pend = context.calcFrozenVol(instid,direction)
            pos = context.position[instid][dirstr]['volume']
            leftvol = pos - pend
            if volume > leftvol:
                status = 'failed'
                errorid = 1
                errormsg = '可平持仓不足.'
                leftvol = 0
                cancelvol = volume
                logger.warning(f"Warning: 可平持仓不足. 目前持仓:{pos}, 冻结持仓:{pend}")
                #elif instid in context.frozenVol:
                #    context.frozenVol[instid]['short'] += volume;
                #else:
                #    context.frozenVol[instid] = {"long":0, "short":volume}


                    
        if errorid == 0:
            if status == 'committed' and action == 'open':
                '''
                if direction > 0:
                    context.longpendvol[instid]['poscost'] = getMixPrice(context.longpendvol[instid]['poscost'],context.longpendvol[instid]['volume'],destprice, volume)
                    context.longpendvol[instid]['volume'] +=  volume
                else:
                    
                    context.shortpendvol[instid]['poscost'] = getMixPrice(context.shortpendvol[instid]['poscost'],context.shortpendvol[instid]['volume'],destprice, volume)                            
                    context.shortpendvol[instid]['volume'] += volume
                '''    
            context.updateFrozenMarg()
            context.stat.avail = context.stat.balance - context.marg - context.frozenMarg
    
        if context.datamode == 'tick':
            pendvol = context.dataslide[instid]['a1_v'] if direction < 0 else context.dataslide[instid]['b1_v']
        else:
            pendvol = 0
        if errorid == 0 and context.instid[-3:] == 'CCF':
            ## CCFX order commission
            context.stat.dayfees += 1
            context.stat.totalfees += 1
            
        context.stat.dayorders += 1
        
        
        orderids = []
        
        if action =='close' and closetype=='auto' and errorid == 0:
            dirstr = 'long' if  direction < 0 else 'short'
            yesvol = context.getAccountPosition(instid, dirstr, 'yesvol')
            tvol = context.getAccountPosition(instid, dirstr, 'volume')
            if yesvol > 0:
                if volume > yesvol:
                    closevol = [ min(volume - yesvol, tvol - yesvol), yesvol]
                else:
                    closevol = [ 0, volume]
            else:
                closevol = [min(volume, tvol - yesvol), 0]
        
            for i in range(len(closevol)):
                if closevol[i] > 0:
                    context.orderid += 1
                    # pendvol = 0
                    # if ordertype == 'limit':
                    closetype = 'closetoday' if i == 0 else 'closeyesterday'    
                    context.orders[context.orderid] = {'instid': instid,
                                                       'time': context.curtime,
                                                       'price': price,
                                                       'direction': direction,
                                                       'ordertype': ordertype,
                                                       'closetype': closetype,
                                                       'volume': closevol[i],
                                                       'leftvol': leftvol,
                                                       'tradevol': 0,
                                                       'cancelvol': cancelvol,
                                                       'pendvol': pendvol,
                                                       'status': status,
                                                       'errorid': errorid,
                                                       'errormsg': errormsg,
                                                       'timecond': timecond,
                                                       'action': action, }
                    orderids.append(context.orderid)
        else:
            context.orderid += 1
            # pendvol = 0
            # if ordertype == 'limit':
            context.orders[context.orderid] = {'instid': instid,
                                               'time': context.curtime,
                                               'price': price,
                                               'direction': direction,
                                               'ordertype': ordertype,
                                               'closetype': closetype,
                                               'volume': volume,
                                               'leftvol': leftvol,
                                               'tradevol': 0,
                                               'cancelvol': cancelvol,
                                               'pendvol': pendvol,
                                               'status': status,
                                               'errorid': errorid,
                                               'errormsg': errormsg,
                                               'timecond': timecond,
                                               'action': action, }
            orderids.append(context.orderid)
        #context.ROrders[context.curtime] = [context.orderid, price, direction, volume, ordertype, closetype, action,
        #                                    errorid, errormsg]
        # print(context.ROrders[context.curtime])
        #print('make_order',volume, action,closetype,leftvol)
        return 0,orderids
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Failed on make order: {e.__traceback__.tb_lineno}, {e}")
        return -1,[]


def test_cancel_order(context, orderid):
    '''
    Paramters
    --------
    context: object
        Context data of this backtest
    orderid: int
        The order oid. if 0 means cancel all orders.
    Returns
    -------
    -1 failed to find orderid
    0 successed

    '''
    try:
        ret = -1
        if orderid == 0:
            ordernum = len(context.orders)
            #context.orders[orderid] = {}
            context.frozenMarg = 0
            #for instid in context.instid:
            #    context.longpendvol[instid] = {'volume':0,'poscost':0}
            #    context.shortpendvol[instid] = {'volume':0,'poscost':0}
            for orderid in context.orders.keys():
                inst = context.orders[orderid]['instid']
                if inst[-3:] == 'CCF':
                    ## CCFX cancel commission
                    context.stat.dayfees += 1
                    context.stat.totalfees += 1
                context.orders[orderid]['status'] = "canceled" if context.orders[orderid][
                                                                      'status'] != "parttraded" else "ptpc"
                # part traded part canceled
                context.orders[orderid]['cancelvol'] = context.orders[orderid]['leftvol']
                context.orders[orderid]['leftvol'] = 0
            ret = 0
            context.stat.daycancels += ordernum

        if orderid in context.orders.keys():
            inst = context.orders[orderid]['instid']
            '''
            if context.orders[orderid]['action'] == 'open':
                if context.orders[orderid]['direction'] > 0:
                    context.longpendvol[inst]['volume'] = max(context.longpendvol[inst]['volume'] - context.orders[orderid]['leftvol'], 0)
                    if context.longpendvol[inst]['volume'] <= 0:
                        context.longpendvol[inst] = {'volume':0, 'poscost':0}
                else:
                    context.shortpendvol[inst]['volume'] = max(context.shortpendvol[inst]['volume'] - context.orders[orderid]['leftvol'], 0)
                    if context.shortpendvol[inst]['volume'] <= 0:
                        context.shortpendvol[inst] = {'volume':0, 'poscost':0}
            '''
            context.updateFrozenMarg()
            context.orders[orderid]['status'] = "canceled" if context.orders[orderid][
                                                                  'status'] != "parttraded" else "ptpc"
            # part traded part canceled
            context.orders[orderid]['cancelvol'] = context.orders[orderid]['leftvol']
            context.orders[orderid]['leftvol'] = 0
            if context.instid[-3:] == 'CCF':
                ## CCFX order commission
                context.stat.dayfees += 1
                context.stat.totalfees += 1
            ret = 0
            context.stat.daycancels += 1
        if ret == 0:
            context.stat.avail = context.stat.balance - context.marg - context.frozenMarg
            context.Cancels[context.curtime] = [orderid, context.stat.daycancels]
            # print(context.Cancels[context.curtime])
        return ret
    except Exception as e:
        logger.error(f"Failed on cancel order: {e.__traceback__.tb_lineno},{e}")
        return -1


def test_record_hedge_point(context, action, dirstr, volume):
    validaction_action = ['open', 'close']  # ['auto','open','close']

    if not action in validaction_action:
        print("action must be one of " + str(validaction_action) + ',your action:' + str(action))
        return

    validcation_dir = ['long', 'short']

    if not dirstr in validcation_dir:
        print('direction must be one of ' + str(validcation_dir) + ',your action' + str(dirstr))

    letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',\
                 'v', 'w', 'x', 'y', 'z']
    mapDict = {}
    for i in range(len(context.instids)):
        inst = context.instids[i]
        mapDict[letters[i]] = context.dataslide[inst]['current'] if context.datamode == 'tick' else context.dataslide[inst]['close']
        
        
    current = eval(context.formula, mapDict)
    if  not context.curtime in context.d.index:
        context.d.loc[context.curtime, 'openlong'] = current if action=='open' and dirstr=='long' else np.nan
        context.d.loc[context.curtime, 'closelong'] = current if action=='close' and dirstr=='long' else np.nan
        context.d.loc[context.curtime, 'openshort'] = current if action=='open' and dirstr=='short' else np.nan
        context.d.loc[context.curtime, 'closeshort'] = current if action=='close' and dirstr=='short' else np.nan
    else:
        if action=='open' and dirstr=='long':
            context.d.loc[context.curtime, 'openlong'] = current  
        if action=='close' and dirstr=='long' :
            context.d.loc[context.curtime, 'closelong'] = current  
        if action=='open' and dirstr=='short' :
            context.d.loc[context.curtime, 'openshort'] = current 
        if action=='close' and dirstr=='short' :
            context.d.loc[context.curtime, 'closeshort'] = current  


def cancel_order(context, orderid):
    if context.runmode =='test':
        return test_cancel_order(context,orderid)
    else:
        return real_cancel_order(context,orderid)
        
        
def make_order(context, instid, direction, price, volume, ordertype="limit", action="open", closetype='auto', timecond='GFD', autoremake=[0,0,0,0], autocancel=[0,0], accid=-1,father=0):
    
    if context.runmode =='test':
        return test_make_order(context, instid, direction, price, volume, ordertype, action,closetype, timecond)
    else:
        return real_make_order(context, instid, direction, price, volume, ordertype,action,closetype,timecond, autoremake, autocancel, accid=accid,father=father)
        

def get_bar(context, freq, count=None):
    if context.runmode == 'test':
        return test_get_bar(context, freq, count)
    else:
       return real_get_bar(context,freq, count)
        


def test_get_bar(context, freq, count=None):
    if hasattr(context, 'bardata'):
        data = context.bardata
        if freq % context.freq != 0 or freq == 1:
            ### do not resample
            if count:
                for inst in data:
                    df = data[inst] 
                    if 'time' in df.columns:
                        del df['time']

                    data[inst]=df.dropna(how='all').iloc[-count:,]
            #del data['time']
            return data
        else:
            f=str(freq)+'min'
            
            for instid in data:
                try:
                    df=data[instid]
                    if len(df) > 0:
                        #print(df.time)
                        #df['runtime']= pd.to_datetime(df.time, format='%Y%m%d%H%M%S',errors='ignore')
                        #df.set_index(["runtime"], inplace=True)
   
                        df2 = pd.DataFrame(columns=df.columns)
                        #print('111',df2)
                        for col in df.columns:
                            tmp = pd.Series(index=df.index, data=df.loc[:,col])
                            if col == "open":
                                tmp=df[col].resample(f, label='right', closed='right').first()
                            elif col =="close":
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'high':
                                tmp=df[col].resample(f, label='right', closed='right').max()
                            elif col == 'low':
                                tmp=df[col].resample(f, label='right', closed='right').min()
                            elif col == 'volume':
                                tmp=df[col].resample(f, label='right', closed='right').sum()
                            elif col == 'money':
                                tmp=df[col].resample(f, label='right', closed='right').sum()
                            elif col == 'position':
                                tmp = df[col].resample(f, label='right', closed='right').last()
                            elif col == 'presett':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'preclose':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'lowerlimit':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'upperlimit':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'tradingday':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            df2.loc[:,col] = tmp
                        #print(df2)
                        if 'time' in df2.columns:
                            del df2['time']
                        if isinstance(count, int):
                            data[instid]=df2.dropna(how='any').iloc[-count:,]
                        else:
                            data[instid]=df2.dropna(how='any')
                except Exception as e:
                    print("get_bar Error:", e.__traceback__.tb_lineno,e)
                
            return data
    else:
        return None

    

def real_get_bar(context, freq, count=None):
    data=get_bar_data(context)
    #print(data )
    if data:
        try:
            f=str(freq)+'min'
            for instid in data.keys():  
                df=data[instid]
                if len(df) > 0:
                    #print(df.time)
                    df['runtime']= pd.to_datetime(df.index, format='%Y%m%d%H%M%S',errors='ignore')
                    #for i in range(len(df['time'])):
                    #    df['runtime'].loc[i]=datetime.datetime.strptime(str(df['time'].loc[i]), "%Y%m%d%H%M%S")
                    df.set_index(["runtime"], inplace=True)
                    #print(df)
                    if f=='1min':
                        if 'time' in data[instid].columns:
                            del data[instid]['time']
                        if count and isinstance(count, int):
                            
                            data[instid]=data[instid].iloc[-count:,]
                            
                    else:

                        df2 = pd.DataFrame(columns=df.columns)
                        #print('111',df2)
                        for col in df.columns:
                            tmp = pd.Series(index=df.index, data=df.loc[:,col])
                            if col == "open":
                                tmp=df[col].resample(f, label='right', closed='right').first()
                            elif col =="close":
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'high':
                                tmp=df[col].resample(f, label='right', closed='right').max()
                            elif col == 'low':
                                tmp=df[col].resample(f, label='right', closed='right').min()
                            elif col == 'volume':
                                tmp=df[col].resample(f, label='right', closed='right').sum()
                            elif col == 'money':
                                tmp=df[col].resample(f, label='right', closed='right').sum()
                            elif col == 'position':
                                tmp = df[col].resample(f, label='right', closed='right').last()
                            elif col == 'presett':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'preclose':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'lowerlimit':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'upperlimit':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            elif col == 'tradingday':
                                tmp=df[col].resample(f, label='right', closed='right').last()
                            df2.loc[:,col] = tmp
                        #print(df2)
                        if 'time' in df2.columns:
                            del df2['time']
                        if isinstance(count, int):
                            data[instid]=df2.dropna(how='any').iloc[-count:,]
                        else:
                            data[instid]=df2.dropna(how='any')
        except Exception as e:
            print("get_bar Error:", e.__traceback__.tb_lineno,e)

        #print(df2.head())
    return data


def force_close(context):
    fcDict = context.fcDict
    for inst in fcDict:
        fclist = fcDict[inst]
        if fclist[0] > 0:
            make_order(context, inst, -1, context.getCurrent(inst),fclist[0],'market', 'close', 'closeyesterday')
        if fclist[1] > 0:
            make_order(context, inst, 1, context.getCurrent(inst),fclist[1],'market', 'close', 'closeyesterday')
        if fclist[2] > 0:    
            make_order(context, inst, -1, context.getCurrent(inst),fclist[2],'market', 'close', 'closetoday')
        if fclist[3] > 0:
            make_order(context, inst, 1, context.getCurrent(inst),fclist[3],'market', 'close', 'closetoday')
        




class testContext(object):
    instid = []
    def __init__(self):
        pass
        
def record_hedge_point(context, action, dirstr, volume):
    if context.runmode=='test':
        test_record_hedge_point(context, action, dirstr, volume)
    else:
        real_record_hedge_point(context, action, dirstr, volume)        
        

def reqCtpLogout(context,accid=0):
    from .qectpmarket_wrap import marketLogout 
    marketLogout()
    traderqueue = getAccidTraderQueue(accid)
    temporder = {}
    temporder['type'] = qetype.KEY_USER_LOGOUT
    traderqueue.put(temporder)
    
    