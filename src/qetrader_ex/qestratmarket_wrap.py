# -*- coding: utf-8 -*-
"""
Created on Thu Feb  2 18:58:25 2023

@author: ScottStation
"""
import pandas as pd

global_stratmarket_exist = False
try:
    from .qestratmarket import readStratCard
    global_stratmarket_exist = True
except:
    pass    

def writeStratPosition_wrap(strat_name, date, position, instClosePnl):
    if global_stratmarket_exist:
        from .qestratmarket import writeStratPosition
        writeStratPosition(strat_name, date, position, instClosePnl)
    else:
        print("Don't support this interface")
    

def readStratPosition_wrap(strat_name, date, prod=None):
    if global_stratmarket_exist:
        from .qestratmarket import readStratPosition
        return readStratPosition(strat_name, date, prod)
    else:
        print("Don't support this interface")
        return {},{}

def save_trades_wrap(stratName,trade, date):
    if global_stratmarket_exist:
        from .qestratmarket import save_trades
        save_trades(stratName, trade, date)
    else:
        print("Don't support this interface")

def writeStratStat_wrap(strat_name,date, posMaxMarg, posTurnover):
    if global_stratmarket_exist:
        from .qestratmarket import writeStratStat
        writeStratStat(strat_name, date,  posMaxMarg, posTurnover)
    else:
        print("Don't support this interface")
    
def writeStratTrade_wrap(strat_name, date, trade):
    if global_stratmarket_exist:
        from .qestratmarket import writeStratTrade
        writeStratTrade(strat_name, date, trade)
    else:
        print("Don't support this interface")

def writeStratPnl_wrap(strat_name,date,prod, pnl):
    if global_stratmarket_exist:
        from .qestratmarket import writeStratPnl
        writeStratPnl(strat_name,date,prod, pnl)
    else:
        print("Don't support this interface")

def readStratStat_wrap(strat_name,date):
    if global_stratmarket_exist:
        from .qestratmarket import readStratStat
        return readStratStat(strat_name,date)
    else:
        print("Don't support this interface")
        return {},{}

def writeContractTable_wrap(stratname, date, position):
    if global_stratmarket_exist:
        from .qestratmarket import writeContractTable
        writeContractTable(stratname, date, position)
    else:
        print("Don't support this interface")
    
def writeContract_messages_wrap(strat_name, date, trade):
    if global_stratmarket_exist:
        from .qestratmarket import writeContract_messages
        writeContract_messages(strat_name, date, trade)
    else:
        print("Don't support this interface")
def update_stratCard_wrap(stratName, indicators, prodMaxmarg):
    if global_stratmarket_exist:
        from .qestratmarket import update_stratCard
        update_stratCard(stratName, indicators, prodMaxmarg)
    else:
        print("Don't support this interface")
def update_stratCard_append_wrap(stratName, initloss):
    if global_stratmarket_exist:
        from .qestratmarket import update_stratCard_append
        update_stratCard_append(stratName, initloss)
    else:
        print("Don't support this interface")
def clearStratTrades_wrap(strat_name, fromdate=None):
    if global_stratmarket_exist:
        from .qestratmarket import clearStratTrades
        clearStratTrades(strat_name, fromdate)
    else:
        print("Don't support this interface")
def clearStratStat_wrap(strat_name, fromdate=None):
    if global_stratmarket_exist:
        from .qestratmarket import clearStratStat
        clearStratStat(strat_name, fromdate)
    else:
        print("Don't support this interface")
def clearStratPosition_wrap(strat_name, fromdate=None):
    if global_stratmarket_exist:
        from .qestratmarket import clearStratPosition
        clearStratPosition(strat_name, fromdate)
    else:
        print("Don't support this interface")
def readFullStratStat_wrap(strat_name, start_date=None, end_date=None):
    if global_stratmarket_exist:
        from .qestratmarket import readFullStratStat
        return readFullStratStat(strat_name, start_date, end_date)
    else:
        print("Don't support this interface")
        return pd.DataFrame()
    
    
    