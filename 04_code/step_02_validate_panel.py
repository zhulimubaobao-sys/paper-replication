# -*- coding: utf-8 -*-
"""
================================================================================
核验脚本：检查月度面板质量（含财务变量）
================================================================================
"""

import pandas as pd
import os

# ====================== 使用绝对路径 ======================
BASE_DIR = r"D:/thailand study/26_7_23paper"
PANEL_PATH = os.path.join(BASE_DIR, '02_processed_data', 'monthly_panel_full.csv')

print("=" * 70)
print("月度面板核验")
print("=" * 70)

# 检查文件是否存在
if not os.path.exists(PANEL_PATH):
    print(f"❌ 文件不存在：{PANEL_PATH}")
    print("请先运行 step_02_build_monthly_panel.py 生成月度面板。")
    exit()

df = pd.read_csv(PANEL_PATH, encoding='utf-8-sig')

print(f"\n【1】基础信息")
print(f"  行数：{len(df):,}")
print(f"  公司数：{df['Stkcd'].nunique()}")
print(f"  各层级分布：\n{df['Layer'].value_counts()}")

print(f"\n【2】时间覆盖")
print(f"  时间范围：{df['year'].min()}-{df['month'].min():02d} 至 {df['year'].max()}-{df['month'].max():02d}")

print(f"\n【3】事件前后样本量")
print(f"  事件前（<2025-01）：{len(df[df['Post']==0]):,}")
print(f"  事件后（>=2025-01）：{len(df[df['Post']==1]):,}")

print(f"\n【4】财务变量完整性")
for col in ['Size', 'ROA', 'Leverage', 'Log_Revenue']:
    miss = df[col].isna().sum()
    status = "✅" if miss == 0 else "⚠️"
    print(f"  {status} {col} 缺失数：{miss:,}")

print(f"\n【5】超额收益统计")
print(df['Excess_Ret'].describe())

print(f"\n【6】每家公司观测值统计")
counts = df.groupby('Stkcd').size()
print(f"  最多：{counts.max()} 个月")
print(f"  最少：{counts.min()} 个月")
print(f"  平均：{counts.mean():.1f} 个月")

# 检查是否有公司观测过少（<24个月）
short_firms = counts[counts < 24]
if len(short_firms) > 0:
    print(f"  ⚠️ 观测不足24个月的公司：{short_firms.index.tolist()}")

print("\n" + "=" * 70)
print("✅ 核验完成！如果上述检查均通过，数据可进入DID回归。")
print("=" * 70)