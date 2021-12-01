"""
	策略：GBHM
	该.py文件是在中信CATS回测平台上运行
"""

import math
import pandas as pd
import datetime
import check_day
from dateutil.relativedelta import relativedelta

# universe 用于提前加载好标的数据，可在filter文件中swap下标的到这边，也可以不加
universe = ['600030.SH', '600038.SH', '600100.SH', '600104.SH', '600153.SH', '600340.SH', '600346.SH', '600372.SH',
            '600436.SH', '600487.SH', '600498.SH', '600535.SH', '600549.SH', '600566.SH', '600570.SH', '600588.SH',
            '600606.SH', '600703.SH', '600741.SH', '600837.SH', '600958.SH', '600999.SH', '601021.SH', '601186.SH',
            '601901.SH', '601919.SH', '603799.SH', '603993.SH', '000338.SZ', '000423.SZ', '000661.SZ', '000671.SZ',
            '000768.SZ', '000792.SZ', '000959.SZ', '002044.SZ', '002179.SZ', '002415.SZ', '002460.SZ', '002475.SZ',
            '002493.SZ', '300003.SZ', '300136.SZ', '300144.SZ', '300251.SZ', '600021.SH', '600060.SH', '600073.SH',
            '600141.SH', '600161.SH', '600216.SH', '600259.SH', '600266.SH', '600298.SH', '600316.SH', '600325.SH',
            '600428.SH', '600435.SH', '600511.SH', '600536.SH', '600563.SH', '600584.SH', '600600.SH', '600618.SH',
            '600623.SH', '600639.SH', '600640.SH', '600648.SH', '600673.SH', '600694.SH', '600717.SH', '600757.SH',
            '600773.SH', '600787.SH', '600801.SH', '600808.SH', '600874.SH', '600879.SH', '600895.SH', '600967.SH',
            '600970.SH', '600978.SH', '601777.SH', '603000.SH', '603899.SH', '000028.SZ', '000039.SZ', '000060.SZ',
            '000062.SZ', '000066.SZ', '000537.SZ', '000581.SZ', '000600.SZ', '000686.SZ', '000690.SZ', '000712.SZ',
            '002013.SZ', '002019.SZ', '002152.SZ', '002176.SZ', '002191.SZ', '002221.SZ', '002250.SZ', '002268.SZ',
            '002285.SZ', '002299.SZ', '002340.SZ', '002353.SZ', '002368.SZ', '002434.SZ', '002444.SZ', '002589.SZ']
benchmark = "000300.SH"  # 基准标的

start = '2019-01-01'  # 回测开始时间
end = '2021-11-26'  # 回测结束时间
frequency = "daily"  # 策略类型，'daily'表示日间策略使用日线回测，'minute'表示日内策略使用分钟线回测
upperlimit_date = datetime.date(2005, 1, 1)
filePath = 'C:\\Users\\044608\\codeProject\\TensorFlow\\GuessByHistory\\outputIndex\\backtest_datav2\\'
target_pool = pd.read_csv(filePath + 'filter.csv', encoding='gbk')
start_date = '2005-01-01'  # 默认从2005年开始统计
T = []  # T日建议配置的仓位
T_minus1 = []  # T-1日建议配置的仓位
T_minus2 = []  # T-2日建议配置的仓位
num_stock = 5  # 每日做多5只股票

# 设置回测股票账户， 账户需要在CATS系统中处于登录状态，sim_capital_base为回测时的初始资金。
add_trade_account(CatsTradeAccount('chenzhibo001', 'S0', sim_capital_base=1000000.0))
# 设置股票类每笔交易时的手续费：买入佣金万分之三，卖出佣金万分之三，卖出时千分之一印花税, 每笔交易佣金最低扣5块钱
set_commission_equity(
    AShareCommission(open_commission=0.0003, sell_commission=0.0003, open_tax=0.0, sell_tax=0.001, min_commission=5.0))


def initialize(context):  # 初始化
    pass


def before_trading_start(context, data):
    #  CATS没有提供查询回测日期的api函数，只能间接获取 T+1 日期，用于预测
    yesterday_df = data.history('600030.SH', 'close', 1, '1d')
    today_date = yesterday_df.index[0].date() + datetime.timedelta(days=1)
    while check_day.is_tradeDay(today_date)[0] == False:
        today_date = today_date + datetime.timedelta(days=1)
    tomorrow_date = today_date
    while check_day.is_tradeDay(tomorrow_date)[0] == False:
        tomorrow_date = tomorrow_date + datetime.timedelta(days=1)

    empty = pd.DataFrame(columns=['code', 'up_accuracy', 'trend_label'])
    for code_baostock in target_pool['code']:
        trend = target_pool.loc[target_pool['code'] == code_baostock]['P_ud']
        df = pd.read_csv(filePath + code_baostock + '.csv', encoding='gbk')
        global upperlimit_date
        upperlimit_date = datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()
        upD_P, upD_X, trend_label = output_fx(df, tomorrow_date)
        up_accuracy = upD_P * upD_X * float(trend.values)
        df_add = pd.DataFrame(
            {"code": [swapCode(code_baostock)], "up_accuracy": [up_accuracy], "trend_label": [trend_label]})
        empty = empty.append(df_add, ignore_index=True)

    empty.sort_values(by="up_accuracy", axis=0, ascending=False, inplace=True)
    empty = empty.reset_index(drop=True)
    global T, T_minus1, T_minus2
    T_minus2 = T_minus1
    T_minus1 = T
    T = []

    # H:high L:Low S:Smooth
    dict_describeState = {'HH': '高开高走', 'HS': '高开平走', 'HL': '高开低走', 'LH': '低开高走', 'LS': '低开平走', 'LL': '低开低走',
                          'SH': '平开高走', 'SL': '平开低走', 'SS': '平开平走'}
    print('------标的走势形态预测------')
    for i in range(num_stock):
        T.append(empty['code'][i])
        print(empty['code'][i], '最可能的走势是', dict_describeState[empty['trend_label'][i]])  # 打印预测走势 提供择时建议


def handle_data(context, data):
    buy_basket, sell_basket = BuySellPosition(context, T, T_minus1)
    if len(sell_basket):
        for Sellcode in sell_basket:
            order_target(symbol(Sellcode), 0)

    if len(buy_basket):
        cash = context.portfolio[0].portfolio_value / (num_stock*2)  # 获取账户资金数额
        for Buycode in buy_basket:
            open_price = get_current_data(Buycode).day_open_price  # 获取交易当日开盘价
            order_amount = math.floor(cash / open_price / 100) * 100  # 计算买入股票的数量， 为100的整数倍
            order(symbol(Buycode), order_amount)  # 用order函数下单， 买卖一定数量股票， order_amount为正数买入，负数卖出


def BuySellPosition(context, T, T_minus1):
    buy_basket = []
    sell_basket = []
    hold_basket = []  # 现已持仓
    for asset, pos in context.portfolio[0].positions.items():
        hold_basket.append(asset.symbol)
    for new_stock in T:
        if not get_current_data(new_stock).is_open:  # 股票停牌或退市处理
            pass
        else:
            if new_stock not in hold_basket:
                buy_basket.append(new_stock)

    for old_stock in hold_basket:  # 卖出股票，包含了对股票恢复停牌处理
        if old_stock not in (T_minus1 + T):
            sell_basket.append(old_stock)

    return buy_basket, sell_basket


def swapCode(code_baostock):  # 将baostock的标的代码改为cats标的代码
    code_cats = code_baostock[3:]
    if code_baostock[1] == 'h':
        code_cats = code_cats + '.SH'
    elif code_baostock[1] == 'z':
        code_cats = code_cats + '.SZ'
    else:
        print('出现未知标的')
    return code_cats


def isNearHoliday(input_date):  # 此函数查询是否在节假日附近会返回不是 或者 是+holiday label
    flag = 0
    for i in range(3):
        i = i + 1
        for _ in range(2):
            i = i * (-1)
            Linput_date = input_date + datetime.timedelta(days=i)  # 同时向左右（其中左侧权重大）找节假日
            if flag * i <= 0:
                if check_day.is_tradeDay(Linput_date)[0]:
                    if flag == 0:
                        flag = i
                    else:
                        return False
                else:
                    if check_day.is_tradeDay(Linput_date)[1] != 'Weekend':
                        holiday_label = check_day.is_tradeDay(Linput_date)[1]
                        if i > 0:  # 判断节假日处于input_date相邻的左或右
                            LR = 'Right'
                        else:
                            LR = 'Left'
                        return True, holiday_label, LR
    return False


def calculate(cal_df):
    dict_trendP = {'HH': 0, 'HS': 0, 'HL': 0, 'LH': 0, 'LS': 0, 'LL': 0, 'SH': 0, 'SL': 0, 'SS': 0}
    dict_updownP = {'Up': [], 'Down': [], 'Smooth': []}
    Up_cout, Down_cout, Smooth_cout = [0, 0], [0, 0], [0, 0]
    len_df = len(cal_df)
    for i in range(len_df):
        if cal_df.loc[i]['UpOrDown'] == 'Up':
            Up_cout[0] = Up_cout[0] + 1
            Up_cout[1] = Up_cout[1] + cal_df.loc[i]['pctChg']
        elif cal_df.loc[i]['UpOrDown'] == 'Down':
            Down_cout[0] = Down_cout[0] + 1
            Down_cout[1] = Down_cout[1] + cal_df.loc[i]['pctChg']
        else:
            Smooth_cout[0] = Smooth_cout[0] + 1
            Smooth_cout[1] = Smooth_cout[1] + cal_df.loc[i]['pctChg']

        dict_trendP[cal_df.loc[i]['label']] = dict_trendP[cal_df.loc[i]['label']] + 1

    if Up_cout[0] == 0:
        dict_updownP['Up'] = [0, 0]
    else:
        dict_updownP['Up'] = [Up_cout[0] / len_df, Up_cout[1] / Up_cout[0]]
    if Down_cout[0] == 0:
        dict_updownP['Down'] = [0, 0]
    else:
        dict_updownP['Down'] = [Down_cout[0] / len_df, Down_cout[1] / Down_cout[0]]
    if Smooth_cout[0] == 0:
        dict_updownP['Smooth'] = [0, 0]
    else:
        dict_updownP['Smooth'] = [Smooth_cout[0] / len_df, Smooth_cout[1] / Smooth_cout[0]]

    for key in dict_trendP.keys():
        dict_trendP[key] = dict_trendP[key] / len_df

    return dict_updownP, dict_trendP


def locLastHoliday(input_date, holiday_label, LR):  # 前提条件是已知inputdate是isNearHoliday
    lastyear_date = input_date + relativedelta(years=-1)
    lastyear_label = check_day.is_tradeDay(lastyear_date)[1]
    if LR == 'Left':  # 说明input_date是节后的第一天
        if lastyear_label == holiday_label:  # 减一年刚好处于节假日中
            ly_date = lastyear_date
            while 1:
                ly_date = ly_date + datetime.timedelta(days=1)  # 向后移动到非节假日
                if check_day.is_tradeDay(ly_date)[0]:
                    return ly_date
        else:
            num = 0
            while bool(num < 60):
                num = num + 1
                for _ in range(2):
                    num = num * (-1)
                    ly_date = lastyear_date + datetime.timedelta(days=num)  # 先减一天，再加一天
                    if check_day.is_tradeDay(ly_date)[1] == holiday_label:
                        while not (check_day.is_tradeDay(ly_date)[0]):
                            ly_date = ly_date + datetime.timedelta(days=1)
                        return ly_date
            return None


    else:  # 说明input_date是节前的最后一天
        if lastyear_label == holiday_label:  # 减一年刚好处于节假日中
            ly_date = lastyear_date
            while 1:
                ly_date = ly_date + datetime.timedelta(days=-1)  # 向前移动到非节假日
                if check_day.is_tradeDay(ly_date)[0]:
                    return ly_date
        else:
            num = 0
            while bool(num < 60):  # 以前的节日有些并不放假，如端午、清明、中秋，排除此影响
                num = num + 1
                for _ in range(2):
                    num = num * (-1)
                    ly_date = lastyear_date + datetime.timedelta(days=num)  # 先减一天，再加一天
                    if check_day.is_tradeDay(ly_date)[1] == holiday_label:
                        while not (check_day.is_tradeDay(ly_date)[0]):
                            ly_date = ly_date + datetime.timedelta(days=-1)
                        return ly_date
            return None


def getProbability_nearHolidaty(df, input_date, holiday_label, LR):
    candidate_group = []
    ly_date = input_date
    while bool((ly_date + relativedelta(years=-1)) >= datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()):
        ly_date = locLastHoliday(ly_date, holiday_label, LR)
        if ly_date == None:
            break
        else:
            ly_date_str = ly_date.strftime('%Y-%m-%d')
            candidate_group.append(ly_date_str)

    column_name = ['date', 'code', 'pctChg', 'label', 'UpOrDown']
    empty = pd.DataFrame(columns=column_name)
    for i in candidate_group:
        empty = pd.concat([empty, df.loc[df['date'] == i][column_name]], ignore_index=True)
    upDownProbability, trendProbability = calculate(empty)
    return upDownProbability, trendProbability


def locLastDay_normalDay(input_date):
    lastyear_date = input_date + relativedelta(years=-1)
    while not check_day.is_tradeDay(lastyear_date)[0]:
        lastyear_date = lastyear_date + datetime.timedelta(days=1)
    LastDayGroup = [lastyear_date.strftime('%Y-%m-%d')]
    Ldate = lastyear_date + datetime.timedelta(days=-1)
    Rdate = lastyear_date + datetime.timedelta(days=1)
    if not isNearHoliday(Ldate):
        for _ in range(2):
            if bool(upperlimit_date <= Ldate):  # 避免回溯超上限
                while 1:
                    Ldate = Ldate + datetime.timedelta(days=-1)
                    if check_day.is_tradeDay(Ldate)[0]:
                        LastDayGroup.append(Ldate.strftime('%Y-%m-%d'))
                        break
                if isNearHoliday(Ldate + datetime.timedelta(days=-1)):
                    break

    if not isNearHoliday(Rdate):
        for _ in range(2):
            while 1:
                Rdate = Rdate + datetime.timedelta(days=1)
                if check_day.is_tradeDay(Rdate)[0]:
                    LastDayGroup.append(Rdate.strftime('%Y-%m-%d'))
                    break
    return LastDayGroup


def getProbability_normalDay(df, input_date):
    ly_date = input_date
    candidate_group = []
    while bool((ly_date + relativedelta(years=-1)) >= datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()):
        candidate_group.extend(locLastDay_normalDay(ly_date))
        ly_date = ly_date + relativedelta(years=-1)
    column_name = ['date', 'code', 'pctChg', 'label', 'UpOrDown']
    empty = pd.DataFrame(columns=column_name)
    for i in candidate_group:
        empty = pd.concat([empty, df.loc[df['date'] == i][column_name]], ignore_index=True)
    upDownProbability, trendProbability = calculate(empty)
    return upDownProbability, trendProbability


def output_fx(df, input_date):
    isNearHoliday_output = isNearHoliday(input_date)
    if isNearHoliday_output:  # 判断是否处于节假日附近
        holiday_label = isNearHoliday_output[1]
        LR = isNearHoliday_output[2]
        dict_upD, dict_trend = getProbability_nearHolidaty(df, input_date, holiday_label, LR)

    else:  # 输入的日期不是特殊的日期
        dict_upD, dict_trend = getProbability_normalDay(df, input_date)

    sorted_trend = sorted(dict_trend.items(), key=lambda item: item[1], reverse=True)
    upD_P = dict_upD['Up'][0]  # 上涨概率
    upD_X = dict_upD['Up'][1]  # 上涨的平均幅度
    trend_label = sorted_trend[0][0]  # 走势形态
    return upD_P, upD_X, trend_label
