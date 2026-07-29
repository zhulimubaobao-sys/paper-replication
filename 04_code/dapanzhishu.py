# -*- coding:utf-8 -*-
"""
功能：批量获取三大核心大盘指数的日线数据，并合并保存至一个总文件
依赖库：pandas, iFinDPy
"""

# 导入必要的库
from iFinDPy import *
import pandas as pd

# ================= 配置区 =================
# 填写你的iFinD登录账号密码
user = "yxwgy037"
pwd = "124228Xf"

# 数据提取的时间范围
START_DATE = '2019-01-01'
END_DATE = '2026-07-01'

# 需要提取的行情指标
FIELDS = "open,close,changeRatio,volume,amount"

# 复权及基准日期参数（注：指数通常不需要复权，但保持参数一致性）
PARAMS = 'CPS:3,baseDate:2019-01-01'

# 定义三大核心指数代码列表
index_codes = "000300.SH,000001.SH,399001.SZ"
# ==========================================

# ================= 主程序入口 =================
if __name__ == "__main__":
    # 登录iFinD接口
    login_status = THS_iFinDLogin(user, pwd)
    if login_status == 0:
        print(" iFinD接口登录成功！")
    else:
        print(f" 登录失败，错误码：{login_status}")
        exit()  # 登录失败则终止程序

    print(f"\n 正在获取全部 {len(index_codes.split(','))} 只大盘指数的数据...")

    # 调用iFinD接口获取历史行情数据 (注意：必须使用位置参数)
    res = THS_HQ(
        index_codes,
        FIELDS,
        PARAMS,
        START_DATE,
        END_DATE
    )

    # 【核心修复】检查接口返回状态并处理数据 (errorcode 是整数 0，不是字符串 '0')
    if res.errorcode == 0:
        df = res.data

        # 增加空数据保护：防止接口返回成功但实际无数据的情况
        if df is None or df.empty:
            print("️ 警告：接口返回成功，但获取到的数据为空！请检查指数代码或时间范围。")
        else:
            # 按指数代码和时间排序，保证数据有序
            df.sort_values(by=['thscode', 'time'], inplace=True)

            # 保存为CSV文件
            output_filename = "dapanzhishu.csv"
            df.to_csv(output_filename, encoding="utf-8-sig", index=False)
            print(f" 数据获取成功！共 {len(df)} 行，已保存至: {output_filename}")
    else:
        print(f" 数据获取失败！错误码: {res.errorcode}, 错误信息: {res.errmsg}")

    # 登出iFinD
    THS_iFinDLogout()
    print("\n 任务完成，已登出iFinD。")