# -*- coding: utf-8 -*-
"""
Created on Sat Mar 12 16:02:44 2022

@author: ScottStation
"""

from .qeredisdb import SET, GET
import json
########################################################################
## Test cases
## 1. arbit_open-- ok
## 2. cancel by canceldiff -- ok
## 3. secondary orders --ok
## 4. force close by closediff --ok
## 5. chase order
## 6. close unfinished
## 7. secondary by 'component' 'quoted'
## 8. maxchase logic
## 9. force close fail and chase
#######################################################################


class qeArbitModel:
    
    arbit_orders={}
    arbit_order_id = 0
    
    def __init__(self, user, order_func, cancel_func,usedb=False):
        self.user = user
        self.order_func = order_func
        self.cancel_func = cancel_func
        self.bCrossDay = False
        self.fcstarted = False
        self.needsave = False
        self.usedb = usedb
        if usedb:
            self.loadFromDB()
        
    
    def arbit_open(self, context, action,  orderdict, destvol, canceldiff, closediff, chaseseconds,closeseconds=180, secondtype='market', todaypos = True, maxchase=2):
        '''

        Parameters
        ----------
        context : TYPE
            DESCRIPTION.
        action : str
            ['open','close'].
        orderdict : dict
            i.e. {'instid1':｛'price':1000, 'volbase': 1, 'dir': 1, 'tradefirst': True｝,'instid2':{'price':1200, 'volbase':1, 'dir': -1, 'tradefirst': False}}
            volbase: trade volume = destvol * volbase
            dir : Bid or Sale
            tradefirst: If this instid will be trade first, if it is true, the volbase must be 1. Only on instid could be traded first.
        destvol: int
            destination valume. it multiply the volbase is detination volume of each instid of orderdict
        canceldiff : float
            price difference to cancel order
        closediff : dict
            {'instid1':3.0, 'instid2':4.0}
            price difference to close order after first order traded, key is instrumentid
        chaseseconds: int
            if cannot trade in such seconds, make chase order
        closeseconds: int
            retry after closeseconds if not traded 
        todaypos: bool
            True: open or  close today False: close yesterday
        secondtype : str, optional
            'market' order or 'opponent'/'quoted'/'initial'/'current' order when trade second batch orders . The default is 'market'.
        maxchase : int, optional
            max number of chase orders. The default is 2.

        Returns
        -------
        None.

        '''
        sampledict ={'price':100.0, 'volbase':1, 'dir':1, 'tradefirst':False}
        validaction =['open','close']
        validtype =['market','opponent','quoted','initial','current']
        ## input paramters check
        if not action in validaction:
            print("Invalid aciton ,should be in",validaction)
            return -1
        
        if not action in validaction:
            print("Invalid order type ,should be in",validtype)
            return -1
        
        if not isinstance(closediff, dict):
            print("Invalide paramter type of closediff, should be float")
            return -1
           
        
        if  not isinstance(canceldiff, float) and not isinstance(canceldiff, int):
            print("Invalide paramter type of canceldiff, should be float or int")
            return -1
            
        if not isinstance(destvol, int) or not isinstance(maxchase,int)  or not isinstance(chaseseconds, int) or not isinstance(closeseconds, int):
            print("Invalid paramter type of destvol/maxchase/chaseseconds/closeseconds, should be int")
            return -1
        
        if not isinstance(todaypos, bool):
            print("Invalid paramter type of todaypos, should be Boolean")
            return -1
        
        for cd in closediff:
            if not cd in orderdict:
                print('key of closediff must be in orderdict')
                return -1
            elif not isinstance(closediff[cd], float) and not isinstance(closediff[cd], int):
                print('closediff values must be int or float numbers')
                return -1
        try:

            firstid = ''       
            for key in orderdict:
                if not key in context.instid:
                    print('The key of context should be instrumentid in context.instid')
                    return -1
                
                if orderdict[key]['tradefirst']:
                    if firstid == '':
                        firstid = key
                        if orderdict[key]['volbase'] != 1:
                            print('The volbase of instrumentid which be traded first should be 1 ')
                            return -1
                    else:
                        print("Only support one instid in orderdict.keys be traded first ")
                        return -1
                    
                for okey in sampledict:
                    if  not okey in orderdict[key].keys() or not isinstance(orderdict[key][okey], type(sampledict[okey])):
                        print("Please check the format of orderdict on key :",key, "example dict:", sampledict)
                        return -1
                ##Check the upperlimit and lowerlimit
                pdir = orderdict[key]['dir'] 
                if 'upperlimit' in  context.dataslide[key] and 'lowerlimit' in context.dataslide[key]:
                    if pdir > 0 and orderdict[key]['price'] == context.dataslide[key]['upperlimit']:
                        print("Price touch the upperlimit so do nothing.",key, orderdict[key]['price'])
                        return  -1
                    if pdir < 0 and orderdict[key]['price'] == context.dataslide[key]['lowerlimit']:
                        print("Price touch the lowerlimit so do nothing.",key, orderdict[key]['price'])
                        return -1
            
            ## make first order
            closetype = 'closeyesterday' if not todaypos else 'closetoday'
            #closetype ='none' if action =='open' else closetype
           
            pdir = orderdict[firstid]['dir']  
            vol = destvol * orderdict[firstid]['volbase']
            orderid = self.order_func(context, firstid, pdir, orderdict[firstid]['price'],vol,\
                            ordertype="limit", action=action, closetype = closetype)
            
            ## register the information
            if orderid > 0:
                self.arbit_order_id += 1
                    
                self.arbit_orders[self.arbit_order_id] = { 'orderdict': orderdict,
                    'destvol': destvol,                                      
                    'instids': list(orderdict.keys()),
                    'todaypos' : todaypos, 
                    'canceldiff': canceldiff,
                    'closediff': closediff,
                    'chaseseconds': chaseseconds,
                    'firstinst': firstid,
                    'maxchase': maxchase,
                    'status': 'unfinished',
                    'action': action,
                    'secondtype': secondtype,
                    'firstorderid': orderid,
                    'fordercancel': False,
                    'secondorders': [],
                    'closingorders': {},
                    'closeseconds':closeseconds,
                    'tradevol': 0,
                    'fclosevol': 0,
                    'cancelvol': 0,
                    }
                print( context.curtime, "arbit open",self.arbit_order_id)
                self.needsave = True
                return self.arbit_order_id
            else:
                return -1
        except Exception as e:
            print('arbit open error', e.__traceback__.tb_lineno,e)
            
            
            
            
    def force_close_unfinished(self,context):
        if self.fcstarted:
            return 
        
        self.fcstarted = True
        try:
            
            allfinished = True
            for key in self.arbit_orders.keys():
                forderid = self.arbit_orders[key]['firstorderid']
                fcanceled = self.arbit_orders[key]['fordercancel']
                if self.arbit_orders[key]["status"] != 'finished' :
                     allfinished = False
                     tmplist = []
                     if context.orders[forderid]['leftvol'] > 0 and not fcanceled:
                         self.cancel_func(context,forderid)
                         self.arbit_orders[key]['fordercancel'] = True
                     for so in self.arbit_orders[key]['secondorders']:
                          if so['status'] != 'finished' and so['status'] != 'forceclosing':
                              ## force close
                              so['status'] = 'foceclosing'      
                              for sokey in so['orderinfo']:
                                    if so['orderinfo'][sokey]['tradevol'] + so['orderinfo'][sokey]['cancelvol'] < so['orderinfo'][sokey]['destvol']:
                                            orderid = so['orderinfo']['orderid']
                                            self.cancel_func(context, orderid)
                          tmplist.append(so)
                          
                     self.arbit_orders[key]['secondorders']  = tmplist
            if not allfinished:
                print("force close unfinished")
        except Exception as e:
            print('arbit open error', e.__traceback__.tb_lineno,e)
                  
    
    def trace_order(self,context):
        '''
        

        Parameters
        ----------
        context : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        try:
            allfinished = True
            for key in self.arbit_orders.keys():
                if self.arbit_orders[key]["status"] != 'finished' :
                        ## check if it is traded
                        inst = self.arbit_orders[key]['firstinst']
                        forderid = self.arbit_orders[key]['firstorderid']
                        fcanceled = self.arbit_orders[key]['fordercancel']
                        tradedvol = self.arbit_orders[key]['tradevol']
                        orderdict = self.arbit_orders[key]['orderdict']
                        action = self.arbit_orders[key]['action']
                        todaypos = self.arbit_orders[key]['todaypos']
                        ordertype = self.arbit_orders[key]['secondtype']
                        #ordertype = 'limit' if not  =='market' else 'market'
                        closetype = 'closeyesterday' if not todaypos else 'closetoday'
                        closediff = self.arbit_orders[key]['closediff']
                        chaseseconds = self.arbit_orders[key]['chaseseconds']
                        closeseconds = self.arbit_orders[key]['closeseconds']
                        maxchase = self.arbit_orders[key]['maxchase']
                        
                        if  context.orders[forderid]['tradevol'] >  tradedvol:
                            ##更新优先合约交易成功vol
                            tradevol = context.orders[forderid]['tradevol'] - tradedvol
                            print(key, "first instid Traded ",tradevol)
                            self.arbit_orders[key]['tradevol'] = context.orders [forderid]['tradevol']
                            secondorders = {'firstvol': tradevol,'status':'unfinished','curtime':context.curtime, 'chasenum': 0}
                            orderinfo = {}
                            orderfail = False
                            for instid in self.arbit_orders[key]['orderdict']:
                                if instid != inst: 
                                    pdir = orderdict[instid]['dir']
                                    orderprice = orderdict[instid]['price']
                                    if ordertype == 'current':
                                        orderprice = context.current[instid]
                                    elif ordertype == 'opponent':
                                        orderprice = context.dataslide[instid]['al_p'] if pdir > 0 else  context.dataslide[instid]['bl_p']
                                    elif ordertype == 'quoted':
                                        orderprice = context.dataslide[instid]['bl_p'] if pdir > 0 else  context.dataslide[instid]['al_p']
                                    if ordertype != 'market':
                                        ordertype = 'limit'
                                    ordervol =     orderdict[instid]['volbase']*tradevol
                                    orderid = self.order_func(context, instid, pdir, orderprice, ordervol,\
                                                    ordertype=ordertype, action=action, closetype = closetype)
                                    if orderid > 0:
                                        orderinfo[instid] = {'orderid':orderid, 'destvol':ordervol, 'tradevol':0, 'cancelvol':0, 'dir':pdir,'chasing':False}    
                                    else:
                                        print(key, "Error to make secondary orders")
                                        orderfail = True
                                        break
                            secondorders['orderinfo'] = orderinfo
                            if orderfail:
                                for inst in orderinfo:
                                    self.cancel_func(context, orderinfo[instid]['orderid'])
                                if context.orders[forderid]['leftvol'] >0 and not fcanceled :
                                        self.cancel_func(context,forderid)
                                        self.arbit_orders[key]['fordercancel'] = True
        
                                secondorders['status'] = 'forceclosing'   
                            self.arbit_orders[key]['secondorders'].append( secondorders)
                                
    
     
                        elif context.current[inst] - self.arbit_orders[key]['orderdict'][inst]['price'] > self.arbit_orders[key]['canceldiff'] and not self.arbit_orders[key]['fordercancel'] :
                            ## 若满足canceldiff 取消剩余仓位
                            print(key, "cancel diff cancel")
                            self.cancel_func(context, forderid)
                            self.arbit_orders[key]['fordercancel'] = True
                        
                        tmplist = []    
                        #处理第二批订单
                        #secondTraded = True
                        for so in self.arbit_orders[key]['secondorders']:
                            if so['status'] != 'finished' and so['status'] != 'forceclosing':
                                ## check second orders.
                                for sokey in  so['orderinfo']:
                                         ## Check trade/chase/Close
                                         orderid = so['orderinfo'][sokey]['orderid']
                                         pdir = so['orderinfo'][sokey]['dir']
                                         if context.orders[orderid]['tradevol'] > so['orderinfo'][sokey]['tradevol']:
                                             ## 订单成交
                                             print(key, "Traded", sokey, context.orders[orderid]['tradevol'] - so['orderinfo'][sokey]['tradevol'])
                                             so['orderinfo'][sokey]['tradevol'] =  context.orders[orderid]['tradevol']
                                             
                                             
                                         elif  context.orders[orderid]['errorid'] != 0 or abs(context.current[sokey] - self.arbit_orders[key]['orderdict'][sokey]['price'])> closediff[sokey]:
                                             ## Force close
                                             so['status'] ='forceclosing'
                                             print(key, 'order error/closediff, forceclosing', sokey ,orderid, context.orders[orderid]['errorid'])
                                             if context.orders[orderid]['cancelvol'] > 0:
                                                 so['orderinfo'][sokey]['cancelvol'] = context.orders[orderid]['cancelvol']
                                             break
                                         elif (context.curtime - so['curtime']).seconds > chaseseconds:
                                             so['chasenum'] += 1
                                             if so['chasenum'] > maxchase:
                                                 ## 追单超过次数 Force close
                                                 print(key, "Exceed maxchase force closing")
                                                 so['status'] ='forceclosing'
                                                 break
                                             elif not so['orderinfo'][sokey]['chasing'] :
                                                 ## 触发追单
                                                 print(key, "chase order", sokey)
                                                 so['orderinfo'][sokey]['chasing'] = True
                                                 self.cancel_func(context, orderid)
                                                 pass                                        
                                            
                                         if context.orders[orderid]['cancelvol'] >  so['orderinfo'][sokey]['cancelvol']:
                                             so['orderinfo'][sokey]['cancelvol'] = context.orders[orderid]['cancelvol']
                                             if so['orderinfo'][sokey]['chasing']:
                                                 orderprice = context.dataslide[sokey]['al_p'] if pdir > 0 else  context.dataslide[sokey]['bl_p']
                                                 ordervol = so['orderinfo'][sokey]['cancelvol']
                                                 so['orderinfo'][sokey]['orderid'] = self.order_func(context, sokey, pdir, orderprice,ordervol,\
                                                    ordertype='limit', action=action, closetype = closetype)
                                                 so['orderinfo'][sokey]['cancelvol'] = 0  
                                                 so['curtime'] = context.curtime
                                                 so['orderinfo'][sokey]['destvol'] -= so['orderinfo'][sokey]['tradevol']
                                                 so['orderinfo'][sokey]['tradevol'] = 0
                                                 so['orderinfo'][sokey]['chasing'] = False
                                                 print(key, 'chase order', sokey, orderprice, ordervol)
     
                                if  so['status'] == 'forceclosing':   
                                    print(key, "forceclosing canceling")
                                    for sokey in so['orderinfo']:
                                        if so['orderinfo'][sokey]['tradevol'] + so['orderinfo'][sokey]['cancelvol'] < so['orderinfo'][sokey]['destvol']:
                                            orderid = so['orderinfo'][sokey]['orderid']
                                            self.cancel_func(context, orderid)
                                    if context.orders[forderid]['leftvol'] >0 and not fcanceled :
                                        self.cancel_func(context,forderid)
                                        self.arbit_orders[key]['fordercancel'] = True
                                    ##self.arbit_orders[key]['status'] = 'forceclosing'    
                                
                                alltraded = True
                                for sokey in so['orderinfo']:
                                    if so['orderinfo'][sokey]['tradevol'] < so['orderinfo'][sokey]['destvol']:
                                            alltraded = False
    
                                
                                if alltraded:
                                    #print(key, so['orderinfo'])
                                    so['status'] = 'finished'
                            elif so['status'] == 'forceclosing':
                                allcanceled = True
                                
                                for sokey in  so['orderinfo']:
                                    
                                    orderid = so['orderinfo'][sokey]['orderid']
                                    if context.orders[orderid]['leftvol'] >0:
                                        allcanceled = False
                                #print(allcanceled,so['orderinfo'][sokey] )
                                if allcanceled and  context.orders[forderid]['leftvol'] == 0:
                                    #self.arbit_orders[key]['status'] = 'forceclosing'
                                    so['status'] = 'finished'
                                    corders = {}
                                    if self.arbit_orders[key]['action'] =='open':
                                        ## force closing opened group
                                        print(key, 'Force closing left open position')
    
                                        firstvol = so['firstvol']
                                        self.arbit_orders[key]['fclosevol'] += firstvol
                                        pdir = - orderdict[inst]['dir']
                                        price = context.current[inst]
                                        orderid =  self.order_func(context, inst, pdir, price,firstvol,\
                                                    ordertype='market', action='close', closetype = closetype)
                                        corders[inst] = {'orderid':orderid, 'tradevol':0, 'destvol':firstvol,'dir':pdir,'curtime':context.curtime,'finished':False}
                                        for sokey in so['orderinfo']:
                                            vol = context.orders[so['orderinfo'][sokey]['orderid']]['tradevol']
                                            if vol > 0:
                                                price = context.current[sokey]
                                                pdir = - so['orderinfo'][sokey]['dir']
                                                orderid =  self.order_func(context, sokey, pdir, price, vol,\
                                                            ordertype='market', action='close', closetype = closetype)
                                                corders[sokey] = {'orderid':orderid, 'tradevol':0, 'destvol':vol,'dir':pdir,'curtime':context.curtime,'finished':False}
                                            
                                            
                                    elif self.arbit_orders[key]['action'] =='close':
                                        ## force closing letf group
                                        print(key, 'Force closing left close position')
                                        for sokey in so['orderinfo']:
                                            so['orderinfo'][sokey]['tradevol'] = context.orders[so['orderinfo'][sokey]['orderid']]['tradevol']
                                            vol = so['orderinfo'][sokey]['destvol'] - so['orderinfo'][sokey]['tradevol']
                                            if vol > 0:
                                                price = context.current[sokey]
                                                pdir =  so['orderinfo'][sokey]['dir']
                                                orderid =  self.order_func(context, sokey, pdir, price, vol,\
                                                            ordertype='market', action='close', closetype = closetype)
                                                corders[sokey] = {'orderid':orderid, 'tradevol':0, 'destvol':vol,'dir':pdir,'curtime':context.curtime,'finished':False}
                                    
                                    self.arbit_orders[key]['closingorders'] = corders
                                
                            tmplist.append(so)
                        self.arbit_orders[key]['secondorders'] = tmplist
                        
                        closenum = 0
                        
                        if len(self.arbit_orders[key]['closingorders']) > 0:
                            ## check trade responese
                            for instid in self.arbit_orders[key]['closingorders']:
                                corders = self.arbit_orders[key]['closingorders'][instid]
                                if not corders['finished']:
                                    orderid = corders['orderid']
                                    if context.orders[orderid]['tradevol'] > corders['tradevol']:
                                        ## New trade
                                        print(key, "force close traded ", instid, context.orders[orderid]['tradevol'] - corders['tradevol'])
                                        self.arbit_orders[key]['closingorders'][instid]['tradevol'] = context.orders[orderid]['tradevol']
                                        if corders['tradevol'] == corders['destvol']:
                                            self.arbit_orders[key]['closingorders'][instid]['finished'] = True
                                            
                                            closenum += 1
                                    if context.orders[orderid]['errorid'] != 0 and (context.curtime - corders['curtime']).seconds > closeseconds:
                                        ## chase order
                                        vol = corders['destvol'] - corders['tradevol']
                                        print(key, "force closing chase order", vol)
                                        orderid = self.order_func(context, instid, corders['dir'], context.current[instid], vol,\
                                                            ordertype='market', action='close', closetype = closetype)
                                        corders['orderid'] = orderid
                                        corders['curtime'] = context.curtime
                                        corders['destvol'] -= corders['tradevol']
                                        corders['tradevol'] = 0
                                        self.arbit_orders[key]['closingorders'][instid] = corders
                                            
                                else:
                                    closenum += 1
                              
                            
                        if  context.orders[forderid]['cancelvol'] > self.arbit_orders[key]['cancelvol'] :
                            ## 更新cancelvol
                            print(key, 'first contract canceled:', context.orders[forderid]['cancelvol'] - self.arbit_orders[key]['cancelvol'])
                            self.arbit_orders[key]['cancelvol'] = context.orders[forderid]['cancelvol']
                            
                            
                        ## 判断是否全部完成
                        secondTraded = True
                        for so in self.arbit_orders[key]['secondorders']:
                            if not so['status'] =='finished':
                                secondTraded = False
                        if secondTraded and closenum == len(self.arbit_orders[key]['closingorders']) and  context.orders[forderid]['leftvol'] == 0:
                            
                            self.arbit_orders[key]["status"] = 'finished'
                            print(key, 'finished')
                        else:
                            allfinished = False
            
            if allfinished and self.needsave and self.usedb:
                self.saveToDB()
            return allfinished
        except Exception as e:
            print('arbit trace error', e.__traceback__.tb_lineno,e)
    
    def saveToDB(self):
        if len(self.arbit_orders) > 0:
            SET(self.user, 'ARBIT_STRUCT',json.dumps(self.arbit_orders))
    
    def loadFromDB(self):
        ostr = GET(self.user, 'ARBIT_STRUCT')
        if ostr:
            self.arbit_orders = json.loads(ostr)
    
            
    def cross_day(self,context):
        self.bCrossDay = True
        self.fcstarted = False
        print('arbit order crossday')
        for key in self.arbit_orders:
            self.arbit_orders[key]['todaypos'] = False
            self.arbit_orders[key]['status'] = 'finished'
            
            
            