# -*- coding: utf-8 -*-
"""
================================================================================
步骤2：构建月度面板（完整版 - 含缩尾处理）
论文：AI产业链的非对称定价
项目根目录：D:/thailand study/26_7_23paper/

输入文件：
  - 01_raw_data/stock/zongdegupiao.csv     （日度个股行情）
  - 01_raw_data/stock/dapanzhishu.csv      （日度大盘指数）
  - 03_clean_data/financial_panel_quarterly_for_merge.csv  （季度财务数据）

输出文件：
  - 02_processed_data/monthly_panel_full.csv  （完整月度面板）
  - 02_processed_data/monthly_panel_build_log.txt  （构建日志）
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

# 输入文件路径
STOCK_PATH = os.path.join(BASE_DIR, '01_raw_data', 'stock', 'zongdegupiao.csv')
INDEX_PATH = os.path.join(BASE_DIR, '01_raw_data', 'stock', 'dapanzhishu.csv')
FIN_PATH = os.path.join(BASE_DIR, '03_clean_data', 'financial_panel_quarterly_for_merge.csv')

# 输出目录和文件
OUTPUT_DIR = os.path.join(BASE_DIR, '02_processed_data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'monthly_panel_full.csv')
LOG_PATH = os.path.join(OUTPUT_DIR, 'monthly_panel_build_log.txt')

print("=" * 70)
print("步骤2：构建月度面板（完整版 - 含缩尾处理）")
print("=" * 70)
print(f"项目根目录：{BASE_DIR}")
print(f"个股数据：{STOCK_PATH}")
print(f"指数数据：{INDEX_PATH}")
print(f"财务数据：{FIN_PATH}")

# ============================================================================
# 2. 读取原始数据
# ============================================================================
print("\n【1】读取原始数据...")


def read_csv_with_encoding(path):
    """自动检测文件编码并读取"""
    for enc in ['utf-8-sig', 'gbk', 'gb2312', 'utf-8']:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"    ✅ 使用编码 {enc} 成功读取 {os.path.basename(path)}")
            return df
        except:
            continue
    raise Exception(f"无法读取文件：{path}")


# 检查文件是否存在
for path in [STOCK_PATH, INDEX_PATH, FIN_PATH]:
    if not os.path.exists(path):
        print(f"    ❌ 文件不存在：{path}")
        exit()

df_stock = read_csv_with_encoding(STOCK_PATH)
df_index = read_csv_with_encoding(INDEX_PATH)
df_fin = pd.read_csv(FIN_PATH, encoding='utf-8-sig')

print(f"    个股数据行数：{len(df_stock):,}")
print(f"    指数数据行数：{len(df_index):,}")
print(f"    财务数据行数：{len(df_fin):,}")

# ============================================================================
# 3. 列名标准化
# ============================================================================
print("\n【2】标准化列名...")

print(f"    个股原始列名：{df_stock.columns.tolist()}")
print(f"    指数原始列名：{df_index.columns.tolist()}")

# 个股列名映射
df_stock = df_stock.rename(columns={
    'time': 'Trddt',
    'thscode': 'Stkcd_raw',
    'close': 'Clsprc',
    'changeRatio': 'Ret'
})

# 指数列名映射
df_index = df_index.rename(columns={
    'time': 'Trddt',
    'close': 'Index_Close',
    'changeRatio': 'Index_Ret'
})


# 【关键修复】统一股票代码格式（移除后缀）
def clean_stock_code(code):
    """移除股票代码的 .SZ/.SH 后缀"""
    if isinstance(code, str):
        return code.replace('.SZ', '').replace('.SH', '').zfill(6)
    return str(code).zfill(6)


df_stock['Stkcd'] = df_stock['Stkcd_raw'].apply(clean_stock_code)
df_stock = df_stock.drop(columns=['Stkcd_raw'])

print(f"    个股列名：{df_stock.columns.tolist()}")
print(f"    个股代码示例：{df_stock['Stkcd'].head(3).tolist()}")

# ============================================================================
# 4. 统一日期格式
# ============================================================================
print("\n【3】统一日期格式...")

df_stock['Trddt'] = pd.to_datetime(df_stock['Trddt'])
df_index['Trddt'] = pd.to_datetime(df_index['Trddt'])

print(f"    个股日期范围：{df_stock['Trddt'].min().date()} 至 {df_stock['Trddt'].max().date()}")
print(f"    指数日期范围：{df_index['Trddt'].min().date()} 至 {df_index['Trddt'].max().date()}")

# ============================================================================
# 5. 处理收益率格式
# ============================================================================
print("\n【4】处理收益率格式...")

df_stock['Ret'] = df_stock['Ret'] / 100
df_index['Index_Ret'] = df_index['Index_Ret'] / 100

print(f"    个股收益率示例：{df_stock['Ret'].head(3).tolist()}")
print(f"    指数收益率示例：{df_index['Index_Ret'].head(3).tolist()}")

# ============================================================================
# 6. 筛选目标公司
# ============================================================================
print("\n【5】筛选目标公司...")

# 【关键修复】财务代码也移除后缀
df_fin['thscode_clean'] = df_fin['thscode'].apply(clean_stock_code)
firm_codes = df_fin['thscode_clean'].unique().tolist()
print(f"    财务数据中包含的公司数：{len(firm_codes)}")
print(f"    公司代码示例：{firm_codes[:5]}")

# 筛选个股数据
df_stock = df_stock[df_stock['Stkcd'].isin(firm_codes)]
print(f"    筛选后个股数据行数：{len(df_stock):,}")

# 检查哪些公司没有日度数据
missing_firms = set(firm_codes) - set(df_stock['Stkcd'].unique())
if missing_firms:
    print(f"    ⚠️ 以下公司无日度数据：{list(missing_firms)[:10]}")
else:
    print(f"    ✅ 所有公司均有日度数据")

# ============================================================================
# 7. 合并个股与指数数据
# ============================================================================
print("\n【6】合并个股与指数数据...")

df_index_subset = df_index[['Trddt', 'Index_Ret']].drop_duplicates(subset=['Trddt'])
df_merged = df_stock.merge(df_index_subset, on='Trddt', how='left')
df_merged['Excess_Ret'] = df_merged['Ret'] - df_merged['Index_Ret']

print(f"    合并后数据行数：{len(df_merged):,}")
print(f"    超额收益统计：均值={df_merged['Excess_Ret'].mean():.6f}, 标准差={df_merged['Excess_Ret'].std():.6f}")

# ============================================================================
# 8. 聚合到月度层面
# ============================================================================
print("\n【7】聚合到月度层面...")

df_merged['year'] = df_merged['Trddt'].dt.year
df_merged['month'] = df_merged['Trddt'].dt.month
df_merged['quarter'] = df_merged['Trddt'].dt.quarter
df_merged['year_quarter'] = df_merged['year'].astype(str) + 'Q' + df_merged['quarter'].astype(str)

monthly = df_merged.groupby(['Stkcd', 'year', 'month', 'quarter', 'year_quarter']).agg({
    'Clsprc': 'last',  # 月末收盘价
    'Ret': lambda x: (1 + x).prod() - 1,  # 月累计收益率（复利）
    'Excess_Ret': lambda x: (1 + x).prod() - 1,  # 月累计超额收益
    'Trddt': 'count'  # 月内交易日数
}).rename(columns={'Trddt': 'trading_days'})

monthly = monthly.reset_index()

print(f"    月度面板行数：{len(monthly):,}")
print(f"    覆盖公司数：{monthly['Stkcd'].nunique()}")
print(
    f"    时间范围：{monthly['year'].min()}-{monthly['month'].min():02d} 至 {monthly['year'].max()}-{monthly['month'].max():02d}")

# ============================================================================
# 9. 合并季度财务数据
# ============================================================================
print("\n【8】合并季度财务数据...")

# 财务数据中的 year_quarter 格式为 "2025Q1"
monthly = monthly.merge(
    df_fin[['thscode_clean', 'year_quarter', 'Size', 'ROA', 'Leverage', 'Log_Revenue']],
    left_on=['Stkcd', 'year_quarter'],
    right_on=['thscode_clean', 'year_quarter'],
    how='left'
)

monthly = monthly.drop(columns=['thscode_clean'], errors='ignore')

print(f"    合并后行数：{len(monthly):,}")
print(f"    Size 缺失数：{monthly['Size'].isna().sum():,}")

# ============================================================================
# 10. 前向填充财务数据
# ============================================================================
print("\n【9】前向填充财务数据...")

monthly = monthly.sort_values(['Stkcd', 'year', 'month'])
fin_cols = ['Size', 'ROA', 'Leverage', 'Log_Revenue']

for col in fin_cols:
    # 前向填充
    monthly[col] = monthly.groupby('Stkcd')[col].ffill()
    # 后向填充（处理公司早期缺失）
    monthly[col] = monthly.groupby('Stkcd')[col].bfill()

print(f"    填充后 Size 缺失数：{monthly['Size'].isna().sum():,}")

# ============================================================================
# 11. 【新增】缩尾处理（Winsorize）- 处理极端值
# ============================================================================
print("\n【10】缩尾处理（Winsorize）...")


def winsorize_series(series, lower=0.01, upper=0.99):
    """
    对序列进行缩尾处理（Winsorize）
    将低于1%分位数的值替换为1%分位数，高于99%分位数的值替换为99%分位数
    """
    lower_bound = series.quantile(lower)
    upper_bound = series.quantile(upper)
    return series.clip(lower=lower_bound, upper=upper_bound)


# 对关键变量进行缩尾处理
winsorize_cols = ['Excess_Ret', 'Ret', 'ROA', 'Leverage']
print(f"    将对以下变量进行缩尾处理：{winsorize_cols}")

for col in winsorize_cols:
    if col in monthly.columns:
        original_mean = monthly[col].mean()
        original_std = monthly[col].std()
        original_max = monthly[col].max()

        # 执行缩尾
        monthly[col] = winsorize_series(monthly[col])

        new_mean = monthly[col].mean()
        new_std = monthly[col].std()
        new_max = monthly[col].max()

        print(f"    {col}:")
        print(f"      均值: {original_mean:.6f} → {new_mean:.6f}")
        print(f"      标准差: {original_std:.6f} → {new_std:.6f}")
        print(f"      最大值: {original_max:.6f} → {new_max:.6f}")

print(f"    ✅ 缩尾处理完成")

# ============================================================================
# 12. 生成DID变量
# ============================================================================
print("\n【11】生成事件时间变量...")

# 创建日期列（每月1日）
monthly['date'] = pd.to_datetime(monthly['year'].astype(str) + '-' + monthly['month'].astype(str) + '-01')

# DeepSeek事件：2025年1月
EVENT_DATE = '2025-01-01'
monthly['Post'] = (monthly['date'] >= EVENT_DATE).astype(int)

# 所有公司均为处理组
monthly['Treat'] = 1

# 相对事件时间（2025年1月 = 0）
monthly['event_time'] = (monthly['year'] - 2025) * 12 + (monthly['month'] - 1)

print(f"    事件前样本量（<2025-01）：{len(monthly[monthly['Post'] == 0]):,}")
print(f"    事件后样本量（>=2025-01）：{len(monthly[monthly['Post'] == 1]):,}")
print(f"    事件时间范围：{monthly['event_time'].min()} 至 {monthly['event_time'].max()}")

# ============================================================================
# 13. 保存月度面板
# ============================================================================
print("\n【12】保存月度面板...")

# 最终列排序
final_cols = [
    'Stkcd', 'year', 'month', 'quarter', 'year_quarter', 'date',
    'Clsprc', 'Ret', 'Excess_Ret', 'trading_days',
    'Size', 'ROA', 'Leverage', 'Log_Revenue',
    'Treat', 'Post', 'event_time'
]

monthly_final = monthly[final_cols].copy()
monthly_final.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')

print(f"    ✅ 已保存：{OUTPUT_PATH}")
print(f"    最终行数：{len(monthly_final):,}")
print(f"    最终列数：{len(monthly_final.columns)}")

# ============================================================================
# 14. 生成构建日志
# ============================================================================
print("\n【13】生成构建日志...")

log_lines = []
log_lines.append("=" * 70)
log_lines.append("月度面板构建日志")
log_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_lines.append("=" * 70)
log_lines.append("")
log_lines.append("【数据来源】")
log_lines.append(f"  个股数据：zongdegupiao.csv ({len(df_stock):,} 行)")
log_lines.append(f"  指数数据：dapanzhishu.csv ({len(df_index):,} 行)")
log_lines.append(f"  财务数据：financial_panel_quarterly_for_merge.csv ({len(df_fin):,} 行)")
log_lines.append("")
log_lines.append("【数据覆盖】")
log_lines.append(f"  公司数：{monthly_final['Stkcd'].nunique()}")
log_lines.append(
    f"  时间范围：{monthly_final['year'].min()}-{monthly_final['month'].min():02d} 至 {monthly_final['year'].max()}-{monthly_final['month'].max():02d}")
log_lines.append(f"  总观测值：{len(monthly_final):,}")
log_lines.append("")
log_lines.append("【缩尾处理】")
log_lines.append(f"  缩尾阈值：1% / 99%")
log_lines.append(f"  处理变量：Excess_Ret, Ret, ROA, Leverage")
log_lines.append("")
log_lines.append("【事件设定】")
log_lines.append(f"  事件日期：{EVENT_DATE}")
log_lines.append(f"  事件前观测值：{len(monthly_final[monthly_final['Post'] == 0]):,}")
log_lines.append(f"  事件后观测值：{len(monthly_final[monthly_final['Post'] == 1]):,}")
log_lines.append("")
log_lines.append("【财务变量完整性】")
for col in ['Size', 'ROA', 'Leverage', 'Log_Revenue']:
    miss = monthly_final[col].isna().sum()
    log_lines.append(f"  {col}：{miss} 条缺失")
log_lines.append("")
log_lines.append("【收益率统计（缩尾后）】")
log_lines.append(f"  月超额收益均值：{monthly_final['Excess_Ret'].mean():.6f}")
log_lines.append(f"  月超额收益标准差：{monthly_final['Excess_Ret'].std():.6f}")
log_lines.append(f"  月超额收益最小值：{monthly_final['Excess_Ret'].min():.6f}")
log_lines.append(f"  月超额收益最大值：{monthly_final['Excess_Ret'].max():.6f}")
log_lines.append("")
log_lines.append("【关键变量统计（缩尾后）】")
for col in ['Size', 'ROA', 'Leverage']:
    log_lines.append(f"  {col}：均值={monthly_final[col].mean():.4f}, 标准差={monthly_final[col].std():.4f}")
log_lines.append("=" * 70)

with open(LOG_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines))

print(f"    ✅ 日志已保存：{LOG_PATH}")

# ============================================================================
# 15. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 月度面板构建完成！")
print("=" * 70)
print(f"\n📁 输出文件：")
print(f"  1. {OUTPUT_PATH}")
print(f"  2. {LOG_PATH}")
print(f"\n📊 数据摘要：")
print(f"   • 公司数：{monthly_final['Stkcd'].nunique()}")
print(f"   • 观测值：{len(monthly_final):,}")
print(
    f"   • 时间范围：{monthly_final['year'].min()}-{monthly_final['month'].min():02d} 至 {monthly_final['year'].max()}-{monthly_final['month'].max():02d}")
print(f"   • 事件后观测值：{len(monthly_final[monthly_final['Post'] == 1]):,}")
print(f"   • 月超额收益均值（缩尾后）：{monthly_final['Excess_Ret'].mean():.6f}")
print("\n下一步：运行 step_04_did_regression.py 进行DID回归分析")
print("=" * 70)