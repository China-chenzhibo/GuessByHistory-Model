# Guess By History Model
* 标签：    `节假日`    `股票涨跌预测`    `股票走势预测`    `历史概率统计`    `回测`
* Label：    `Holiday Label`    `Price Forecast`    `Trend Forecast`    `Probability Statistics`    `Backtest`

## 一、模型介绍
这是一种基于日历效应的统计概率预测模型，认为存在某些产业、个股一年内在部分区间或者节假日前后涨跌一致，统计同时期的历史数据，预测涨跌概率/走势形态，并且给出粗择时建议。 <br> <br>
* 根据查询日期，判断所处是否为节假日前后或者是正常交易日，自动追溯往年同一时期涨跌平情况及走势形态，如果是节假日的前/后会定位到上一个节假日的前/后，如果是普通交易日则取往年的一周数据。个股及各类指数数据的标的代码在IndexData这个文件中。 <br>
* 在东方财富上进行组合实盘模拟，发行时间为2021年12月6日，初始资金一百万，后因存在不可控的策略回撤及市场行情（国内一月份m1和m2剪刀差过大且美国通胀加息）选择在2月7日下架模拟盘，可以点开[GBHM实盘模拟链接](http://group.eastmoney.com/other,10183245.html)查看每日调仓情况。<br>
* 下图是模型的框架预览，如果打开不了图片，可以自行搜索[解决方案](https://blog.csdn.net/qq_38232598/article/details/91346392)，修改hosts对github的域名解析。
* 数据接口来自于baostock。

![GBHMpic](https://github.com/China-chenzhibo/GuessByHistory-Model/blob/f70a72aeeb7ff64372870a27932735f4388d0690/images/GBHMpic.png)

## 二、回测结果
策略选取的标的是沪深300和中证500成分股，在中信自研的CATS量化平台上执行回测，选取每日竞争力(=模型适用度x当日上涨概率x当日历史平均涨幅)前五的标的买入，保持每日持仓5-10只股票，基准是沪深300，回测时间2019年-2021年，股票每笔交易时买入佣金万分之三，卖出佣金万分之三，卖出时千分之一印花税, 每笔交易佣金最低扣5块钱，文件详见GBH_strategy.py，模型表现如下：（蓝色线是本策略，白色线是沪深300）<br>

    年化收益率26.57% 阿尔法12.04% 贝塔0.71 夏普比率1.24 收益率波动20.83% 信息比率0.39 (整个回测周期)最大回撤22.01%

![yieldcurve](https://github.com/China-chenzhibo/GuessByHistory-Model/blob/64902f795bea2ab9b8b2691e40b55e2826a12239/images/yieldcurve.png)
![stocktrend](https://github.com/China-chenzhibo/GuessByHistory-Model/blob/132f67bc26eef1042d66eadf512df128cf18ea1e/images/logstocktrend.png)
## 三、注意事项
代码中已考虑停牌、新股上市数据异常、节假日重叠、往年节假日可能不休市等情况，在代码文件的备注中有所体现。<br>
* 涨跌说明：涨跌是由当日收盘价和前一日收盘价决定，其中如果幅度小于万三视为平，相当于交了股票交易费。<br>
* 走势说明：日志会返回股票价格走势择时建议，走势是由预测当天开盘价和收盘价决定，共'高开高走'、'高开平走'、'高开低走'、'低开高走'、'低开平走'、'低开低走'、'平开高走'、'平开低走'、'平开平走'九种形态。

## 四、文件介绍
### 1. check_day文件夹
做了一个package，如果只为查询所输入的日期是否交易日，只需要下载这个包就可以，目前数据只更新到2022年，输入某个具体的日期，is_tradeDay这个方法可以返回【是否为交易日】和【该日期的属性标签<交易日None,周末Weekend,节假日xxxx Day>】具体用法如下展示。

#### is_tradeDay.py
```python
# 可以将check_day放在项目文件夹的同级目录中
import check_day
import datetime
# 可以如下两种形式输入 即需要转成date形式否则报错
search_date1 = datetime.date(2021, 11, 26) # 正常交易日的周五
search_date2 = datetime.datetime.strptime('2021-11-27', '%Y-%m-%d').date()  # 周末
search_date3 = datetime.datetime.strptime('2021-10-7', '%Y-%m-%d').date() # 国庆节
print(check_day.is_tradeDay(search_date1))
print(check_day.is_tradeDay(search_date2))
print(check_day.is_tradeDay(search_date3))
#返回的结果如下:
#(True, 'None')
#(False, 'Weekend')
#(False, 'National Day')
```

一开始想找判断是否为交易日的包，但在网上只找到一些可调用的api，而我需要的数据是返回节假日的标签，所以就尝试爬证监会的休市声明文件，但是发现官网上发布的文件存在不齐。后面基于chinese_calendar这个包做了一些修改，自研成check_day的包。 <br>

理论上也可以用baostock和chinese_calendar【目前这两个包使用起来是不收费】结合起来，前者是判断所查询日期是否为交易日，后者是判断所查询的日期是否为节假日，并返回节日标签。

#### holiday_data.py
存放节假日信息的匹配标签，可以理解为一个数据库，可以再这个文件上修改节假日的定义，holidays里面的内容可以通过爬取政府网站有关节假日放假的通知，其中，2005年和2006年春节前股市有几天不进行交易，还有国庆和中秋恰好处于同一天，所以需要手动修改这三处，目前只增加到2022年。


### 2. GuessByHistory文件夹
主文件，存放模型、回测策略、测试用例、下载数据等文件。

#### GBH_main.py
命令行交互的模型，运行后根据指令输入标的和日期，会返回相应的日期属性、被统计日期、涨跌概率、走势形态概率、回测概率。
#### GBH_testCase.py
放了一些测试用例，用来测试模型的使用。
#### densityPlot.py
运行后，插入想查找的标的，会生成从2005-01-01或者是上市日期至今的涨跌幅度频率分布直方图。
#### filter_stock.py & GBH_strategy.py
将模型升级为策略，遍历沪深300和中证500的标的，先做一遍标的筛选，除去一些模型准确度不合格的标的，因此先运行filter_stock.py，里面训练集选取的日期可以根据实际修改。filter_stock.py没有多线程跑，运行时间相对较长，大概是6个小时上下，尝试用了线程池去优化，但是python一个进程最多只有一个cpu做处理，所以对于计算密集型的部分优化不明显，之后会尝试用多进程优化一下。对于下载数据方面尝试用了多线程下载，可是本身baostock分配给一个ip的服务是单线的，所以用多线程下载数据会报错。<br>
GBH_strategy.py设置回测开始到结束时间分别是2019年1月1日到2021年11月26日，可根据个人实际进行修改num_stock，表示同一天最多做多5只股票。由于CATS回测平台只能设置在开盘成交，因此买卖逻辑如下图：

          第T日       第T+1日     第T+2日     第T+3日
    盘前  预测T+1日①  预测T+2日②  预测T+3日③  预测T+4日④ 
    开盘    买①         买②        买③卖①      买④卖②
#### mock_stock.py
实盘模拟，每日运行，返回买入卖出建议，做一个.bat文件就可以一键执行策略。
#### outputIndex文件夹
主要放置一些从baostock的api拿下来的数据。<br>
其中，IndexData存放个股代码和指数数据（综合指数、规模指数、一级行业指数、二级行业指数、策略指数、成长指数、价值指数、主题指数、基金指数、债券指数），具体打开文件查找相应的标的代码。<br>
backtest_data放的是回测数据（2005-2018作为训练集，2019-2021作为验证集），nowaday_data用来预测未来（2005-2021年作为训练集），实盘进行。
