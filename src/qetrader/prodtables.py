


prods_sfe = ['ag','cu','al','pb','ni','hc','rb','ru','au','zn','bu','fu','sp','sn','ss','wr','ao','br']
prods_ine = ['sc','lu','nr','bc']
prods_zce = ['PM', 'WH', 'SR', 'CF', 'TA', 'OI', 'RI', 'MA', 'FG', 'RS', 'RM', 'ZC', 'JR', 'LR', 'SF', 'SM', 'CY', 'AP', 'CJ', 'UR', 'SA', 'PF', 'PK', 'ME','RO','TC','WS','ER','SH','PX']
prods_ccf = ['IF','IH','IC','T','TF','TS','TL',"IO",'MO','HO','IM']
prods_dce = ['a', 'b', 'c', 'm', 'y', 'p', 'l', 'v', 'j', 'jm', 'i', 'jd', 'fb', 'bb', 'pp', 'cs', 'eg', 'rr', 'eb', 'pg', 'lh']
prods_gfe = ['si','lc']
prods = prods_sfe + prods_ine + prods_zce + prods_ccf + prods_dce + prods_gfe

ticksize = {'AG':1,'AO':1,'CU':10,'AL':5,'HC':1,'RB':1,'PB':5,'NI':10,'RU':5,'AU':0.05,'ZN':5,'BU':2,'FU':1,'SP':2,'SN':10,'BR':5,
					  'A':1,'B':1,'C':1,'M':1,'Y':2,'P':2,'L':5,'V':5,'J':0.5,'JM':0.5,'I':0.5,'JD':1,'FB':0.5,'BB':0.05,'PP':1,'CS':1,'EG':1,'RR':1,'EB':1,'PG':1,'LH':5,
					  'PM':1,'WH':1,'SR':1,'CF':5,'TA':2,'OI':1,'RI':1,'MA':1,'FG':1,'RS':1,'RM':1,'ZC':0.2,'JR':1,'LR':1,'SF':2,'SM':2,'CY':5,'AP':1,'CJ':5,'UR':1,'SA':1,'PF':2,'PK':2,'SH':1,'PX':2,
					  'SC':0.1,'LU':1,'NR':5,'BC':5,'EC':0.1,
                      'SI':5,'LC':50,
					  'IF':0.2,'IC':0.2,'IH':0.2,'IM':0.2,'T':0.005,'TF':0.005,'TS':0.005,'TL':0.001,'IO':0.2,'MO':0.2,'HO':0.2,'WS':1,'ER':1,'ME':1,'RO':2,'TC':0.2,'WR':1,'SS':5}
volmult = {'AG':15,'AO':20,'CU':5,'AL':5,'HC':10,'RB':10,'PB':5,'NI':1,'RU':10,'AU':1000,'ZN':5,'BU':10,'FU':10,'SP':10,'SN':1,'BR':5,
					  'A':10,'B':10,'C':10,'M':10,'Y':10,'P':10,'L':5,'V':5,'J':100,'JM':60,'I':100,'JD':10,'FB':10,'BB':500,'PP':5,'CS':10,'EG':10,'RR':10,'EB':5,'PG':20,'LH':16,
					  'PM':50,'WH':20,'SR':10,'CF':5,'TA':5,'OI':10,'RI':20,'MA':10,'FG':20,'RS':10,'RM':10,'ZC':100,'JR':20,'LR':20,'SF':5,'SM':5,'CY':5,'AP':10,'CJ':5,'UR':20,'SA':20,'PF':5,'PK':5,'SH':30,'PX':5,
					  'SC':1000,'LU':10,'NR':10,'BC':10,"EC":50,
                      'SI':5,'LC':1,
					  'IF':300,'IC':200,'IH':300,'IM':200,'T':10000,'TF':10000,'TS':20000,'TL':10000,'IO':100,'MO':200,'HO':100,'WS':20,'ER':20,'ME':50,'RO':5,'TC':200,'WR':10, 'SS':5} 




prodTimes = {'A': {'morning': ['', ''], 'night': ['2100', '2300']},
             'AG': {'morning': ['0000', '0230'], 'night': ['2100', '2359']},
             'AL': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'AP': {'morning': ['', ''], 'night': ['', '']},
             'AO': {'morning': ['', ''], 'night': ['', '']},
             'AU': {'morning': ['0000', '0230'], 'night': ['2100', '2359']},
             'B': {'morning': ['', ''], 'night': ['2100', '2300']}, 'BB': {'morning': ['', ''], 'night': ['', '']},
             'BC': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'BU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'BR': {'morning': ['', ''], 'night': ['', '']},
             'C': {'morning': ['', ''], 'night': ['2100', '2300']},
             'CF': {'morning': ['', ''], 'night': ['2100', '2300']}, 'CJ': {'morning': ['', ''], 'night': ['', '']},
             'CS': {'morning': ['', ''], 'night': ['2100', '2300']},
             'CU': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'CY': {'morning': ['', ''], 'night': ['2100', '2300']},
             'EB': {'morning': ['', ''], 'night': ['2100', '2300']},
             'EG': {'morning': ['', ''], 'night': ['2100', '2300']}, 'FB': {'morning': ['', ''], 'night': ['', '']},
             'FG': {'morning': ['', ''], 'night': ['2100', '2300']},
             'FU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'HC': {'morning': ['', ''], 'night': ['2100', '2300']},
             'I': {'morning': ['', ''], 'night': ['2100', '2300']}, 'IC': {'morning': ['', ''], 'night': ['', '']},
             'IO': {'morning': ['', ''], 'night': ['', '']}, 'IF': {'morning': ['', ''], 'night': ['', '']},
             'MO': {'morning': ['', ''], 'night': ['', '']}, 'IM': {'morning': ['', ''], 'night': ['', '']},
             'HO': {'morning': ['', ''], 'night': ['', '']}, 'IH': {'morning': ['', ''], 'night': ['', '']},
             'J': {'morning': ['', ''], 'night': ['2100', '2300']},
             'JD': {'morning': ['', ''], 'night': ['', '']}, 'JM': {'morning': ['', ''], 'night': ['2100', '2300']},
             'JR': {'morning': ['', ''], 'night': ['', '']}, 'L': {'morning': ['', ''], 'night': ['2100', '2300']},
             'LH': {'morning': ['', ''], 'night': ['', '']}, 'LR': {'morning': ['', ''], 'night': ['', '']},
             'LU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'M': {'morning': ['', ''], 'night': ['2100', '2300']},
             'MA': {'morning': ['', ''], 'night': ['2100', '2300']},
             'NI': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'NR': {'morning': ['', ''], 'night': ['2100', '2300']},
             'OI': {'morning': ['', ''], 'night': ['2100', '2300']},
             'P': {'morning': ['', ''], 'night': ['2100', '2300']},
             'PB': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'PF': {'morning': ['', ''], 'night': ['2100', '2300']},
             'PG': {'morning': ['', ''], 'night': ['2100', '2300']}, 'PK': {'morning': ['', ''], 'night': ['', '']},
             'PM': {'morning': ['', ''], 'night': ['', '']}, 'PP': {'morning': ['', ''], 'night': ['2100', '2300']},
             'RB': {'morning': ['', ''], 'night': ['2100', '2300']}, 'RI': {'morning': ['', ''], 'night': ['', '']},
             'RM': {'morning': ['', ''], 'night': ['2100', '2300']},
             'RR': {'morning': ['', ''], 'night': ['2100', '2300']}, 'RS': {'morning': ['', ''], 'night': ['', '']},
             'RU': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SA': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SH': {'morning': ['', ''], 'night': ['2100', '2300']},
             'PX': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SC': {'morning': ['0000', '0230'], 'night': ['2100', '2359']},
             'EC': {'morning': ['', ''], 'night': ['', '']},
             'SF': {'morning': ['', ''], 'night': ['', '']}, 'SM': {'morning': ['', ''], 'night': ['', '']},
             'SN': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'SP': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SR': {'morning': ['', ''], 'night': ['2100', '2300']},
             'SS': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'T': {'morning': ['', ''], 'night': ['', '']},
             'TA': {'morning': ['', ''], 'night': ['2100', '2300']},
             'TF': {'morning': ['', ''], 'night': ['', '']},
             'TL': {'morning': ['', ''], 'night': ['', '']},
             'TS': {'morning': ['', ''], 'night': ['', '']}, 
             'UR': {'morning': ['', ''], 'night': ['', '']},
             'V': {'morning': ['', ''], 'night': ['2100', '2300']}, 'WH': {'morning': ['', ''], 'night': ['', '']},
             'WR': {'morning': ['', ''], 'night': ['', '']}, 'Y': {'morning': ['', ''], 'night': ['2100', '2300']},
             'ZC': {'morning': ['', ''], 'night': ['2100', '2300']},
             'ZN': {'morning': ['0000', '0100'], 'night': ['2100', '2359']},
             'SGE': {'morning': ['0000', '0230'], 'night': ['2000', '2359']},
             'SSE': {'morning': ['',''],'night':['','']},
             'SZE': {'morning':['',''],'night':['','']},
             'SI': {'morning': ['', ''], 'night': ['', '']},
             'LC': {'morning': ['', ''], 'night': ['', '']},
             'ME': {'morning': ['', ''], 'night': ['2100', '2300']},
             'RO': {'morning': ['', ''], 'night': ['2100', '2300']}, 
             'TC': {'morning': ['', ''], 'night': ['2100', '2300']},
             'WS': {'morning': ['', ''], 'night': ['2100', '2300']},
             'ER': {'morning': ['', ''], 'night': ['2100', '2300']}}



def autoCheck():
    for p in prods:
        p = p.upper()
        if not p in prodTimes:
            print("prodTime leak: ",p)
            continue
        if not p in ticksize:
            print("ticksize leak: ",p)
            continue
        if not p in volmult:
            print("volmult leak: ",p)
            continue


if  __name__ == '__main__':
    autoCheck()
    print("autoCheck done")
    