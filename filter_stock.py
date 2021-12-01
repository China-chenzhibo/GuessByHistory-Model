import check_day
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import os
import baostock as bs
import time


def getLatestCode(input_date):
    # 登陆系统
    bs.login()
    # 获取沪深300和中证500成分股
    rs_hs300 = bs.query_hs300_stocks(input_date)
    rs_zz500 = bs.query_zz500_stocks(input_date)
    # 打印结果集
    all_stocks = []
    while (rs_hs300.error_code == '0') & rs_hs300.next():
        # 获取一条记录，将记录合并在一起
        all_stocks.append(rs_hs300.get_row_data())

    while (rs_zz500.error_code == '0') & rs_zz500.next():
        # 获取一条记录，将记录合并在一起
        all_stocks.append(rs_zz500.get_row_data())

    result = pd.DataFrame(all_stocks, columns=rs_zz500.fields)

    for i in range(len(result)):
        global targetCode
        targetCode = result["code"][i]
        getMarketIndex(targetCode, start_date)
        print(targetCode, '数据已下载')
        df = pd.read_csv(output_Folder + targetCode + ".csv")
        if len(df)==0:
            P_ud = 0
        else:
            # 删除掉近期三年内上市的股票
            if datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()>datetime.datetime.strptime(input_date, '%Y-%m-%d').date() + relativedelta(years=-3):
                P_ud = 0
            else:
                P_ud = verify_output(df)
        result.loc[i, 'P_ud'] = P_ud
    result = result.drop(index=(result.loc[(result['P_ud'] <= P_line)].index))
    # 结果集输出到csv文件
    result.to_csv(output_Folder + "filter.csv", encoding="gbk", index=False)

    # 登出系统
    bs.logout()


def getMarketIndex(targetCode, b_date):
    filePath = output_Folder + targetCode + ".csv"
    bear_date = datetime.date.today()+ datetime.timedelta(days=-250) # 设定一年刷新一次数据
    if os.path.exists(filePath) and bool(bear_date.strftime('%Y-%m-%d') < time.strftime('%Y-%m-%d',
                                                                                                     time.localtime(
                                                                                                         os.stat(
                                                                                                             filePath).st_mtime))):
        null_package = bs.query_trade_dates()  # 发射空包 保持心跳
    else:
        rs = bs.query_history_k_data_plus(targetCode, "date,code,open,high,low,close,preclose,volume,amount,pctChg",
                                          start_date=b_date, end_date=boundary_date, frequency="d")
        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        trade_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        while not check_day.is_tradeDay(trade_date)[0]:  # 消除新股上市的影响 默认2个月恢复正常走势
            trade_date =trade_date + datetime.timedelta(days=1)
        if result['date'][0]!=trade_date.strftime('%Y-%m-%d'):
            result = result[40:]
        result = result.drop(index=(result.loc[(result['volume'] == '0')].index)) # 消除停牌情况
        result.reset_index(drop=True, inplace=True)
        if len(result)!=0:
            for i in range(len(result)):
                open = float(result['open'][i])
                close = float(result['close'][i])
                preclose = float(result['preclose'][i])
                result.loc[i, 'label'] = describeState(open, close, preclose)[0]
                result.loc[i, 'UpOrDown'] = describeState(open, close, preclose)[1]

        # 结果集输出到csv文件
        result.to_csv(output_Folder + targetCode + ".csv", index=False)


def describeState(open, close, preclose):
    fee = 0.0002
    if open > (preclose * (1 + fee)):
        label = 'H'
    elif open < (preclose * (1 - fee)):
        label = 'L'
    else:
        label = 'S'

    if close > (open * (1 + fee)):
        label = label + 'H'
    elif close < (open * (1 - fee)):
        label = label + 'L'
    else:
        label = label + 'S'

    if close > (preclose * (1 + fee)):
        UoD = 'Up'
    elif close < (preclose * (1 - fee)):
        UoD = 'Down'
    else:
        UoD = 'Smooth'

    return label, UoD


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
    return LastDayGroup  # 乱序的date 之后再看有没有必要排序


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


def verify_fx(df, VOtemp_date):  # 取2021年作为验证
    global upperlimit_date
    upperlimit_date = datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()
    correct_ud, wrong_ud = 0, 0
    if check_day.is_tradeDay(VOtemp_date)[0]:
        isNearHoliday_output = isNearHoliday(VOtemp_date)
        if isNearHoliday_output:  # 判断是否处于节假日附近
            holiday_label = isNearHoliday_output[1]
            LR = isNearHoliday_output[2]
            dict_upD = getProbability_nearHolidaty(df, VOtemp_date, holiday_label, LR)[0]
        else:  # 输入的日期不是特殊的日期
            dict_upD = getProbability_normalDay(df, VOtemp_date)[0]

        for key1, value1 in dict_upD.items():
            if value1 == max(dict_upD['Up'], dict_upD['Down'], dict_upD['Smooth']):
                new_ud = key1

        if df.loc[df['date'] == VOtemp_date.strftime('%Y-%m-%d')]['UpOrDown'].to_string()[-2:] == new_ud[-2:]:
            correct_ud = correct_ud + 1
        else:
            wrong_ud = wrong_ud + 1
    return [correct_ud, wrong_ud]


def verify_output(df):
    VOend_date = datetime.datetime.strptime(boundary_date, '%Y-%m-%d').date() + datetime.timedelta(days=-1)
    VOstart_date = VOend_date + relativedelta(years=-1)  #  选择回测的范围 由于调至两年或者三年运行时间过长，因此偷工减料到1年
    VOtemp_date = VOstart_date
    P = [0, 0]
    while not bool(VOtemp_date > VOend_date):
        temp = verify_fx(df, VOtemp_date)
        for j in range(len(temp)):
            P[j] = P[j] + temp[j]
        VOtemp_date = VOtemp_date + datetime.timedelta(days=1)

    return P[0] / (P[0] + P[1])


if __name__ == '__main__':
    output_Folder = os.getcwd() + "\\outputIndex\\backtest_data\\"
    start_date = '2005-01-01'
    boundary_date = '2018-12-28' # 回测的日期即训练集的最后一天/验证集的前一天
    P_line = 0.5
    targetCode = ""
    getLatestCode(boundary_date)
