# -*- coding: utf-8 -*-
"""
功能：将日度数据聚合为月度面板，计算CAR、Post、DID
输入：02_intermediate_data/stock_with_meta.csv
输出：03_clean_data/panel_final.csv
"""
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(r"D:\thailand study\26_7_23paper")
INPUT_FILE = BASE_DIR / "02_intermediate_data" / "stock_with_meta.csv"
OUTPUT_DIR = BASE_DIR / "03_clean_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "panel_final.csv"

print("=" * 60)
print("开始执行 02_panel_construction.py ...")

df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
df['日期'] = pd.to_datetime(df['日期'])

# ========== 关键修复：涨跌幅转数值，非法文本转为缺失值 ==========
df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')

# 生成月份
df['月份'] = df['日期'].dt.to_period('M')

# 按股票+月份聚合
panel = df.groupby(['股票代码', '月份']).agg({
    '涨跌幅': lambda x: (1 + x/100).prod() - 1,  # 月度累计收益率（转为小数）
    '收盘价': 'last',
    'AI_exposure': 'first',
    '产业链位置': 'first'
}).rename(columns={
    '涨跌幅': 'CAR'  # 用月度累计收益作为CAR的近似
}).reset_index()

# 计算波动率（月内日收益率标准差 × 100）
vol_df = df.groupby(['股票代码', '月份'])['涨跌幅'].std().reset_index()
vol_df.rename(columns={'涨跌幅': '波动率'}, inplace=True)
panel = panel.merge(vol_df, on=['股票代码', '月份'], how='left')
panel['波动率'] = panel['波动率'] * 100

# 构建DID核心变量
panel['月份_dt'] = panel['月份'].dt.start_time
panel['Post'] = (panel['月份_dt'] >= '2025-01-01').astype(int)
panel['DID'] = panel['Post'] * panel['AI_exposure']

# 删除缺失值
panel = panel.dropna(subset=['AI_exposure', '产业链位置'])

panel.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

print(f"\n✅ 月度面板构建完成！")
print(f"   输出文件: {OUTPUT_FILE}")
print(f"   总观测数: {len(panel)}")
print(f"   覆盖股票: {panel['股票代码'].nunique()} 只")
print(f"   时间范围: {panel['月份'].min()} 至 {panel['月份'].max()}")
print(f"\n变量预览:")
print(panel[['股票代码', '月份', 'CAR', 'AI_exposure', 'Post', 'DID']].head())