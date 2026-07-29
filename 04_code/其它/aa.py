# -*- coding: utf-8 -*-
from iFinDPy import *
import pandas as pd

USERNAME = "yxwgy037"
PASSWORD = "124228Xf"
TEST_STOCK = "301117.SZ"
START_DATE = "2024-07-23"
END_DATE = "2026-07-23"

print("正在登录 iFinD ...")
login_result = THS_iFinDLogin(USERNAME, PASSWORD)
if login_result not in (0, -201):
    print(f"登录失败，错误码: {login_result}")
    exit()
print("登录成功！\n")

print(f"正在获取 {TEST_STOCK} 的数据 ...")

# 【核心修复】：严格按照官方顺序传参
# 1. 股票代码
# 2. 指标字段（用分号隔开）
# 3. 周期参数（日频，不复权）
# 4. 开始日期
# 5. 结束日期
raw_result = THS_HistoryQuotes(
    TEST_STOCK,
    "close;pct_chg;volume;turnover",
    "period:D,pricetype:1",
    START_DATE,
    END_DATE
)

# 检查错误码
error_code = raw_result.get('errorcode', -999)
print(f"接口返回错误码: {error_code}")

if error_code == 0:
    data = raw_result.get('data')
    if data is not None and len(data) > 0:
        df = pd.DataFrame(data)
        print(f"\n✅ 数据获取成功！")
        print(f"数据行数: {len(df)}")
        print("列名:", df.columns.tolist())
        print("\n前5行预览:")
        print(df.head())
    else:
        print("⚠️ 返回的 data 为空")
else:
    print(f"❌ 获取失败，错误信息: {raw_result.get('errmsg')}")

THS_iFinDLogout()
print("\n测试结束。")