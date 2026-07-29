# -*- coding: utf-8 -*-
"""
================================================================================
步骤1：财务数据清洗 - 完整版（含异常值处理）
功能：清洗iFinD原始财务数据，生成标准化面板和控制变量
================================================================================
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

# ============================================================================
# 1. 路径配置
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

INPUT_PATH = os.path.join(BASE_DIR, '01_raw_data', 'financial_data_all_quarters.csv')
CLEAN_DATA_DIR = os.path.join(BASE_DIR, '03_clean_data')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output')
TABLES_DIR = os.path.join(OUTPUT_DIR, 'tables')
FIGURES_DIR = os.path.join(OUTPUT_DIR, 'figures')

for dir_path in [CLEAN_DATA_DIR, OUTPUT_DIR, TABLES_DIR, FIGURES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

CLEAN_PANEL_PATH = os.path.join(CLEAN_DATA_DIR, 'financial_panel_clean.csv')
MERGE_PANEL_PATH = os.path.join(CLEAN_DATA_DIR, 'financial_panel_quarterly_for_merge.csv')
QUALITY_REPORT_PATH = os.path.join(OUTPUT_DIR, 'data_quality_report.txt')
SUMMARY_STATS_PATH = os.path.join(TABLES_DIR, 'table1_summary_stats.csv')
OUTLIER_LOG_PATH = os.path.join(OUTPUT_DIR, 'outlier_log.csv')

print("=" * 70)
print("步骤1：财务数据清洗 - 含异常值处理")
print("=" * 70)
print(f"输入文件：{INPUT_PATH}")
print("=" * 70)

# ============================================================================
# 2. 读取数据
# ============================================================================
print("\n【1/8】读取原始数据...")

df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')
print(f"   ✅ 总行数：{len(df):,}, 股票数：{df['thscode'].nunique()}")

# ============================================================================
# 3. 日期标准化
# ============================================================================
print("\n【2/8】标准化日期格式...")

df['report_date'] = pd.to_datetime(df['report_date'], format='%Y%m%d')
df['year'] = df['report_date'].dt.year
df['quarter'] = df['report_date'].dt.quarter
df['year_quarter'] = df['year'].astype(str) + 'Q' + df['quarter'].astype(str)
print(f"   ✅ 共 {df['year_quarter'].nunique()} 个季度")

# ============================================================================
# 4. 单位转换
# ============================================================================
print("\n【3/8】单位转换（元 → 亿元）...")

value_cols = ['资产总计', '净利润', '营业收入', '负债合计', '所有者权益合计']
for col in value_cols:
    df[col + '_原始'] = df[col]
    df[col + '_亿'] = df[col] / 1e8
print(f"   ✅ 转换完成")

# ============================================================================
# 5. 验证资产负债表恒等式
# ============================================================================
print("\n【4/8】验证资产负债表恒等式...")

df['balance_diff'] = df['资产总计_原始'] - (df['负债合计_原始'] + df['所有者权益合计_原始'])
diff_count = (df['balance_diff'].abs() > 1).sum()
print(f"   ✅ 恒等式偏差：{diff_count} 条")

# ============================================================================
# 6. 处理缺失值
# ============================================================================
print("\n【5/8】处理缺失值...")

df_sorted = df.sort_values(['thscode', 'report_date'])
fill_cols = ['资产总计_亿', '净利润_亿', '营业收入_亿', '负债合计_亿', '所有者权益合计_亿']

# 记录并填充
missing_before = sum(df_sorted[col].isna().sum() for col in fill_cols)
for col in fill_cols:
    df_sorted[col] = df_sorted.groupby('thscode')[col].ffill()
    df_sorted[col] = df_sorted.groupby('thscode')[col].bfill()
missing_after = sum(df_sorted[col].isna().sum() for col in fill_cols)
print(f"   ✅ 缺失值：{missing_before} → {missing_after}")

# ============================================================================
# 7. 【新增】异常值处理
# ============================================================================
print("\n【6/8】异常值处理...")

outlier_log = []

# 7.1 处理ROA异常值（>100% 或 <-100%）
roa_outliers = df_sorted[(df_sorted['净利润_亿'] / df_sorted['资产总计_亿'] > 1) |
                         (df_sorted['净利润_亿'] / df_sorted['资产总计_亿'] < -1)]
if len(roa_outliers) > 0:
    print(f"   ⚠️ 发现 {len(roa_outliers)} 条ROA异常值")
    # 记录异常值
    for idx, row in roa_outliers.iterrows():
        outlier_log.append({
            'thscode': row['thscode'],
            'report_date': row['report_date'],
            'variable': 'ROA',
            'value': row['净利润_亿'] / row['资产总计_亿'],
            'action': 'winsorized'
        })
    # 缩尾处理：将ROA限制在[-1, 1]范围内
    roa = df_sorted['净利润_亿'] / df_sorted['资产总计_亿']
    df_sorted['ROA_raw'] = roa
    df_sorted['ROA'] = roa.clip(lower=-1, upper=1)
else:
    df_sorted['ROA'] = df_sorted['净利润_亿'] / df_sorted['资产总计_亿']

# 7.2 处理Leverage异常值（>1.5 或 <0）
leverage_outliers = df_sorted[(df_sorted['负债合计_亿'] / df_sorted['资产总计_亿'] > 1.5) |
                              (df_sorted['负债合计_亿'] / df_sorted['资产总计_亿'] < 0)]
if len(leverage_outliers) > 0:
    print(f"   ⚠️ 发现 {len(leverage_outliers)} 条Leverage异常值")
    for idx, row in leverage_outliers.iterrows():
        outlier_log.append({
            'thscode': row['thscode'],
            'report_date': row['report_date'],
            'variable': 'Leverage',
            'value': row['负债合计_亿'] / row['资产总计_亿'],
            'action': 'winsorized'
        })
    # 缩尾处理：将Leverage限制在[0, 1.5]范围内
    lev = df_sorted['负债合计_亿'] / df_sorted['资产总计_亿']
    df_sorted['Leverage_raw'] = lev
    df_sorted['Leverage'] = lev.clip(lower=0, upper=1.5)
else:
    df_sorted['Leverage'] = df_sorted['负债合计_亿'] / df_sorted['资产总计_亿']

# 7.3 处理Size异常值（<0 或 >30）
size_outliers = df_sorted[(np.log(df_sorted['资产总计_亿']) < 0) |
                          (np.log(df_sorted['资产总计_亿']) > 30)]
if len(size_outliers) > 0:
    print(f"   ⚠️ 发现 {len(size_outliers)} 条Size异常值")
    for idx, row in size_outliers.iterrows():
        outlier_log.append({
            'thscode': row['thscode'],
            'report_date': row['report_date'],
            'variable': 'Size',
            'value': np.log(row['资产总计_亿']),
            'action': 'winsorized'
        })
    # 缩尾处理：将Size限制在[1, 28]范围内
    size_val = np.log(df_sorted['资产总计_亿'])
    df_sorted['Size_raw'] = size_val
    df_sorted['Size'] = size_val.clip(lower=1, upper=28)
else:
    df_sorted['Size'] = np.log(df_sorted['资产总计_亿'])

# 保存异常值日志
if outlier_log:
    outlier_df = pd.DataFrame(outlier_log)
    outlier_df.to_csv(OUTLIER_LOG_PATH, index=False, encoding='utf-8-sig')
    print(f"   ✅ 异常值日志已保存：{OUTLIER_LOG_PATH}")

# ============================================================================
# 8. 生成其他衍生变量
# ============================================================================
print("\n【7/8】生成衍生控制变量...")

# 权益乘数
df_sorted['Equity_Multiplier'] = df_sorted['资产总计_亿'] / df_sorted['所有者权益合计_亿']

# 营业收入对数
df_sorted['Log_Revenue'] = np.log(df_sorted['营业收入_亿'].replace(0, np.nan))

# 对Log_Revenue进行缩尾处理
log_rev = df_sorted['Log_Revenue']
df_sorted['Log_Revenue'] = log_rev.clip(
    lower=log_rev.quantile(0.01),
    upper=log_rev.quantile(0.99)
)

print(f"   ✅ 衍生指标：Size, ROA, Leverage, Equity_Multiplier, Log_Revenue")

# ============================================================================
# 9. 保存面板
# ============================================================================
print("\n【8/8】保存清洗面板...")

output_cols = [
    'thscode', 'Layer', 'report_date', 'year', 'quarter', 'year_quarter',
    '资产总计_亿', '负债合计_亿', '所有者权益合计_亿', '营业收入_亿', '净利润_亿',
    'Size', 'ROA', 'Leverage', 'Equity_Multiplier', 'Log_Revenue'
]
df_clean = df_sorted[output_cols].copy()

df_clean.to_csv(CLEAN_PANEL_PATH, index=False, encoding='utf-8-sig')
print(f"   ✅ 主面板已保存：{CLEAN_PANEL_PATH}")

# 保存合并专用版
df_merge = df_clean[['thscode', 'year_quarter', 'Size', 'ROA', 'Leverage', 'Log_Revenue']].copy()
df_merge.to_csv(MERGE_PANEL_PATH, index=False, encoding='utf-8-sig')
print(f"   ✅ 合并面板已保存：{MERGE_PANEL_PATH}")

# ============================================================================
# 10. 生成质量报告
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
report_lines.append(f"\n【3. 异常值处理】")
report_lines.append(f"  处理异常值数量：{len(outlier_log)} 条")
report_lines.append(f"\n【4. 关键变量统计（缩尾后）】")
for col in ['Size', 'ROA', 'Leverage']:
    report_lines.append(f"  {col}：均值={df_clean[col].mean():.4f}, 标准差={df_clean[col].std():.4f}")
report_lines.append("\n" + "=" * 70)

with open(QUALITY_REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))
print(f"   ✅ 质量报告已保存：{QUALITY_REPORT_PATH}")

# ============================================================================
# 11. 汇总统计表
# ============================================================================
print("\n生成汇总统计表...")

summary_stats = df_clean[['Size', 'ROA', 'Leverage', 'Equity_Multiplier', 'Log_Revenue']].describe()
summary_stats.to_csv(SUMMARY_STATS_PATH, encoding='utf-8-sig')
print(f"   ✅ 汇总统计表已保存：{SUMMARY_STATS_PATH}")

# ============================================================================
# 12. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 财务数据清洗完成！")
print("=" * 70)
print(f"\n📁 输出文件：")
print(f"   • 主面板：{CLEAN_PANEL_PATH}")
print(f"   • 合并面板：{MERGE_PANEL_PATH}")
print(f"   • 质量报告：{QUALITY_REPORT_PATH}")
print(f"   • 汇总统计：{SUMMARY_STATS_PATH}")
if outlier_log:
    print(f"   • 异常值日志：{OUTLIER_LOG_PATH}")
print("=" * 70)
