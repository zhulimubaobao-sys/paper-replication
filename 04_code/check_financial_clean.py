# -*- coding: utf-8 -*-
"""
================================================================================
核验脚本：验证财务数据清洗结果
功能：检查清洗后的数据质量，确保满足回归要求
================================================================================
"""

import pandas as pd
import os

BASE_DIR = r"D:/thailand study/26_7_23paper"

# 读取清洗后的面板
df = pd.read_csv(os.path.join(BASE_DIR, "03_clean_data", "financial_panel_clean.csv"))

print("=" * 70)
print("财务数据清洗核验报告")
print("=" * 70)

# ============================================================================
# 核验1：数据完整性
# ============================================================================
print("\n【核验1】数据完整性")
print("-" * 50)

print(f"  总观测值：{len(df):,}")
print(f"  股票数量：{df['thscode'].nunique()}")
print(f"  季度数量：{df['year_quarter'].nunique()}")
print(f"  时间范围：{df['report_date'].min()} 至 {df['report_date'].max()}")

# ============================================================================
# 核验2：缺失值检查
# ============================================================================
print("\n【核验2】缺失值检查（应全部为0）")
print("-" * 50)

required_cols = ['Size', 'ROA', 'Leverage', 'Equity_Multiplier', 'Log_Revenue']
for col in required_cols:
    miss = df[col].isna().sum()
    status = "✅" if miss == 0 else "⚠️"
    print(f"  {status} {col}: {miss} 条缺失")

# ============================================================================
# 核验3：异常值检查
# ============================================================================
print("\n【核验3】异常值检查")
print("-" * 50)

# 检查ROA是否在合理范围（-1到1之间）
roa_outliers = df[(df['ROA'] > 1) | (df['ROA'] < -1)]
print(f"  ROA异常值（>100%或<-100%）：{len(roa_outliers)} 条")

# 检查Leverage是否在合理范围（0到1.5之间）
leverage_outliers = df[(df['Leverage'] > 1.5) | (df['Leverage'] < 0)]
print(f"  Leverage异常值（>150%或<0%）：{len(leverage_outliers)} 条")

# 检查Size是否在合理范围
size_outliers = df[(df['Size'] < 0) | (df['Size'] > 30)]
print(f"  Size异常值（<0或>30）：{len(size_outliers)} 条")

# ============================================================================
# 核验4：各股票观测数量
# ============================================================================
print("\n【核验4】各股票观测数量")
print("-" * 50)

stock_counts = df.groupby('thscode').size()
print(f"  最少观测：{stock_counts.min()} 条")
print(f"  最多观测：{stock_counts.max()} 条")
print(f"  平均观测：{stock_counts.mean():.1f} 条")
print(f"  标准差：{stock_counts.std():.1f}")

# 检查是否有观测过少的股票（<20条）
short_stocks = stock_counts[stock_counts < 20]
if len(short_stocks) > 0:
    print(f"  ⚠️ 观测不足的股票：{short_stocks.index.tolist()}")

# ============================================================================
# 核验5：各层级分布
# ============================================================================
print("\n【核验5】各层级分布")
print("-" * 50)

layer_counts = df.groupby('Layer').size()
for layer, count in layer_counts.items():
    pct = count / len(df) * 100
    print(f"  {layer}：{count:,} 条 ({pct:.1f}%)")

# ============================================================================
# 核验6：关键变量统计
# ============================================================================
print("\n【核验6】关键变量统计")
print("-" * 50)

for col in ['Size', 'ROA', 'Leverage', 'Equity_Multiplier']:
    print(f"\n  {col}:")
    print(f"    均值：{df[col].mean():.4f}")
    print(f"    标准差：{df[col].std():.4f}")
    print(f"    5%分位数：{df[col].quantile(0.05):.4f}")
    print(f"    50%分位数：{df[col].quantile(0.50):.4f}")
    print(f"    95%分位数：{df[col].quantile(0.95):.4f}")

# ============================================================================
# 核验结论
# ============================================================================
print("\n" + "=" * 70)
print("核验结论")
print("=" * 70)

all_pass = True
if df[required_cols].isna().sum().sum() > 0:
    print("❌ 存在缺失值，需要进一步处理")
    all_pass = False
if len(roa_outliers) > 0:
    print("⚠️ 存在ROA异常值，建议检查")
if len(leverage_outliers) > 0:
    print("⚠️ 存在Leverage异常值，建议检查")

if all_pass:
    print("✅ 数据质量通过，可进入下一步")
else:
    print("⚠️ 数据存在部分问题，建议处理后再继续")

print("=" * 70)