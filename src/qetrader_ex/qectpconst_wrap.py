# -*- coding: utf-8 -*-
"""
Created on Tue Jan 31 14:49:43 2023

@author: ScottStation
"""

class TThostEnumValues(object):
    THOST_FTDC_OPT_LimitPrice = "2"
    THOST_FTDC_OPT_AnyPrice	= "1"
    THOST_FTDC_D_Buy = "0"
    THOST_FTDC_D_Sell = "1"
    THOST_FTDC_OF_Open = "0"
    THOST_FTDC_OF_Close = "1"
    THOST_FTDC_OF_ForceClose = "2"
    THOST_FTDC_OF_CloseToday = "3"
    THOST_FTDC_OF_CloseYesterday = "4"
    THOST_FTDC_PD_Net = "1"
    THOST_FTDC_PD_Long = "2"
    THOST_FTDC_PD_Short = "3"
    THOST_FTDC_OST_AllTraded = '0'
    THOST_FTDC_OST_PartTradedQueueing = '1'
    THOST_FTDC_OST_PartTradedNotQueueing = '2'
    THOST_FTDC_OST_NoTradeQueueing = '3'
    THOST_FTDC_OST_NoTradeNotQueueing = '4'
    THOST_FTDC_OST_Canceled = '5'
    THOST_FTDC_OST_Unknown = 'a'
    THOST_FTDC_OST_NotTouched = 'b'
    THOST_FTDC_OST_Touched = 'c'

    THOST_FTDC_CC_Immediately = '1'
    THOST_FTDC_VC_AV = '1'
    THOST_FTDC_VC_MV = '2'
    THOST_FTDC_VC_CV = '3'    
    THOST_FTDC_TC_IOC = '1'
    THOST_FTDC_TC_GFD = '3'
    THOST_FTDC_HF_Speculation = '1'
    THOST_FTDC_FCC_NotForceClose = '0'
    THOST_FTDC_AF_Delete = '0'
    THOST_FTDC_OSS_InsertRejected = '4'
    THOST_TERT_RESTART = 0
    THOST_TERT_RESUME = 1
    THOST_TERT_QUICK = 2
    THOST_TERT_NONE = 3
