# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 12:55:19 2022

@author: ScottStation
"""
#import asyncio

import qesdk
from .qeredisdb import async_get_bar_data, check_auth
from .qeinterface import test_get_bar
import pandas as pd
buffer_bar_data = None
buffer_dominant_insts = None
from datetime import datetime, timedelta
from .qelogger import logger

@check_auth
async def aio_get_bar(context, freq, count=None):
    global buffer_bar_data
    if context.runmode == 'test':
        return test_get_bar(context, freq, count)
    elif buffer_bar_data is None:
        data= await async_get_bar_data(context.instid, context.tradingday)
    else:
        data = { key:value for key,value in buffer_bar_data.items() if key in context.instid}
    #print(data )
    if data:
        try:
            f=str(freq)+'min'
            for instid in data.keys():  
                df=data[instid]
                if len(df) > 0:
                    #print(df.time)
                    df['runtime']= pd.to_datetime(df['time'], format='%Y%m%d%H%M%S',errors='ignore')
                    #for i in range(len(df['time'])):
                    #    df['runtime'].loc[i]=datetime.datetime.strptime(str(df['time'].loc[i]), "%Y%m%d%H%M%S")
                    df.set_index(["runtime"], inplace=True)
                    #print(df)
                    if f=='1min':
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
                        del df2['time']
                        if isinstance(count, int):
                            data[instid]=df2.dropna(how='all').iloc[-count:,]
                        else:
                            data[instid]=df2.dropna(how='all')
        except Exception as e:
            logger.error(f"qeasyncdata {e.__traceback__.tb_lineno},{e}",exc_info=True)
 
        #print(df2.head())
    return data

@check_auth
async def aio_get_price(security, start_date, end_date, freq='minute', fields=None, overnight=False, silent=False):
    return await qesdk.aio_get_price(security,start_date,end_date, freq, fields,overnight,silent)


@check_auth
async def aio_get_dominant_instID(symbol, curdate=None, code='9999'):
    global buffer_dominant_insts
    if code == '9999' and buffer_dominant_insts:
        if curdate in buffer_dominant_insts:
            if symbol in buffer_dominant_insts[curdate]:
                return buffer_dominant_insts[curdate][symbol]
    return await qesdk.aio_get_dominant_instID(symbol, curdate, code)


@check_auth
def buffer_get_bar(instids,tradingday):
    global buffer_bar_data
    try:
        dfDict =  qesdk.get_bar_data(instids, tradingday, 5)
        if isinstance(dfDict,dict):
            if buffer_bar_data:
                for inst in dfDict:
                    if inst in buffer_bar_data:
                        buffer_bar_data[inst] = pd.concat([dfDict[inst],buffer_bar_data[inst]], join='outer')
                    else:
                        buffer_bar_data[inst] = dfDict[inst]
            else:
                buffer_bar_data = dfDict
        else:
            logger.warning(f"get_bar_data report:{dfDict}")
    except Exception as e:
        logger.error(f"qeasyncdata {e.__traceback__.tb_lineno},{e}",exc_info=True)


def reset_buffer_data():
    global buffer_bar_data
    del buffer_bar_data
    buffer_bar_data = None
    
def getProd(inst):
    if inst[1].isdigit():
        return inst[0]
    else:
        return inst[:2]
@check_auth    
def buffer_get_dominant_instIDs(instids,tradingday):
    global buffer_dominant_insts
    curdate = datetime.strptime(tradingday,'%Y%m%d')
    syms = [getProd(inst) for inst in instids]
    df = qesdk.get_dominant_instIDs(syms, curdate, curdate)
    if not df is None and len(df) > 0:
        if buffer_dominant_insts:
            if not tradingday in buffer_dominant_insts:
                buffer_dominant_insts.clear()
            buffer_dominant_insts[tradingday] = df.to_dict('record')
        else:
            buffer_dominant_insts = {tradingday:df.to_dict('record')}