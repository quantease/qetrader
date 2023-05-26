# -*- coding: utf-8 -*-
"""
Created on Wed Nov  3 11:30:36 2021

@author: ScottStation
"""

from multiprocessing.dummy import Pool
from multiprocessing import Queue, cpu_count
from .qectpmarket_wrap import runQEMarketProcess,  checkMarketTime
from .qestockmarket import runStockMarketProcess, checkStockTime
#from .qectptrader import runQERealTraderProcess
from .qectptrader_wrap import runQERealTraderProcess
from .qesimtrader import  runQETraderProcess #, getCurTradingDay
from .qestratprocess import qeStratProcess
from .qeasyncstrat import qeAsyncStratProcess
from .qelogger import logger, initLogger
#from .qeriskctl import soptriskctl, ctpriskctl
from .qeinterface import qeStratBase, simuqueue
from .qestatistics import g_stat
from .qebacktestmul import runBacktest, historyDataBackTest, dynamicBacktest
from .qeredisdb import savePidToDB,saveStrategyfreqToDB,initMyredis
#from .qecsvorder import qeCsvOrders
from .qeglobal import  getAccidTraderQueue, setClassAccID
from .qesysconf import read_sysconfig
#from .qecsvorder import g_csvorders


try:
    from codeconfig import getSoptFuncs
    soptmd, sopttime, sopttd = getSoptFuncs()    
except:
    soptmd, sopttime, sopttd = None, None, None
#from .qesoptmarket import runQEMarketSoptProcess, checkSoptMarketTime
#from .qesopttrader import runQESoptTraderProcess




import os
# import time
from datetime import datetime
#from .qetype import *

from .qeredisdb import saveSettingDataToDB, saveFormulaDataToDB, saveSettingDatarealToDB, saveFormulaDatarealToDB
from .qeredisdb import isTokenValid
#from qedata.qeaccounts import checkUserValid
from qesdk import get_broker_info, check_auth
#import qedata
from .qeudpclient import udpClient_bar
from .qeaccount import realAccountInfo


     
        


# stratqueue = multiprocessing.Queue()

# mdqueue = Queue()

processlist = []
curuser = 'test'
tdqueue_ready = False

master_strat_id = 10


def getuserid(user):
    if user[:5] != '/home':
        return None
    loc = user[6:].find('/')
    if loc < 0:
        return user[6:]
    else:
        return user[6:6 + loc]




def noticMarketReady():
    logger.info('Market is Ready')






def processFunc(processInfo):
    '''
    Parameters
    ----------
    processInfo : TYPE
        type: 'trader','market','strat'.
        name: str
        insts: list of instIDs
        queue: msgqueue
    Returns
    -------
    None.

    '''
    global curuser
    try:
        #print(processInfo)
        #print(type(processInfo))
        

        if processInfo['type'] == 'market':
            if processInfo['name'].find('ctp') >= 0:
                if processInfo['setting']:
                    runQEMarketProcess(curuser,'888888',processInfo['strats'],processInfo['runmode'], processInfo['setting'],processInfo['mode_724'])
                else:
                    runQEMarketProcess(curuser,'888888',processInfo['strats'],processInfo['runmode'],None)
                logger.info("add ctp Market")
            elif processInfo['name'].find('sopt') >= 0 and soptmd:
                soptmd(curuser,'888888',processInfo['strats'],processInfo['runmode'], None)
                logger.info("add sopt Market")
            elif processInfo['name'].find('stock') >= 0:
                runStockMarketProcess(curuser,'888888',processInfo['strats'],processInfo['runmode'])
                logger.info("add stock Market") 
            
        elif processInfo['type'] == 'trader':
            logger.info("add simulation Trader")
            # balance=processInfo['balance']
            runQETraderProcess(curuser, processInfo['token'],processInfo['strats'] ,simuqueue, processInfo['mode_724'])
            #tdqueue_ready = True
        #             runQETraderProcess(curuser, '888888',None)
        elif processInfo['type'] == 'realtrader' :
            if processInfo['name'].find('ctp')>=0:
                runQERealTraderProcess(curuser,processInfo['account'], processInfo['class'], processInfo['strats'], processInfo['queue'] , processInfo['setting'], processInfo['mode_724'])
            elif processInfo['name'].find('sopt')>=0 and sopttd:
                sopttd(curuser, processInfo['account'],processInfo['class'], processInfo['strats'], processInfo['queue'] , processInfo['setting'], processInfo['mode_724'])
            #tdqueue_ready = True
        elif processInfo['type'] == 'strat':
            print("add Strat: "+str(processInfo['name']))
            #print(processInfo['data'].freq)
            #apiset = processInfo['data'].mduser
                
            processInfo['data'].user = curuser
            processInfo['data'].stratProcess(processInfo['strat'])
        elif processInfo['type'] == 'bar':
            udpClient_bar(processInfo['api'])
    except Exception as e:
        logger.error("qemain_pf: " + str(e), exc_info=True)


def checkformula(strat):
    if strat.formula is None:
        return False
    elif len(strat.instid) == 0:
        return False
        logger.info('1 instrument')
    elif strat.formula is not None and len(strat.instid) == 1:
        logger.info('formula is not None but 1 instrument')
        return False
    elif strat.formula is not None and len(strat.instid) >= 2:
        return True



def getAddress(user, mode, account, rfrate=0.02):
    # webaddress = socket.gethostbyname(socket.gethostname())
    ip = '127.0.0.1:5000'
    try:
        #from .qedockerconfig import log_path
        with open('/srv/jupyterhub/webhost', 'r') as f:
            ip = f.read()
            if ip[-1] == '\n' or ip[-1] == '\t' or ip[-1] == '\r':
                ip = ip[:-1]
    except:
        json_data = read_sysconfig()
        if json_data:
            ip = f"{json_data['webpage']['host']}:{json_data['webpage']['port']}"
    if mode=='simu':
        address="http://" + str(ip) + "/monitor_ex?user=" + str(user) + "&mode=" + str(mode)+"&token="+str(account) + "&rfrate=" + str(rfrate)
    else:
        address="http://" + str(ip) + "/monitor_ex?user=" + str(user) + "&mode=" + str(mode)+"&investorid="+str(account) + "&rfrate=" + str(rfrate)

    return address


def startSimuProcess(user, token, strats, feesmult=1.0, ignorepass=True, mode_724=False, 
                     simnow724_account=None, md=['ctp'], printlog=True, rfrate=0.02, record_strat=False, async_strats=False):
    global processlist, curuser, master_strat_id
    #if not ignorepass and not checkUserValid(user):
    #    print(u'您的用户名或密码不正确。')
    #    return
    if not check_auth():
        print("您还没有获得授权，请先在quantease官网获取授权码，详见https://quantease.cn/newdoc/auth.html")
        return
    now = datetime.now()
    if not isinstance(user, str):
        print('user必须是字符串')
        return
    if not isinstance(token, str):
        print('token必须是字符串')
        return
    if not isTokenValid(user, token):
        print('不合法的token，请使用createSimuAccount函数获取合法模拟账号.')
        return
    if not isinstance(strats, list):
        print('strats 必须是 list 类型')
        return
    if not isinstance(feesmult, float):
        print("feesmult 必须是 float 类型")
        return None
    if feesmult<0:
        print("feesmult 不能为负数")
        return None

    nameset = set()
    i = 0
    for strat in strats:
        if not isinstance(strat, qeStratBase):
            print('strats 必须是 qeStratBase类型策略类的list. ')
            return
        if not hasattr(strat, 'instid') or (not isinstance(strat.instid, str) and not isinstance(strat.instid, list)):
            print('策略必须包含属性instid, strat.instid是合约名或者合约名的列表')
            return
        
        else:
            if isinstance( strat.instid, str):
                strat.instid = [strat.instid]
            for inst in strat.instid:
                if not isinstance(inst, str):
                    print('strat.instid是合约名或者合约名的列表')
                    return
                if inst.find('.') < 0:
                    print('instid不是合法的用户名.')
                    return
            
            for j in range(len(strat.instid)):
                strat.instid[j]=strat.instid[j].upper()
                
                
            if strat.recordinsts:
                if not isinstance(strat.recordinsts, list):
                    print("strat.recordinsts must be list.")
                    return None
                for inst in strat.recordinsts:
                    if not inst in strat.instid:
                        print('The member of reocrdinsts', inst, 'is not in strat.instid')
                        return None
            
            
            


        if (not hasattr(strat, 'name')) or strat.name == None:
            strat.name = 'stg%d' % (i)
            nameset.add(strat.name)
        elif not strat.name in nameset:
            nameset.add(strat.name)
        else:
            print(strat.name, nameset)
            print('策略名strat.name必须是唯一的，并且不要使用stg[0-9]来作为策略名称，因其与系统冲突.')
            return
        i += 1

    #if os.path.exists('mduser.pid'):
    #    with open("mduser.pid", 'r') as f:
    #        os.system('kill - 9 ' + f.read())
    #with open("mduser.pid", 'w') as f:
    #    f.write(str(os.getpid()) + '\n')
    #    print('pid:'+str(os.getpid()))
    savePidToDB(user, token, str(os.getpid()))
    #with open(f'/var/log/qelog/{user}_{token}.pid','w') as f:
    #    f.write(str(os.getpid()))
    g_stat.setUserToken(user, token)
    # qectpmarket.marketInit(user, '888888')
    #allocateMdFuncs(md)
    if not mode_724:
            markettime = False
            if ('ctp' in md or 'ctptest' in md) and checkMarketTime(now):
                markettime = True
            if ('sopt' in md or 'sopttest' in md) and sopttime and sopttime(now):
                markettime = True
            if 'stock' in md and checkStockTime(now):
                markettime = True
            if not markettime:    
                print(u"市场此时没有开盘.")
                return
    print('请通过如下网址查看交易：')
    print(str(getAddress(user, mode='simu',account=token,rfrate=rfrate)))
    curuser = user.replace('/', '')
    initLogger(curuser, False,printlog=printlog)
    
    #if csv_orders:
    #    csvstrat = qeCsvOrders()
    #    strats.append(csvstrat)
    
    #tradingday = getCurTradingDay()
    #g_stat.loadFromDBSimu(curuser, token, tradingday)
    d = {}
  
    if mode_724 and simnow724_account is None:
        print("模拟测试使用7*24小时模式必须提供simnow账号信息")
        return
    if mode_724 and simnow724_account:
        if not isinstance(simnow724_account,dict) or not 'investorid' in simnow724_account or not 'password'  in simnow724_account:
            print("SIMNOW 7*24账号信息必须是dict类型并含有如下key：'investorid', 'password' ")
            return 
        
    
        d['investorid'] = simnow724_account['investorid']
        d['password'] = simnow724_account['password']
        d['brokerid'] = '9999'
        d['mdaddress'] = 'tcp://180.168.146.187:10131'
        d['api'] = 'ctp'
        #d['recmode'] = record_strat
    settings = d if mode_724 else None
    # watchdog_bar
    #wait_all=[]
            
    #print(wait_all,"#")
    bar_flag = sum([strat.freq for strat in strats]) > 0
    if bar_flag:
        barprocess = {'type': 'bar','api':md}
        processlist.append(barprocess)
    '''
    if 'all' and 'new' in wait_all:
        barprocess = {'type': 'bar','wait_all':'both','freq':freq}
        processlist.append(barprocess)
    elif 'all' in wait_all:
        barprocess = {'type': 'bar','wait_all':'all','freq':freq}
        processlist.append(barprocess)
    elif 'new' in wait_all:
        barprocess = {'type': 'bar','wait_all':'new','freq':freq}
        processlist.append(barprocess)
    '''
    stratSetts={}
    if not async_strats:
        for strat in strats:
            stratQueue = Queue()  # multiprocessing.Queue()
            # strat.addQueue('strat',stratQueue)
            # strat.addQueue('td',traderqueue)
    
            strategy = qeStratProcess(strat.name,  stratQueue)
            ishedgemodel = checkformula(strat)
            strategy.hedgemodel = ishedgemodel
            strategy.formula = strat.formula
            strategy.printlog = printlog
            strat.user = curuser
            strategy.token = token
            strat.hedgemodel = ishedgemodel
            #strategy.instid_ex, strategy.exID = transInstID2Real(strat.instid)
            strategy.flippage, strategy.traderate = strat.flippage, strat.traderate
            strategy.feesmult = feesmult
            master_strat_id += 1
            strategy.ID = master_strat_id
            strategy.instid = strat.instid
            strategy.trader = 'simu'
            strategy.mduser = md
            strategy.recmode = record_strat
            #print(freq)
            strategy.freq=strat.freq
            strategy.datamode = strat.datamode
            strategy.wait_all=strat.wait_all
            #print(333)
            #print(strat.wait_all)
            stratSetts['async'] = False
            stratSetts[strat.name] ={'queue':stratQueue,'instid':strat.instid, 'strat':strat,'datamode':strat.datamode}
            stratprocess = {'type': 'strat', 'name': strat.name, 'strat': strat, 'data': strategy}
            # stratprocess = {'type':'strat','name':strat.name,'insts':transInstIDs( strat.insts), 'queue':stratqueue}
            processlist.append(stratprocess)
    else:
        stratQueue = Queue()
        strategy = qeAsyncStratProcess([strats], stratQueue)  
        strategy.printlog = printlog
        strategy.token = token
        strategy.trader = 'simu'
        strategy.mduser = md
        strategy.recmode = record_strat
        for strat in strats:
            strat.user = curuser
            strat.hedgemodel = checkformula(strat)
        stratprocess = {'type': 'strat', 'name': 'asyncstrat', 'strat': strats, 'data': strategy}
    #queuesett ={'runmode':'simu','queue': simuqueue}
    
        stratSetts ={'async':True,'queue':stratQueue,'strat':strats, 'recmode': record_strat}
        processlist.append(stratprocess)
    
    for m in md:
        mode724 = mode_724 if m.find('ctp') >=0 else False
        mdprocess = {'type': 'market', 'name': m, 'setting': settings,"mode_724":mode724,'strats':stratSetts, 'runmode':'simu'}
        processlist.append(mdprocess)

    traderprocess = {'type': 'trader', 'name': 'ctp', 'insts': [], 'token':token,"mode_724":mode_724,'strats':stratSetts}
    processlist.append(traderprocess)

    stgsetts = {}
    stgformual = {}
    stgimagesetts ={}
    for strat in strats:
        if strat.name != 'csvorders':
            stgsetts[strat.name] = strat.instid
            if strat.hedgemodel:
                stgformual[strat.name] = strat.formula
            else:
                stgformual[strat.name] = '0'
            if strat.recordinsts:
                stgimagesetts[strat.name] = strat.recordinsts
            else:
                stgimagesetts[strat.name] = strat.instid


    saveSettingDataToDB(curuser, token, stgsetts)
    saveFormulaDataToDB(curuser, token, stgformual)
    freq = { strat.name : strat.freq for strat in strats}
    saveStrategyfreqToDB(curuser,token, freq)
    #aveImageSettingDataToDB(curuser, stgimagesetts)

    with Pool(max(int(cpu_count()), 10)) as pool:
        results = pool.map(processFunc, processlist)


def startRealProcess(user, strats, user_setting, feesmult=1.0, ignorepass=True, mode_724=False,  riskctlparas=None,printlog=True,rfrate=0.02, record_strat=False, async_strats=False, skip_settle_check=False):
    global processlist, curuser, master_strat_id
    #if not ignorepass and not checkUserValid(user):
    #    print(u'您的用户名或密码不正确。')
    #    return
    if not check_auth():
        print("您还没有获得授权，请先在quantease官网获取授权码，详见https://quantease.cn/newdoc/auth.html")
        return
    if user_setting is None or len(user_setting) == 0:
        print("参数real_account不能为空")
        return
    now = datetime.now()
    if not isinstance(user, str):
        print('user必须是合法用户名')
        return

    if not isinstance(strats, list):
        print('strats必须是qeStratBase类型实例的列表')
        return
    
    if riskctlparas and not isinstance(riskctlparas, dict):
        print("风控参数设置错误，必须是dict.")
        return 
    

    flag = True
    d = {}
    d['api'] = 'ctp'
    d['broker'] = 'simnow'
    d['class'] = 'future'
    d['investorid'] = 'username'
    d['password'] = '123456'
    d['appid'] = 'quantease_1.0'
    d['authcode'] = '0000000000000000'
    d['brokerid'] = '9999'
    d['tdaddress'] = 'tcp://180.168.146.187:10101'
    d['mdaddress'] = 'tcp://180.168.146.187:10111'

    if isinstance(user_setting,dict):
        user_setting =[user_setting]
    if not isinstance(user_setting, list):
        print('real_account必须是dict类型或者dict类型的列表')
        return
    
    classset = set()
    accounts = []
    apiset= set()
    evalmode = False
    for j in range(len(user_setting)):
        sett = user_setting[j]
        brokerinfo = get_broker_info(sett['broker'])
        if not 'broker' in sett or brokerinfo is None:
            print("检查user_setting的'broker'不合法")
            return
        for key in brokerinfo:
            if not key in sett:
                user_setting[j][key] = brokerinfo[key]
            
        if set(d.keys()) == set(sett.keys()):
            flag = True
        else:
            flag = False

        for k in sett.keys():

            if sett[k] == '' or (not isinstance(sett[k], str)):
                flag = False
                
        # print('flag '+str(flag))
        if flag == False:
            print("请检查real_account, 必须是合法的ctp配置。该dict示例如下：\n real_account =", d)
            return
        if not sett['api'] in ['ctp','ctptest','sopt','sopttest']:
            print(" real_account的api必须是‘ctp’或者'sopt'")
            return
        if not sett['class'] in ['future','stock', 'stockoption']:
            print(" real_account的class建议是'future','stock'或者'stockoption',您设置的class为", sett['class'])
            return 
        #if sett['class'] in classset:
        #    print("账号class不可重复, 重复class：",sett['class'])
        #    return
        else:
            classset.add(sett['class'])
            accounts.append(realAccountInfo(accid=j))
            setClassAccID(sett['class'], j)
        apiset.add(sett['api'])
        if sett['api'].find('test') > 0:
            evalmode = True
    
    #print(user_setting)
    #print(apiset)
    #print(classset)
    token = user_setting[0]['investorid']
    if len(user_setting) > 1:
        for si in range(1,len(user_setting)):
            token = token + '_' + user_setting[si]['investorid']
    
    ## Ask for user's confirm for 对账单
    if not skip_settle_check:
        answer = ''
        while not answer.lower() in ['y','n']:
            answer = input("您是否已经查看并确认了监控中心发给您的上个交易日对账单(y表示已确认,n程序将终止）？(y/n)")
        if answer == 'n':
            print('请通过期货公司官方平台查询并确认监控中信发给您的上个交易日对账单。')
            return
        answer2 = ''
        while not answer2.lower() in ['y','n']:
            answer2 = input("您是否已经知晓若您确认已经核对过对账单，所有因此产生的对账单纠纷和责任由您自行承担，与平台无关。(y表示确认,n程序将终止）？(y/n)")
        if answer2 == 'n':
            print('请通过期货公司官方平台查询并确认监控中信发给您的上个交易日对账单。')
            return
        print('对账单已确认。')
    
    #user_setting_dict = user_setting
    # user_setting_dict = user_setting.data
    savePidToDB(user, token, str(os.getpid()))
    #with open(f'/var/log/qelog/{user}_{token}.pid','w') as f:
    #    f.write(str(os.getpid()))
    g_stat.setUserToken(user, token)
    try:
        #allocateTdFuncs(td)
        #allocateMdFuncs(md)
        if not mode_724:
            markettime = False
            if ('ctp' in apiset or 'ctptest' in apiset) and checkMarketTime(now):
                markettime = True
            if ('sopt' in apiset or 'sopttest' in apiset) and sopttime and sopttime(now):
                markettime = True
            if 'stock' in apiset and checkStockTime(now):
                markettime = True
            if not markettime:    
                print(u"市场此时没有开盘.")
                return
        print('请通过如下网址查看交易：')
        print(str(getAddress(user, mode='real',account=token,rfrate=rfrate)))
        #if csv_orders:
        #    csvstrat = qeCsvOrders()
        #    strats.append(csvstrat)

        nameset = set()
        i = 0
        for strat in strats:
            if not isinstance(strat, qeStratBase):
                print('strat策略必须是 qeStratBase类型或者qeStratBase类型实例的列表 . ')
                return
            if not hasattr(strat, 'instid') or (not isinstance(strat.instid, str) and not isinstance(strat.instid, list)):
                print('策略必须包含属性instid, strat.instid是合约名或者合约名的列表')
                return
            else:
                if isinstance(strat.instid, str):
                    strat.instid = [strat.instid]
                for inst in strat.instid:
                    if not isinstance(inst, str):
                        print(' strat.instid是合约名或者合约名的列表')
                        return
                    if inst.find('.') < 0:
                        print('不合法的策略名称.',inst)
                        return
                for j in range(len(strat.instid)):
                    strat.instid[j]=strat.instid[j].upper()
                #print(strat.instid)
                if strat.recordinsts:
                    if not isinstance(strat.recordinsts, list):
                        print("strat.recordinsts must be list.")
                        return None
                    for inst in strat.recordinsts:
                        if not inst in strat.instid:
                            print('The member of reocrdinsts', inst, 'is not in strat.instid')
                            return None

            if (not hasattr(strat, 'name')) or strat.name == None:
                strat.name = 'stg%d' % (i)
                nameset.add(strat.name)
            elif not strat.name in nameset:
                nameset.add(strat.name)
            else:
                print('策略名strat.name必须是唯一的，并且不要使用stg[0-9]来作为策略名称，因其与系统冲突.')
                return
            i += 1

        #         if os.path.exists('mduser.pid'):
        #             with open("mduser.pid",'r') as f:
        #                 os.system('kill - 9 '+f.read())
        #         with open("mduser.pid",'w') as f:
        #             f.write(str(os.getpid())+'\n')
        #             print('pid:',os.getpid() )

        # qectpmarket.marketInit(user, '888888')
        curuser = user.replace('/', '')
        initLogger(curuser, True,printlog=printlog)
        print("logger initialized")
        #tradingday = getCurTradingDay()
        #g_stat.loadFromDBReal(curuser, [user_setting['investorid']], tradingday)
        
                

        #print(wait_all,"#")
        bar_flag = sum([strat.freq for strat in strats]) > 0
        if bar_flag:
            barprocess = {'type': 'bar','api':apiset}
            processlist.append(barprocess)
        #if 'stockoption' in classset and riskctlparas:
        #    if 'dailymax' in riskctlparas:
        #        soptriskctl.setDailyMax(riskctlparas['dailymax'])
        #    if 'secmax' in riskctlparas:
        #        soptriskctl.setSecMax(riskctlparas['secmax'])
        #elif 'ctp' in apiset and riskctlparas:
        #    if 'dailymax' in riskctlparas:
        #        ctpriskctl.setDailyMax(riskctlparas['dailymax'])
        
        stratQueues = {}
        stratSetts = {}
        for strat in strats:
            stratQueue = Queue()  # multiprocessing.Queue()
            # strat.addQueue('strat',stratQueue)
            # strat.addQueue('td',traderqueue)
            #         print(strat.instid)
            #         print(strat.instid_ex)

            strategy = qeStratProcess(strat.name, stratQueue, True)  # realtrade
            ishedgemodel = checkformula(strat)
            strategy.hedgemodel = ishedgemodel
            strategy.formula = strat.formula
            strategy.printlog = printlog
            strategy.evalmode = evalmode
            strat.hedgemodel = ishedgemodel
            #strategy.instid_ex, strategy.exID = transInstID2Real(strat.instid)
            strategy.flippage, strategy.traderate = strat.flippage, strat.traderate
            strategy.feesmult = feesmult
            master_strat_id += 1
            strat.user = curuser
            strategy.token = token
            strategy.ID = master_strat_id
            strategy.instid = strat.instid
            strategy.trader = list(classset)
            strategy.mduser = list(apiset)
            strategy.recmode = record_strat
            #print("#",strategy.wait_all)
            strategy.wait_all=strat.wait_all
            
            strategy.freq=strat.freq
            strategy.datamode = strat.datamode
            strategy.accounts = accounts
            stratSetts['async'] = False
            stratSetts[strat.name] ={'queue':stratQueue,'instid':strat.instid, 'strat':strat,'datamode':strat.datamode}
            
            stratQueues[strat.name] = {'instid':strat.instid, 'queue':stratQueue,'datamode':strat.datamode}

            stratprocess = {'type': 'strat', 'name': strat.name, 'strat': strat, 'data': strategy}

            processlist.append(stratprocess)

        mdlist = []
        
        for j  in range(len(user_setting)):
            sett = user_setting[j]
            
            if not sett['api'] in mdlist:
                mdprocess = {'type': 'market', 'name': sett['api'], 'setting': sett,"mode_724":mode_724,'strats':stratSetts,'runmode':'real'}
                processlist.append(mdprocess)
                mdlist.append(sett['api'])
            accounts[j].token = token
            tdprocess = {'type': 'realtrader', 'name': sett['api'],'class':sett['class'], 'setting': sett,"mode_724":mode_724,'strats':stratQueues,'account':accounts[j], 'queue':getAccidTraderQueue(j)}
            processlist.append(tdprocess)

        stgsetts = {}
        stgformual = {}
        stgimagesetts = {}
        for strat in strats:
            if strat.name != 'csvorders':
                stgsetts[strat.name] = strat.instid
                if strat.hedgemodel:
                    stgformual[strat.name] = strat.formula
                else:
                    stgformual[strat.name] = '0'
                if strat.recordinsts:
                    stgimagesetts[strat.name] = strat.recordinsts
                else:
                    stgimagesetts[strat.name] = strat.instid

        saveSettingDatarealToDB(curuser, token, stgsetts)
        saveFormulaDatarealToDB(curuser, token, stgformual)
        freq = {strat.name:strat.freq for strat in strats}
        saveStrategyfreqToDB(curuser,token, freq)
        
        #saveImageSettingDataRealToDB(curuser, stgimagesetts)

        with Pool(max(int(cpu_count()), 10)) as pool:
            results = pool.map(processFunc, processlist)
    except Exception as e:
        logger.error("qemain_begin: " + str(e), exc_info=True)

def isDataModeValid(datamode):
    import re
    if datamode == 'tick':
        return 0
    elif datamode == 'minu':
        return 1
    elif datamode == 'hour':
        return 60
    elif datamode == 'daily':
        return 1
    elif re.match(r'\d+m',datamode, 0):
        return int(datamode[:-1])
    else:
        return -1
    
 
        
        
def runStrat(user, runmode, strat,  simu_token=None, simu_md=['ctp'],mode_724=False, record_strat=False,\
             simu_simnow724_account=None, real_account=None,\
             printlog=True, rfrate=0.00, test_dynamic_instid=True, test_data=None, test_startdate=None, test_enddate=None, \
             test_exdata=None,  test_initcap=10000000, test_showchart=False,
             async_strats=False, real_skip_settle_check=False)    :
    '''
    unified interface for strategy
    Parameters
    ----------
    user : str
        username.
    runmode : str
        "test" for backtest; 'simu' for simulation; 'real' for real trades.
    strat : qeStratBase or list
        (list of ) qeStratBase object(s).
    simu_token : str, optional
        token of simulation account, for 'simu' runmode only. The default is None.
    simu_724mode : bool, optional
        If simualtion use 7*24 hours mode. default is False    
    simu_simnow724_account: dict
        SIMNOW account information for 7*24 hours mode in simulation. default is None.
    real_account : dict or list, optional
        (list of ) setting dictionary of real trade account . The default is None.
    printlog : bool, optional
        If or not print trade logs and warnings. The default is True.
    test_data : pandas.DataFrame, optional
        Data for backtest, for 'test' mode only. The default is None.
    test_startdate : str, optional
        Start date string for backtest, for 'test' mode only.. The default is None.
    test_enddate : str, optional
        End date string for backtest, for 'test' mode only.. The default is None.
    test_initCap : float, optional
        Initial Capital of backtest, for 'test' mode only. The default is 10000000.
    test_showchart : bool, optional
        If or not show the chart. The default is True.

    Returns
    -------
    None.

    '''
    
    ## check input paras
    
    if isinstance(strat, qeStratBase):
        strategy = strat
        strats = [strat]
    elif isinstance(strat, list) and len(strat) >0 and isinstance(strat[0], qeStratBase):
        strategy = strat[0]
        strats = strat
    else:
        print('strat参数必须qeStratBase继承类，或者qeStratBase继承类的列表')
        return 
    if  not hasattr(strategy, 'instid') or not hasattr(strategy, 'datamode'):
        print('strat类必须包含 datamode 和 instid 属性')
        return
    if isinstance(strategy.instid, str):
        instids = [strategy.instid]
    elif isinstance(strategy.instid, list) and len(strategy.instid) > 0 and isinstance(strategy.instid[0], str):    
        instids = strategy.instid
    else:
        print('strat.instid必须是合约名或合约名列表')
        return   
    validDataMode =['tick','minute','daily','hour']
    for strat in strats:
        if isinstance(strat.instid, str):
            strat.instid = [strat.instid]
        if not isinstance(strat.instid, list):
            print('strat.instid 必须是合约名，或者合约名列表')
            return
            
        #strat.instid = getValidInstIDs(strat.instid)  
        if not hasattr(strat, 'datamode') or not isinstance(strat.datamode, str) :
            print('strat必须有datamode字段并且datamode必须是合法字符串')
            return
        elif not isinstance(strat.freq, int):
            print("strat必须有freq字段并且该字段必须是int类型")
            return
        elif strat.datamode in validDataMode:
            if strat.datamode == 'minute' and strat.freq == 0:
                strat.freq = 1
            if strat.datamode == 'hour':
                strat.datamode = 'minute'
                strat.freq = 60
        else:        
            print('strat.datamode必须是合法字符串')
            return
    
    if test_startdate and isinstance(test_startdate, str):
        try:
            if len(test_startdate) == 10:
                test_startdate = datetime.strptime(test_startdate, '%Y-%m-%d')
            elif len(test_startdate) == 16:
                test_startdate = datetime.strptime(test_startdate, '%Y-%m-%d %H:%M')
            elif len(test_startdate) == 19:
                test_startdate = datetime.strptime(test_startdate, '%Y-%m-%d %H:%M:%S')
            else:
                raise ValueError
        except Exception:
            print("test_startdate时间字符串不合法", test_startdate)
            return
                
    if test_enddate and isinstance(test_enddate, str):
        try:
            if len(test_enddate) == 10:
                test_enddate = datetime.strptime(test_enddate, '%Y-%m-%d')
            elif len(test_enddate) == 16:
                test_enddate = datetime.strptime(test_enddate, '%Y-%m-%d %H:%M')
            elif len(test_enddate) == 19:
                test_enddate = datetime.strptime(test_enddate, '%Y-%m-%d %H:%M:%S')
            else:
                raise ValueError
        except Exception:
            print("test_enddate时间字符串不合法", test_enddate)
            return           
    if not initMyredis():
        return
    if runmode == 'test':
        ## deal with strat
        #instids = getValidInstIDs(instids)
        if test_dynamic_instid:
            if test_data or test_exdata:
                print("回测动态合约模式不支持test_data和test_exdata字段")
                return
            if not strategy.datamode in ['minute','hour','daily']:
                print("回测动态合约模式不支持tick级数据或者datamode不合法。")
                return 
                
            if test_startdate is None or test_enddate is None:    
                print("回测动态模式test_startdate和test_enddate不能为空")
                return 
                
            return dynamicBacktest(user, strategy.datamode, instids, test_startdate, test_enddate, strategy, \
                        initCap=test_initcap, printlog=printlog, showchart=test_showchart,rfrate=rfrate, record_strat= record_strat, async_strats=async_strats)
            

        elif not test_data is None:
            return runBacktest(user, test_data, strategy.datamode, instids, strategy, exdata=test_exdata, \
                        initCap=test_initcap, printlog=printlog, showchart=test_showchart,rfrate=rfrate, record_strat=record_strat)
        elif test_startdate is None or test_enddate is None:
            print("回测模式需要提供test_startdate和test_enddate.")
            return 
        else:
            if strat.datamode[-1:] == 'm':
                strat.datamode = strat.datamode[:-1]+'T'
            return historyDataBackTest(user, strategy.datamode, instids, test_startdate, test_enddate, strategy, \
                        exdata=test_exdata, initCap=test_initcap, printlog=printlog, showchart=test_showchart,rfrate=rfrate,record_strat=record_strat)
            
            
    elif runmode == 'simu':
        startSimuProcess(user, simu_token, strats,md=simu_md, mode_724=mode_724, simnow724_account=simu_simnow724_account,\
                         printlog=printlog,rfrate=rfrate, record_strat=record_strat, async_strats=async_strats)
        
    elif runmode == 'real':
        startRealProcess(user, strats, real_account,mode_724=mode_724, printlog=printlog,rfrate=rfrate,record_strat=record_strat, skip_settle_check=real_skip_settle_check)
        
    else:
        print('不合法的runmode', runmode)
        return
    
    

if __name__ == '__main__':
    import easyStrat

    user = 'scott'
    strat = easyStrat.easyStrat()  # qeStratBase()
    strat.instid = ['RB2201.SFE']

    startSimuProcess(user, [strat])
