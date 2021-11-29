# Guess By History Model

## 模型介绍
这是一种基于统计概率方法的预测模型，认为存在某些产业、个股一年内在部分区间或者节假日前后涨跌一致。根据查询日期，判断所处是否为节假日前后或者是正常交易日，回溯往年同一时期涨跌平情况及走势形态概率，如果是节假日的前/后会定位到上一个节假日的前/后，如果是普通交易日则取往年的一周数据。个股及各类指数数据的标的代码在IndexData这个文件中。

![image](https://github.com/China-chenzhibo/GuessByHistory-Model/blob/f70a72aeeb7ff64372870a27932735f4388d0690/images/GBHMpic.png)

## 回测结果
在中信自研的CATS量化平台上回测，模型表现如果如下：

## 注意事项
代码中已考虑停牌、新股上市数据异常、节假日重叠、往年节假日可能不休市等情况，在代码的备注中有所体现。

## 文件介绍
### check_day文件夹
这是一个python package，如果只为查询所输入的日期是否交易日，只需要下载这个包就可以，目前数据只更新到2022年，输入某个具体的日期，is_tradeDay这个方法可以返回【是否为交易日】和【该日期的属性标签<交易日None,周末Weekend,节假日xxxx Day>】具体用法如下展示。

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


### GuessByHistory文件夹
主文件，存放模型、回测策略、测试用例、下载数据等文件


#### GBH_main.py
命令行交互的模型，运行后根据指令输入标的和日期，会返回相应的日期属性、被统计日期、涨跌概率、走势形态概率、回测概率。
#### GBH_testCase.py
放了一些测试用例，用来测试模型的使用。
#### densityPlot.py
运行后，插入想查找的标的，会生成从2005-01-01或者是上市日期至今的涨跌幅度频率分布直方图。
#### GBH_strategy.py
将模型升级为策略，遍历沪深300和中证500的标的
#### outputIndex文件夹
主要放置一些从baostock的api拿下来的数据。
其中，IndexData存放个股代码和指数数据（综合指数、规模指数、一级行业指数、二级行业指数、策略指数、成长指数、价值指数、主题指数、基金指数、债券指数），具体打开文件查找相应的标的代码。
backtest_data放的是回测数据（2005-2018作为训练集，2018-2021作为验证集），nowaday_data用来预测未来（2005-2021年作为训练集），实盘进行。
