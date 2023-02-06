# -*- coding: utf-8 -*-
"""
Created on Tue Nov 30 20:01:48 2021

@author: ScottStation
"""

__version__ = '1.0.6'

from .qeinterface import qeStratBase
from .qeinterface import make_order
from .qeinterface import cancel_order
from .qeinterface import get_bar
#from .qecsvorder import algo_trade
from .qemain import runStrat
from .qemain import startSimuProcess
from .qemain import startRealProcess
#from .qeimage import qesimu_Plots,qereal_Plots
#from .qetable import qereal_Tables,qesimu_Tables
from .qemain import getuserid
from .qesimtrader import createSimuAccount
from .qesimtrader import listSimuAccounts
from .qesimtrader import removeSimuAccountData
from .qeinterface import record_hedge_point
#from .qereal_monitor_tab import run_real_monitor
#from .qesimu_monitor_tab import run_simu_monitor
#from .qemonitor_log_real import run_monitor_log_real
#from .qemonitor_log_simu import run_monitor_log_simu
from .qearbit import qeArbitModel
from .qelogger import logger
from .qeredisdb import HGET, HSET, HDEL, GET, SET, DEL
from .qebacktestmul import akshare_data_convert
from .qebacktestmul import runBacktest
#from .qebacktestmul import qeStratBase
#from .qebacktestmul import record_hedge_point
#from .qebacktestmul import make_order
#from .qebacktestmul import cancel_order
from .qebacktestmul import showCharts
from .qebacktestmul import reportPerformance
from .qebacktestmul import reportIndicators
from .qebacktestmul import historyDataBackTest
from .qestatistics import g_stat
from .qeoption import bs_put, bs_call, bs_theta, bs_vega, bs_gamma, bs_delta, find_vol
#from .qeglobal import getValidInstID, getValidInstIDs

from .qeasyncdata import aio_get_price
from .qeasyncdata import aio_get_dominant_instID
from .qeasyncdata import aio_get_bar

from .qesysconf import read_sysconfig, setRedisConfig, setWebConfig
from .qeplugins import installPlugin