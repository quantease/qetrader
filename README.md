# qetrader交易接口



## 简介

qetrader交易接口可以通过pip直接安装在用户本地，实现在任意python环境下进行策略开发、回测、模拟交易和实盘交易。



## 安装说明

首先，您的系统上必须已经安装了python环境（版本3.7或以上），推荐使用anaconda3. 然后，就可以按照如下步骤安装了。

- ### windows环境

  - 安装Microsoft C++ Build Tools

    下载链接：

    [Microsoft C++ Build Toosl]: https://visualstudio.microsoft.com/visual-cpp-build-tools/

    > 注：该工具版本号需要在14以上

  - 安装Redis-server数据库服务

    宽易提供了小工具InstallRedis.exe方便安装配套的redis-server服务。下载链接：

    [installRedis.exe]: https://quantease.cn/downloads/qeserver/installRedis.exe

    下载后运行该工具即可

    > qetrader使用的Redis端口号是6379。若需要修改为其他端口号，需要在qetrader安装完毕后修改qetrader的配置

  - 安装qetrader

    ```bash
    pip install -U qetrader --timeout=60
    ```

    > 注： 若要加快安装速度，可以使用国内镜像站点

- ### linux环境配置

  - 安装Redis

    linux下安装Redis最简单快捷的方式是使用Docker安装

    首先用docker pull 下载redis最新版本

    ```
    sudo docker pull redis
    ```

    然后启动redis容器

    ```
    sudo docker run -itd --name redis-server -p 6379:6379 redis
    ```

  - 安装qetrader

    ```bash
    pip install -U qetrader --timeout=60
    ```

    > 注： 若要加快安装速度，可以使用国内镜像站点

## 使用说明

- ### 启动网页服务

  - 写一个python文件命名为runWeb.py

    ```python
    from qetrader.qeweb import runWebpage
    runWebpage()
    ```

    

  - 在Anaconda的命令行环境下进入runWeb.py所在目录，并运行如下命令

    ```bash
    python runWeb.py
    ```

    运行后web网页服务将启动，用户可以实时查看订单委托，成交，持仓，权益和日志信息，并可以观察行情图。

    按键Ctrl+C或者关闭窗口可以终止该服务，网页将无法查看，重新运行上述命令后可恢复。

    

- ### 编写策略文件并运行

  - 如下是一个python策略文件范例

    ```python
    import qesdk
    from datetime import datetime,timedelta
    from qetrader import *
    qesdk.auth('Your username','Your authcode')
    user_setting = {'investorid':'000000', 'password':'XXXXXXXXXXXXXX','broker':'simnow'}
    user = 'myname'
    
    def getLastToken(user):
        acclist = listSimuAccounts(user)
        if len(acclist)>0:
            return acclist[-1]
        else:
            return  createSimuAccount(user, initCap=10000000)
    
    class mystrat(qeStratBase):
        
        def __init__(self):
            self.instid=['AG2306.SFE']
            self.datamode='minute'
            self.freq = 1
            
        def crossDay(self,context):
            pass
        def onBar(self,context):
            print(get_bar(context,1))
            
        def handleData(self,context):
            pass
    
    
    if __name__=='__main__':
        strat1 = mystrat()
        token_code = getLastToken(user)
        runStrat(user,'real', [strat1], simu_token=token_code, real_account=user_setting)
    
    ```

    > 注：
    >
    > 1.auth语句中授权码需要在https://quantease.cn上注册登录后点击主页右上角菜单'授权码'获取。
    >
    > 2.user_setting中账户信息需要换成您自己的账户信息
    >
    > 3.运行后复制给出的网页链接在浏览器中查看运行结果即可

  

- ### 修改系统配置

  - 获取系统配置

    ```python
    from qetrader import read_sysconfig
    read_sysconfig()
    ```

    获取结果为

    ```
    {'redis': {'host': '127.0.0.1', 'port': 6379, 'password': ''}, 'webpage': {'host': '127.0.0.1', 'port': 5814}}
    ```

    

  - 修改Redis配置

    接口函数为

    ```python
    setRedisConfig(host='127.0.0.1', port=6379, password='')
    ```

    根据您本地Redis-server配置修改该接口，使得qetrader可以访问您的本地数据库。

    比如您本地Redis端口号为6380， 那么可以这么运行

    ```python
    from qetrader import setRedisConfig
    setRedisConfig(port=6380)
    
    ```

    恢复默认出厂设置仅需要调用不带参数的setRedisConfig即可

    ```python
    from qetrader import setRedisConfig
    setRedisConfig()
    ```

    

  - 修改网页配置

    接口函数为

    ```python
    setWebConfig(host='127.0.0.1',port=5814)
    ```

    如果qetrader网页服务默认端口号5814和您本地端口冲突，您可以修改为其他端口号，比如修改为5008。

    ```python
    from qetrader import setWebConfig
    setWebConfig(port=5008)
    ```

    恢复默认出厂设置仅需要调用不带参数的setWebConfig即可

    ```
    from qetrader import setWebConfig
    setWebConfig()
    ```

    

    在浏览器测试一下输入网址http://127.0.0.1:5814, 出现如下文字代表启动成功

    ```
    qetrader网页展示服务已经成功启动
    ```

    

## 		

## 如何编写策略

​	请参照[官方文档](https://quantease.cn/newdoc)文档说明



