# -*- coding: utf-8 -*-
"""

@author: ScottStation
"""

import os
import stat
import sys
import platform
from qesdk import get_package_address
import requests

def get_mac_address():
    import uuid
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:].upper()
    return '%s:%s:%s:%s:%s:%s' % (mac[0:2], mac[2:4], mac[4:6], mac[6:8],mac[8:10], mac[10:])

def get_ver():
    vers= sys.version.split('.')
    return '_'.join(vers[:2])

def get_plat():
    return platform.system().lower()

global_macaddr = get_mac_address()
global_pythonver = get_ver()
global_platform = get_plat()

global_pluginpath = os.path.abspath(os.path.dirname(__file__))+'/plugins/'

def installPlugin(plugin_name, overwrite=False):
    ##If already exist
    ##getPackageAddress
    try:
        if not os.path.exists(global_pluginpath):
            os.mkdir(global_pluginpath)
        msg = get_package_address(plugin_name, global_platform, global_pythonver, global_macaddr)
        if isinstance(msg, dict):
            filename = msg['filename']
            token = msg['token']
        else:
            print(msg)
            return
        fullname = global_pluginpath+filename
        if not overwrite and os.path.exists(fullname):
            print('该插件已经存在')
            return
        if not downloadFile(plugin_name, token, filename):
            print('插件下载失败')
            return 
        if os.path.exists(fullname):
            print('下载完毕，正在删除旧版插件...')
            os.chmod(fullname,stat.S_IRWXO)
            os.remove(fullname)
        
        os.rename(fullname+'-bak',fullname)
        print(f'插件{plugin_name}下载成功')
        print(f'在策略文件中按如下格式import该插件:')
        print(f'from qetrader.plugins.qe{plugin_name} import plugin_{plugin_name}')
        ##DownloadPackage
        ##Overwrite and show information
    except Exception as e:
        print(f"Error: {e.__traceback__.tb_lineno} {e}")
    
def downloadFile(plugin, token, filename):
    url = 'https://quantease.cn/auth/get_plugins'
    params={'plugin':plugin,'token':token,'filename':filename}
    try:
        r = requests.get(url,params)
        fullname = global_pluginpath+filename+'-bak'
        if os.path.exists(fullname):
            os.chmod(fullname,stat.S_IRWXO)
            os.remove(fullname)
        if r.status_code == 200:
            
            with open(fullname,'wb') as fp:
                fp.write(r.content)
            return True    
        else:
            print(f'下载插件服务器返回:{r.status_code}')
            return False
    except Exception as e:
        print(f"Error: {e.__traceback__.tb_lineno} {e}")
        return False

if __name__=='__main__':
    installPlugin('algoex')
    #downloadFile('algoex','test','qealgoex.cp38-win_amd64.pyd')