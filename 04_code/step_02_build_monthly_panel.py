# -*- coding: utf-8 -*-
"""
================================================================================
步骤2：构建月度面板【最终修复：清洗行情表股票代码，剔除.SZ/.SH】
论文：AI产业链的非对称定价
================================================================================
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

# ====================== 固定项目根目录 ======================
BASE_DIR = r"D:\thailand study\26_7_23paper"

# 输入文件路径
STOCK_PATH = os.path.join(BASE_DIR, '01_raw_data', 'stock', 'zongdegupiao.csv')
INDEX_PATH = os.path.join(BASE_DIR, '01_raw_data', 'stock', 'dapanzhishu.csv')
FIN_MERGE_PATH = os.path.join(BASE_DIR, '03_clean_data', 'financial_panel_quarterly_for_merge.csv')
FIN_FULL_PATH = os.path.join(BASE_DIR, '03_clean_data', 'financial_panel_clean.csv')

# 输出路径
OUTPUT_DIR = os.path.join(BASE_DIR, '02_processed_data')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'monthly_panel_full.csv')
LOG_PATH = os.path.join(OUTPUT_DIR, 'monthly_panel_build_log.txt')

print("=" * 70)
print("步骤2：构建月度面板")
print("=" * 70)
print(f"项目根目录：{BASE_DIR}")

# ============================================================================
# 读取函数
# ============================================================================
def read_csv_with_encoding(path):
    for enc in ['utf-8-sig', 'gbk', 'gb2312', 'utf-8']:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"    ✅ 使用编码 {enc} 成功读取 {os.path.basename(path)}")
            return df
        except Exception:
            continue
    raise Exception(f"无法读取文件：{path}")

# ============================================================================
# 【1】读取全部数据
# ============================================================================
print("\n【1】读取数据...")
# 行情
df_stock = read_csv_with_encoding(STOCK_PATH)
df_index = read_csv_with_encoding(INDEX_PATH)
# 用于合并财务指标（Size/ROA）
df_fin_merge = pd.read_csv(FIN_MERGE_PATH, encoding='utf-8-sig')
# 专门读取完整财务表获取【Layer产业链层级】
df_fin_full = pd.read_csv(FIN_FULL_PATH, encoding='utf-8-sig')

print(f"    个股数据行数：{len(df_stock):,}")
print(f"    指数数据行数：{len(df_index):,}")
print(f"    季度财务精简表行数：{len(df_fin_merge):,}")

# ============================================================================
# 【2】列名标准化 + 【核心修复】行情代码去除.SZ .SH
# ============================================================================
print("\n【2】标准化列名 & 清洗股票代码...")
df_stock = df_stock.rename(columns={
    'time': 'Trddt',
    'thscode': 'Stkcd',
    'close': 'Clsprc',
    'changeRatio': 'Ret'
})
df_index = df_index.rename(columns={
    'time': 'Trddt',
    'close': 'Index_Close',
    'changeRatio': 'Index_Ret'
})

# ==========重点修复==========
# 行情表：去除 .SZ .SH，保留纯6位数字
df_stock['Stkcd'] = df_stock['Stkcd'].astype(str).str.replace(r'\.SZ|\.SH', '', regex=True).str.zfill(6)
stock_code_set = set(df_stock['Stkcd'].unique())

# 财务表同样处理
df_fin_merge['Stkcd_clean'] = df_fin_merge['thscode'].str.replace(r'\.SZ|\.SH', '', regex=True).str.zfill(6)
fin_code_set = set(df_fin_merge['Stkcd_clean'].unique())

# 调试打印
print("\n【DEBUG调试】代码样本对比：")
print(f"行情表前10个代码：{sorted(list(stock_code_set))[:10]}")
print(f"财务表前10个代码：{sorted(list(fin_code_set))[:10]}")
print(f"交集数量：{len(stock_code_set & fin_code_set)}")

# ============================================================================
# 【3】日期标准化
# ============================================================================
print("\n【3】标准化日期...")
df_stock['Trddt'] = pd.to_datetime(df_stock['Trddt'])
df_index['Trddt'] = pd.to_datetime(df_index['Trddt'])

# ============================================================================
# 【4】收益率转换：百分比 → 小数
# ============================================================================
print("\n【4】处理收益率格式...")
df_stock['Ret'] = df_stock['Ret'] / 100
df_index['Index_Ret'] = df_index['Index_Ret'] / 100

# ============================================================================
# 【5】筛选目标公司
# ============================================================================
print("\n【5】筛选目标公司...")
firm_codes_clean = list(fin_code_set)
print(f"    财务数据中包含公司数量：{len(firm_codes_clean)}")

df_stock_filtered = df_stock[df_stock['Stkcd'].isin(firm_codes_clean)].copy()
print(f"    筛选后个股数据行数：{len(df_stock_filtered):,}")
df_stock = df_stock_filtered

# ============================================================================
# 【6】个股合并指数，计算超额收益
# ============================================================================
print("\n【6】合并个股与指数数据...")
df_index_subset = df_index[['Trddt', 'Index_Ret']].drop_duplicates(subset=['Trddt'])
df_merged = df_stock.merge(df_index_subset, on='Trddt', how='left')
df_merged['Excess_Ret'] = df_merged['Ret'] - df_merged['Index_Ret']

# ============================================================================
# 【7】日度聚合为月度面板
# ============================================================================
print("\n【7】聚合到月度层面...")
monthly = pd.DataFrame()
if len(df_merged) > 0:
    df_merged['year'] = df_merged['Trddt'].dt.year
    df_merged['month'] = df_merged['Trddt'].dt.month
    df_merged['quarter'] = df_merged['Trddt'].dt.quarter
    df_merged['year_quarter'] = df_merged['year'].astype(str) + 'Q' + df_merged['quarter'].astype(str)

    monthly = df_merged.groupby(['Stkcd', 'year', 'month', 'quarter', 'year_quarter']).agg({
        'Clsprc': 'last',
        'Ret': lambda x: (1 + x).prod() - 1,
        'Excess_Ret': lambda x: (1 + x).prod() - 1,
        'Trddt': 'count'
    }).rename(columns={'Trddt': 'trading_days'})
    monthly = monthly.reset_index()
print(f"    月度面板原始行数：{len(monthly):,}")

# ============================================================================
# 【8】合并季度财务控制变量
# ============================================================================
print("\n【8】合并季度财务控制变量...")
if len(monthly) > 0:
    merge_fin_cols = ['Stkcd_clean', 'year_quarter', 'Size', 'ROA', 'Leverage', 'Log_Revenue']
    monthly = monthly.merge(
        df_fin_merge[merge_fin_cols],
        left_on=['Stkcd', 'year_quarter'],
        right_on=['Stkcd_clean', 'year_quarter'],
        how='left'
    )
    monthly.drop(columns=['Stkcd_clean'], inplace=True)
    print(f"    Size 合并后缺失数量：{monthly['Size'].isna().sum():,}")

# ============================================================================
# 【9】财务指标按个股前后填充
# ============================================================================
print("\n【9】前向+后向填充财务指标...")
if len(monthly) > 0:
    monthly = monthly.sort_values(['Stkcd', 'year', 'month'])
    fin_cols = ['Size', 'ROA', 'Leverage', 'Log_Revenue']
    for col in fin_cols:
        monthly[col] = monthly.groupby('Stkcd')[col].ffill()
        monthly[col] = monthly.groupby('Stkcd')[col].bfill()
    print(f"    Size 填充后缺失数量：{monthly['Size'].isna().sum():,}")

# ============================================================================
# 【10】生成DID事件变量
# ============================================================================
print("\n【10】生成事件变量...")
if len(monthly) > 0:
    monthly['date'] = pd.to_datetime(monthly['year'].astype(str) + '-' + monthly['month'].astype(str) + '-01')
    EVENT_DATE = '2025-01-01'
    monthly['Post'] = (monthly['date'] >= EVENT_DATE).astype(int)
    monthly['Treat'] = 1
    monthly['event_time'] = (monthly['year'] - 2025) * 12 + (monthly['month'] - 1)
    monthly['event_period'] = monthly['event_time'].apply(lambda x: 'pre' if x < 0 else ('event' if x == 0 else 'post'))

# ============================================================================
# 【11】匹配产业链Layer分层信息
# ============================================================================
# ============================================================================
# 【11】匹配产业链Layer分层信息
# ============================================================================
print("\n【11】匹配产业链Layer分层信息...")
if len(monthly) > 0:
    # 【修复】确保 df_fin_full 有 Stkcd_clean 列
    if 'Stkcd_clean' not in df_fin_full.columns:
        df_fin_full['Stkcd_clean'] = df_fin_full['thscode'].str.replace(r'\.SZ|\.SH', '', regex=True).str.zfill(6)
    layer_map = df_fin_full[['Stkcd_clean', 'Layer']].drop_duplicates(subset=['Stkcd_clean'])
    layer_map.rename(columns={'Stkcd_clean': 'Stkcd'}, inplace=True)
    monthly = monthly.merge(layer_map, on='Stkcd', how='left')
    print(f"    Layer缺失数量：{monthly['Layer'].isna().sum():,}")

# ============================================================================
# 【12】整理输出列并保存面板
# ============================================================================
print("\n【12】保存完整月度面板...")
final_cols = [
    'Stkcd', 'Layer', 'year', 'month', 'quarter', 'year_quarter', 'date',
    'Clsprc', 'Ret', 'Excess_Ret', 'trading_days',
    'Size', 'ROA', 'Leverage', 'Log_Revenue',
    'Treat', 'Post', 'event_time', 'event_period'
]
if len(monthly) > 0:
    monthly_final = monthly[final_cols].copy()
else:
    monthly_final = pd.DataFrame(columns=final_cols)

monthly_final.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
print(f"    ✅ 月度面板已保存：{OUTPUT_PATH}")
print(f"    最终观测行数：{len(monthly_final):,}")
print(f"    覆盖企业数量：{monthly_final['Stkcd'].nunique()}")

# ============================================================================
# 【13】生成构建日志
# ============================================================================
print("\n【13】生成构建日志...")
log_lines = []
log_lines.append("=" * 70)
log_lines.append("月度面板构建日志")
log_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_lines.append("=" * 70)
log_lines.append(f"  公司数：{monthly_final['Stkcd'].nunique()}")
log_lines.append(f"  总观测值：{len(monthly_final):,}")
log_lines.append("=" * 70)
with open(LOG_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines))
print(f"    ✅ 构建日志已保存：{LOG_PATH}")

print("\n" + "=" * 70)
print("🎉 月度面板构建完成！")
print("=" * 70)