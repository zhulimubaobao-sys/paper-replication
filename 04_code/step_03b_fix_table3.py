# -*- coding: utf-8 -*-
"""
================================================================================
补救脚本：单独生成 table3_mechanism.csv
机制检验：上游业绩渠道 vs 下游情绪渠道
【稳定版本】linearmodels 原生双向固定效应 + 股票聚类标准误
彻底规避手动构造虚拟变量、组内去均值带来的各类pandas报错
================================================================================
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

from linearmodels.panel import PanelOLS

# ============================================================================
# 1. 路径配置
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

INPUT_PATH = os.path.join(BASE_DIR, '02_processed_data', 'monthly_panel_full.csv')
FIN_PATH = os.path.join(BASE_DIR, '03_clean_data', 'financial_panel_clean.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output', 'tables')
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("补救：生成 Table 3 机制检验")
print("=" * 70)
print(f"输入文件：{INPUT_PATH}")
print(f"输出目录：{OUTPUT_DIR}")

# ============================================================================
# 2. 读取数据
# ============================================================================
print("\n【1】读取数据...")

if not os.path.exists(INPUT_PATH):
    print(f"   ❌ 文件不存在：{INPUT_PATH}")
    exit()

df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')
df['date'] = pd.to_datetime(df['date'])
df['Stkcd'] = df['Stkcd'].astype(str).str.zfill(6)

print(f"   月度面板行数：{len(df):,}")

# ============================================================================
# 3. 补充Layer信息
# ============================================================================
print("\n【2】补充Layer信息...")

def clean_code(code):
    if isinstance(code, str):
        return code.replace('.SZ', '').replace('.SH', '').zfill(6)
    return str(code).zfill(6)

if os.path.exists(FIN_PATH):
    fin_raw = pd.read_csv(FIN_PATH, encoding='utf-8-sig')
    layer_map = fin_raw[['thscode', 'Layer']].drop_duplicates(subset=['thscode'])
    layer_map['Stkcd_clean'] = layer_map['thscode'].apply(clean_code)

    df['Stkcd_clean'] = df['Stkcd'].apply(clean_code)
    df = df.merge(layer_map[['Stkcd_clean', 'Layer']], on='Stkcd_clean', how='left')
    df['Layer'] = df['Layer'].fillna('全样本')
    df = df.drop(columns=['Stkcd_clean'])

print(f"各层级分布：\n{df['Layer'].value_counts()}")

# ============================================================================
# 4. 数据预处理
# ============================================================================
print("\n【3】数据预处理...")

def winsorize_series(s, lower=0.01, upper=0.99):
    low = s.quantile(lower)
    high = s.quantile(upper)
    return s.clip(low, high)

for col in ['Size', 'ROA', 'Leverage']:
    if col in df.columns:
        df[col] = winsorize_series(df[col])

if 'year_month' not in df.columns:
    df['year_month'] = df['date'].dt.strftime('%Y%m').astype(int)

df_clean = df.dropna(subset=['Excess_Ret', 'Size', 'ROA', 'Leverage', 'Post', 'Layer'])
print(f"删除缺失值后行数：{len(df_clean):,}")

# ============================================================================
# 5. 回归函数【linearmodels原生实现，工业稳定方案】
# ============================================================================
def panel_fe_regression(df_sub, y_var, x_vars=['Post']):
    df_reg = df_sub.copy()
    # 设置面板索引：个体 + 时间
    df_reg = df_reg.set_index(['Stkcd', 'year_month'])
    all_vars = [y_var] + x_vars
    df_reg = df_reg[all_vars].dropna()
    n_obs = len(df_reg)
    if n_obs < 50:
        return None, 0

    y = df_reg[y_var]
    X = df_reg[x_vars]
    # 双向固定效应 + 股票聚类稳健标准误
    mod = PanelOLS(y, X, entity_effects=True, time_effects=True)
    res = mod.fit(cov_type='clustered', cluster_entity=True)
    return res, n_obs

# ============================================================================
# 6. 构建机制变量
# ============================================================================
print("\n【4】构建机制变量...")

# 情绪代理：使用交易天数
if 'trading_days' in df_clean.columns:
    df_clean['Sentiment_Proxy'] = df_clean['trading_days']
    print("    使用 trading_days（交易天数）作为情绪代理")
else:
    df_clean['Sentiment_Proxy'] = df_clean.groupby('Stkcd')['Excess_Ret'].rolling(3, min_periods=1).std().reset_index(0, drop=True)
    print("    使用滚动3个月超额收益标准差作为情绪代理")

# 标准化
df_clean['Sentiment_Proxy_std'] = (df_clean['Sentiment_Proxy'] - df_clean['Sentiment_Proxy'].mean()) / df_clean['Sentiment_Proxy'].std()

print(f"    ROA 均值：{df_clean['ROA'].mean():.4f}")
print(f"    情绪代理均值：{df_clean['Sentiment_Proxy_std'].mean():.4f}")

# ============================================================================
# 7. 机制检验回归
# ============================================================================
print("\n【5】执行机制检验...")

def run_mech_regression(df_sub, dep_var, var_name):
    """运行机制检验回归"""
    x_vars = ['Post', 'Size', 'ROA', 'Leverage']
    results, n_obs = panel_fe_regression(df_sub, dep_var, x_vars)

    if results is None:
        print(f"    ⚠️ {var_name} 回归失败（样本量不足）")
        return None, 0

    if 'Post' not in results.params.index:
        print(f"    ⚠️ {var_name} 未找到Post系数")
        return None, 0

    coef = results.params['Post']
    se = results.std_errors['Post']
    t = results.tstats['Post']
    p = results.pvalues['Post']
    print(f"    {var_name}: Post系数={coef:.4f}, p={p:.4f}, N={n_obs}")

    return {
        'Coefficient': coef,
        'Std_Error': se,
        't_stat': t,
        'p_value': p,
        'N_obs': n_obs,
        'R_squared': results.rsquared
    }, n_obs

results_dict = {}

# 准备子样本
df_up = df_clean[df_clean['Layer'] == '上游'].copy()
df_down = df_clean[df_clean['Layer'] == '下游'].copy()

print(f"   上游样本量：{len(df_up):,}")
print(f"   下游样本量：{len(df_down):,}")

# 检验1：上游 → ROA（业绩渠道）
if len(df_up) > 50:
    res, n = run_mech_regression(df_up, 'ROA', '上游→ROA')
    if res:
        results_dict['上游→ROA'] = res

# 检验2：下游 → 情绪代理（情绪渠道）
if len(df_down) > 50:
    res, n = run_mech_regression(df_down, 'Sentiment_Proxy_std', '下游→情绪')
    if res:
        results_dict['下游→情绪'] = res

# 检验3：下游 → ROA（对照）
if len(df_down) > 50:
    res, n = run_mech_regression(df_down, 'ROA', '下游→ROA(对照)')
    if res:
        results_dict['下游→ROA(对照)'] = res

# 检验4：上游 → 情绪（对照）
if len(df_up) > 50:
    res, n = run_mech_regression(df_up, 'Sentiment_Proxy_std', '上游→情绪(对照)')
    if res:
        results_dict['上游→情绪(对照)'] = res

# ============================================================================
# 8. 生成 Table 3
# ============================================================================
print("\n【6】生成 Table 3...")

if len(results_dict) == 0:
    print("   ⚠️ 无回归结果，生成空表格")
    table3_df = pd.DataFrame({
        '渠道': ['无可用结果'],
        '样本': ['-'],
        '被解释变量': ['-'],
        'Post系数': [np.nan],
        '标准误': [np.nan],
        't值': [np.nan],
        'p值': [np.nan],
        '显著性': [''],
        '观测值': [0],
        'R²': [np.nan],
        '结论': ['样本量不足']
    })
else:
    table3_rows = []

    channel_names = {
        '上游→ROA': '上游 → 业绩 (ROA)',
        '下游→情绪': '下游 → 情绪 (市场关注)',
        '下游→ROA(对照)': '下游 → 业绩 (对照)',
        '上游→情绪(对照)': '上游 → 情绪 (对照)'
    }

    for key, res in results_dict.items():
        channel_name = channel_names.get(key, key)

        if res['p_value'] < 0.01:
            sig = '***'
        elif res['p_value'] < 0.05:
            sig = '**'
        elif res['p_value'] < 0.1:
            sig = '*'
        else:
            sig = ''

        if key == '上游→ROA' and res['p_value'] < 0.1:
            conclusion = '✅ 业绩渠道成立'
        elif key == '下游→情绪' and res['p_value'] < 0.1:
            conclusion = '✅ 情绪渠道成立'
        elif key in ['下游→ROA(对照)', '上游→情绪(对照)'] and res['p_value'] >= 0.1:
            conclusion = '✅ 不显著(对照)'
        else:
            conclusion = f'系数={res["Coefficient"]:.4f}'

        table3_rows.append({
            '渠道': channel_name,
            '样本': '上游' if '上游' in key else '下游',
            '被解释变量': 'ROA' if 'ROA' in key else '情绪代理(标准化)',
            'Post系数': res['Coefficient'],
            '标准误': res['Std_Error'],
            't值': res['t_stat'],
            'p值': res['p_value'],
            '显著性': sig,
            '观测值': res['N_obs'],
            'R²': res['R_squared'],
            '结论': conclusion
        })

    table3_df = pd.DataFrame(table3_rows)

table3_path = os.path.join(OUTPUT_DIR, 'table3_mechanism.csv')
table3_df.to_csv(table3_path, index=False, encoding='utf-8-sig')
print(f"    ✅ Table 3已保存：{table3_path}")

# ============================================================================
# 9. 打印摘要
# ============================================================================
print("\n【Table 3 摘要】")
print("-" * 70)

if len(table3_df) > 0:
    for _, row in table3_df.iterrows():
        sig = row['显著性']
        print(f"  {row['渠道']}: 系数={row['Post系数']:.4f}{sig}, p={row['p值']:.4f}  {row['结论']}")
else:
    print("  ⚠️ 无有效回归结果")
    print(table3_df.to_string(index=False))
print("-" * 70)

print("\n" + "=" * 70)
print("✅ Table 3 机制检验生成完成！")
print("=" * 70)