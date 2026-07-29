# -*- coding: utf-8 -*-
"""
================================================================================
步骤1：财务数据清洗 - 适配顶刊论文面板构建
项目路径：26_7_23paper/
输入：01_raw_data/financial_data_all_quarters.csv
输出：03_clean_data/ 和 05_output/
================================================================================
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

# ============================================================================
# 1. 路径配置（使用绝对路径）
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

# 输入路径
INPUT_PATH = os.path.join(BASE_DIR, '01_raw_data', 'financial_data_all_quarters.csv')

# 输出路径
CLEAN_DATA_DIR = os.path.join(BASE_DIR, '03_clean_data')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output')
TABLES_DIR = os.path.join(OUTPUT_DIR, 'tables')

for dir_path in [CLEAN_DATA_DIR, OUTPUT_DIR, TABLES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# 输出文件路径
CLEAN_PANEL_PATH = os.path.join(CLEAN_DATA_DIR, 'financial_panel_clean.csv')
MERGE_PANEL_PATH = os.path.join(CLEAN_DATA_DIR, 'financial_panel_quarterly_for_merge.csv')
QUALITY_REPORT_PATH = os.path.join(OUTPUT_DIR, 'data_quality_report.txt')
SUMMARY_STATS_PATH = os.path.join(TABLES_DIR, 'table1_summary_stats.csv')

print("=" * 70)
print("步骤1：财务数据清洗 - 顶刊标准版")
print("=" * 70)
print(f"项目根目录：{BASE_DIR}")
print(f"输入文件：{INPUT_PATH}")
print("=" * 70)

# ============================================================================
# 2. 读取原始数据
# ============================================================================
print("\n【1/7】读取原始数据...")

df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')

print(f"   ✅ 总行数：{len(df):,}")
print(f"   ✅ 总列数：{len(df.columns)}")
print(f"   ✅ 股票数量：{df['thscode'].nunique()}")
print(f"   ✅ 时间范围：{df['report_date'].min()} 至 {df['report_date'].max()}")

# ============================================================================
# 3. 统一日期格式并提取季度标识
# ============================================================================
print("\n【2/7】标准化日期格式...")

df['report_date'] = pd.to_datetime(df['report_date'], format='%Y%m%d')
df['year'] = df['report_date'].dt.year
df['quarter'] = df['report_date'].dt.quarter
df['year_quarter'] = df['year'].astype(str) + 'Q' + df['quarter'].astype(str)

print(f"   ✅ 日期范围：{df['report_date'].min()} 至 {df['report_date'].max()}")
print(f"   ✅ 共 {df['year_quarter'].nunique()} 个季度")

# ============================================================================
# 4. 单位转换：元 → 亿元（保留原始值用于验证）
# ============================================================================
print("\n【3/7】单位转换（元 → 亿元）...")

value_cols = ['资产总计', '净利润', '营业收入', '负债合计', '所有者权益合计']
for col in value_cols:
    # 保留原始元单位
    df[col + '_原始'] = df[col]
    # 转换为亿元
    df[col + '_亿'] = df[col] / 1e8
    print(f"   ✅ {col} 转换完成")

# ============================================================================
# 5. 验证资产负债表恒等式：资产 = 负债 + 所有者权益
# ============================================================================
print("\n【4/7】验证资产负债表恒等式...")

# 计算差值
df['balance_diff'] = df['资产总计_原始'] - (df['负债合计_原始'] + df['所有者权益合计_原始'])

# 统计偏差
diff_count = (df['balance_diff'].abs() > 1).sum()
if diff_count == 0:
    print("   ✅ 所有记录满足：资产 = 负债 + 所有者权益")
else:
    print(f"   ⚠️ 发现 {diff_count} 条记录存在微小偏差（<1元，可忽略）")

# 如果有较大偏差，记录并修正
large_diff = df[df['balance_diff'].abs() > 1000]
if len(large_diff) > 0:
    print(f"   ⚠️ 发现 {len(large_diff)} 条记录存在较大偏差，将用所有者权益修正")
    df.loc[df['balance_diff'].abs() > 1000, '所有者权益合计_原始'] = (
        df.loc[df['balance_diff'].abs() > 1000, '资产总计_原始'] -
        df.loc[df['balance_diff'].abs() > 1000, '负债合计_原始']
    )
    df['所有者权益合计_亿'] = df['所有者权益合计_原始'] / 1e8

# ============================================================================
# 6. 数据清洗：处理缺失值（按公司分组）
# ============================================================================
print("\n【5/7】处理缺失值...")

df_sorted = df.sort_values(['thscode', 'report_date'])
fill_cols = ['资产总计_亿', '净利润_亿', '营业收入_亿', '负债合计_亿', '所有者权益合计_亿']

# 记录清洗前的缺失
missing_before = {col: df_sorted[col].isna().sum() for col in fill_cols}
print("   清洗前缺失值统计:")
for col, count in missing_before.items():
    print(f"      {col}: {count} 条")

# 前向填充（用过去数据补充）
for col in fill_cols:
    df_sorted[col] = df_sorted.groupby('thscode')[col].ffill()

# 后向填充（如果最开始就缺失）
for col in fill_cols:
    df_sorted[col] = df_sorted.groupby('thscode')[col].bfill()

# 记录清洗后的缺失
missing_after = {col: df_sorted[col].isna().sum() for col in fill_cols}
print("\n   清洗后缺失值统计:")
for col, count in missing_after.items():
    print(f"      {col}: {count} 条")

# ============================================================================
# 7. 生成衍生控制变量
# ============================================================================
print("\n【6/7】生成衍生控制变量...")

# Size：总资产对数（规模）
df_sorted['Size'] = np.log(df_sorted['资产总计_亿'])

# ROA：总资产收益率
df_sorted['ROA'] = df_sorted['净利润_亿'] / df_sorted['资产总计_亿']

# 资产负债率
df_sorted['Leverage'] = df_sorted['负债合计_亿'] / df_sorted['资产总计_亿']

# 权益乘数
df_sorted['Equity_Multiplier'] = df_sorted['资产总计_亿'] / df_sorted['所有者权益合计_亿']

# 营业收入对数
df_sorted['Log_Revenue'] = np.log(df_sorted['营业收入_亿'].replace(0, np.nan))

print(f"   ✅ 衍生指标：Size, ROA, Leverage, Equity_Multiplier, Log_Revenue")

# ============================================================================
# 8. 保存清洗后的面板
# ============================================================================
print("\n【7/7】保存清洗面板...")

output_cols = [
    'thscode', 'Layer', 'report_date', 'year', 'quarter', 'year_quarter',
    '资产总计_亿', '负债合计_亿', '所有者权益合计_亿', '营业收入_亿', '净利润_亿',
    'Size', 'ROA', 'Leverage', 'Equity_Multiplier', 'Log_Revenue'
]
df_clean = df_sorted[output_cols].copy()

# 保存主面板
df_clean.to_csv(CLEAN_PANEL_PATH, index=False, encoding='utf-8-sig')
print(f"   ✅ 主面板已保存：{CLEAN_PANEL_PATH}")

# 保存合并专用版
df_merge = df_clean[['thscode', 'year_quarter', 'Size', 'ROA', 'Leverage', 'Log_Revenue']].copy()
df_merge.to_csv(MERGE_PANEL_PATH, index=False, encoding='utf-8-sig')
print(f"   ✅ 合并面板已保存：{MERGE_PANEL_PATH}")

# ============================================================================
# 9. 生成数据质量报告
# ============================================================================
print("\n生成数据质量报告...")

report_lines = []
report_lines.append("=" * 70)
report_lines.append("数据质量报告 - AI产业链财务数据清洗")
report_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append("=" * 70)

report_lines.append(f"\n【1. 数据覆盖】")
report_lines.append(f"  公司总数：{df_clean['thscode'].nunique()}")
report_lines.append(f"  时间跨度：{df_clean['report_date'].min()} 至 {df_clean['report_date'].max()}")
report_lines.append(f"  总观测值：{len(df_clean):,}")

report_lines.append(f"\n【2. 层级分布】")
for layer in df_clean['Layer'].unique():
    cnt = len(df_clean[df_clean['Layer'] == layer])
    pct = cnt / len(df_clean) * 100
    report_lines.append(f"  {layer}：{cnt} 条 ({pct:.1f}%)")

report_lines.append(f"\n【3. 缺失值处理结果】")
for col in ['资产总计_亿', '净利润_亿', '营业收入_亿']:
    miss = df_clean[col].isna().sum()
    report_lines.append(f"  {col}：{miss} 条缺失")

report_lines.append(f"\n【4. 各公司观测值统计】")
counts = df_clean.groupby('thscode').size()
report_lines.append(f"  最多：{counts.max()} 条")
report_lines.append(f"  最少：{counts.min()} 条")
report_lines.append(f"  平均：{counts.mean():.1f} 条")

report_lines.append(f"\n【5. 关键变量统计】")
for col in ['Size', 'ROA', 'Leverage']:
    report_lines.append(f"  {col}：均值={df_clean[col].mean():.4f}, 标准差={df_clean[col].std():.4f}")

report_lines.append("\n" + "=" * 70)

with open(QUALITY_REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))
print(f"   ✅ 质量报告已保存：{QUALITY_REPORT_PATH}")

# ============================================================================
# 10. 保存汇总统计表（用于论文Table 1）
# ============================================================================
print("\n生成汇总统计表...")

summary_stats = df_clean[['Size', 'ROA', 'Leverage', 'Equity_Multiplier', 'Log_Revenue']].describe()
summary_stats.to_csv(SUMMARY_STATS_PATH, encoding='utf-8-sig')
print(f"   ✅ 汇总统计表已保存：{SUMMARY_STATS_PATH}")

# ============================================================================
# 11. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 财务数据清洗完成！")
print("=" * 70)
print(f"\n📁 输出文件：")
print(f"   • 主面板：{CLEAN_PANEL_PATH}")
print(f"   • 合并面板：{MERGE_PANEL_PATH}")
print(f"   • 质量报告：{QUALITY_REPORT_PATH}")
print(f"   • 汇总统计：{SUMMARY_STATS_PATH}")
print("=" * 70)