"""
	实盘模拟：http://group.eastmoney.com/other,10183245.html
"""
import sys

sys.path.extend(['C:\\Users\\044608\\codeProject\\TensorFlow'])  # 为了bat能够识别module 添加check_day的路径
import pandas as pd
import datetime
import check_day
from dateutil.relativedelta import relativedelta


def before_trading_start():
    getOtherDay()
    #  CATS没有提供查询回测日期的api函数，只能间接获取 T+1 日期，用于预测
    today_date = test_date
    tomorrow_date = today_date + datetime.timedelta(days=1)
    while check_day.is_tradeDay(tomorrow_date)[0] == False:
        tomorrow_date = tomorrow_date + datetime.timedelta(days=1)

    empty = pd.DataFrame(columns=['code', 'up_accuracy', 'trend_label'])
    for code_baostock in target_pool['code']:
        trend = target_pool.loc[target_pool['code'] == code_baostock]['P_ud']
        df = pd.read_csv(filePath + code_baostock + '.csv', encoding='gbk')
        global upperlimit_date
        upperlimit_date = datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()
        upD_P, upD_X, trend_label = output_fx(df, tomorrow_date)
        trend_label = output_fx(df, today_date)[2]
        up_accuracy = upD_P * upD_X * float(trend.values)
        df_add = pd.DataFrame(
            {"code": [swapCode(code_baostock)], "up_accuracy": [up_accuracy], "trend_label": [trend_label]})
        empty = empty.append(df_add, ignore_index=True)

    empty.sort_values(by="up_accuracy", axis=0, ascending=False, inplace=True)
    empty = empty.reset_index(drop=True)
    global T
    T = []

    dict_describeState = {'HH': '高开高走', 'HS': '高开平走', 'HL': '高开低走', 'LH': '低开高走', 'LS': '低开平走', 'LL': '低开低走',
                          'SH': '平开高走', 'SL': '平开低走', 'SS': '平开平走'}
    for i in range(num_stock):
        T.append(empty['code'][i])
    print('T  天看多', T)
    print('')
    print('------标的走势形态预测------')
    for i in range(num_stock):
        print(empty['code'][i], '最可能的走势是', dict_describeState[empty['trend_label'][i]])  # 打印预测走势 提供择时建议

    suggestionOrder()


def suggestionOrder():
    buy_market = []
    sell_market = []
    for stock_buy in T:
        if stock_buy not in (T_minus1 + T_minus2):
            buy_market.append(stock_buy)
    for stock_sell in T_minus2:
        if stock_sell not in (T_minus1 + T):
            sell_market.append(stock_sell)
    print('')
    print('------买入卖出辅助建议------')
    print('请卖出标的', sell_market)
    print('请买入标的', buy_market)


def getOtherDay():  # 获取T_1和T_2天看多仓位
    T_1date = test_date
    while check_day.is_tradeDay(T_1date)[0] == False:
        T_1date = T_1date + datetime.timedelta(days=-1)

    T_1df = pd.DataFrame(columns=['code', 'up_accuracy', 'trend_label'])
    for code_baostock in target_pool['code']:
        trend = target_pool.loc[target_pool['code'] == code_baostock]['P_ud']
        df = pd.read_csv(filePath + code_baostock + '.csv', encoding='gbk')
        global upperlimit_date
        upperlimit_date = datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()
        upD_P, upD_X, trend_label = output_fx(df, T_1date)
        up_accuracy = upD_P * upD_X * float(trend.values)
        df_add = pd.DataFrame(
            {"code": [swapCode(code_baostock)], "up_accuracy": [up_accuracy], "trend_label": [trend_label]})
        T_1df = T_1df.append(df_add, ignore_index=True)

    T_1df.sort_values(by="up_accuracy", axis=0, ascending=False, inplace=True)
    T_1df = T_1df.reset_index(drop=True)
    global T_minus1
    T_minus1 = []
    for i in range(num_stock):
        T_minus1.append(T_1df['code'][i])

    T_2date = T_1date + datetime.timedelta(days=-1)
    while check_day.is_tradeDay(T_2date)[0] == False:
        T_2date = T_2date + datetime.timedelta(days=-1)

    T_2df = pd.DataFrame(columns=['code', 'up_accuracy', 'trend_label'])
    for code_baostock in target_pool['code']:
        trend = target_pool.loc[target_pool['code'] == code_baostock]['P_ud']
        df = pd.read_csv(filePath + code_baostock + '.csv', encoding='gbk')
        upperlimit_date = datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()
        upD_P, upD_X, trend_label = output_fx(df, T_2date)
        up_accuracy = upD_P * upD_X * float(trend.values)
        df_add = pd.DataFrame(
            {"code": [swapCode(code_baostock)], "up_accuracy": [up_accuracy], "trend_label": [trend_label]})
        T_2df = T_2df.append(df_add, ignore_index=True)

    T_2df.sort_values(by="up_accuracy", axis=0, ascending=False, inplace=True)
    T_2df = T_2df.reset_index(drop=True)
    global T_minus2
    T_minus2 = []
    for i in range(num_stock):
        T_minus2.append(T_2df['code'][i])
    print('T-2天看多', T_minus2)
    print('T-1天看多', T_minus1)


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
    while not check_day.is_tradeDay(lastyear_date)[0] or isNearHoliday(lastyear_date):
        lastyear_date = lastyear_date + datetime.timedelta(days=1)
    LastDayGroup = [lastyear_date.strftime('%Y-%m-%d')]
    Ldate = lastyear_date + datetime.timedelta(days=-1)
    Rdate = lastyear_date + datetime.timedelta(days=1)
    if not isNearHoliday(Ldate):
        for _ in range(2):
            if bool(upperlimit_date <= Ldate):  # 避免回溯超上限
                while not check_day.is_tradeDay(Ldate)[0]:
                    Ldate = Ldate + datetime.timedelta(days=-1)
                LastDayGroup.append(Ldate.strftime('%Y-%m-%d'))
                Ldate = Ldate + datetime.timedelta(days=-1)
                if isNearHoliday(Ldate + datetime.timedelta(days=-1)):
                    break

    if not isNearHoliday(Rdate):
        for _ in range(2):
            while not check_day.is_tradeDay(Rdate)[0]:
                Rdate = Rdate + datetime.timedelta(days=1)
            LastDayGroup.append(Rdate.strftime('%Y-%m-%d'))
            Rdate = Rdate + datetime.timedelta(days=1)
            if isNearHoliday(Rdate + datetime.timedelta(days=1)):
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


if __name__ == '__main__':
    test_date = datetime.date.today()  # 实盘当天日期

    filePath = 'C:\\Users\\044608\\codeProject\\TensorFlow\\GuessByHistory\\outputIndex\\backtest_data\\'
    target_pool = pd.read_csv(filePath + 'filter.csv', encoding='gbk')
    start_date = '2005-01-01'  # 默认从2005年开始统计
    T = []  # T日建议配置的仓位
    T_minus1 = []  # T-1日建议配置的仓位
    T_minus2 = []  # T-2日建议配置的仓位

    num_stock = 5  # 每日做多5只股票
    upperlimit_date = datetime.date(2005, 1, 1)
    before_trading_start()
