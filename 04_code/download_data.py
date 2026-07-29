# -*- coding: utf-8 -*-
"""
功能：批量下载100只AI概念股的日行情数据（收盘价、涨跌幅、成交量、换手率）
输入：stock_list.py 中的股票列表
输出：01_raw_data/stock/stock_returns_raw.csv
"""
import pandas as pd
import time
from pathlib import Path

# ---------- 导入股票列表 ----------
from stock_list import ALL_STOCKS

# ---------- 设置路径 ----------
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "01_raw_data" / "stock"
RAW_DIR.mkdir(parents=True, exist_ok=True)  # 自动创建文件夹

# ---------- 导入iFinD ----------
try:
    from iFinDPy import *
    print("✅ iFinD接口导入成功")
except ImportError:
    print("❌ iFinD接口未安装，请先运行SuperCommand的环境修复工具")
    exit()

# ---------- 登录（务必修改账号密码！） ----------
print("正在登录iFinD...")
# ⚠️ 把下面的 "你的账号" 和 "你的密码" 改成你自己的！
THS_iFinDLogin("你的账号", "你的密码")
print("✅ 登录成功\n")

# ---------- 开始下载 ----------
all_data = []
total = len(ALL_STOCKS)
print(f"共 {total} 只股票，时间区间：2019-01-01 至 2026-06-30")

for i, code in enumerate(ALL_STOCKS):
    try:
        print(f"  ({i+1:3d}/{total}) {code} ... ", end="", flush=True)
        data = THS_StockQuote(code, "close,pct_chg,volume,turnover",
                              "2019-01-01", "2026-06-30", "日")
        if data is not None and len(data) > 0:
            df = pd.DataFrame(data)
            df['股票代码'] = code
            all_data.append(df)
            print("✅")
        else:
            print("⚠️ 无数据")
        time.sleep(0.3)
    except Exception as e:
        print(f"❌ 报错: {e}")

# ---------- 保存 ----------
if all_data:
    df_all = pd.concat(all_data, ignore_index=True)
    output_path = RAW_DIR / "stock_returns_raw.csv"
    df_all.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 下载完成！保存至：{output_path}")
else:
    print("\n❌ 没有下载到数据，请检查网络或账号权限")

THS_iFinDLogout()