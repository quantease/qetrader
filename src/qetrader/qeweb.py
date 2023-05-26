#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  5 07:34:57 2022

@author: root
"""
try:
    from flask import Flask, request, redirect, abort, render_template, make_response, json, jsonify
    from flask_bootstrap import Bootstrap
    #from pandas import DataFrame as df
    app = Flask(__name__, static_url_path="")
    from flask_compress import Compress
    Compress(app)
    app.debug = True
    app.config['COMPRESS_MIN_SIZE'] = 1024
    #from qereal 
    #print(1)
    from .qeredisdb import getDBHedgePoint,getDBTradeData,getDBTradeDatareal,getDBOrderData,getDBOrderDatareal
    from .qeredisdb import getDBHedgeMarketData1,getDBMarketData1,getDBfreqData,loadDBStatData,loadDBStatDataReal
    from .qeredisdb import getDBPositionData,getDBPositionDatareal,getDBAccountData,getDBAccountDatareal,delDBPid
    from .qeredisdb import loadTradingDay, loadDBPid,loadForumalgData,loadForumalgDatareal,loadSettingData,loadSettingDatareal
    from .qeredisdb import loadBackTestList,loadBackTestReport,loadBackTestData,loadBackTestSetting
    from .qeinterface import get_bar
    from .qesysconf import read_sysconfig
    import math
    import sys
    import os
    #print(2)
    #import gzip
    #import json
    import pandas as pd
    #import qedata
    from datetime import datetime, timedelta
    import numpy as np
    #from qetable_web import qetable_read_db_data,qetable_read_db_order_data,qetable_read_db_lastdata,qetable_read_db_position,qetable_getSetting,TimeKeeper,get_BS_table,get_position_table,get_order_table,get_trade_table
    #from qeimage_web import *
    from .qemonitor_log_web import get_qemonitor_log
    #import qeimage_web
    #import math
    from .qelogger import logger, initTableLogger
    initTableLogger()
    #import time
    #from bardata import gettradedata
    #from tickdata import gettickdata
    import matplotlib.pyplot as plt
    import io
    import base64
    import warnings
    warnings.filterwarnings("ignore")
    #print(3)
except Exception as e:
    print('import error:', e.__traceback__.tb_lineno,e)

# error
@app.route("/error")
def error():
    abort(404)

@app.route('/')
def homePage():
    return redirect('/runstrat')

@app.route('/login')
def login():
    return 'login'

@app.route('/runstrat')
def runStrat():
    return 'qetrader网页展示服务已经成功启动'

@app.route('/base', methods=['GET', 'POST'])
def base():
    userid = request.args.get('user')
    # password = request.args.get('password') # password
    password = '1'
    mode = request.args.get('mode')
    return render_template("base.html", user=userid, password=password, mode=mode)




################################ new design ##################################################

data_batch_num = 1000
page_batch_num = 100

def getTimeStr(time):
    tstr = str(time)
    return tstr[:4]+'-'+tstr[4:6]+'-'+tstr[6:8]+" "+tstr[8:10]+':'+tstr[10:12]+':'+tstr[12:14]

def formhedgeInstid(instid):
    instid_hedge = '&'+instid[0]
    if len(instid) > 1:
        for i in range(1, len(instid)): 
            instid_hedge += '_' + str(instid[i]) 
    return instid_hedge

def getOpenCloseData(user, token, mode, freq, curstg, curinst,tradingday, start=0, end=0,ishedge=False):
    #return {},0,{}
    try:
        class tmpContext(object):
            instid =[]
            tradingday=''
        
        #print(f'OpenCloseData input tradingDay:{tradingday}')
        if tradingday is None:
            tradingday = getLocalTradingDay()
            #print('OpenCloseData local',tradingday)    
            
        curday = datetime.strptime(tradingday,'%Y%m%d')
        days = 3 if curday.weekday() == 0 else 1
        prevday = curday - timedelta(days=days)
        starttime = int(prevday.strftime('%Y%m%d200000000'))
        
        ishedge = curinst[0] == '&'
        
        
        if ishedge:
            hedgedata = getDBHedgePoint(user, token, curstg, starttime, sys.maxsize)
            tradedict = {}
            for i in range(len(hedgedata)):
                    tradedict[i]=eval(hedgedata[i][0])
            
        
        if mode == 'simu':
            tradedata=getDBTradeData(user,token, tradingday)
        else:
            tradedata=getDBTradeDatareal(user,token, tradingday)
        for key in tradedata:
            tradedata[key] = eval(tradedata[key])
        
        #print(len(tradedata),tradingday,curstg, curinst,mode)
        
        
        if (not ishedge and len(tradedata) == 0) or (ishedge and len(hedgedata) == 0) :
             openclose = pd.DataFrame(columns=['openlong','closelong','openshort','closeshort'])
        
        else:
            
            if not ishedge:
                trades = pd.DataFrame.from_dict(tradedata,orient='index')
                #print('1',len(trades),mode)
                trades = trades[(trades['instid']==curinst) & (trades['stratName']==curstg)]
                #print('2',len(trades),mode)
            else:
                trades = pd.DataFrame.from_dict(tradedict,orient='index')


            if len(trades) > 0:
                if ishedge:
                    trades.rename(columns={'time':'timedigit','direction':'dir','price':'tradeprice'},inplace=True)
                    trades['dir'] = np.where(trades['dir'] == 'short', 1,-1)
                #print(trades)
                trades = trades.set_index(trades['timedigit'])
                
                openclose = pd.DataFrame()
                openlong =pd.DataFrame(index=trades.index,columns=['openlong'], data=np.where((trades.dir>0)&(trades.action=='open'), trades.tradeprice, np.nan))
                
                openlong = openlong.dropna(how='all')
                openlong['time'] = openlong.index
                
                openlong.drop_duplicates('time',inplace=True)
                openlong.drop(columns=['time'],inplace=True)
                if len(openlong) > 0:
                    openclose = pd.merge(openclose, openlong, how='outer',left_index=True, right_index=True)
                else:
                    openclose['openlong'] = np.nan
                closelong =pd.DataFrame(index=trades.index,columns=['closelong'], data=np.where((trades.dir<0)&(trades.action=='close'), trades.tradeprice, np.nan))
                closelong = closelong.dropna(how='all')
                closelong['time'] = closelong.index
                closelong.drop_duplicates('time',inplace=True)
                closelong.drop(columns=['time'],inplace=True)
                if len(closelong) > 0:
                    openclose = pd.merge(openclose, closelong, how='outer',left_index=True, right_index=True)
                else:
                    openclose['closelong'] = np.nan
                openshort =pd.DataFrame(index=trades.index,columns=['openshort'], data=np.where((trades.dir<0)&(trades.action=='open'), trades.tradeprice, np.nan))
                openshort = openshort.dropna(how='all')
                openshort['time'] = openshort.index
                openshort.drop_duplicates('time',inplace=True)
                openshort.drop(columns=['time'],inplace=True)
                if len(openshort) > 0:
                    openclose = pd.merge(openclose, openshort, how='outer',left_index=True, right_index=True)
                else:
                    openclose['openshort'] = np.nan
                closeshort =pd.DataFrame(index=trades.index,columns=['closeshort'], data=np.where((trades.dir>0)&(trades.action=='close'), trades.tradeprice, np.nan))
                closeshort = closeshort.dropna(how='all')
                closeshort['time'] = closeshort.index
                closeshort.drop_duplicates('time',inplace=True)
                closeshort.drop(columns=['time'],inplace=True)
                if len(closeshort) > 0:
                    openclose = pd.merge(openclose, closeshort, how='outer',left_index=True, right_index=True)
                else:
                    openclose['closeshort'] = np.nan
                
                if not ishedge:
                    if mode == 'simu':
                        openclose.index = [int(i) for i in openclose.index]
                    else:
                        openclose.index = [int(str(i)+'000') for i in openclose.index]
                    
                #print('oc',mode, (openclose), type(openclose.index[0]))
                    
                #openclose = pd.DataFrame(index=trades.index, columns=['openlong','closelong','openshort','closeshort'])
                #openclose.openlong = np.where((trades.dir>0)&(trades.action=='open'), trades.tradeprice, np.nan)
                #openclose.closelong = np.where((trades.dir<0)&(trades.action=='close'), trades.tradeprice, np.nan)
                #openclose.openshort = np.where((trades.dir<0)&(trades.action=='open'), trades.tradeprice, np.nan)
                #openclose.closeshort = np.where((trades.dir>0)&(trades.action=='close'), trades.tradeprice, np.nan)
            else:
                 openclose = pd.DataFrame(columns=['openlong','closelong','openshort','closeshort'])

        #print('oc',len(openclose))    
        #print('tradingday',tradingday)
        
        if ishedge:
            instname = curinst[1:]
            ddict={}
            #if mode == 'simu':
            tickdata = getDBHedgeMarketData1(user, curstg, instname, starttime,start,end)
            #print('tickdata',len(tickdata),instname,starttime)
            #elif mode == 'real':
            #    tickdata = getDBHedgeMarketDatareal1(user, curstg, instname, starttime,start,end)
            keylist = [d[1] for d in tickdata]
            vallist = [eval(d[0]) for d in tickdata]
            ddict ={}
            for i in range(len(keylist)):
                ddict[keylist[i]] = vallist[i]
            ddata = pd.DataFrame.from_dict(ddict,orient='index')
            #print('ddata', len(ddata))
            if len(ddata) > 0:
                newdf = pd.DataFrame(index=ddata.time, columns=['current'])
                newdf['volume'] = 0
                datalen = len(newdf)
                #print('newdf',datalen)
                newdf['current'] = ddata['current']
                
                newdf['date'] = newdf.index
                newdf.date = [getTimeStr(d) for d in newdf.date]
                newdf = pd.merge(newdf,openclose,left_index=True, right_index=True,how='left')
            else:
                newdf = pd.DataFrame()
                datalen = 0
    
        elif int(freq) == 0:
            tickdata = getDBMarketData1(curinst, starttime, start, end)
            keylist = [d[1] for d in tickdata]
            vallist = [eval(d[0]) for d in tickdata]
            ddict ={}
            for i in range(len(keylist)):
                ddict[keylist[i]] = vallist[i]
            ddata = pd.DataFrame.from_dict(ddict,orient='index')
            #print(ddata)
            if len(ddata) > 0:
                newdf = pd.DataFrame(index=ddata.timedigit, columns=['current'])
                newdf['volume'] = ddata['volume'].diff(1).fillna(0)
                datalen = len(newdf)
                newdf['current'] = ddata['current']
                
                newdf['date'] = newdf.index
                newdf.date = [getTimeStr(d) for d in newdf.date]
                newdf = pd.merge(newdf,openclose,left_index=True, right_index=True,how='left')
                #print(newdf.index)
            else:
                newdf = pd.DataFrame()
                datalen = 0
            
            
        else:
    
            context = tmpContext()
            context.instid = [curinst]
            context.tradingday = tradingday
            context.runmode = mode
            #print("get_bar", curinst, freq)
            
            result=get_bar(context,int(freq))
            if curinst in result:
                result = result[curinst]
                #result=result.set_index(result.time)
                result['runtime'] = [int(t.strftime('%Y%m%d%H%M%S')) for t in result.index]
                result = result.set_index(result.runtime)
                result = result.iloc[start:,:]
                #print('getopenclose', start, len(result))
                if len(result) > 0:
                    openclose.index = [math.floor(openclose.index[i]/100000)*100 for i in range(len(openclose.index))]
                    newdf = pd.DataFrame(index=result.index, columns=['open','close','high','low','volume'])
                    newdf['open'] = result['open']
                    newdf['close'] = result['close']
                    newdf['high'] = result['high']
                    newdf['low'] = result['low']
                    newdf['volume'] = result['volume']
                    newdf['date'] = newdf.index
                    newdf.date = [getTimeStr(d) for d in newdf.date]
                    datalen=len(newdf)
                    newdf = pd.merge(newdf,openclose,left_index=True, right_index=True,how='left')
                else:
                    newdf = pd.DataFrame()
                    datalen = 0
            else:
                print('Could not find bar Data of', curinst)
                newdf = pd.DataFrame()
                datalen = 0
                
            #print('datalen',datalen)    
        newdf = newdf.fillna(0)
        #print('getopenclose datalen',len(newdf))
        #newdf = newdf.iloc[:1, :] ## only for test
        return newdf.to_dict('records'),datalen,tradedata
    except Exception as e:
        print('getOpenCloseData',e, e.__traceback__.tb_lineno)
        return {},0,{}


def getStgFreq(user, token,  curstg):
    try:
        freq_d=getDBfreqData(user, token)
        if freq_d:
            return int(freq_d.get(curstg, 0))
    except Exception as e:
        print('getStgFreq',e, e.__traceback__.tb_lineno)
        return 0

def getTradeItems(tradedata, pagenum):    
    tradeids = list(tradedata.keys())
    if len(tradeids) > 0:
        tradeids.sort(reverse=True)
        tradenum = len(tradeids)
        tradeids = tradeids[(pagenum-1)*page_batch_num : pagenum * page_batch_num]
        trades = {}
        for tid in tradeids:
            trades[tid] = tradedata[tid]
        tradedf = pd.DataFrame.from_dict(trades, orient='index')    
        tradedf = tradedf.drop(columns=['timedigit','tradeid','accid'])

        tradedf = tradedf.reindex(sorted(tradedf.columns), axis=1)
        
        tradedf['action'] = np.where(tradedf.action=='open', '开仓','平仓')
        tradedf['dir'] = np.where(tradedf['dir'] > 0, '多','空')
        tradedf['closetype'] = tradedf['closetype'].replace('auto','自动')
        tradedf['closetype'] = tradedf['closetype'].replace('closetoday','平今')
        tradedf['closetype'] = tradedf['closetype'].replace('closeyesterday','平昨')
        tradedf.columns=['开平','平仓类型','日期','多空','合约名','订单号','策略名','时间','成交价','成交量']
        
        return tradedf.to_html(classes='table table-striped'), tradenum    
    else:
        return '',0

def getOrderItems(user, token, mode, tradingDay, pagenum):
    if mode=='simu':
        orderdata = getDBOrderData(user, token, tradingDay)
    else:
        orderdata = getDBOrderDatareal(user, token, tradingDay)
    
    orderids = list(orderdata.keys())
    if len(orderids)>0:
        orderids.sort(reverse=True)
        ordernum = len(orderids)
        orderids = orderids[(pagenum-1)*page_batch_num : pagenum * page_batch_num]
        orders = {}
        for oid in orderids:
             orders[oid] = eval(orderdata[oid])
        orderdf = pd.DataFrame.from_dict(orders, orient='index') 
        if mode == 'simu':
            orderdf = orderdf.drop(columns=['errorid','pendvol','orderid','type','accid'])
        else:
            orderdf = orderdf.drop(columns=['errorid','orderid','type','offset',
                                            'date','orderTime','direction_ctp','status_ctp',
                                            'offset_ctp','cancelTime','from','torderid','accid'])
        if 'timedigit' in orderdf.columns:
            orderdf = orderdf.drop(columns=['timedigit'])
        
        orderdf = orderdf.reindex(['time','instid','action','direction','closetype','status',
                                   'price','volume','tradevol','cancelvol','leftvol','stratName',
                                   'timecond','errormsg'], axis=1)
        orderdf['direction'] = np.where(orderdf.direction > 0, '多','空')
        orderdf['action'] = np.where(orderdf.action=='open', '开仓','平仓')
        orderdf['status'] = orderdf['status'].replace('committed', '已报')
        orderdf['status'] = orderdf['status'].replace('failed', '被拒')
        orderdf['status'] = orderdf['status'].replace('parttraded', '部成')
        orderdf['status'] = orderdf['status'].replace('alltraded', '全成')
        orderdf['status'] = orderdf['status'].replace('canceled', '已撤')
        orderdf['status'] = orderdf['status'].replace('ptpc', '部成部撤')
        orderdf['closetype'] = orderdf['closetype'].replace('auto','自动')
        orderdf['closetype'] = orderdf['closetype'].replace('closetoday','平今')
        orderdf['closetype'] = orderdf['closetype'].replace('closeyesterday','平昨')
        orderdf.columns=['时间','合约名','开平','多空','平仓类型','状态','价格','总量','成交量',
                         '撤单量','剩余量','策略名','时间类型','错误信息']
        return orderdf.to_html(classes='table table-striped'), ordernum    
    else:
        return '',0

    
    
def getPositionItems(user, token, mode, tradingDay):
    postab = {}    
    if mode == 'simu':
        accounts = [token]
        pos = getDBPositionData(user,token)
        if pos:
            pos = eval(pos)
            for key in pos:
                for dirstr in pos[key]:
                    for field in pos[key][dirstr]:
                        if not key in postab:
                            postab[key] = {dirstr+'_'+field : pos[key][dirstr][field]}
                        else:
                            postab[key][dirstr+'_'+field] =pos[key][dirstr][field]    
    else:
        accounts = token.split('_')
        for acc in accounts:
            pos = getDBPositionDatareal(user, acc, tradingDay)
            if pos:
                pos = eval(pos)
                for key in pos:
                    for dirstr in pos[key]:
                        for field in pos[key][dirstr]:
                            if not key in postab:
                                postab[key] = {dirstr+'_'+field : pos[key][dirstr][field]}
                            else:
                                postab[key][dirstr+'_'+field] =pos[key][dirstr][field]    
            
    if postab != {}:
        posdf = pd.DataFrame.from_dict(postab, orient='index')
        posdf = posdf.fillna(0)
        posdf = posdf.reindex(['long_poscost','long_volume','long_yesvol','short_poscost','short_volume','short_yesvol'], axis=1)
        posdf.columns=['多头成本仓位','多头持仓','多头昨仓','空头持仓成本','空头仓位','空头昨仓']
        return posdf.to_html(classes='table table-striped')    
    else:
        return ''

def getAccountItems(user, token, mode, tradingDay):
    accdict = {}
    if mode == 'simu':
        acc = getDBAccountData(user,token )
        ttoken = token[:6]+'...'
        if acc:
            accdict[ttoken]= eval(acc)
    else:
        #acc = getDBAccountDetailReal(user,token,tradingDay)
        acc = getDBAccountDatareal(user,tradingDay)
        accounts = token.split('_')
        if acc:
            accids = list(acc.keys())
            for aid in accids:
                if aid in accounts:
                    accdict[aid] = eval(acc[aid])
    
    if accdict != {}:
        if mode =='simu' :
            balance = round(float(accdict[ttoken]['balance']), 2) 
        else:
            balance = 0
            for aid in accdict:
                balance += float(accdict[aid]['balance'])
            balance = round(balance, 2)    
        accdf = pd.DataFrame.from_dict(accdict, orient='index')
        accdf = accdf.drop(columns=['closeProf','wincount','winamount','lossamount','losscount','tradingDay'])
        accdf = accdf.reindex(sorted(accdf.columns), axis=1)
        accdf.columns=['可用权益','资金','当日手续费','当日平仓盈亏','冻结保证金','保证金','当日最大保证金','持仓盈亏','总手续费','总盈亏','交易额']
        return accdf.to_html(classes='table table-striped') , balance 
    else:
        return '',0

def getLogItems(user, mode, pagenum):
    logdata = get_qemonitor_log(user, '', mode)
    lognum = 0
    if len(logdata) > 0:
            logdata.columns = [u'日志']
            logdata = logdata.reindex(index=logdata.index[::-1])
            lognum = len(logdata)
            #print('logitem', lognum)
            logdata = logdata.iloc[(pagenum-1)*page_batch_num : pagenum*page_batch_num, :]
            return logdata.to_html(classes='table table-striped') , lognum   
            #pd.set_option('display.max_rows', None, 'display.max_colwidth', 900)
    else:
            return '',0

def getStatAccu(stat):
    retlist = [0]
    if len(stat) > 1:
        for i in range(1,len(stat)):
            index = stat.index[i]
            netbal = stat.loc[index,'balance'] - stat.loc[index,'deposit'] + stat.loc[index,'withdraw']
            ret = np.log(netbal) - np.log(stat.loc[stat.index[i-1],'balance'])
            retlist.append(ret)
    stat['dayret'] = retlist
    #stat.dayret = stat.dayret.diff(1).fillna(0)
    stat['accret'] = stat.dayret.cumsum()
    stat['accpnl'] = stat.daypnl.cumsum()
    stat['accfee'] = stat.dayfee.cumsum()
    stat['highwater'] = stat.balance.cummax()
    stat['drawback'] = stat.highwater - stat.balance
    return stat

def getIndicators(user, mode, token, riskfree):
    if mode == 'simu':
        stat = loadDBStatData(user, token)
    else:
        stat = loadDBStatDataReal(user, token)        
    
    
    if not stat is None:
        #print(len(stat))
        stat = getStatAccu(stat)
        return reportIndicators(stat, riskfree)    
    else:
        return  {}

def getLocalTradingDay():
    now = datetime.now()
    if now.hour < 19:
        return (now.strftime('%Y%m%d'))
    else:
        wday = now.weekday()
        days = 1 if wday != 4 else 3
        return ((now + timedelta(days=days)).strftime('%Y%m%d'))
        


@app.route('/monitor_ex', methods=['GET', 'POST'])
def monitor_ex():
    try:

        user = request.args.get('user')  # user
        # password = request.args.get('password') # password
        mode = request.args.get('mode')  # real or simu
        rfrate = request.args.get('rfrate')
        if mode=='simu':
            token = request.args.get('token')
        elif mode=='real':
            token=request.args.get('investorid')
        logger.info(token)
        
        ##check input
        if user == None:
            return '请输入user'
        elif mode == None:
            return '请输入mode'
        mode = mode.lower()
        if mode != 'real' and mode != 'simu':
             return 'Incorrect mode, real or simu'

        ##get tradingday
        tradingDay = loadTradingDay(user,token)
        if tradingDay is None:
            tradingDay = getLocalTradingDay()
            #print(f'local tradingday:{tradingDay}')
        else:
            tradingDay = str(tradingDay)
        
        pid = str(loadDBPid(user, token))
        if pid:
            pidexist = os.path.exists('/proc/'+pid)
            status_title = u'运行中' if pidexist else u'未运行'
        else:
            status_title = u'未运行'
        
        print(user, mode, token, tradingDay, pidexist)
        ## get stglist and instid list 
        if mode == 'simu':
            formulastruct = loadForumalgData(user,token)
            setting = loadSettingData(user,token)
            if setting is None:
                print('no setting', user, token)
                return '没有检测到正在运行的模拟策略，请先运行策略。'
        elif mode == 'real':
            formulastruct = loadForumalgDatareal(user,token)
            setting = loadSettingDatareal(user,token)
            if setting is None:
                print('no setting', user, token)
                return '没有检测到正在运行的实盘策略，请先运行策略。'
        stglist = [stg for stg in setting.keys()]
        #stg_name_list=['选择策略']
        stg_name_list = stglist
        
        #print(stglist)
        #print(stg_name_list)
        stgdict = {}
        for stg in stglist: 
            stgdict[stg] = setting[stg]
            if formulastruct[stg] != '0':
                stgdict[stg] = [formhedgeInstid(stgdict[stg])]
        
        curstg = stglist[0]
        
        curinst = stgdict[curstg][0]
        #print('stgdict',stgdict)
        #print('curstg',curstg)
        #print('curisnt',curinst)
        inst_name_list = stgdict[curstg]
        

        ## get data and freq
        freq = getStgFreq(user, token, curstg)
        if freq is None:
            return '没有检测到正在运行的策略，请先在交易时间运行策略。'

        print(tradingDay, stglist, inst_name_list, freq)
        data,datalen, tradedata = getOpenCloseData(user, token, mode, freq, curstg, curinst, tradingDay, 0,\
                                                   data_batch_num)   
        curpos = datalen
        trades_item, tradenum = getTradeItems(tradedata, 1)
        orders_item, ordernum = getOrderItems(user, token, mode, tradingDay, 1)
        position_item = getPositionItems(user, token, mode, tradingDay)
        account_item, balance = getAccountItems(user, token, mode, tradingDay)
        log_item, lognum = getLogItems(user, mode, 1)
        indicators = getIndicators(user, mode, token, float(rfrate))
        #print(rfrate,indicators)
       
        #print('data',data)
        #print('curpos',curpos)
        #print('trades',trades_item)
        #print('orders',orders_item)
        #print('position',position_item)
        #print('account',account_item)
        #print('log', log_item )
        #print('num',tradenum,ordernum, lognum)
        
        pagesett={'shownum':page_batch_num, 'tradenum':tradenum, 'ordernum':ordernum, 'lognum':lognum}
        
        return render_template("image_ex.html", data=data, user=user, mode=mode, curpos=curpos, trades_item=trades_item,\
                               tradingDay=tradingDay, stg_name_list=stg_name_list, curstg=curstg, curinst=curinst,\
                               freq=str(freq), stgdetail=stgdict, token=token, inst_name_list=inst_name_list,indicators=indicators,\
                               orders_item=orders_item, position_item=position_item, account_item=account_item,\
                               log_item=log_item, pagesett = pagesett, balance = balance,status_title = status_title )
                                   

    except Exception as e:
        print('monitor_ex',e, e.__traceback__.tb_lineno)


@app.route('/timer_refresh', methods=['GET', 'POST'])
def timer_refresh():
    try:
        user = request.form.get('user')
        #logger.info(user)
        curpos = request.form.get('curpos')
        curstginst = request.form.get('curstginst')
        mode = request.form.get('mode')
        token= request.form.get('token')       
        freq = request.form.get('freq')       
        tradingDay = request.form.get('tradingday')  
        tradenum = int(request.form.get('tradenum'))
        tradesel = int(request.form.get('tradesel'))
        ordernum = int(request.form.get('ordernum'))
        ordersel = int(request.form.get('ordersel'))
        lognum = int(request.form.get('lognum'))
        logsel = int(request.form.get('logsel'))
        tabname = request.form.get('tabname')
        #print(logrefresh , type(logrefresh))
        if not  curstginst:
            return jsonify({'valid':False})
        
        tradingDay = loadTradingDay(user,token)
        if tradingDay is None:
            tradingDay = getLocalTradingDay()
        else:
            tradingDay = str(tradingDay)
        #print('timer refresh',tradingDay)    
        pid = str(loadDBPid(user, token))
        if pid:
            pidexist = os.path.exists('/proc/'+pid)
            status_title = u'运行中' if pidexist else u'未运行'
        else:
            status_title = u'未运行'
        
        strlist=curstginst.split('_')
        curinst = strlist[-1]
        curstg = '_'.join(strlist[:-1])
        curpos = int(curpos)
        #print('fresh stgdict',curstginst)
        #print('fresh curstg',curstg)
        #print('fresh curisnt',curinst)
       
                
        #print('refresh',curstg, curinst, curpos,freq)
        #print(curpos,curstg,curinst,mode, token, freq, tradingDay,user)
        data,datalen,tradedata = getOpenCloseData(user, token, mode, freq, curstg, curinst, tradingDay,\
                                        curpos, data_batch_num+curpos)   
        curpos += datalen   
        if tabname == 'trades':
            trades_item, totalnum = getTradeItems(tradedata, tradesel)
            if totalnum == tradenum:
                trades_item = ''
        else:
            trades_item = ''
        
        if tabname == 'orders':    
            orders_item, totalnum = getOrderItems(user, token, mode, tradingDay, ordersel)
            if totalnum == ordernum:
                orders_item = ''
        else:
            orders_item = ''
            
        if tabname =='log':
            log_item, totalnum = getLogItems(user, mode, logsel)
            #print('lognum', totalnum)
            if totalnum== lognum:
                log_item = ''
        else:
            log_item = ''
            
        position_item = getPositionItems(user, token, mode, tradingDay)
        account_item, balance = getAccountItems(user, token, mode, tradingDay)
        
        return jsonify({'valid':True, 'data':data, 'curpos':curpos,'tradingday':tradingDay,
                        'trades':trades_item, 'orders':orders_item, 'balance': balance,'status':status_title,
                        'log':log_item, 'account':account_item, 'position':position_item})
        
        
        
    except Exception as e:
        print('monitor_ex',e, e.__traceback__.tb_lineno)
    
@app.route('/change_inst_ex', methods=['GET', 'POST'])
def change_inst_ex():
    try:
        curinst = request.form.get('curinst')
        curstg = request.form.get('curstg')
        user = request.form.get('user')
        token = request.form.get('token')
        mode = request.form.get('mode')
        
        tradingDay = request.form.get('tradingday')    
        freq = getStgFreq(user,token,curstg)
        #print('change inst', user, mode, curstg, curinst, freq)
        if not freq is None:
            curpos = 0
            data,datalen,tradedata = getOpenCloseData(user, token, mode, freq, curstg, curinst, tradingDay, curpos,\
                                            data_batch_num+curpos)   
            curpos += datalen   
            print('changeinst',curstg,curinst, 'curpos',curpos, 'datalen', datalen)
            return jsonify({'valid':True, 'data':data, 'freq':freq, 'curpos':curpos, 'curinst':curinst })
        else:
            return jsonify({'valid':False})
    except Exception as e:
        print('change_inst_ex',e, e.__traceback__.tb_lineno)



@app.route('/page_select_ex', methods=['GET', 'POST'])
def page_select_ex():
    try:
        user = request.form.get('user')
        mode = request.form.get('mode')
        token = request.form.get('token')
        tradingDay = request.form.get('tradingday')
        table = request.form.get('table')
        pagenum = request.form.get('page')
        pagenum = int(pagenum)
        #print('page select', table, pagenum)
        if table =='trades':
            if mode == 'simu':
                tradedata = getDBTradeData(user,token, tradingDay)
            else:
                tradedata = getDBTradeDatareal(user,token,tradingDay)
            for key in tradedata:
                tradedata[key] = eval(tradedata[key])
            content, totalnum = getTradeItems(tradedata, pagenum)        
            
        elif table == 'orders':
            content, totalnum = getOrderItems(user, token, mode, tradingDay, pagenum)
            
        elif table == 'log':
            content, totalnum = getLogItems(user, mode, pagenum)
            
        else:
            content = None
            totalnum = 0
        
        if content:
            #print(content)
            return jsonify({'valid':True, 'content':content, 'totalnum': totalnum})
        else:    
            return jsonify({'valid':False})
    except Exception as e:
        print('page_select_ex',e, e.__traceback__.tb_lineno)
    
@app.route('/stop_all_ex', methods=['GET', 'POST'])
def stop_all_ex():
    user = request.form.get('user')
    token = request.form.get('token')
    pid = loadDBPid(user, token)
    if pid:
        ret = os.system('kill -9 '+pid)
        delDBPid(user,token)
    else:
        ret = -1
    print(pid, ret) 
    if ret == 0:
        return jsonify({'success':True, 'status':u'未运行'})
    else:
        return jsonify({'success':False})

##################################### Back test ###############################################
def reportIndicators(stat, riskfree, benchmark=None):
    try:
        indicators = {}
        annual_workdays = 250
        startbal = stat.loc[stat.index[0],'balance']
        #print('balance', startbal)
        if len(stat) < 2 or (len(stat) >= 2 and  startbal == 0) :
            indicators[u'累积回报率'] = '0.00%'
            indicators[u'年化回报率'] = '0.00%'
            indicators[u'最高水位比'] = '0.00%'
            indicators[u'最大回撤率'] = '0.00%'
            indicators[u'年化波动率'] = '0.00%'
            indicators[u'胜率'] = '0.00%'
            indicators[u'赔率'] = '0'
            indicators[u'下行风险'] = '0.00%'
            indicators[u'Sharpe比率'] = '0'
            indicators[u'Sortino比率'] = '0'
            indicators[u'Calmar比率'] = '0'
            indicators[u'最大保证金比率'] = '0.00%'
            indicators[u'无风险利率'] = round(100*riskfree,2)
            return indicators
            
        #print(stat.index)
        #print(type(stat.index[0]))
        #totaldays = (stat.index[-1] - stat.index[0]).days + 1
        totaldays = len(stat)
        #print(totaldays)
        indicators[u'记录天数'] = totaldays
        indicators[u'累积回报率'] = str(round(100*stat.loc[stat.index[len(stat)-1],'accret'],2))+'%'
        arr = stat.loc[stat.index[len(stat)-1],'accret']*annual_workdays / totaldays
        indicators[u'年化回报率'] = str(round(100*arr,2))+'%'
        indicators[u'最高水位比'] = str(round(100*stat.loc[stat.index[len(stat)-1],'highwater']/startbal,2))+'%'
        maxdrawback = min(stat.drawback)/startbal
        indicators[u'最大回撤率'] = str(round(100*maxdrawback,2))+'%'
        avol = np.std(stat.dayret) * np.sqrt(annual_workdays)
        indicators[u'年化波动率'] = str(round(100*avol,2))+'%'
        if sum(stat.wincount) + sum(stat.losscount) > 0:
            indicators[u'胜率'] = str(round(100*sum(stat.wincount) / (sum(stat.wincount) + sum(stat.losscount)),2))+'%'
        else:
            indicators[u'胜率'] = '0.00%'
            
        if np.mean(stat.lossamount) != 0:
            odd = abs(np.mean(stat.winamount)) / abs(np.mean(stat.lossamount))   
        else:
            odd = 1
        indicators[u'赔率'] = str(round(odd,2))
        downside = [-ret for ret in stat.dayret if ret < riskfree]
        if len(downside) > 0:
            indicators[u'下行风险'] = str(round(100* np.std(downside),2 ))+'%'
        else:
            indicators[u'下行风险'] = '0.00%'
        if avol != 0:
            indicators[u'Sharp比率'] = str(round((arr - riskfree)/avol,2))
        else:
            indicators[u'Sharp比率'] = '0'
        if  np.std(downside) != 0:   
            indicators[u'Sortino比率'] = str(round((arr - riskfree)/(np.std(downside)*np.sqrt(annual_workdays)),2))
        else:
            indicators[u'Sortino比率'] = '0'
        if maxdrawback != 0:
            indicators[u'Calmar比率'] = str(round((arr - riskfree)/abs(maxdrawback),2))
        else:
            indicators[u'Calmar比率'] = '0'
        indicators[u'最大保证金比率'] = str(round(100*max(stat.maxmarg)/startbal,2))+'%'
        #indicators[u'无风险利率'] = str(round(100*riskfree,2))+'%'
        if benchmark:
            if len(benchmark) != len(stat):
                print('benchmark必须是与回测同时间段，同等长度的日对数收益率')
            else:
                try:
                    indicators['relativeret'] = stat.accret[-1] - sum(benchmark)
                    indicators['arrr'] = annual_workdays * indicators['relativeret'] / totaldays 
                    stat2 = pd.DataFrame(columns=['a','b'])
                    stat2['a'] = list(stat['dayret'])
                    stat2['b'] = list(benchmark)
                    stat2 = stat2[stat2.a != 0]
                    indicators['correlation'] = stat2['a'].corr(stat2['b'])
                    ssr = np.sum((stat2.a - stat2.b) ** 2)
                    sst = np.sum((stat2.a - np.mean(stat2.a))** 2)
                    if sst != 0:
                        indicators['rsquare'] = 1-float(ssr)/sst
                    else:
                        indicators['rsquare'] = 0
                except:
                    print("Invalid benchmark data.")
            
        return indicators
    except Exception as e:
        print('reportIndicators',e, e.__traceback__.tb_lineno)
        return {}


def getCapChart(stat,stratname):
        img = io.BytesIO()
        stat.index = np.array(stat.index)
        fig = plt.figure(figsize=(8,5))
        ax = fig.add_subplot(111)
        ax.plot(stat.index, stat['balance'], '-', c='blue', label='Balance')
        #line1=Report[instids[0]]['underwater']
        #line1
        #ax.fill_between(Report[instids[0]].index,0,Report[instids[0]]['underwater'],'lightblue')
        ax.legend(loc=2)
        #ax.grid()
        ax.set_title(stratname+' 资金和保证金占用')
        ax.set_xlabel('Date')
        ax.set_ylabel('money:RMB')
        ax2 = ax.twinx()
        # ax2.plot(Report.index, Report['longpos'],'-r',c='red',label='Long Position')
        # ax2.plot(Report.index, Report['shortpos'],'-r',c='green',label='Short Position')
        ax2.plot(stat.index, stat['drawback'], '-', c='orange', label='underwater')
        ax2.fill_between(stat.index.values, list(stat['drawback']),0, facecolor='orange', alpha=0.3)
        
        ax2.scatter(stat.index, stat['maxmarg'], s=5, marker='o',
                        alpha=0.5,
                        label='maxmargin')
        
        ax2.legend(loc=4)
        ax2.set_ylabel("Maxium Margin")
        fig.savefig(img, format='png')
        img.seek(0)
         
        return base64.b64encode(img.getvalue()).decode()

def getPnlChart(Report,stratname):
        img = io.BytesIO()
        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_subplot(111)
        ax.plot(Report.index, Report['accret'], '-', c='red', label='Accumulative Return')
        ax.plot(Report.index, Report['dayret'], '-', c='orange', label='Daily Log Return')
        ax.legend(loc=2)
        ax.grid()
        ax.set_title(stratname+' 回报率和盈亏')
        ax.set_xlabel('Date')
        ax.set_ylabel('Return Rate')
        ax2 = ax.twinx()
        ax2.plot(Report.index, Report['accpnl'], '-r', c='darkblue', label='Total P&L')
        ax2.plot(Report.index, Report['accfee'], '-r', c='mediumblue', alpha=0.5, label='Total Commission')
        ax2.legend(loc=4)
        ax2.set_ylabel("money:RMB")
        fig.savefig(img, format='png')
        img.seek(0)
        return base64.b64encode(img.getvalue()).decode()


def getCompressDict(data):
    d = {}
    if data is None or len(data) == 0:
        return d
    fdata = data.fillna(0)
    d['index'] = list(fdata.index.strftime('%Y-%m-%d %H:%M:%S'))
    if 'openlong' in fdata.columns:
        d['openlong'] = list(fdata.openlong)
    if 'openshort' in fdata.columns:
        d['openshort'] = list(fdata.openshort)
    if 'closelong' in fdata.columns:
        d['closelong'] = list(fdata.closelong)
    if 'closeshort' in fdata.columns:
        d['closeshort'] = list(fdata.closeshort)
    if 'open' in fdata.columns:
        d['open'] = list(fdata.open)
        if 'close' in data.columns:
            d['close'] = list(fdata.close)
        else:
            d['close'] = list(fdata.current)
            
        d['high'] = list(fdata.high)
        d['low'] = list(fdata.low)
        d['volume'] = list(fdata.volume)
    
        
    else:
        d['current'] = list(fdata.current)
        
    #print(d)
    return d

@app.route('/backtest_pagesel',methods=['GET', 'POST'])
def backtest_pagesel():
    pagemax = 100
    user = request.form.get('user').replace(' ','')
    pagenum = int(request.form.get('page'))
    table = request.form.get('table')
    print(user, pagenum, table)
    if table == 'trades':
        ttrades = loadBackTestList(user, 'trades', (pagenum-1)*pagemax, pagenum*pagemax)
        if not ttrades is None:
            trades = pd.DataFrame.from_dict(ttrades, orient='index')
            trades = trades.drop(columns=['price','current','posprof'])
            trades.columns=['时间','操作类型','多空','合约名','成交价','成交量','订单编号','多头持仓均价','空头持仓均价','平仓盈亏','日期']
            
            return jsonify({'result':True,'data':trades.to_html(classes='table table-striped')})
        else:
            return jsonify({'result':False})
        
    elif table == 'orders':
        torders = loadBackTestList(user,'orders',(pagenum-1)*pagemax, pagenum*pagemax )
        if not torders is None:
            orders = pd.DataFrame.from_dict(torders, orient='index')
            orders = orders.drop(columns=['pendvol','errorid'])
            orders.columns=['合约名','时间','价格','多空','订单类型','平仓类型','下单量','剩余量','成交量','撤单量',\
                                '状态','错误信息',"时态",'操作类型']
          
            return jsonify({'result':True,'data':orders.to_html(classes='table table-striped')})
        else:
            return jsonify({'result':False})
       
    elif table == 'stat':
        stat = loadBackTestReport(user, 'Stat')   
        if not stat is None:
            stat = stat.drop(columns=['highwater','winamount','wincount','lossamount','losscount'])
            stat.columns=['日收益率','累积收益率','日盈亏','累积盈亏','最大保证金','交易额','回撤','日手续费','累积手续费','资金']
            stat_show = stat.iloc[(pagenum-1)*pagemax:pagenum*pagemax,:]
            return jsonify({'result':True,'data':stat_show.to_html(classes='table table-striped')})
        else:
            return jsonify({'result':False})
        
        
@app.route('/backtestinst',methods=['GET', 'POST'])
def backtest_instchange():
    inst = request.form.get('instid')
    user = request.form.get('user').replace(' ','')
    #if inst == 'test':
    #    inst = 'AG2112.SFE'
    #print(user,type(user),inst,type(inst))
    data =  loadBackTestData(user, inst,False)  
    print(len(data))
    if isinstance(data, dict):
        print(data.keys())
    if not data is None:
        rawdata = getCompressDict(data)
        #print(rawdata)
        return jsonify({'result':True,'data':rawdata})
    else:
        return jsonify({'result':False})

@app.route('/backtest', methods=['GET', 'POST'])
def backtest():
    try:
        pagemax = 100
        user = request.args.get('user')  # user
        rfrate = request.args.get('rfrate')
        if user == None:
            return '请输入user'
        if rfrate is None:
            rfrate = 0.02
        setting = loadBackTestSetting(user)
        if setting:
            #print(setting)
            instids = setting['instids']
            stratname = setting['stratname']
            if setting['hedge']:
                data = loadBackTestData(user, "", setting['hedge'])
            else:
                inst = instids[0]
                data = {inst : loadBackTestData(user, inst,False)}
                #print(inst, data[inst])
                            
            torders = loadBackTestList(user,'orders', 0, pagemax)
            order_cols = ['合约名','时间','价格','多空','订单类型','平仓类型','下单量','剩余量','成交量','撤单量',\
                                '状态','错误信息','时态','操作类型']
            if not torders is None:
                orders = pd.DataFrame.from_dict(torders, orient='index') 
                if len(orders) > 0:
                    orders = orders.drop(columns=['pendvol','errorid'])
                    orders.columns= order_cols
            else:
                orders = pd.DataFrame(columns=order_cols)
                        
            ttrades = loadBackTestList(user, 'trades', 0, pagemax)
            trade_cols = ['时间','操作类型','多空','合约名','成交价','成交量','订单编号','多头持仓均价','空头持仓均价','平仓盈亏','日期']
            if not ttrades is None:
                trades = pd.DataFrame.from_dict(ttrades, orient='index') 
                if len(trades) > 0:
                    trades.closeprof = trades.closeprof.diff(1).fillna(0)
                    trades = trades.drop(columns=['price','current','posprof'])
                    trades.columns=   trade_cols
            else:
                trades = pd.DataFrame(columns=trade_cols)
                
            stat = loadBackTestReport(user, 'Stat')   
            
            indicators = reportIndicators(stat, float(rfrate))
            show_insts = instids if not setting['hedge'] else []
            plot_cap = getCapChart(stat,stratname)
            plot_pnl = getPnlChart(stat,stratname)
            if setting['hedge']:
                plot_data = json.dumps(getCompressDict(data))
            
            else:
                plot_data = json.dumps(getCompressDict(data[instids[0]]))
            chartmode = 'tick' if setting['datamode'] == 'tick' or setting['hedge'] else 'bar'     
            stgdetail={'user':user,'insts':show_insts,'tradenum':setting['tradenum'],'ordernum':setting['ordernum'],'statnum':len(stat),'chartmode':chartmode}
            stat = stat.drop(columns=['highwater','winamount','wincount','lossamount','losscount'])
            stat.columns=['日收益率','累积收益率','日盈亏','累积盈亏','最大保证金','交易额','回撤','日手续费','累积手续费','资金']
            #print(instids)
            orders_show = orders.iloc[:pagemax,:]
            trades_show = trades.iloc[:pagemax,:]
            stat_show = stat.iloc[:pagemax,:]

            return render_template("backtest.html",user=user, stratname=stratname, stgdetail=stgdetail, orders_item=orders_show.to_html(classes='table table-striped'),\
                                   trades_item=trades_show.to_html(classes='table table-striped'),stat_item=stat_show.to_html(classes='table table-striped'),\
                                   indicators=indicators, plot_cap=plot_cap,plot_pnl=plot_pnl,plot_data=plot_data)
            
        else:
            return "该回测数据不存在。"
    
    except Exception as e:
        print("backtest", e.__traceback__.tb_lineno, e)


#################################基本面页面################################################
@app.route('/fundhome', methods=['GET', 'POST'])
def fundhome():
    return render_template("fundhome.html")

def runWebpage():
     
    try:
        json_data = read_sysconfig()
        if json_data:
            webpage_config = json_data['webpage']
            print(f"Run webpage on {webpage_config['host']}:{webpage_config['port']}")
            app.run(host=webpage_config['host'],port=webpage_config['port'])
        else:
            print('Error to parse sysconfig.json')
        #from config import webpage_config
    except Exception as e:
        print(f'Error:{e.__traceback__.tb_lineno} {e}')
        return 
    #app.run(host=webpage_config['ip'],port=webpage_config['port'])

    
if __name__ == '__main__':
    #app.run()
    runWebpage()

