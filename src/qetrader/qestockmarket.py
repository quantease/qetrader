import platform 

if platform.system() == 'Windows':
    from .win import qestockmarket as sm
else:
    from .linux import qestockmarket as sm

def checkStockTime(now):
    return sm.checkStockTime(now)

def changeStockInstIDs(stratname, instids):
    sm.changeStockInstIDs(stratname, instids)


def runStockMarketProcess(user, passwd, strats,runmode):
    sm.runStockMarketProcess(user, passwd, strats,runmode)