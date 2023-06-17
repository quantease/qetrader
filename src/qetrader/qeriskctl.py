# -*- coding: utf-8 -*-
"""
Created on Mon Mar 21 11:04:10 2022

@author: ScottStation
"""


from  datetime import datetime, timedelta
import traceback
import csv
import pandas as pd
#import mysql.connector
from .qelogger import logger
from .qeglobal import get_riskctl_paras
from .qeredisdb import saveRiskCtlRecord, loadRiskCtlRecord
import json
class riskControl:
    def __init__(self, callback, user, token, settings_file = None, runmode = 'real'):
        self.modules = {'daymaxacts': False, 'secmaxacts': False,
                        'selftrade': False, 'daymaxcancels': False, 'bigvolcancels': False}
        self.daymaxacts = 1000
        self.dayacts = 0
        self.user = user
        self.token = token
        self.runmode = runmode

        self.secmaxacts = 10000
        self.secacts = []

        self.maxselftrades = {}
        self.dayselftrades = {}

        self.maxwithdrawal = {}
        self.daywithdrawal = {}


        self.limitwithdrawal = {}
        self.maxnumorder = {}
        self.daylargewithdrawal = {}
        self.bigvolpercent = {}

        self.callback = callback

        self.tradingday = ''
        #self.load()
        # if settings_file:
        #     self.load_settings_from_csv(settings_file)

    def save(self):
        if self.tradingday != '':
            riskdata = {'dayacts': self.dayacts, 'dayselftrades': self.dayselftrades, 'daywithdrawal': self.daywithdrawal, 'daylargewithdrawal': self.daylargewithdrawal}
            saveRiskCtlRecord(self.user, self.token, self.tradingday, riskdata, runmode = self.runmode)
            
    def setTradingDay(self, tradingday): 
        self.tradingday = tradingday
    
    def load(self, tradingday):
        self.tradingday = tradingday
        riskctl_para = get_riskctl_paras()
        if isinstance(riskctl_para, dict):
        # example: 'RS': {'maxselftrade': 5, 'maxwithdrawal': 500, 'bigvolwithdrawal': 50, 'maxvolume': 800},
            for key, value in riskctl_para.items():
                self.maxselftrades[key.upper()] = value['maxselftrade']
                self.maxwithdrawal[key.upper()] = value['maxwithdrawal']
                self.limitwithdrawal[key.upper()] = value['bigvolwithdrawal']
                self.maxnumorder[key.upper()] = value['maxvolume']
                self.bigvolpercent[key.upper()] = value['bigvolpercent']
                self.bigvolpercent[key.upper()] = value['bigvolpercent'] 
        riskdata = loadRiskCtlRecord(self.user, self.token, tradingday, runmode = self.runmode)
        if riskdata:
            self.dayacts = riskdata['dayacts']
            self.dayselftrades = riskdata['dayselftrades']
            self.daywithdrawal = riskdata['daywithdrawal']
            self.daylargewithdrawal = riskdata['daylargewithdrawal']

    def load_settings_from_csv(self, settings_file):
        # 读取CSV文件
        data = pd.read_csv(settings_file)

        data.set_index('prodid', inplace=True)
        #print(data)

        # 将DataFrame转换为字典
        dictionary = data.to_dict(orient='index')
        #print(dictionary)

        self.maxselftrade = {key.upper(): value['maxselftrade'] for key, value in dictionary.items()}
        self.maxwithdrawal = {key.upper(): value['maxwithdrawal'] for key, value in dictionary.items()}
        self.limitwithdrawal = {key.upper(): value['limitwithdrawal'] for key, value in dictionary.items()}
        self.maxnumorder = {key.upper(): value['maxnumorder'] for key, value in dictionary.items()}


        self.daywithdrawal = {key.upper(): 0 for key in dictionary.keys()}
        self.dayselftrades = {key.upper(): 0 for key in dictionary.keys()}

        
        self.daylargewithdrawal= {key.upper(): 0 for key in dictionary.keys()}




    def active(self, module):
        try:
            if not module  in self.modules.keys():
                print('Invalid risk control module name.')
                return
            if module == 'daymaxacts':
                print('Successfully activated daymaxacts risk control')
            elif module == 'secmaxacts':
                print('Successfully activated secmaxacts risk control')
            elif module == 'selftrade':
                print('Successfully activated selftrade risk control')
            elif module == 'daymaxcancels':
                print('Successfully activated daymaxcancels risk control')
            elif module == 'bigvolcancels':
                print('Successfully activated bigvolcancels risk control')
            self.modules[module] = True

        except:
            import traceback
            traceback.print_exc()



    def getCancelPercent(self, instid):
        # 获取指定合约的撤单比例
        prod_id = self.transfer(instid)
        try:
            daywithdrawal = self.daywithdrawal[instid ] if instid  in self.daywithdrawal.keys() else 0
            daylarge_withdrawal = self.daylargewithdrawal[instid ] if instid  in self.daylargewithdrawal.keys() else 0
            freq_percentage = (daywithdrawal / self.maxwithdrawal[prod_id ])
            large_percentage = (daylarge_withdrawal / self.limitwithdrawal[prod_id ])
            return [freq_percentage, large_percentage] ## not implemented
            # 调用回调函数，获取指定合约的撤单比例
        except Exception as e:
            print(f"Error getting cancel percentage for '{instid}': {str(e)}")
            return [0,0]           
            # 调用回调函数，获取指定合约的撤单比例


    def getBigOrderThreshold(self, instid):
        prod_id = self.transfer(instid)
        return self.maxnumorder[prod_id]*self.bigvolpercent[prod_id]


    def transfer(self, instid):
        prod_id = ''
        # 判断instid第二位是否为数字
        if instid[1].isdigit():
            prod_id = instid[0]
        else:
            prod_id = instid[:2]
        return prod_id

    def make_order(self, context, volume, instid=None, limitprice=None, direction=0):
        num = 1
        prod_id = self.transfer(instid)
        if self.modules['daymaxacts']:
            if self.dayacts + num > self.daymaxacts:
                return -3
            self.dayacts += num

        if self.modules['secmaxacts']:
            self.secacts = [ct for ct in self.secacts if (context.curtime - ct).seconds < 1]
            if len(self.secacts) + num > self.secmaxacts:
                return -4
            for i in range(num):
                self.secacts.append(context.curtime)

        if self.modules['bigvolcancels']:
            if  volume >= self.maxnumorder[prod_id]:
                return -5

        if self.modules['selftrade']:
            if limitprice and instid and direction != 0:
                instPrices = self.callback()
                checkfield = 'longhigh' if direction < 0 else 'shortlow'
                if instid in instPrices and checkfield in instPrices[instid]:
                    price = instPrices[instid][checkfield]

                    if direction > 0 and limitprice > price:
                        # if instid not in self.dayselftrades:
                        #     self.dayselftrades[prod_id] = 0
                        self.dayselftrades[prod_id] += 1
                    elif direction < 0 and limitprice < price:
                        # if instid not in self.dayselftrades:
                        #     self.dayselftrades[prod_id] = 0
                        self.dayselftrades[prod_id] += 1

                # if self.dayselftrades[prod_id] > self.percentage * self.maxselftrades[prod_id]:
                #     print(f'Warning: 自成交达到最大自成交次数的{self.percentage * 100:.2f}%以上.')
                #     logger.info(f'Warning: 自成交达到最大自成交次数的{self.percentage * 100:.2f}%以上.')
                # if self.dayselftrades[prod_id] < self.maxselftrades[prod_id]:
                #     self.dayselftrades[prod_id] += 1
                if self.dayselftrades[prod_id] > self.maxselftrades[prod_id]:
                    return -5
        self.save()
        return 0

    def cancel_order(self, context, orderid):
        instid = context.orders[orderid]['instid']

        prod_id = self.transfer(instid)

        num = 1
        if self.modules['daymaxacts']:
            if self.dayacts + num > self.daymaxacts:
                return -3
            self.dayacts += num

        if self.modules['secmaxacts']:
            self.secacts = [ct for ct in self.secacts if (context.curtime - ct).seconds < 1]
            if len(self.secacts) + num > self.secmaxacts:
                return -4
            for i in range(num):
                self.secacts.append(context.curtime)

        if self.modules['daymaxcancels']:
            if not instid in self.daywithdrawal:
                self.daywithdrawal[instid] = num
            elif self.daywithdrawal[instid] + num >= self.maxwithdrawal[prod_id] - 1:
                return -2
            # elif self.daywithdrawal[prod_id] + num >= self.percentage * self.maxwithdrawal[prod_id]:
            #     print(f'Warning: 频繁撤单次数达到最大撤单次数的{self.percentage * 100:.2f}%以上.')
            #
            #     logger.info(f'Warning: 频繁撤单次数达到最大撤单次数的{self.percentage * 100}%以上.')
            else:
                self.daywithdrawal[instid] += num

        if self.modules['bigvolcancels']:
            if context.orders[orderid]['leftvol'] >= self.maxnumorder[prod_id] * self.bigvolpercent[prod_id]:
                if not instid in self.daylargewithdrawal:
                    self.daylargewithdrawal[instid] = num
                elif self.daylargewithdrawal[instid] + num >= self.limitwithdrawal[prod_id] :
                    return -2
                else:
                    self.daylargewithdrawal[instid] += num
        self.save()
        return 0

    def crossDay(self):

        self.dayacts = 0
        self.secacts = []
        self.dayselftrades = {}
        self.daywithdrawal = {}
        self.daylargewithdrawal = {}
        #self.save()
















