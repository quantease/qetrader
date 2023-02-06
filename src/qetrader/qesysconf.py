# -*- coding: utf-8 -*-
"""
Created on Wed Feb  1 19:07:43 2023

@author: ScottStation
"""


import json
import os

config_path = os.path.abspath(os.path.dirname(__file__)) +'/sysconfig.json'

def read_sysconfig():
    json_data = None
    if os.path.exists(config_path):
        with open(config_path,'r',encoding='utf8') as fp:
            json_data = json.load(fp)
            
    return json_data

def setRedisConfig(host='127.0.0.1', port=6379, password=''):
    try:
        assert isinstance(host, str) and isinstance(password, str), 'host和password必须是合法ip地址'
        assert isinstance(port, int), 'port 必须是int类型'
        json_data = read_sysconfig()
        assert not json_data is None, 'json配置数据文件丢失'
        json_data['redis'] ={'host': host,'port':port,'password':password}
        with open(config_path,'w') as fp:
            json.dump(json_data, fp)
    except Exception as e:
        print(f'Error:{e.__traceback__.tb_lineno},{e}')
        
def setWebConfig(host='127.0.0.1',port=5814):
    try:
        assert isinstance(host, str), 'host必须是合法ip地址'
        assert isinstance(port, int), 'port 必须是int类型'
        json_data = read_sysconfig()
        assert not json_data is None, 'json配置数据文件丢失'
        json_data['webpage'] ={'host': host,'port':port}
        with open(config_path,'w') as fp:
            json.dump(json_data, fp)
    except Exception as e:
        print(f'Error:{e.__traceback__.tb_lineno},{e}')


if __name__ == "__main__":
    setWebConfig()
    print(read_sysconfig())
    
