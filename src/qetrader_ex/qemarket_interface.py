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
from .qeglobal import getAccidTraderQueue, g_dataSlide
from .qeinterface import simuqueue
from .qelogger import logger
from .qeredisdb import saveMarketToDB
import copy

'''
以下为需要订阅行情的合约号，注意选择有效合约；
有效连上但没有行情可能是过期合约或者不再交易时间内导致
'''







g_mode_724=False
market_ready = False
strat_instIDs = {}
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
    global strat_instIDs, instID_update
    instID_update = True
    strat_instIDs[stratName] = instIDs

def save_tick_data(data):
    tickdata = data['data']
    for inst in tickdata:
        datastr = json.dumps(tickdata[inst])
        timedigit = tickdata[inst]['timedigit']
        saveMarketToDB(inst, timedigit, datastr)

def update_data(strats, data, runmode):    
    try:
        assert 'type' in data and 'data' in data, 'incorrect data format'
        assert data['type'] == qetype.KEY_MARKET_DATA, 'incorrect data type'
        if strats['async']:
            strats['queue'].put(data)
        else:
            for key in strats:
                strats[key]['queue'].put(data)



        if runmode == 'simu':
            simuqueue.put(data)
        

    except Exception as e:
        logger.error(f"CTP market interface callback error {e}",exc_info=True )      

def cross_day(data, runmode):
    try:
        if runmode == 'simu':
            simuqueue.put(data)               
        else:
            queues = getAccidTraderQueue(0) #getInstTraderQueue(d['instid'])
            for queue in queues:
                queue.put(data)

    except Exception as e:
        logger.error(f"CTP market interface crossday error {e}",exc_info=True )





def runMarketInterface(strats, runmode,  data_slides, instIDs,mode_724=False):
    ### 1. 接受行情服务消息 updateData
    ### 2. 接受策略服务消息 updateInstIDs
    ### 3. 接受交易服务消息 updateInstIDs
    ### 4. 接受行情服务消息 market_ready
    global strat_instIDs, instID_update, market_ready, g_mode_724
    last_trading_day = ""
    last_timedigit = 0
    last_save_timedigit = 0
    g_mode_724 = mode_724
    
    instSave = False
    if strats['async']:    
        for s in strats['strat']:
            if s.datamode == 'tick':
                instSave = True
            
    else:
        for name in strats:
            if name != 'async':
                instSave = strats[name]['strat'].datamode == 'tick'

    while True:
        if 'lastdigit' in data_slides and last_timedigit < data_slides['lastdigit']:
            print('updateData')
            ## send to strats and traders
            d = {}
            d['type'] = qetype.KEY_MARKET_DATA
            d['data'] = data_slides.copy()
            g_dataSlide.update(data_slides)
            update_data(strats, d, runmode)
            if instSave and last_save_timedigit <= data_slides['lastdigit']-500:
                last_save_timedigit = data_slides['lastdigit']
                save_tick_data(d)


        if 'tradingday' in data_slides and data_slides['tradingday'] != last_trading_day:
            crossday = last_trading_day != ""
            last_trading_day = data_slides['tradingday']
            if crossday:
                print('updateCrossDay')
                ## send to strats and traders
                cd_data = {}
                cd_data['type'] = qetype.KEY_ON_CROSS_DAY
                cd_data['tradingday'] = last_trading_day
                cross_day(cd_data, runmode)
                
        if 'market_ready' in data_slides and data_slides['market_ready']:
            market_ready = True
        else:
            market_ready = False    
        if instID_update:
            print('updateInstIDs')
            ## send to traders
            instID_update = False
            instIDs.update(strat_instIDs)
            now = datetime.now()
            instIDs['lastupdate'] = now.strftime('%Y%m%d%H%M%S%f')

        time.sleep(0.1)



if __name__ == '__main__':
    pass