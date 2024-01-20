# -*- coding: utf-8 -*-
"""
Created on Wed Oct 13 17:35:49 2021

@author: ScottStation
"""
from datetime import datetime, timedelta
import time
import json
#import os
from .qetype import qetype
from .qeglobal import  g_dataSlide
from .qeredisdb import saveMarketToDB, resetMarketData
from .qestatistics import getPrevTradingDay
#from .qeinterface import simuqueue
from .qelogger import logger

import copy

'''
以下为需要订阅行情的合约号，注意选择有效合约；
有效连上但没有行情可能是过期合约或者不再交易时间内导致
'''







g_mode_724=False
market_ready = False
strat_instIDs = {}
cur_insts = set()
instID_update = False

        

        
   
    
def checkMarketTime(now):
    global g_mode_724
    if g_mode_724:
        return True
    curminu = now.hour *100 + now.minute    
    if (curminu > 230 and curminu < 850) or (curminu >= 1530 and curminu <2050)  :
        return False
    elif now.weekday ==6 or (now.weekday==5 and curminu > 240) or (now.weekday == 0 and curminu < 850):
        return False
    return True 
  
def getMarketReady():
    global market_ready

    return market_ready


def changeCtpInstIDs(stratName, instIDs):
    global strat_instIDs, instID_update,cur_insts
    instID_update = True
    strat_instIDs[stratName] = instIDs
    curset = set()
    for key in strat_instIDs:
        curset.update(strat_instIDs[key])
    for inst in cur_insts:
        if not inst in curset:
            print('add inst',inst)
            resetOldMarketData(inst, datetime.now())
    
    cur_insts = curset



def save_tick_data(tickdata):
    for inst in tickdata:
            datastr = json.dumps(tickdata[inst])
            #print(inst,tickdata[inst])
            timedigit = tickdata[inst]['timedigit']
            saveMarketToDB(inst, str(timedigit), datastr)

def update_data(strats, data):    
    try:
        assert 'type' in data and 'data' in data, 'incorrect data format'
        assert data['type'] == qetype.KEY_NEW_MARKET_DATA, 'incorrect data type'

      
        if strats['async']:
            strats['queue'].put(data)
        else:
            #print(strats)
            for key in strats:
                if not key in ['async']:
                    strats[key]['queue'].put(data)



        

    except Exception as e:
        logger.error(f"CTP market interface callback error {e}",exc_info=True )      


def resetOldMarketData(instIDs, now):
    before_time = getPrevTradingDay(now) + '160000000'    
    for inst in instIDs:
        resetMarketData(inst, before_time)


def runMarketInterface(strats, runmode,  data_slides, instIDs, tqueue,mode_724=False):
    ### 1. 接受行情服务消息 updateData
    ### 2. 接受策略服务消息 updateInstIDs
    ### 3. 接受交易服务消息 updateInstIDs
    ### 4. 接受行情服务消息 market_ready
    global strat_instIDs, instID_update, market_ready, g_mode_724,cur_insts
    last_trading_day = ""
    last_timedigit = 0
    last_save_timedigit = 0
    g_mode_724 = mode_724
    origin_instIDs = {}
    
    instSave = False
    if strats['async']:    
        for s in strats['strat']:
            if s.datamode == 'tick':
                instSave = True
            origin_instIDs[s.name] = s.instid
            
    else:
        for name in strats:
            if name != 'async':
                instSave = strats[name]['strat'].datamode == 'tick'
                origin_instIDs[name] = strats[name]['strat'].instid
    for key in origin_instIDs:
        strat_instIDs[key] = origin_instIDs[key]
        cur_insts.update(origin_instIDs[key])
        instIDs[key] = origin_instIDs[key]
    now = datetime.now()
    for inst in cur_insts:
        resetOldMarketData(inst, now)
    instIDs['lastupdate'] = now.strftime('%Y%m%d%H%M%S%f')

    while True:
        #print('interface of market')
        if 'lastdigit' in data_slides and last_timedigit < data_slides['lastdigit']:
            #print('updateData')
            ## send to strats and traders
            d = {}
            d['type'] = qetype.KEY_NEW_MARKET_DATA
            d['data'] = data_slides.copy()
            
            g_dataSlide.updateEx(data_slides.copy())
            update_data(strats, d)
            if runmode == 'simu':
                tqueue.put(d)
            if instSave and last_save_timedigit <= data_slides['lastdigit']-500:
                last_save_timedigit = data_slides['lastdigit']
                save_tick_data(g_dataSlide)


        if 'tradingday' in data_slides and data_slides['tradingday'] != last_trading_day:
            crossday = last_trading_day != ""
            last_trading_day = data_slides['tradingday']
            if crossday:
                print('updateCrossDay')
                ## send to strats and traders
                cd_data = {}
                cd_data['type'] = qetype.KEY_ON_CROSS_DAY
                cd_data['tradingday'] = last_trading_day
                #cross_day(cd_data, runmode)
                if runmode == 'simu':
                    tqueue.put(cd_data)
                else:
                    for key in tqueue:
                        tqueue[key].put(cd_data)
                
        if 'market_ready' in data_slides and data_slides['market_ready']:
            market_ready = True
        else:
            market_ready = False    
        if instID_update:
            print('updateInstIDs')
            ## send to traders
            instID_update = False
            for key in strat_instIDs:
                instIDs[key] = strat_instIDs[key]
            now = datetime.now()
            instIDs['lastupdate'] = now.strftime('%Y%m%d%H%M%S%f')

        time.sleep(0.2)



if __name__ == '__main__':
    pass