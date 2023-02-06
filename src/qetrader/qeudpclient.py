# -*- coding: utf-8 -*-
"""
Created on Tue Apr  5 16:40:27 2022

@author: ScottStation
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr  3 21:55:41 2022

@author: root
"""

import socket
import time
from datetime import datetime
from threading import Timer, Lock
from .qelogger import logger
from .qeglobal import g_userinfo, dbconfig


mutex = Lock()
#client 
num = 0
if dbconfig['ip']=='103.36.172.183':
    host = dbconfig['ip']
    port = 9018
else:
    host= '192.168.123.15'
    port= 9080
flag_bar_new=True
flag_bar_all=True

def setNum(n):
    global num
    mutex.acquire()
    num = n
    mutex.release()


def onTimer():
    global num
    setNum(num+1)
    if num > 8:
        logger.warning("Watchdog timeout")
        setNum(0)
    timer = Timer(15, onTimer)
    timer.start()

def isServerSleep():
    now = datetime.now()
    wday = now.weekday()
    if wday ==5:
        return now.hour >= 4
    elif wday==6:
        return True
    elif wday==0 :
        return now.hour < 7
    elif now.hour >=4 and now.hour <7:
        return True
    else:
        return False



def doConnect(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((host, port))
    except:
        pass
    return sock


def udpClient(apiset):
    global num,flag_bar_new,flag_bar_all, market_connected

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    
    while True:
        try:
            sec = datetime.now().second
            if apiset == ['sopt'] or apiset == ['sopttest']:
                data_new='ssenewm' + str(sec)
                data_all='sseallm' + str(sec)
            else:
                data_new='newminu' + str(sec)
                data_all='allminu' + str(sec)
            client.settimeout(10)
            setNum(0)
            client.sendto(data_new.encode('utf-8'), (host, port))
            info_new = client.recv(1024).decode('utf-8')
            #print(info_new)
            client.sendto(data_all.encode('utf-8'), (host, port))
            info_all = client.recv(1024).decode('utf-8')
            #print(info_all)
            if info_new and len(info_new) == 9:#有info才操作
                try:
                    info_time_new = int(info_new[-4:])
                except:
                    setNum(0)
                else:    
                    if g_userinfo.info_time_new < info_time_new:
                        if info_time_new > 3900 and g_userinfo.info_time_new < 2400:
                            pass
                        else:   
                            g_userinfo.info_time_new=info_time_new
                    elif g_userinfo.info_time_new > 3800 and info_time_new < 2400:    
                        g_userinfo.info_time_new=info_time_new
                    
                    flag_bar_new=False
            if info_all and len(info_all) == 9:#有info才操作
                try:
                    info_time_all = int(info_all[-4:])
                except:
                    setNum(0)
                else:  
                    #print(info_time_all,"info_time_all")
                    if g_userinfo.info_time_all < info_time_all:
                        if info_time_all > 3900 and g_userinfo.info_time_all < 2400:
                            pass
                        else:   
                            g_userinfo.info_time_all=info_time_all
                    elif g_userinfo.info_time_all > 3800 and info_time_all < 2400:    
                        g_userinfo.info_time_all=info_time_all
                            
                    flag_bar_all=False
            setNum(0)

        except socket.error:
            #print("\r\nsocket error,do reconnect ")
            time.sleep(3)
            client = doConnect(host, port)
           
        except Exception as e:
            logger.warning('\r\nother error occur: ', e)
            time.sleep(3)
        time.sleep(2)
def udpClient_bar(apiset):
    onTimer()
    udpClient(apiset)
    
    
        
if __name__=='__main__':
    onTimer()
    udpClient('ctp')        
        