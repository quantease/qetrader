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
import shutil
import zipfile
import glob

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

def installPlugin(plugin_name, version='latest'):
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
        if not downloadFile(plugin_name, token, filename,version):
            print('插件下载失败')
            return 
        if os.path.exists(fullname):
            print('下载完毕，正在删除旧版插件...')
            os.chmod(fullname, 0o777)
            os.remove(fullname)
        
        os.rename(fullname+'-bak',fullname)
        if fullname.endswith('.zip'):
        
            fullpath = global_pluginpath+f"qe{plugin_name}"
            # 判断目录是否存在
            if os.path.exists(fullpath):
                # 修改目录权限
                os.chmod(fullpath, 0o777)
                
                # 删除目录及其内容
                shutil.rmtree(fullpath)
                
                print("原目录删除成功！")

            # 创建 ZipFile 对象
            with zipfile.ZipFile(fullname, 'r') as zip_ref:
                zip_ref.extractall(global_pluginpath)

            print("解压缩完成！")
            suffix = '*.pyd' if global_platform== 'windows' else '*.so'
            old_files = glob.glob(os.path.join(global_pluginpath, suffix))
            if old_files:
                print('删除旧版文件...')
            for old_file in old_files:
                os.chmod(old_file, 0o777)
                os.remove(old_file)
        print(f'插件{plugin_name}下载成功')
        print('在策略文件中按如下格式import该插件:')
        print(f'from qetrader.plugins.qe{plugin_name} import plugin_{plugin_name}')
        ##DownloadPackage
        ##Overwrite and show information
    except Exception as e:
        print(f"Error: {e.__traceback__.tb_lineno} {e}")
    
def downloadFile(plugin, token, filename,version):
    url = 'https://quantease.cn/auth/get_plugins'
    params={'plugin':plugin,'token':token,'filename':filename,'version':version}
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