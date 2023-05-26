# -*- coding: utf-8 -*-
"""
Created on Wed Nov  3 11:22:54 2021

@author: ScottStation
"""
from .qelogger import logger
import qesdk
import redis
import json
import pandas as pd
import datetime
import pickle
import zlib
from .qeglobal import getExemode, dbconfig

remote_db = {'ip':'data.quantease.store', 'port': 9019}
local_db = {'ip':'192.168.123.188', 'port':58002}

dbip =  remote_db['ip'] if dbconfig['ip'] == remote_db['ip'] else local_db['ip']
dbport = remote_db['port'] if dbconfig['ip'] == remote_db['ip'] else local_db['port']


redis_config = {'host':'127.0.0.1', 'port':6379, 'passwd':''}


myredis = None
redisconn = None

try:
    from  .qedbconfig import  redis_server
    redis_config = {**redis_config, **redis_server}
except ImportError:
    try:
        from .qedockerconfig import redis_server
        redis_config = {**redis_config, **redis_server}
    except:
        from .qesysconf import read_sysconfig
        sysconfig = read_sysconfig()
        redis_server = sysconfig['redis']
        redis_config = {**redis_config, **redis_server}
if redis_config['host']=="docker":
    try:
        with open("/srv/jupyterhub/dockerhost",'r') as f:
            hoststr =(f.read())
            hoststr =hoststr.replace('\n','')
            redis_config['host'] = hoststr
    except:
        pass
    
from functools import wraps
auth_checked = False
def check_auth(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        global auth_checked
        if not auth_checked:
            qesdk.auth('quantease','$1$$k7yjPQKv8AJuZERDA.eQX.')
            auth_checked = True
        return func(*args, **kwargs)
    return _wrapper

    
    
def initMyredis():
    global myredis
    #print(redis_config)
    try:
        if not getExemode():    
            #print('redisconfig',redis_config)
            pool = redis.ConnectionPool(host=redis_config['host'], port=redis_config['port'], password=redis_config['passwd'], db=0, decode_responses=True)
            myredis = redis.Redis(connection_pool=pool)
            myredis.set('hello','world')
        else:
            #print('exemode is on ')
            redis_config['port'] = 6379
            pool = redis.ConnectionPool(host=redis_config['host'], port=redis_config['port'], db=0, decode_responses=True)
            myredis = redis.Redis(connection_pool=pool)
        return True    
    except Exception as e:
        print("连接Redis数据库pool失败,请检查Redis-server服务是否已经安装并启动，端口是否配置正确.")
        print(f'{e}')
        return False
    
def initRedisconn():
    global redisconn
    try:
        if not getExemode():    
            redisconn = redis.StrictRedis(host=redis_config['host'], port=redis_config['port'], password=redis_config['passwd'], db=0)
        else:
            #print('exemode is on ')
            redis_config['port'] = 6379
            redisconn = redis.StrictRedis(host=redis_config['host'], port=redis_config['port'], db=0)
        return True    
    except Exception as e:
        print(f'连接Redis数据库pool失败,请检查Redis-server服务是否已经安装并启动，其IP/端口是否配置正确:{e}')         
        return False
# pool = redis.ConnectionPool(host='127.0.0.1', port=6388, password='Qs201689$', db=0, decode_responses=True)
# myredis = redis.Redis(connection_pool=pool)
from functools import wraps
def check_redisconn(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        global redisconn
        if redisconn is None:
            if initRedisconn():
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return _wrapper

def check_myredis(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        global myredis
        if myredis is None:
            if initMyredis():
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return _wrapper


@check_myredis
def saveMarketToDB(instid, time, datastr):
    additem = {datastr: int(time)}
    myredis.zadd('sysgen_mdata_' + instid, additem)

@check_myredis
def resetMarketData(instid, before_time):
    #myredis.delete('sysgen_mdata_' + instid)
    myredis.zremrangebyscore('sysgen_mdata_' + instid, 0, before_time)

@check_myredis
def saveOrderDataToDB(userid,token, day, d):
    #global KEY_COLLECTION
    
    datastr = json.dumps(d)
    #print(d)
    orderid = d['orderid']
    myredis.hset('sysgen_order_' + str(userid)+'_'+token+'_'+str(day), str(orderid), datastr)
    #additem = {datastr: int(time)}
    #myredis.zadd(, additem)


#     print('sysgen_test18_order_'+str(userid)+'_'+str(stratName))
#     myredis.zadd('sysgen_'+KEY_COLLECTION+ '_order_'+str(userid)+'_'+str(stratName), additem)
@check_myredis
def saveTradeDataToDB(userid,token, day, d):
    datastr = json.dumps(d)
    orderid = d['tradeid']
    myredis.hset('sysgen_trade_' + str(userid)+'_'+token+'_'+str(day), str(orderid), datastr)
    
    #additem = {datastr: int(time)}
    #myredis.zadd('sysgen_tradeDB1_trade_' + str(userid), additem)
#     print('sysgen_test18_trade_'+str(userid)+'_'+str(stratName))
@check_redisconn
def saveStatDataToDB(user, token, df):
    key = 'sysgen_stat_'+user+'_'+token
    redisconn.set(key, zlib.compress(pickle.dumps(df)))

@check_myredis
def saveStatCurrentToDB(user, token, d):
    key = 'sysgen_statcur_'+user+'_'+token
    myredis.set(key, json.dumps(d))

@check_myredis
def saveSettingDataToDB(userid, token, stratsetts):
    datastr = json.dumps(stratsetts, ensure_ascii=False)
    myredis.set('sysgen_setting_' + str(userid)+'_'+token, datastr)

@check_myredis
def saveImageSettingDataToDB(userid, imagesetts):
    datastr = json.dumps(imagesetts)
    myredis.set('sysgen_test19_image_setting_' + str(userid), datastr)
@check_myredis    
def removeDBSimuAccounts(user, tlist):
    if len(tlist) == 0:
        return 
    for t in tlist:
        removePositionData(user, t)
        removeAccountData(user, t)
        orderlist = myredis.keys('sysgen_order_' + str(user)+'_'+t+'_*')
        for order in orderlist:
            myredis.delete(order)
        tradelist =  myredis.keys('sysgen_trade_' + str(user)+'_'+t+'_*')
        for trade in tradelist:
            myredis.delete(trade)
            
        ## remove trades, orders, position and accountdata of token 
    ## remove token from tokenlist
    tokenlist = loadSimuAccounts(user)
    tokenlist = [token for token  in tokenlist if not token in tlist ]
    myredis.set("sysgen_simuaccounts_"+user, json.dumps(tokenlist))
    
@check_myredis    
def saveNewAccountToDB(user, token):
    res = myredis.get("sysgen_simuaccounts_"+user)
    if res:
        tokenlist = json.loads(res)
        if not token in tokenlist:
            tokenlist.append(token)
    else:
        tokenlist = [token]
    myredis.set("sysgen_simuaccounts_"+user, json.dumps(tokenlist))    
        
#def saveSettingDataToDBReal(userid, stratsetts):
    #datastr = json.dumps(stratsetts)
    #myredis.set('sysgen_real1_setting_' + str(userid), datastr)    





#def loadSettingDataReal(userid):
   # userdata = myredis.get('sysgen_real1_setting_' + str(userid))
    #if userdata:
     #   return json.loads(userdata)
    #else:
        #logger.error('请先运行策略模拟交易程序startSimuProcess使用用户名跑一个空的qeBaseStrat（不做任何交易）。')
        #return None    
@check_myredis
def saveHedgeMarketToDB(userid, stratName, instid_hedge, time, tickdata):
    datastr = json.dumps(tickdata)
    additem = {datastr: int(time)}
    myredis.zadd('sysgen_hedgedata1_' + str(userid) + '_' + str(stratName) + '_' + instid_hedge, additem)
@check_myredis
def savePositionDataToDB(userid, token, d):
    # parameter 2
    try:

        if len(d) > 0:
            datastr = json.dumps(d)
            myredis.set('sysgen_position_'+str(userid)+'_'+token, datastr)
        #                 print('sysgen_test18_position_'+str(userid)+'_'+str(stratName))
    except Exception as e:
        logger.error(f"Failed on position writeDB: {e}", exc_info=True)

@check_myredis
def removePositionData(user, token):
    myredis.delete('sysgen_position_'+str(user)+'_'+token)    
@check_myredis
def saveTradingDay(user, token, tradingday):
    myredis.set('sysgen_tradingday_'+str(user)+'_'+str(token), tradingday)

@check_myredis
def savePidToDB(user, token, pid):
    myredis.set('sysgen_pid_'+str(user)+'_'+str(token), str(pid))
@check_myredis
def saveStrategyContextToDB(userid, stratName, day, context):
    try:

        d = {}
        d['trading_day'] = day
        d['strategy'] = stratName        
       
        d['posProf'] = str(round(context.posProf,3))
        d['frozenMarg'] = str(round(context.frozenMarg,3))
        d['marg'] = str(round(context.marg,3))
        d['closeProf'] = str(round(context.closeProf,3))
        d['balance'] = str(round(context.stat.balance,3))
        d['avail'] = str(round(context.stat.avail,3))
        d['totalpnl'] = str(round(context.stat.totalpnl,3))
        d['totalfee'] = str(round(context.stat.totalfees,3))
        d['daypnl'] = str(round(context.stat.daypnl,3))
        d['dayfee'] = str(round(context.stat.dayfees,3))
        
        #         d['initcapital'] = context.initCapital
        # d['curpnl'] = context.curpnl
        #d['posProf'] = context.posProf
        #d['frozenMarg'] = context.frozenMarg
        #d['marg'] = context.marg
        #d['closeProf'] = context.closeProf
        #d['balance'] = context.stat.balance
        #d['avail'] = context.stat.avail
        #d['totalpnl'] = context.stat.totalpnl
        #d['totalfees'] = context.stat.totalfees
        #d['daypnl'] = context.stat.daypnl
        #d['dayfees'] = context.stat.dayfees

        count = 0
        if len(context.position) > 0:
            for instid in context.position.keys():
                count += (context.position[instid]['long']['volume'] + context.position[instid]['short']['volume'])

        d['grossCount'] = str(int(count))

        '''
        d['long_volume'] = context.position['long']['volume']
        d['long_poscost'] = context.position['long']['poscost']
        d['long_yesvol'] = context.position['long']['yesvol']
        d['short_volume'] = context.position['short']['volume']
        d['short_poscost'] = context.position['short']['poscost']
        d['short_yesvol'] = context.position['short']['yesvol']
        '''
        datastr = json.dumps(d)
        myredis.hset('sysgen_contextDB5_context_'+str(userid), str(day) + '-' + str(stratName), datastr)
    #         print('sysgen_test18_context_'+str(userid)+'_'+str(stratName))
    except Exception as e:
        logger.error(f"Failed on context writeDB: {e}", exc_info=True)

@check_myredis
def saveStrategyfreqToDB(userid, token, d):
    try:
        datastr = json.dumps(d)
        myredis.set('sysgen_freqDB6_'+str(userid)+'_'+str(token), datastr)
    #         print('sysgen_test18_context_'+str(userid)+'_'+str(stratName))
    except Exception as e:
        logger.error(f"Failed on context writeDB: {e}", exc_info=True)
@check_myredis
def getDBfreqData(userid, token):
    ret = myredis.get('sysgen_freqDB6_'+ str(userid)+'_'+str(token))
    if ret:
        return json.loads(ret)
@check_myredis
def loadTradingDay(user, token):
    return myredis.get('sysgen_tradingday_'+str(user)+'_'+str(token))

@check_myredis
def loadDBPid(user, token):
    return myredis.get('sysgen_pid_'+str(user)+'_'+str(token))

@check_myredis
def delDBPid(user, token):
    myredis.delete('sysgen_pid_'+str(user)+'_'+str(token))

@check_myredis       
def saveAccountDataToDB(userid, token, d):
    try:
        #         d = {}
        #         d['timedigit'] = time
        #         d['posProf'] = account.posProf
        #         d['frozenMarg'] = account.frozenMarg
        #         d['marg'] = account.marg
        #         d['closeProf'] = account.closeProf
        #         d['balance'] = account.balance
        #         d['avail'] = account.avail
        #         d['totalpnl'] = account.totalpnl
        #         d['totalfee'] = account.totalfees
        #         d['daypnl'] = account.daypnl
        #         d['dayfee'] = account.dayfees

        datastr = json.dumps(d)
        myredis.set('sysgen_account_'+str(userid)+'_'+token, datastr)
    #         print('sysgen_test18_account_'+str(userid)+'_'+str(stratName))
    except Exception as e:
        print("Failed on account writeDB: ", e.__traceback__.tb_lineno, e)

@check_myredis
def removeAccountData(user, token):
    myredis.delete('sysgen_account_'+str(user)+'_'+token)

@check_myredis
def updateInitCap(userid, balance):
    myredis.set('sysgen_test19_capital_' + userid, str(round(balance, 2)))

@check_myredis
def saveHedgePointToDB(userid, token, stratName, time, d):
    datastr = json.dumps(d)
    additem = {datastr: int(time)}
    myredis.zadd('sysgen_test19_hedgepoint_' + str(userid) + '_' + str(token)+ '_' + str(stratName), additem)

@check_myredis
def saveFormulaDataToDB(userid, token, strats_formula):
    datastr = json.dumps(strats_formula)
    myredis.set('sysgen_formual_' + str(userid)+'_'+str(token), datastr)

@check_myredis
def loadSettingData(userid,token):
    userdata = myredis.get('sysgen_setting_' + str(userid)+'_'+str(token))
    if userdata:
        return json.loads(userdata)
    else:
        #logger.error('请先运行策略模拟交易程序startSimuProcess。')
        return None

@check_myredis
def loadForumalgData(userid,token):
    userdata = myredis.get('sysgen_formual_' + str(userid)+'_'+str(token))
    if userdata:
        return json.loads(userdata)
    else:
        #logger.error('请先运行策略模拟交易程序startSimuProcess使用用户名跑一个空的qeBaseStrat（不做任何交易）。')
        return None

@check_redisconn
def loadDBStatData(user, token):
    res = redisconn.get('sysgen_stat_'+user+'_'+token)
    if res:
        return pickle.loads(zlib.decompress(res))

@check_myredis
def loadDBStatCurrent(user, token):
    key = 'sysgen_statcur_'+user+'_'+token
    ret = myredis.get(key)
    if ret:
        return json.loads(ret)

@check_myredis
def loadImageSettingData(userid):
    userdata = myredis.get('sysgen_test19_image_setting_' + str(userid))
    if userdata:
        return json.loads(userdata)
    else:
        #logger.error('请先运行策略模拟交易程序startSimuProcess。')
        return None

@check_myredis
def getDBHedgePoint(userid, token, stratName, fromtime, endtime):
    return myredis.zrangebyscore('sysgen_test19_hedgepoint_' + str(userid) + '_' +str(token) + '_' + str(stratName), fromtime, endtime,
                                 withscores=True)

@check_myredis
def getDBMarketData(instid, fromtime,endtime= 302112021015560000):
    return myredis.zrangebyscore('sysgen_mdata_' + instid, fromtime, endtime, withscores=True)

@check_myredis
def getDBMarketData1(instid, fromtime,start=0,num=15000,endtime= 302112021015560000):
    return myredis.zrangebyscore('sysgen_mdata_' + instid, fromtime, endtime,start=start,num=num ,withscores=True)

#def getDBOrderData(userid, fromtime, endtime):
#    return myredis.zrangebyscore('sysgen_orderDB2_order_' + userid, fromtime, endtime, withscores=True)
@check_myredis
def getDBOrderData(userid, token, day):
    return myredis.hgetall('sysgen_order_' + str(userid)+'_'+token+'_'+str(day))

@check_myredis
def getDBTradeData(userid, token, day):
    #return myredis.zrangebyscore('sysgen_tradeDB1_trade_' + userid, fromtime, endtime, withscores=True)
    return myredis.hgetall('sysgen_trade_' + str(userid)+'_'+token+'_'+str(day))


@check_myredis
def getDBPositionData(userid,token):
    return myredis.get('sysgen_position_'+str(userid)+'_'+token)


# def getDBPositionData_past(userid,fromtime,endtime):
#     return myredis.zrangebyscore('sysgen_test19_position_'+userid, fromtime, endtime ,withscores=True)
@check_myredis
def getDBAccountData(userid, token):
    return myredis.get('sysgen_account_'+str(userid)+'_'+token)

@check_myredis
def getDBContextData(userid, stratName, day):
    return myredis.hget('sysgen_contextDB5_context_'+ str(userid), str(day) + '-' + str(stratName))


# def getDBPositionDataLast(userid):
#     return myredis.zrange('sysgen_test19_position_'+userid, start=-1,end=-1)

# def getDBAccountDataLast(userid):
#     return myredis.zrange('sysgen_test19_account_'+userid,  start=-1,end=-1)

# def getDBContextDataLast(userid,stratName):
#     return myredis.zrange('sysgen_test19_context_'+userid+'_'+stratName,  start=-1,end=-1)
@check_myredis
def getSimuInitCap(userid):
    if myredis.exists('sysgen_test19_capital_' + userid):
        return myredis.get('sysgen_test19_capital_' + userid)
    else:
        return None

@check_myredis
def loadSimuAccounts(user):
    res = myredis.get("sysgen_simuaccounts_"+user)
    if res:
        tlist = json.loads(res)
        return tlist
    
def isTokenValid(user, token):
    tlist = loadSimuAccounts(user)
    if tlist:
        return token in tlist
    else:
        return False


@check_myredis
def getDBHedgeMarketData(userid, stratName, instid_hedge, fromtime,endtime=302112021015560000):
    return myredis.zrangebyscore('sysgen_hedgedata1_' + str(userid) + '_' + str(stratName) + '_' + instid_hedge,
                                 fromtime, endtime, withscores=True)
@check_myredis
def getDBHedgeMarketData1(userid, stratName, instid_hedge, fromtime,start=0,num=15000,endtime=302112021015560000):
    return myredis.zrangebyscore('sysgen_hedgedata1_' + str(userid) + '_' + str(stratName) + '_' + instid_hedge,
                                 fromtime, endtime,start=start,num=num, withscores=True)
####################For real trade##########################################
#=====================================================================================real
@check_myredis
def saveOrderDatarealToDB(userid,investor, day, d):
    #global KEY_COLLECTION
    datastr = json.dumps(d)
    #additem = {datastr: int(time)}
    #myredis.zadd('sysgen_realDB2_order_' + str(userid), additem)
    #print('11',d)
    #print(datastr)
    orderid = d['orderid']
    #print(day)
    myredis.hset('sysgen_realDB2_order_' + str(userid)+'_'+investor+'_'+str(day), str(orderid), datastr)


#     print('sysgen_test18_order_'+str(userid)+'_'+str(stratName))
#     myredis.zadd('sysgen_'+KEY_COLLECTION+ '_order_'+str(userid)+'_'+str(stratName), additem)
@check_myredis
def delDBOrderDataReal(userid, investor, day):
    myredis.delete('sysgen_realDB2_order_' + str(userid)+'_'+investor+"_"+str(day))
@check_myredis
def saveTradeDatarealToDB(userid, investor, day, d):
    datastr = json.dumps(d)
    #additem = {datastr: int(time)}
    #myredis.zadd('sysgen_realDB2_trade_' + str(userid), additem)
    orderid = d['tradeid']
    myredis.hset('sysgen_realDB2_trade_' + str(userid)+'_'+investor+'_'+str(day), str(orderid), datastr)
@check_myredis
def delDBTradeDataReal(userid, investor, day):
    myredis.delete('sysgen_realDB2_trade_' + str(userid)+'_'+investor+"_"+str(day))

#     print('sysgen_test18_trade_'+str(userid)+'_'+str(stratName))

@check_redisconn
def saveStatDataToDBReal(user, token, df):
    key = 'sysgen_stat_'+user+'_' + token
    redisconn.set(key, zlib.compress(pickle.dumps(df)))

@check_myredis
def saveStatCurrentToDBReal(user, token, d):
    key = 'sysgen_statcur_'+user+'_' + token
    myredis.set(key, json.dumps(d))


###
@check_myredis
def saveSettingDatarealToDB(userid,token, stratsetts):
    datastr = json.dumps(stratsetts, ensure_ascii=False)
    myredis.set('sysgen_setting_' + str(userid)+'_'+str(token), datastr)

###
@check_myredis
def saveImageSettingDataRealToDB(userid, imagesetts):
    datastr = json.dumps(imagesetts)
    myredis.set('sysgen_realDB1_image_setting_' + str(userid), datastr)


###
@check_myredis
def updateInitCapreal(userid, balance):
    myredis.set('sysgen_realDB1_capital_' + userid, str(round(balance, 2)))

@check_myredis
def saveHedgePointrealToDB(userid, stratName, time, d):
    datastr = json.dumps(d)
    additem = {datastr: int(time)}
    myredis.zadd('sysgen_realDB1_hedgepoint_' + str(userid) + '_' + str(stratName), additem)


@check_myredis
def savePositionDatarealToDB(userid, investor, d, day):
    # parameter 2
    try:

        if len(d) > 0:
            datastr = json.dumps(d)
            myredis.hset('sysgen_realDB2_position_'+str(userid)+'_'+investor, str(day), datastr)
        #                 print('sysgen_test18_position_'+str(userid)+'_'+str(stratName))
    except Exception as e:
        logger.error(f"Failed on position writeDB: {e}", exc_info=True)

@check_myredis
def saveStrategyContextrealToDB(userid, stratName, day, context):
    try:

        d = {}
        d['trading_day'] = day
        d['strategy'] = stratName
        #         d['initcapital'] = context.initCapital
        # d['curpnl'] = context.curpnl
       
        d['posProf'] = str(round(context.posProf,3))
        d['frozenMarg'] = str(round(context.frozenMarg,3))
        d['marg'] = str(round(context.marg,3))
        d['closeProf'] = str(round(context.closeProf,3))
        d['balance'] = str(round(context.stat.balance,3))
        d['avail'] = str(round(context.stat.avail,3))
        d['totalpnl'] = str(round(context.stat.totalpnl,3))
        d['totalfee'] = str(round(context.stat.totalfees,3))
        d['daypnl'] = str(round(context.stat.daypnl,3))
        d['dayfee'] = str(round(context.stat.dayfees,3))
        
        count = 0
        if len(context.position) > 0:
            for instid in context.position.keys():
                count += (context.position[instid]['long']['volume'] + context.position[instid]['short']['volume'])

        d['grossCount'] = str(int(count))

        datastr = json.dumps(d)
        myredis.hset('sysgen_realDB3_context_'+ str(userid), str(day) + '-' + str(stratName), datastr)
    #         print('sysgen_test18_context_'+str(userid)+'_'+str(stratName))
    except Exception as e:
        logger.error(f"Failed on context writeDB: {e}", exc_info=True)

@check_myredis
def saveAccountDatarealToDB(userid, investor, day, d):
    try:
        
        d['tradingDay'] = day
        datastr = json.dumps(d)
        myredis.hset('sysgen_realDB3_account_'+ str(userid)+'_'+str(day), str(investor), datastr)
#         print(str(userid))
#         tempdata = myredis.hget('sysgen_realDB2_account', str(userid))
#         print(tempdata)
    except Exception as e:
        print("Failed on account writeDB: ", e.__traceback__.tb_lineno, e)

@check_myredis
def saveHedgeMarketrealToDB(userid, stratName, instid_hedge, time, tickdata):
    datastr = json.dumps(tickdata)
    additem = {datastr: int(time)}
    myredis.zadd('sysgen_realDB1_' + str(userid) + '_' + str(stratName) + '_' + instid_hedge, additem)

@check_myredis
def saveFormulaDatarealToDB(userid, token, strats_formula):
    datastr = json.dumps(strats_formula)
    myredis.set('sysgen_formual_' + str(userid)+'_'+str(token), datastr)
    
@check_myredis
def loadSettingDatareal(userid,token):
    userdata = myredis.get('sysgen_setting_' + str(userid)+'_'+str(token))
    if userdata:
        return json.loads(userdata)
    else:
        #logger.error('请先运行策略模拟交易程序startRealProcess。')
        return None
@check_myredis
def loadImageSettingDatareal(userid):
    userdata = myredis.get('sysgen_realDB1_image_setting_' + str(userid))
    if userdata:
        return json.loads(userdata)
    else:
        #logger.error('请先运行策略模拟交易程序startRealProcess。')
        return None
@check_myredis
def loadForumalgDatareal(userid,token):
    userdata = myredis.get('sysgen_formual_' + str(userid)+'_'+str(token))
    if userdata:
        return json.loads(userdata)
    else:
        #logger.error('请先运行策略模拟交易程序startSimuProcess使用用户名跑一个空的qeBaseStrat（不做任何交易）。')
        return None

#def getDBOrderDatareal(userid, fromtime, endtime):
#    return myredis.zrangebyscore('sysgen_realDB2_order_' + userid, fromtime, endtime, withscores=True)

@check_redisconn
def loadDBStatDataReal(user, token):
    key = 'sysgen_stat_'+user+'_'+token
    res = redisconn.get(key)
    if res:
        return pickle.loads(zlib.decompress(res))

@check_myredis
def loadDBStatCurrentReal(user, token):
    key = 'sysgen_statcur_'+user+'_'+token
    ret = myredis.get(key)
    if ret :
        return json.loads(ret)

@check_myredis
def getDBOrderDatareal(userid, investor, day):
    return myredis.hgetall('sysgen_realDB2_order_' + str(userid)+'_'+investor+"_"+str(day))

@check_myredis
def getDBTradeDatareal(userid, investor, day):
    #return myredis.zrangebyscore('sysgen_realDB2_trade_' + userid, fromtime, endtime, withscores=True)
    return myredis.hgetall('sysgen_realDB2_trade_' + str(userid)+'_'+investor+"_"+str(day))

@check_myredis
def getDBPositionDatareal(userid, investor, day):
    return myredis.hget('sysgen_realDB2_position_'+str(userid)+'_'+investor, str(day))


# def getDBPositionData_past(userid,fromtime,endtime):
#     return myredis.zrangebyscore('sysgen_test19_position_'+userid, fromtime, endtime ,withscores=True)
###
@check_myredis    
def getDBAccountDatareal(userid, day):
    return myredis.hgetall('sysgen_realDB3_account_'+str(userid)+'_'+str(day))

@check_myredis
def getDBAccountDetailReal(userid, investor, day):
    return myredis.hget('sysgen_realDB3_account_'+str(userid)+'_'+str(day), investor)



###
@check_myredis
def getDBContextDatareal(userid, stratName, day):
    return myredis.hget('sysgen_realDB3_context_'+str(userid), str(day) + '-' + str(stratName))

#def saveStrategyfreqrealToDB(userid, token, d):
#    try:
#        datastr = json.dumps(d)
#        myredis.set('sysgen_freqrealDB6_'+str(userid)+'_'+str(token), datastr)
    #         print('sysgen_test18_context_'+str(userid)+'_'+str(stratName))
#    except Exception as e:
#        logger.error(f"Failed on context writeDB: {e}", exc_info=True)
#def getDBfreqrealData(userid, token, stratName, day):
#    return myredis.hget('sysgen_freqrealDB5_'+ str(userid)+'_'+str(token), str(day) + '-' + str(stratName)) 

# def getDBPositionDataLast(userid):
#     return myredis.zrange('sysgen_test19_position_'+userid, start=-1,end=-1)

# def getDBAccountDataLast(userid):
#     return myredis.zrange('sysgen_test19_account_'+userid,  start=-1,end=-1)

# def getDBContextDataLast(userid,stratName):
#     return myredis.zrange('sysgen_test19_context_'+userid+'_'+stratName,  start=-1,end=-1)
###
@check_myredis
def getSimuInitCapreal(userid):
    if myredis.exists('sysgen_realDB1_capital_' + userid):
        return myredis.get('sysgen_realDB1_capital_' + userid)
    else:
        return None

@check_myredis
def getDBHedgePointreal(userid, stratName, fromtime, endtime):
    return myredis.zrangebyscore('sysgen_realDB1_hedgepoint_' + str(userid) + '_' + str(stratName), fromtime, endtime,
                                 withscores=True)



@check_myredis
def getDBHedgeMarketDatareal(userid, stratName, instid_hedge, fromtime):
    return myredis.zrangebyscore('sysgen_realDB1_' + str(userid) + '_' + str(stratName) + '_' + instid_hedge,
                                 fromtime, 30211202101556000, withscores=True)
@check_myredis
def getDBHedgeMarketDatareal1(userid, stratName, instid_hedge, fromtime,start=0,num=15000,endtime=302112021015560000):
    return myredis.zrangebyscore('sysgen_realDB1_' + str(userid) + '_' + str(stratName) + '_' + instid_hedge,
                                 fromtime, endtime,start=start,num=num, withscores=True)
    
######################################################################
##    Redis commands


@check_myredis
def saveProcessToDB(userid,d):
    key = d.get('type','simu')
    datastr = json.dumps(d)   
    myredis.hset('sysgen_test20_status_'+key,str(userid) , datastr)
    # myredis.hset('sysgen_test19_status_'+key,str(userid) + '_' + str(stratName), datastr)
@check_myredis
def saveRequestToDB(userid,stratName,dtype,realtrade=False):
    if realtrade:
        key1 = 'real'
    else:
        key1 = 'simu'
     
    if dtype == -1:
        key = '_stop'
    elif dtype == 1:
        key = '_stop_confirm'
    elif dtype == -2:
        key = '_resume'
    elif dtype == 2:
        key = '_resume_confirm'    
    elif dtype == -3:
        key = '_liquidate'
    elif dtype == 3:
        key = '_liquidate_confirm'     
    else:
        print('key is unknown1')
#         key = '_unknown'
    myredis.set('sysgen_test20_request_'+str(userid) + '_' + str(stratName)+key + '_'+key1, str(dtype))
    return
    
@check_myredis
def resetRequestToDB(userid,stratName,dtype,realtrade=False):
    if realtrade:
        key1 = 'real'
    else:
        key1 = 'simu'
    
    if dtype == -1:
        key = '_stop'
    elif dtype == 1:
        key = '_stop_confirm'
    elif dtype == -2:
        key = '_resume'
    elif dtype == 2:
        key = '_resume_confirm' 
    elif dtype == -3:
        key = '_liquidate'
    elif dtype == 3:
        key = '_liquidate_confirm'         
    else:
        print('key is unknown')
#         key = '_unknown'
    myredis.delete('sysgen_test20_request_'+str(userid) + '_' + str(stratName)+key+ '_'+key1)
    return


@check_myredis    
def getDBProcess(userid,realtrade=False):
    if realtrade:
        key = 'real'
    else:
        key = 'simu'
    return myredis.hget('sysgen_test20_status_'+key, str(userid) )
    # return myredis.hget('sysgen_test19_status_'+key, str(userid) + '_' + str(stratName))
@check_myredis   
def getDBRequest(userid,stratName,dtype,realtrade=False):
    if realtrade:
        key1 = 'real'
    else:
        key1 = 'simu'
    
    if dtype == -1:
        key = '_stop'
    elif dtype == 1:
        key = '_stop_confirm'
    elif dtype == -2:
        key = '_resume'
    elif dtype == 2:
        key = '_resume_confirm'  
    elif dtype == -3:
        key = '_liquidate'
    elif dtype == 3:
        key = '_liquidate_confirm'         
    else:
        print('key is unknown2')
#         key = '_unknown'
    return myredis.get('sysgen_test20_request_'+str(userid) + '_' + str(stratName)+key+ '_'+key1)


########################### BackTest ##################################################
@check_myredis
def saveBackTestSetting(user, d):
    myredis.set('sysgen_backtest_setting_'+str(user), json.dumps(d))

@check_myredis
def loadBackTestSetting(user):
    ret = myredis.get('sysgen_backtest_setting_'+str(user))
    if ret:
        return json.loads(ret)
    
@check_redisconn
def saveBackTestData(user, data, hedge=False):
    if hedge:
        key = 'sysgen_backtest_hedgedata_'+str(user)
        redisconn.set(key, zlib.compress(pickle.dumps(data)))
    else:
        key = 'sysgen_backtest_rawdata_'+str(user)
        for inst in data:
            redisconn.hset(key, inst, zlib.compress(pickle.dumps(data[inst])))

@check_redisconn
def saveBackTestDataDynamic(user, inst, data):
    key = 'sysgen_backtest_rawdata_'+str(user)
    redisconn.hset(key, inst, zlib.compress(pickle.dumps(data)))
    
@check_redisconn
def saveBackTestReport(user, field, df):
    key = 'sysgen_backtest_report_'+str(user)
    redisconn.hset(key, field, zlib.compress(pickle.dumps(df)))

@check_myredis
def saveBackTestList(user,field, datadict):
    key = 'sysgen_backtest_List_'+str(user)+"_"+str(field)
    ids = list(datadict.keys())
    myredis.hset(key, 'index', json.dumps(ids))
    for kid in datadict:
        myredis.hset(key, str(kid), json.dumps(datadict[kid]))

@check_redisconn
def loadBackTestData(user,instid, hedge=False):
    if hedge:
        key = 'sysgen_backtest_hedgedata_'+str(user)
        ret = redisconn.get(key)
        if ret:
            return pickle.loads(zlib.decompress(ret))
    else:
        key = 'sysgen_backtest_rawdata_'+str(user)
        ret = redisconn.hget(key, instid)
        if ret:
            return pickle.loads(zlib.decompress(ret))
@check_myredis        
def loadBackTestList(user, field, start, end):
    key = 'sysgen_backtest_List_'+str(user)+"_"+str(field)
    ids = myredis.hget(key,'index')
    if ids:
        indexlist = json.loads(ids)
        indexlist = indexlist[start:end]
        datadict = {}
        for kid in indexlist:
            ret = myredis.hget(key, str(kid))
            if ret:
                datadict[kid] = json.loads(ret) 
        return datadict
@check_redisconn    
def loadBackTestReport(user, field):
    key = 'sysgen_backtest_report_'+str(user)
    ret = redisconn.hget(key, field)
    if ret:
        return pickle.loads(zlib.decompress(ret))
        
@check_myredis
def clearBackTestData(user):
    myredis.delete('sysgen_backtest_setting_'+str(user))
    myredis.delete('sysgen_backtest_hedgedata_'+str(user))
    myredis.delete('sysgen_backtest_rawdata_'+str(user))
    myredis.delete('sysgen_backtest_report_'+str(user))
    myredis.delete('sysgen_backtest_List_'+str(user)+'_orders')
    myredis.delete('sysgen_backtest_List_'+str(user)+'_trades')
    


###########################FOR 103 SMS AUTH############################################
@check_myredis
def setSmsAuth(phone_number, authcode, expires):
    myredis.set("MPAUTH_"+phone_number, authcode, ex=expires)
@check_myredis    
def getSmsAuth(phone_number):
    return myredis.get("MPAUTH_"+phone_number)    

#######################################################################
## For user visit Redis
@check_myredis
def GET(user, name):
    dbname = 'usergen_'+user+'_'+name
    return myredis.get(dbname)

@check_myredis
def SET(user, name,value):
    dbname = 'usergen_'+user+'_'+name
    return myredis.set(dbname, value)
@check_myredis    
def HGET(user, name, key):
    dbname = 'usergen_'+user+'_'+name
    return myredis.hget(dbname, key)
@check_myredis
def HSET(user, name, key, value):
    dbname = 'usergen_'+user+'_'+name
    return myredis.hset(dbname, key, value)
@check_myredis
def HDEL(user,name,key):
    dbname = 'usergen_'+user+'_'+name
    return myredis.hdel(dbname, key)
@check_myredis
def DEL(user,name):
    dbname = 'usergen_'+user+'_'+name
    return myredis.delete(dbname)

def transExID(exID):
    if exID == 'ZCE':
        return "CZCE"
    elif exID == "SFE":
        return "SHFE"
    elif exID == "CCF":
        return "CFFEX"
    else:
        return exID.upper()


def inst2tablename(inst):
    instid  = inst.split('.')
    if instid[1] == 'SSE':
        tname = 'options_sse_bar.S'+instid[0].upper() + '_' + transExID(instid[1])
    else:    
        tname = instid[0].upper() + '_' + transExID(instid[1])
    return tname

def get_bar_data(context):
    return qesdk.get_bar_data(context.instid, context.tradingday)

async def async_get_bar_data(instids, tradingday):
    return await qesdk.aio_get_bar_data(instids, tradingday)