# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 21:11:45 2022

@author: ScottStation
"""

class qeEnumTypes():
    KEY_MARKET_DATA = 0
    KEY_ON_INSTRUMENT = 1
    KEY_ON_ORDER = 2
    KEY_ON_TRADE = 3
    KEY_ON_POSITION = 4
    KEY_ON_ACCOUNT = 5
    KEY_ON_BALANCE = 6
    KEY_ON_ORDER_ERROR = 7
    KEY_ON_TRADE_ERROR = 8
    KEY_ON_POSITION_DETAIL = 9
    KEY_ON_SETTLEMENT = 10
    KEY_ON_SEND_ORDER_ERROR = 11
    KEY_ON_CANCEL_ORDER_ERROR = 12
    KEY_ON_QRY_ORDER = 13
    KEY_ON_QRY_TRADE = 14
    KEY_TIMER = 15
    KEY_TIMER_PROCESS = 16
    KEY_TIMER_SIMU = 17
    KEY_MARKET_MULTIDATA = 18
    KEY_SEND_ORDER = 101
    KEY_CANCEL_ORDER = 102
    KEY_STATUS_ALL_TRADED = "alltraded"
    KEY_STATUS_PART_TRADED = 'parttraded'
    KEY_STATUS_PENDING = 'committed'
    KEY_STATUS_CANCEL ='canceled'
    KEY_STATUS_UNKNOWN = 'unknown'
    KEY_STATUS_REJECT = 'failed'
    KEY_STATUS_PTPC = 'ptpc'
    KEY_REQ_ACCOUNT = 110
    KEY_REQ_POSITION = 111
    KEY_REQ_POSITION_DETAIL = 112
    KEY_REQ_INSTRUMENT = 113
    KEY_QRY_ORDER = 114
    KEY_QRY_TRADE = 115
    KEY_USER_LOGOUT = 116

qetype = qeEnumTypes()

