# -*- coding:utf-8 -*-
"""
功能：批量获取上中下游共60只股票的日线数据，并合并保存至一个总文件
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

# 复权及基准日期参数
PARAMS = 'CPS:3,baseDate:2019-01-01'

# 定义上中下游股票代码列表（已包含后缀）
upstream_codes = "688256.SH,688041.SH,603019.SH,002049.SZ,688008.SH,300474.SZ,300308.SZ,300502.SZ,300394.SZ,002281.SZ,000988.SZ,000977.SZ,002463.SZ,300476.SZ,600183.SH,688981.SH,002371.SZ,688012.SH,300223.SZ,603986.SH"
midstream_codes = "002230.SZ,688111.SH,300229.SZ,688327.SH,002415.SZ,603160.SH,300033.SZ,002405.SZ,300624.SZ,300634.SZ,002777.SZ,300365.SZ,688088.SH,300496.SZ,002253.SZ,300078.SZ,002236.SZ,688023.SH,300451.SZ,000997.SZ"
downstream_codes = "688228.SH,300785.SZ,300058.SZ,002131.SZ,600556.SH,300781.SZ,600570.SH,002607.SZ,300253.SZ,688369.SH,300188.SZ,002439.SZ,300036.SZ,300020.SZ,300075.SZ,300168.SZ,002065.SZ,600410.SH,300170.SZ,002368.SZ"

# 合并所有股票代码
all_codes = f"{upstream_codes},{midstream_codes},{downstream_codes}"
# ==========================================

# ================= 主程序入口 =================
if __name__ == "__main__":
    # 登录iFinD接口
    login_status = THS_iFinDLogin(user, pwd)
    if login_status == 0:
        print("✅ iFinD接口登录成功！")
    else:
        print(f"❌ 登录失败，错误码：{login_status}")
        exit()  # 登录失败则终止程序

    print(f"\n🔄 正在获取全部 {len(all_codes.split(','))} 只股票的数据...")

    # 调用iFinD接口获取历史行情数据 (注意：必须使用位置参数)
    res = THS_HQ(
        all_codes,
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
            print("⚠️ 警告：接口返回成功，但获取到的数据为空！请检查股票代码或时间范围。")
        else:
            # 按股票代码和时间排序，保证数据有序
            df.sort_values(by=['thscode', 'time'], inplace=True)

            # 保存为CSV文件
            output_filename = "zongdegupiao.csv"
            df.to_csv(output_filename, encoding="utf-8-sig", index=False)
            print(f"✅ 数据获取成功！共 {len(df)} 行，已保存至: {output_filename}")
    else:
        print(f"❌ 数据获取失败！错误码: {res.errorcode}, 错误信息: {res.errmsg}")

    # 登出iFinD
    THS_iFinDLogout()
    print("\n🎉 任务完成，已登出iFinD。")