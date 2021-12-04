import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

output_Folder = os.getcwd() + "\\outputIndex\\nowaday_data\\"
targetIndex = ['sh.600038']  # 输入相应的标签
for target in targetIndex:
    df = pd.read_csv(output_Folder + target + ".csv")

# density值为true使得纵坐标从频数转换为频率/组距，横坐标是涨跌幅，其单位是%
# bins值可以通过调整，增减组距的大小
a = df['pctChg']
plt.hist(x=a, density=1, alpha=0.9, bins=500)
# 调整生成图片的尺寸比例
plt.rcParams['figure.figsize'] = (12.0, 4.0)
# 绘制网格线
plt.grid(color='black', ls='--', alpha=0.6)
# 增加横坐标数量
new_ticks = np.linspace(-10, 10, 17)
plt.xticks(new_ticks)
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 减号默认用unicode编码
plt.title('上证指数涨跌幅频率分布图')
plt.xlabel("涨跌幅(%)")
plt.ylabel("频率/组距")
plt.show()
