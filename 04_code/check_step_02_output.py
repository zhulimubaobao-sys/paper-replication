# -*- coding:utf-8 -*-
"""
==============================================================
Step 2: Aggregate Daily Data to Monthly Panel (iFinD Adapted)
【顶刊规范优化版｜日度面板聚合股票-月度平衡面板】
核心逻辑：
1. iFinD导出Ret为百分比数值，除以100转为小数，复利计算月度简单收益率
2. 月内波动率：当月日超额收益率标准差；当月仅1个交易日时Volatility=NaN
3. 输出变量：月度个股收益、月度超额收益、沪深300月度收益、月末收盘价、波动率、当月交易天数
4. 输出面板直接供给Step3构建DID事件研究变量
==============================================================
"""

import pandas as pd
import numpy as np
import os

# ===================== 项目路径配置（集中管理，便于修改） =====================
BASE_DIR = r"D:\thailand study\26_7_23paper"
INPUT_FILE = os.path.join(BASE_DIR, "02_processed_data", "01_excess_return_panel.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "02_processed_data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "02_monthly_panel.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===================== 参数开关（方便稳健性调试） =====================
WARN_EXTREME_THRESHOLD = 0.5    # 月度收益绝对值阈值，触发警告
SAVE_LOG = False                 # 是否将运行日志保存至文本

# ===================== 读取日度面板 =====================
print("=" * 60)
print("Step 2: Aggregate Daily Data to Monthly Panel")
print("=" * 60)

print(f"\n[1/4] Reading daily panel: {INPUT_FILE}")
df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
df['time'] = pd.to_datetime(df['time'])
print(f"      Success! Rows: {len(df):,}, Stocks: {df['thscode'].nunique()}")

# 生成时间标识并强制整型
df["year"] = df["time"].dt.year.astype(int)
df["month"] = df["time"].dt.month.astype(int)
df["year_month"] = df["time"].dt.strftime("%Y%m").astype(int)
print("      【自动生成】year / month / year_month 字段完成")

# ===================== 必要字段校验 =====================
required_cols = ['thscode', 'time', 'year', 'month', 'year_month', 'Ret', 'Excess_Ret', 'close', 'Index_Ret']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise KeyError(f"缺失必要字段: {missing_cols}. 请检查Step1输出文件！")

# 过滤收益率NaN/Inf异常观测
valid_mask = (
    np.isfinite(df["Ret"])
    & np.isfinite(df["Excess_Ret"])
    & np.isfinite(df["Index_Ret"])
)
df = df[valid_mask].copy()
print(f"      剔除收益率NaN/inf异常日观测，剩余有效日数据：{len(df):,}")

# ===================== 分组聚合函数 =====================
print("\n[2/4] Aggregating to monthly frequency...")

def agg_func(sub_df: pd.DataFrame) -> pd.Series:
    """
    单只股票单月日度数据聚合函数
    param sub_df: 个股单月全部日观测
    return: 月度汇总指标
    note:
        1. Ret原始为百分比，先/100转为小数；采用简单收益复利
        2. Volatility：当月日超额收益标准差；交易日=1时输出NaN
    """
    sub_df = sub_df.sort_values("time").copy()
    # iFinD百分比转小数
    ret_daily = sub_df['Ret'] / 100
    excess_daily = sub_df['Excess_Ret'] / 100
    index_daily = sub_df['Index_Ret'] / 100

    ret_m = (1 + ret_daily).prod() - 1
    excess_m = (1 + excess_daily).prod() - 1
    idx_ret_m = (1 + index_daily).prod() - 1

    close_end = sub_df['close'].iloc[-1]
    vol = excess_daily.std()
    trade_days = len(sub_df)
    y = sub_df['year'].iloc[0]
    m = sub_df['month'].iloc[0]

    return pd.Series([
        y, m, ret_m, excess_m, close_end, vol, trade_days, idx_ret_m
    ], index=[
        "year", "month", "Ret_monthly", "Excess_Ret_monthly",
        "Clsprc_end", "Volatility", "Trading_Days", "HS300_Ret_monthly"
    ])

df_monthly = df.groupby(["thscode", "year_month"]).apply(agg_func).reset_index()
print(f"      Success! Monthly panel rows: {len(df_monthly):,}")

# ===================== 数据质量检验 =====================
print("\n[3/4] Running data quality checks...")

extreme_ret = df_monthly[(df_monthly['Ret_monthly'] > WARN_EXTREME_THRESHOLD) | (df_monthly['Ret_monthly'] < -WARN_EXTREME_THRESHOLD)]
if len(extreme_ret) > 0:
    print(f"      Warning: Found {len(extreme_ret)} extreme monthly returns (>{WARN_EXTREME_THRESHOLD*100}% or <{-WARN_EXTREME_THRESHOLD*100}%)")

stock_month_count = df_monthly.groupby('thscode').size()
min_months = stock_month_count.min()
max_months = stock_month_count.max()
print(f"      Months per stock: Min {min_months}, Max {max_months}")

mean_excess_monthly = df_monthly['Excess_Ret_monthly'].mean()
print(f"      Mean monthly excess return: {mean_excess_monthly:.6f}")

# ===================== 输出月度面板 =====================
print("\n[4/4] Saving monthly panel...")
df_monthly = df_monthly.sort_values(['thscode', 'year', 'month'])
df_monthly.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print(f"      Saved: {OUTPUT_FILE}")

# ===================== 汇总信息输出 =====================
print("\n" + "=" * 60)
print("Step 2 Completed! Summary:")
print("=" * 60)
print(f"   Stocks: {df_monthly['thscode'].nunique():,}")
start_y = int(df_monthly['year'].min())
start_m = int(df_monthly['month'].min())
end_y = int(df_monthly['year'].max())
end_m = int(df_monthly['month'].max())
print(f"   Time Range: {start_y}-{start_m:02d} to {end_y}-{end_m:02d}")
print(f"   Total Observations: {len(df_monthly):,} (Stock-Month records)")
print(f"   Mean Monthly Excess Ret: {df_monthly['Excess_Ret_monthly'].mean():.6f}")
print(f"   Std Monthly Excess Ret: {df_monthly['Excess_Ret_monthly'].std():.6f}")
print("=" * 60)
print("Next step: Run step_03_build_did_variables.py")
print("=" * 60)