# -*- coding:utf-8 -*-
# 脚本名称：step_03_build_did_variables.py
# 功能：构建DID核心变量、计算CAR、绘制双样式平行趋势图 (优化版)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 文件路径设置
# ============================================================
base_dir = r"D:\thailand study\26_7_23paper"
input_file = os.path.join(base_dir, "02_processed_data/02_monthly_panel.csv")
output_file = os.path.join(base_dir, "02_processed_data/03_did_panel.csv")

# 图片输出目录
fig_cn_dir = os.path.join(base_dir, "05_output/figures/CN")
fig_en_dir = os.path.join(base_dir, "05_output/figures/EN")
for dir_path in [fig_cn_dir, fig_en_dir]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

print("=" * 60)
print("步骤 3：构建DID核心变量与事件研究数据 (优化版)")
print("=" * 60)

# ============================================================
# 2. 读取月度面板
# ============================================================
print(f"\n[1/7] 正在读取月度面板: {input_file}")
df = pd.read_csv(input_file)

# 【核心修复】智能处理 year_month 格式
print(f"   - 原始 year_month 数据类型: {df['year_month'].dtype}")

if df['year_month'].dtype == 'int64':
    # 如果是整数（如 202501），转换为字符串 '2025-01'
    df['year_month_str'] = df['year_month'].astype(str).str.slice(0, 4) + '-' + df['year_month'].astype(str).str.slice(
        4, 6)
else:
    # 如果已经是字符串，直接使用
    df['year_month_str'] = df['year_month']

# 转换为 datetime 对象
df['year_month_dt'] = pd.to_datetime(df['year_month_str'] + '-01')
print(f"   - 转换后日期示例: {df['year_month_dt'].iloc[0]}")

print(f" ✓ 读取成功！行数: {len(df):,}, 股票数: {df['thscode'].nunique()}")

# ============================================================
# 3. 创建"沪深300对照组"虚拟企业
# ============================================================
print("\n[2/7] 正在创建沪深300对照组虚拟记录...")

# 3.1 获取所有月份的唯一列表
all_months = df[['year', 'month', 'year_month', 'year_month_dt']].drop_duplicates().sort_values('year_month_dt')

# 3.2 构建沪深300的月度记录
# 关键点：确保所有列都存在，并且数据类型与主表一致
hs300_records = []
for _, row in all_months.iterrows():
    hs300_records.append({
        'thscode': 'HS300',
        'year': row['year'],
        'month': row['month'],
        'year_month': row['year_month'],
        'year_month_dt': row['year_month_dt'],
        'Ret_monthly': 0.0,  # 明确指定为浮点数
        'Excess_Ret_monthly': 0.0,
        'Clsprc_end': np.nan,
        'Volatility': np.nan,
        'Trading_Days': np.nan,
        'HS300_Ret_monthly': 0.0,
        'Layer': 'HS300'
    })
df_hs300 = pd.DataFrame(hs300_records)

# 3.3 为原有的企业添加 Treat=1 和 Layer 信息
df['Treat'] = 1
if 'Layer' not in df.columns:
    df['Layer'] = 'AI企业'

# 为HS300添加 Treat=0
df_hs300['Treat'] = 0

# 3.4 合并处理组与对照组
# 使用 concat 而不是 append (append已弃用)
df_panel = pd.concat([df, df_hs300], ignore_index=True)
df_panel = df_panel.sort_values(['thscode', 'year', 'month']).reset_index(drop=True)

print(f" ✓ 合并完成！总行数: {len(df_panel):,}")
print(f" ✓ 处理组（Treat=1）: {df_panel[df_panel['Treat'] == 1].shape[0]:,} 行")
print(f" ✓ 对照组（Treat=0）: {df_panel[df_panel['Treat'] == 0].shape[0]:,} 行")

# ============================================================
# 4. 构建Post虚拟变量与DID交互项
# ============================================================
print("\n[3/7] 正在构建 Post 与 DID 变量...")
# DeepSeek事件时间：2025年1月
event_date = pd.Timestamp('2025-01-01')
df_panel['Post'] = (df_panel['year_month_dt'] >= event_date).astype(int)
df_panel['DID'] = df_panel['Treat'] * df_panel['Post']

print(f" ✓ Post=1 的观测数: {df_panel[df_panel['Post'] == 1].shape[0]:,}")
print(f" ✓ DID=1 的观测数: {df_panel[df_panel['DID'] == 1].shape[0]:,}")

# ============================================================
# 5. 计算事件相对时间（event_time）
# ============================================================
print("\n[4/7] 正在计算事件相对时间...")
# 2025年1月 = 0
df_panel['event_time'] = (df_panel['year'] - 2025) * 12 + (df_panel['month'] - 1)
print(f" ✓ event_time 范围: {df_panel['event_time'].min()} 至 {df_panel['event_time'].max()}")

# ============================================================
# 6. 计算事件窗口CAR（累计超额收益）
# ============================================================
print("\n[5/7] 正在计算事件窗口CAR...")


def calculate_car_for_firm(firm_data, windows):
    """ 计算单只股票在事件窗口的CAR """
    event_idx = firm_data[firm_data['event_time'] == 0].index
    if len(event_idx) == 0:
        return {f'CAR_{w[0]}_{w[1]}': np.nan for w in windows}

    event_pos = firm_data.index.get_loc(event_idx[0])
    total_rows = len(firm_data)
    results = {}

    for w in windows:
        start = max(0, event_pos + w[0])
        end = min(total_rows - 1, event_pos + w[1])
        if start <= end:
            window_data = firm_data.iloc[start:end + 1]
            results[f'CAR_{w[0]}_{w[1]}'] = window_data['Excess_Ret_monthly'].sum()
        else:
            results[f'CAR_{w[0]}_{w[1]}'] = np.nan
    return results


windows = [[-1, 1], [-2, 2], [-3, 3], [-1, 0], [0, 1]]
# 只对处理组（AI企业）计算CAR
firms_only = df_panel[df_panel['Treat'] == 1]

car_results = []
for stkcd in firms_only['thscode'].unique():
    firm_data = firms_only[firms_only['thscode'] == stkcd].sort_values('year_month_dt')
    if len(firm_data) == 0: continue
    car_dict = calculate_car_for_firm(firm_data, windows)
    car_dict['thscode'] = stkcd
    car_results.append(car_dict)

car_df = pd.DataFrame(car_results)

# 将CAR结果合并回主面板
# 使用 merge 而不是循环赋值，效率更高且更安全
df_panel = df_panel.merge(car_df, on='thscode', how='left')

print(f" ✓ CAR计算完成！")
# 检查CAR均值时，只关注处理组的事件月
mean_car = df_panel[(df_panel['Treat'] == 1) & (df_panel['event_time'] == 0)]['CAR_-1_1'].mean()
print(f" ✓ CAR[-1,1] 均值 (事件月, 处理组): {mean_car:.4f}")

# ============================================================
# 7. 保存DID面板
# ============================================================
print("\n[6/7] 正在保存DID面板...")
df_panel.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f" ✓ DID面板已保存: {output_file}")

# ============================================================
# 8. 双样式平行趋势图绘制
# ============================================================
print("\n[7/7] 正在绘制双样式平行趋势图...")

# 准备绘图数据：计算每个 event_time 的平均超额收益和置信区间
plot_data = df_panel[df_panel['Treat'] == 1].groupby('event_time')['Excess_Ret_monthly'].agg(
    ['mean', 'count', 'std']).reset_index()
plot_data['se'] = plot_data['std'] / np.sqrt(plot_data['count'])
plot_data['ci_95'] = 1.96 * plot_data['se']

# --- 中文图 ---
plt.figure(figsize=(12, 6))
sns.lineplot(data=plot_data, x='event_time', y='mean', marker='o', color='#1f77b4')
plt.fill_between(plot_data['event_time'], plot_data['mean'] - plot_data['ci_95'],
                 plot_data['mean'] + plot_data['ci_95'], alpha=0.2, color='#1f77b4')
plt.axvline(x=0, color='red', linestyle='--', label='事件发生 (2025-01)')
plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
plt.title('平行趋势检验：AI企业平均超额收益', fontsize=16)
plt.xlabel('相对事件时间 (月)', fontsize=12)
plt.ylabel('平均超额收益', fontsize=12)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(fig_cn_dir, 'figure1_parallel_trend_CN.pdf'))
plt.close()

# --- 英文图 ---
plt.figure(figsize=(12, 6))
sns.lineplot(data=plot_data, x='event_time', y='mean', marker='o', color='#1f77b4')
plt.fill_between(plot_data['event_time'], plot_data['mean'] - plot_data['ci_95'],
                 plot_data['mean'] + plot_data['ci_95'], alpha=0.2, color='#1f77b4')
plt.axvline(x=0, color='red', linestyle='--', label='Event Date (Jan 2025)')
plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
plt.title('Parallel Trend Test: Avg. Excess Return of AI Firms', fontsize=16)
plt.xlabel('Relative Event Time (Month)', fontsize=12)
plt.ylabel('Average Excess Return', fontsize=12)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(fig_en_dir, 'figure1_parallel_trend_EN.pdf'))
plt.close()

print(f" ✓ 图片已保存: {os.path.join(fig_cn_dir, 'figure1_parallel_trend_CN.pdf')}")
print(f" ✓ 图片已保存: {os.path.join(fig_en_dir, 'figure1_parallel_trend_EN.pdf')}")

print("\n" + "=" * 60)
print("✅ 步骤 3 执行完成！")
print("=" * 60)
print(f" • DID面板: {output_file}")
print(f" • 中文图片: {os.path.join(fig_cn_dir, 'figure1_parallel_trend_CN.pdf')}")
print(f" • 英文图片: {os.path.join(fig_en_dir, 'figure1_parallel_trend_EN.pdf')}")
print("=" * 60)