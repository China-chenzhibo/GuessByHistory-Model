import check_day
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import os
import baostock as bs
import time


"""
Initialization Phase: 处理输入的数据|下载数据|打标签
"""
def download_data():
    print("****** 请查阅代码对照表，输入想要查找的标的，如sh.000001 *****")
    global targetCode
    targetCode = input("->请输入标的，回车继续执行操作:")

    getMarketIndex(targetCode, start_date)
    return 0


def getMarketIndex(targetCode, b_date):
    output_Folder = os.getcwd() + "\\outputIndex\\nowaday_data\\"
    filePath = output_Folder + targetCode+ ".csv"
    # 当天已经更新了数据集的则不再通过baostock获取
    if os.path.exists(filePath) and bool(datetime.date.today().strftime('%Y-%m-%d')==time.strftime('%Y-%m-%d',time.localtime(os.stat(filePath).st_mtime))):
        print('【本地已存在该标的最新数据集，正在读取...】')
        pass
    else:
        # 登陆系统
        lg = bs.login()
        # 显示登陆返回信息
        print('【请稍等，正在抓取数据...】')
        rs = bs.query_history_k_data_plus(targetCode, "date,code,open,high,low,close,preclose,volume,amount,pctChg",
                                          start_date=b_date,  frequency="d")
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
        result = result.drop(index=(result.loc[(result['volume'] == '0')].index))  # 消除停牌情况
        result.reset_index(drop=True, inplace=True)

        # 结果集输出到csv文件
        result.to_csv(output_Folder + targetCode + ".csv", index=False)
        # 登出系统
        bs.logout()
    print("")

def init_date():
    dict_holiday = {"New Year's Day": '元旦', 'Spring Festival': '春节', 'Tomb-sweeping Day': '清明节', 'Labour Day': '劳动节',
                    'Dragon Boat Festival': '端午节', 'National Day': '国庆节', 'Mid-autumn Festival': '中秋节', 'Weekend': '周末'}
    while 1:
        print("****** 请依指令输入要查询的交易日，离开请输入字母q *****")
        input_year = input("->请输入年份，回车继续执行操作:")
        if input_year == 'q':
            break
        input_month = input("->请输入月份，回车继续执行操作:")
        if input_month == 'q':
            break
        input_day = input("->请输入日份，回车继续执行操作:")
        if input_day == 'q':
            break

        print("正在查询日期", input_year + '/' + input_month + '/' + input_day,"...")
        print("")
        search_date = datetime.date(int(input_year), int(input_month), int(input_day))
        if check_day.is_tradeDay(search_date)[0]:
            return search_date
        else:
            print("！你所查询的日期是" + dict_holiday[check_day.is_tradeDay(search_date)[1]] + "，股市不开盘，请重新输入。")
            print("")


def tag_df():
    global targetCode
    output_Folder = os.getcwd() + "\\outputIndex\\nowaday_data\\"
    df = pd.read_csv(output_Folder + targetCode + ".csv")
    for i in range(len(df)):
        open = float(df['open'][i])
        close = float(df['close'][i])
        preclose = float(df['preclose'][i])
        df.loc[i, 'label'] = describeState(open, close, preclose)[0]
        df.loc[i, 'UpOrDown'] = describeState(open, close, preclose)[1]
    return df


# 由于刚好是相等的情况极少发生，因此默认拿券商所能提供的最低费率万二，只要在这幅度内默认为“平”
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




"""
GetProbability Phase: 获得涨跌、走势形态的概率结果
"""
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


def getProbability_nearHolidaty(df, input_date, holiday_label, LR, Flag): # Flag表示打不打印被统计的日期
    candidate_group = []
    ly_date = input_date
    while bool((ly_date + relativedelta(years=-1)) >= datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()):
        ly_date = locLastHoliday(ly_date, holiday_label, LR)
        if ly_date == None:
            break
        else:
            ly_date_str = ly_date.strftime('%Y-%m-%d')
            candidate_group.append(ly_date_str)
    if Flag == 1:
        print("||被统计的日期||") # 打印被统计的日期群
        print(candidate_group)
        print("")

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
    Ldate = lastyear_date
    Rdate = lastyear_date
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


def getProbability_normalDay(df, input_date, Flag): # Flag表示打不打印被统计的日期
    ly_date = input_date
    candidate_group = []
    while bool((ly_date + relativedelta(years=-1)) >= datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()):
        candidate_group.extend(locLastDay_normalDay(ly_date))
        ly_date = ly_date + relativedelta(years=-1)
    if Flag == 1:
        print("||被统计的日期||")
        print(sorted(candidate_group, reverse=True))
        print("")
    column_name = ['date', 'code', 'pctChg', 'label', 'UpOrDown']
    empty = pd.DataFrame(columns=column_name)
    for i in candidate_group:
        empty = pd.concat([empty, df.loc[df['date'] == i][column_name]], ignore_index=True)
    upDownProbability, trendProbability = calculate(empty)
    return upDownProbability, trendProbability




"""
ProcessOutput Phase: 将概率结果打印出来
"""
def output_fx(df,input_date):
    # H:high L:Low S:Smooth
    dict_describeState = {'HH': '高开高走', 'HS': '高开平走', 'HL': '高开低走', 'LH': '低开高走', 'LS': '低开平走', 'LL': '低开低走',
                          'SH': '平开高走', 'SL': '平开低走', 'SS': '平开平走'}
    dict_LR = {'Left': '后', 'Right': '前'}
    dict_holiday = {"New Year's Day": '元旦', 'Spring Festival': '春节', 'Tomb-sweeping Day': '清明节', 'Labour Day': '劳动节',
                    'Dragon Boat Festival': '端午节', 'National Day': '国庆节', 'Mid-autumn Festival': '中秋节', 'Weekend': '周末'}

    isNearHoliday_output = isNearHoliday(input_date)
    if isNearHoliday_output:  # 判断是否处于节假日附近
        holiday_label = isNearHoliday_output[1]
        LR = isNearHoliday_output[2]
        print("！所查询的日期", input_date, "处于" + dict_holiday[holiday_label] + "的" + dict_LR[LR] + "一天")
        dict_upD, dict_trend = getProbability_nearHolidaty(df, input_date, holiday_label, LR, Flag=True)  # Flag=1表示打印被统计的日期
        print('||统计概率||')
        print(input_date, "上涨的概率是", round(dict_upD['Up'][0] * 100, 2), "% ，历史平均上涨幅度为", round(dict_upD['Up'][1], 2),
              "% ；下跌的概率是", round(dict_upD['Down'][0] * 100, 2), "% ，历史平均下跌幅度为", round(dict_upD['Down'][1], 2),
              "% ；平走的概率是", round(dict_upD['Smooth'][0] * 100, 2), "% ，历史平均平走涨跌幅度为", round(dict_upD['Smooth'][1], 4),
              "%")
        sorted_trend = sorted(dict_trend.items(), key=lambda item:item[1], reverse=True)
        strPrint = '形态上，该天'
        for composition in sorted_trend:
            strPrint = strPrint + dict_describeState[composition[0]] +'的概率是'+str(round(composition[1]*100,2))+'%; '
        print(strPrint)


    else:  # 输入的日期不是特殊的日期
        dict_upD, dict_trend = getProbability_normalDay(df, input_date, Flag=True) # Flag=1表示打印被统计的日期
        print('||统计概率||')
        print(input_date, "上涨的概率是", round(dict_upD['Up'][0] * 100, 2), "% ，历史平均上涨幅度为", round(dict_upD['Up'][1], 2),
              "% ；下跌的概率是", round(dict_upD['Down'][0] * 100, 2), "% ，历史平均下跌幅度为", round(dict_upD['Down'][1], 2),
              "% ；平走的概率是", round(dict_upD['Smooth'][0] * 100, 2), "% ，历史平均平走涨跌幅度为", round(dict_upD['Smooth'][1], 4),
              "%")
        sorted_trend = sorted(dict_trend.items(), key=lambda item:item[1], reverse=True)
        strPrint = '形态上，该天'
        for composition in sorted_trend:
            strPrint = strPrint + dict_describeState[composition[0]] +'的概率是'+str(round(composition[1]*100,2))+'%; '
        print(strPrint)





"""
Verifying Phase: 将概率结果打印出来
"""
def verify_fx(df, VOtemp_date):  # 取2021年作为验证
    correct_trend, wrong_trend, correct_ud, wrong_ud = 0, 0, 0, 0
    if check_day.is_tradeDay(VOtemp_date)[0]:
        isNearHoliday_output = isNearHoliday(VOtemp_date)
        if isNearHoliday_output:  # 判断是否处于节假日附近
            holiday_label = isNearHoliday_output[1]
            LR = isNearHoliday_output[2]
            dict_upD, dict_trend = getProbability_nearHolidaty(df, VOtemp_date, holiday_label, LR , Flag=False) # Flag=0表示不打印被统计的日期
        else:  # 输入的日期不是特殊的日期
            dict_upD, dict_trend = getProbability_normalDay(df, VOtemp_date, Flag=False) # Flag=0表示不打印被统计的日期

        for key1, value1 in dict_upD.items():
            if value1 == max(dict_upD['Up'], dict_upD['Down'], dict_upD['Smooth']):
                new_ud = key1

        for key2, value2 in dict_trend.items():
            if value2 == max(dict_trend['HH'], dict_trend['HS'], dict_trend['HL'], dict_trend['LH'], dict_trend['LS'],
                             dict_trend['LL'], dict_trend['SH'], dict_trend['SL'], dict_trend['SS']):
                new_trend = key2

        if df.loc[df['date'] == VOtemp_date.strftime('%Y-%m-%d')]['label'].to_string()[-2:] == new_trend[-2:]:
            correct_trend = correct_trend + 1
        else:
            wrong_trend = wrong_trend + 1
        if df.loc[df['date'] == VOtemp_date.strftime('%Y-%m-%d')]['UpOrDown'].to_string()[-2:] == new_ud[-2:]:
            correct_ud = correct_ud + 1
        else:
            wrong_ud = wrong_ud + 1
    return [correct_ud, wrong_ud, correct_trend, wrong_trend]


def verify_output(df):
    print("")
    print("【请稍等，正在回测...】")
    VOend_date = datetime.date.today()+ datetime.timedelta(days=-1)
    VOstart_date = VOend_date + relativedelta(years=-1)
    VOtemp_date = VOstart_date
    P = [0, 0, 0, 0]  # [correct_trend,wrong_trend,correct_ud,wrong_ud]
    while not bool(VOtemp_date > VOend_date):
        temp = verify_fx(df, VOtemp_date)
        for j in range(len(temp)):
            P[j] = P[j] + temp[j]
        VOtemp_date = VOtemp_date + datetime.timedelta(days=1)
    print("||该标的回测一年的结果||")
    print('回测', VOstart_date, '到', VOend_date, '涨跌正确率为', round(P[0] * 100 / (P[0] + P[1]), 2), "%")
    print('回测', VOstart_date, '到', VOend_date, '走势形态正确率为', round(P[2] * 100 / (P[2] + P[3]), 2), "%")




if __name__ == '__main__':
    global targetCode
    start_date = '2005-01-01'  # 默认从2005年开始统计
    download_data()
    input_date = init_date()
    df = tag_df()
    upperlimit_date = datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()
    output_fx(df,input_date)
    verify_output(df)



"""
# 下面代码是用来验证is_tradeDay函数的准确性，可以调整time来扩大范围
import check_day
import datetime
import pandas as pd
import os

output_Folder = os.getcwd() + "\\outputIndex\\nowaday_data\\"
targetIndex = ['sh.000001']
for target in targetIndex:
    df = pd.read_csv(output_Folder + target + ".csv") 
a = df['date'] # 读取有股票信息的date
list1 = []
for i in a:
    date_object = datetime.datetime.strptime(i, '%Y-%m-%d').date()
    list1.append(date_object)

start_date = datetime.date(2005, 1, 1)
time = 6149
jj = 0

for time in range(time):
    if check_day.is_tradeDay(start_date)[0]:
        if not(start_date == list1[jj]):
            print(start_date)
            print(list1[jj])
            print("something wrong happened on ", start_date)
        jj = jj + 1
    else:
        pass
    start_date = start_date + datetime.timedelta(days=1)    
"""


"""
# 下面代码是用来循环验证各个日期能否返回正常的结果
if __name__ == '__main__':
    upperlimit_date = datetime.datetime.strptime(df['date'][0], '%Y-%m-%d').date()    
    input_date = datetime.date(2018,1,1)
    for i in range(1460):
        input_date = input_date + datetime.timedelta(days=1)
        output_fx(input_date)
        print('############################')
"""
