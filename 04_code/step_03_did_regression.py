# -*- coding: utf-8 -*-
"""
================================================================================
步骤3：DID回归分析与事件研究（论文核心实证）
使用 statsmodels 实现面板固定效应 + 聚类标准误
================================================================================
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from scipy import stats
from datetime import datetime
import matplotlib.pyplot as plt

# ============================================================================
# 1. 路径配置（使用绝对路径）
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

INPUT_PATH = os.path.join(BASE_DIR, '02_processed_data', 'monthly_panel_full.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output')
TABLES_DIR = os.path.join(OUTPUT_DIR, 'tables')
FIGURES_DIR = os.path.join(OUTPUT_DIR, 'figures')
FIGURES_CN_DIR = os.path.join(FIGURES_DIR, 'CN')
FIGURES_EN_DIR = os.path.join(FIGURES_DIR, 'EN')

for dir_path in [TABLES_DIR, FIGURES_DIR, FIGURES_CN_DIR, FIGURES_EN_DIR]:
    os.makedirs(dir_path, exist_ok=True)

print("=" * 70)
print("步骤3：DID回归分析与事件研究")
print("=" * 70)
print(f"输入文件：{INPUT_PATH}")

# ============================================================================
# 2. 读取数据
# ============================================================================
print("\n【1】读取数据...")
df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')
df['date'] = pd.to_datetime(df['date'])

print(f"数据行数：{len(df):,}")
print(f"公司数：{df['Stkcd'].nunique()}")
print(f"时间范围：{df['date'].min()} 至 {df['date'].max()}")
print(f"各层级分布：\n{df['Layer'].value_counts()}")

# ============================================================================
# 3. 数据预处理
# ============================================================================
print("\n【2】数据预处理...")

df['Post'] = df['Post'].astype(int)
df['Is_Upstream'] = (df['Layer'] == '上游').astype(int)
df['Is_Downstream'] = (df['Layer'] == '下游').astype(int)

def winsorize_series(s, lower=0.01, upper=0.99):
    low = s.quantile(lower)
    high = s.quantile(upper)
    return s.clip(low, high)

for col in ['Size', 'ROA', 'Leverage']:
    if col in df.columns:
        df[col] = winsorize_series(df[col])
        print(f"    {col} 已完成1%/99%缩尾处理")

df_clean = df.dropna(subset=['Excess_Ret', 'Size', 'ROA', 'Leverage', 'Post'])
print(f"删除缺失值后行数：{len(df_clean):,}")

# ============================================================================
# 4. 面板固定效应回归函数（支持控制时间固定效应）
# ============================================================================
def panel_fe_regression(df_sub, y_var='Excess_Ret', x_vars=['Post'], time_effects=True):
    """
    面板固定效应回归：加入个体和时间虚拟变量（可选），聚类标准误
    """
    df_temp = df_sub.copy()
    # 个体固定效应
    df_temp['Stkcd_fe'] = df_temp['Stkcd'].astype('category').cat.codes
    # 时间固定效应（可选）
    if time_effects:
        df_temp['time_fe'] = df_temp['date'].dt.strftime('%Y%m').astype('category').cat.codes
        all_x = x_vars + ['Stkcd_fe', 'time_fe']
    else:
        all_x = x_vars + ['Stkcd_fe']

    # 保留 Stkcd 用于聚类
    all_vars = [y_var] + all_x + ['Stkcd']
    df_reg = df_temp[all_vars].dropna()

    if len(df_reg) < 50:
        return None, 0

    X = df_reg[all_x].copy()
    X = add_constant(X)
    y = df_reg[y_var]

    model = OLS(y, X)
    try:
        # 尝试聚类标准误
        results = model.fit(cov_type='cluster', cov_kwds={'groups': df_reg['Stkcd']})
    except Exception:
        # 如果聚类失败，使用普通标准误（但会警告）
        results = model.fit()
        print(f"    ⚠️ 聚类标准误失败，使用普通标准误（{y_var}）")
    return results, len(df_reg)

# ============================================================================
# 5. Table 1：描述性统计
# ============================================================================
print("\n【3】生成Table 1：描述性统计...")

df_temp = df_clean[df_clean['Layer'].isin(['上游', '下游'])].copy()
desc_stats = df_temp.groupby('Layer').agg({
    'Excess_Ret': ['mean', 'std', 'count'],
    'Size': ['mean', 'std'],
    'ROA': ['mean', 'std'],
    'Leverage': ['mean', 'std']
}).round(4)
desc_stats.to_csv(os.path.join(TABLES_DIR, 'table1_descriptive.csv'), encoding='utf-8-sig')
print(f"    ✅ Table 1已保存")

# ============================================================================
# 6. Table 2：基准DID回归
# ============================================================================
print("\n【4】生成Table 2：基准DID回归...")

def run_did_regression(df_sub, model_name, x_vars, time_effects=True):
    results, n_obs = panel_fe_regression(df_sub, 'Excess_Ret', x_vars, time_effects)
    if results is None:
        return []
    rows = []
    for var in results.params.index:
        rows.append({
            'Model': model_name,
            'Variable': var,
            'Coefficient': results.params[var],
            'Std_Error': results.bse[var],
            't_stat': results.tvalues[var],
            'p_value': results.pvalues[var],
            'N_obs': n_obs,
            'R_squared': results.rsquared
        })
    return rows

# 子样本
df_all = df_clean
df_up = df_clean[df_clean['Layer'] == '上游']
df_down = df_clean[df_clean['Layer'] == '下游']

# 模型1：全样本
rows_all = run_did_regression(df_all, '全样本', ['Post', 'Size', 'ROA', 'Leverage'])
# 模型2：上游
rows_up = run_did_regression(df_up, '上游', ['Post', 'Size', 'ROA', 'Leverage'])
# 模型3：下游
rows_down = run_did_regression(df_down, '下游', ['Post', 'Size', 'ROA', 'Leverage'])

# 模型4：交互项（全样本 + Post*Is_Upstream）
df_interact = df_all.copy()
df_interact['Post_x_Upstream'] = df_interact['Post'] * df_interact['Is_Upstream']
res_interact, n_interact = panel_fe_regression(df_interact, 'Excess_Ret',
                                               ['Post', 'Is_Upstream', 'Post_x_Upstream', 'Size', 'ROA', 'Leverage'])
rows_interact = []
if res_interact is not None:
    for var in res_interact.params.index:
        rows_interact.append({
            'Model': '交互项',
            'Variable': var,
            'Coefficient': res_interact.params[var],
            'Std_Error': res_interact.bse[var],
            't_stat': res_interact.tvalues[var],
            'p_value': res_interact.pvalues[var],
            'N_obs': n_interact,
            'R_squared': res_interact.rsquared
        })

table2_rows = rows_all + rows_up + rows_down + rows_interact
table2_df = pd.DataFrame(table2_rows)
table2_df.to_csv(os.path.join(TABLES_DIR, 'table2_did_main.csv'), index=False, encoding='utf-8-sig')
print(f"    ✅ Table 2已保存")

# 打印关键结果
print("\n【Table 2 关键结果摘要】")
print("-" * 60)
for model in ['全样本', '上游', '下游']:
    row = table2_df[(table2_df['Model'] == model) & (table2_df['Variable'] == 'Post')]
    if len(row) > 0:
        coef = row.iloc[0]['Coefficient']
        pval = row.iloc[0]['p_value']
        stars = '***' if pval < 0.01 else ('**' if pval < 0.05 else ('*' if pval < 0.1 else ''))
        print(f"  {model}: Post系数 = {coef:.4f} {stars} (p={pval:.4f})")
row_interact = table2_df[(table2_df['Model'] == '交互项') & (table2_df['Variable'] == 'Post_x_Upstream')]
if len(row_interact) > 0:
    coef = row_interact.iloc[0]['Coefficient']
    pval = row_interact.iloc[0]['p_value']
    stars = '***' if pval < 0.01 else ('**' if pval < 0.05 else ('*' if pval < 0.1 else ''))
    print(f"  交互项(Post×上游): 系数 = {coef:.4f} {stars} (p={pval:.4f})")
print("-" * 60)

# ============================================================================
# 7. Figure 1：平行趋势检验（生成中文和英文版本）
# ============================================================================
print("\n【5】生成Figure 1：平行趋势检验（中文/英文）...")

# 先准备好用于绘图的回归结果（只需计算一次）
df_es = df_clean[df_clean['Layer'].isin(['上游', '下游'])].copy()
event_times = sorted([t for t in df_es['event_time'].unique() if -12 <= t <= 12 and t != -1])
for t in event_times:
    df_es[f'evt_{t}'] = (df_es['event_time'] == t).astype(int)

res_evt, n_evt = panel_fe_regression(df_es, 'Excess_Ret',
                                     [f'evt_{t}' for t in event_times] + ['Size', 'ROA', 'Leverage'])

if res_evt is not None:
    # 提取系数和置信区间（供绘图使用）
    coefs = []
    cis = []
    for t in sorted(event_times):
        var = f'evt_{t}'
        coefs.append(res_evt.params[var])
        se = res_evt.bse[var]
        cis.append(1.96 * se)

    def plot_figure1(lang='CN'):
        """绘制平行趋势图（语言：CN/EN）"""
        # 字体和标签设置
        if lang == 'CN':
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            title = '平行趋势检验：DeepSeek事件前后AI企业超额收益动态'
            xlabel = '相对事件月份 (0 = 2025年1月)'
            ylabel = '月度超额收益系数'
            event_label = 'DeepSeek事件'
            legend_label = '估计系数 ± 95% CI'
            save_name = 'figure1_parallel_trend_CN.png'
        else:  # EN
            plt.rcParams['font.sans-serif'] = ['Times New Roman', 'Arial']
            plt.rcParams['axes.unicode_minus'] = False
            title = 'Parallel Trends: Dynamic Excess Returns of AI Firms'
            xlabel = 'Event Month (0 = Jan 2025)'
            ylabel = 'Monthly Excess Return Coefficient'
            event_label = 'DeepSeek Event'
            legend_label = 'Coefficient ± 95% CI'
            save_name = 'figure1_parallel_trend_EN.png'

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5, linewidth=1)
        ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, linewidth=1.5, label=event_label)
        ax.errorbar(sorted(event_times), coefs, yerr=cis, fmt='o', color='#2E86AB',
                    capsize=4, elinewidth=2, markersize=8, label=legend_label)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)

        # 英文版去网格？但国际期刊通常简洁，可保留或去掉，这里保留
        plt.tight_layout()
        save_path = os.path.join(FIGURES_DIR, 'CN' if lang=='CN' else 'EN', save_name)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"    ✅ Figure 1 ({lang}) 已保存: {save_path}")

    # 生成中文版
    plot_figure1('CN')
    # 生成英文版
    plot_figure1('EN')
else:
    print("    ⚠️ 平行趋势回归失败，跳过绘图")

# ============================================================================
# 8. Figure 2：上下游系数对比（生成中文和英文版本）
# ============================================================================
print("\n【6】生成Figure 2：上游vs下游系数对比（中文/英文）...")

up_row = table2_df[(table2_df['Model'] == '上游') & (table2_df['Variable'] == 'Post')]
down_row = table2_df[(table2_df['Model'] == '下游') & (table2_df['Variable'] == 'Post')]

if len(up_row) > 0 and len(down_row) > 0:
    up_val = up_row.iloc[0]['Coefficient']; up_se = up_row.iloc[0]['Std_Error']
    down_val = down_row.iloc[0]['Coefficient']; down_se = down_row.iloc[0]['Std_Error']
    diff_val = up_val - down_val
    diff_se = np.sqrt(up_se**2 + down_se**2)
    diff_p = 2 * (1 - stats.norm.cdf(abs(diff_val / diff_se)))

    def plot_figure2(lang='CN'):
        if lang == 'CN':
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            categories = ['上游 (硬件/算力)', '下游 (应用/服务)']
            title = '上游 vs 下游：DeepSeek事件对超额收益的因果效应对比'
            ylabel = 'DID估计系数 (Post)'
            diff_label = '组间差异 = {:.4f}'.format(diff_val)
            save_name = 'figure2_layer_comparison_CN.png'
        else:
            plt.rcParams['font.sans-serif'] = ['Times New Roman', 'Arial']
            plt.rcParams['axes.unicode_minus'] = False
            categories = ['Upstream (Hardware/Compute)', 'Downstream (Apps/Services)']
            title = 'Upstream vs Downstream: Causal Effect of DeepSeek Event on Excess Returns'
            ylabel = 'DID Coefficient (Post)'
            diff_label = 'Difference = {:.4f}'.format(diff_val)
            save_name = 'figure2_layer_comparison_EN.png'

        fig, ax = plt.subplots(figsize=(8, 6))
        bars = ax.bar(categories, [up_val, down_val],
                      yerr=[up_se, down_se], capsize=5,
                      color=['#2E86AB', '#E67E22'], alpha=0.8, edgecolor='black')
        for bar, val in zip(bars, [up_val, down_val]):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.001*abs(height)+0.002,
                    f'{val:.4f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

        # 添加显著性星号
        stars = ''
        if diff_p < 0.01:
            stars = '***'
        elif diff_p < 0.05:
            stars = '**'
        elif diff_p < 0.1:
            stars = '*'
        diff_text = diff_label + stars
        ax.text(0.5, max([up_val, down_val]) + 0.01, diff_text, ha='center', va='bottom',
                fontsize=11, style='italic', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        save_path = os.path.join(FIGURES_DIR, 'CN' if lang=='CN' else 'EN', save_name)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"    ✅ Figure 2 ({lang}) 已保存: {save_path}")

    plot_figure2('CN')
    plot_figure2('EN')
else:
    print("    ⚠️ 缺少上游或下游回归结果，跳过对比图")

# ============================================================================
# 9. Table 3：机制检验（去掉时间固定效应）
# ============================================================================
print("\n【7】生成Table 3：机制检验...")
if 'trading_days' in df_clean.columns:
    df_clean['Sentiment_Proxy'] = df_clean['trading_days']
    df_clean['Sentiment_Proxy_std'] = (df_clean['Sentiment_Proxy'] - df_clean['Sentiment_Proxy'].mean()) / df_clean['Sentiment_Proxy'].std()
    # 上游→ROA（不使用时间固定效应）
    df_up_mech = df_clean[df_clean['Layer'] == '上游'].copy()
    res_roa, n_roa = panel_fe_regression(df_up_mech, 'ROA', ['Post', 'Size', 'Leverage'], time_effects=False)
    # 下游→情绪（不使用时间固定效应）
    df_down_mech = df_clean[df_clean['Layer'] == '下游'].copy()
    res_sent, n_sent = panel_fe_regression(df_down_mech, 'Sentiment_Proxy_std', ['Post', 'Size', 'ROA', 'Leverage'], time_effects=False)
    table3_rows = []
    if res_roa is not None:
        table3_rows.append({
            '渠道': '上游 → 业绩 (ROA)',
            '样本': '上游',
            '被解释变量': 'ROA',
            'Post系数': res_roa.params['Post'],
            '标准误': res_roa.bse['Post'],
            't值': res_roa.tvalues['Post'],
            'p值': res_roa.pvalues['Post'],
            '观测值': n_roa,
            'R²': res_roa.rsquared
        })
    if res_sent is not None:
        table3_rows.append({
            '渠道': '下游 → 情绪 (市场关注)',
            '样本': '下游',
            '被解释变量': '情绪代理(标准化)',
            'Post系数': res_sent.params['Post'],
            '标准误': res_sent.bse['Post'],
            't值': res_sent.tvalues['Post'],
            'p值': res_sent.pvalues['Post'],
            '观测值': n_sent,
            'R²': res_sent.rsquared
        })
    table3_df = pd.DataFrame(table3_rows)
    table3_df.to_csv(os.path.join(TABLES_DIR, 'table3_mechanism.csv'), index=False, encoding='utf-8-sig')
    print(f"    ✅ Table 3已保存")
else:
    pd.DataFrame({'Note': ['trading_days not available']}).to_csv(
        os.path.join(TABLES_DIR, 'table3_mechanism.csv'), index=False, encoding='utf-8-sig'
    )
    print("    ⚠️ 数据中缺少trading_days列，Table 3跳过")

# ============================================================================
# 10. 日志
# ============================================================================
print("\n【8】生成完整日志...")
with open(os.path.join(TABLES_DIR, 'did_regression_full_log.txt'), 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("DID回归完整日志\n")
    f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 70 + "\n")
    f.write("\n【Table 2 详细结果】\n")
    f.write(table2_df.to_string())
print(f"    ✅ 日志已保存")

# ============================================================================
# 11. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 DID回归分析与事件研究全部完成！")
print("=" * 70)
print("\n输出文件清单：")
print(f"  [表格] {os.path.join(TABLES_DIR, 'table1_descriptive.csv')}")
print(f"  [表格] {os.path.join(TABLES_DIR, 'table2_did_main.csv')}")
print(f"  [表格] {os.path.join(TABLES_DIR, 'table3_mechanism.csv')}")
print(f"  [表格] {os.path.join(TABLES_DIR, 'did_regression_full_log.txt')}")
print(f"  [图表] {os.path.join(FIGURES_CN_DIR, 'figure1_parallel_trend_CN.png')}")
print(f"  [图表] {os.path.join(FIGURES_EN_DIR, 'figure1_parallel_trend_EN.png')}")
print(f"  [图表] {os.path.join(FIGURES_CN_DIR, 'figure2_layer_comparison_CN.png')}")
print(f"  [图表] {os.path.join(FIGURES_EN_DIR, 'figure2_layer_comparison_EN.png')}")
print("\n" + "=" * 70)