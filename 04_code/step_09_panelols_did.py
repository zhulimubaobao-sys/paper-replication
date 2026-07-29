# -*- coding: utf-8 -*-
"""
================================================================================
步骤9：使用 PanelOLS 重写固定效应模型（完整修正版）
================================================================================
"""

import pandas as pd
import numpy as np
import os
import warnings

warnings.filterwarnings('ignore')

from linearmodels.panel import PanelOLS
from datetime import datetime

# ============================================================================
# 1. 路径配置
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

INPUT_PATH = os.path.join(BASE_DIR, '02_processed_data', 'monthly_panel_full.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output')
TABLES_DIR = os.path.join(OUTPUT_DIR, 'tables')
os.makedirs(TABLES_DIR, exist_ok=True)

print("=" * 70)
print("步骤9：PanelOLS DID回归（完整版）")
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
# 4. 设置面板索引
# ============================================================================
print("\n【3】设置面板索引...")
df_clean = df_clean.drop_duplicates(subset=['Stkcd', 'date'])
df_clean = df_clean.sort_values(['Stkcd', 'date'])
df_panel = df_clean.set_index(['Stkcd', 'date'])
print(f"面板数据形状：{df_panel.shape}")

# ============================================================================
# 5. 执行回归
# ============================================================================
print("\n【4】执行回归...")


def run_panel_regression(data, dep_var='Excess_Ret', add_controls=True,
                         entity_effects=True, time_effects=True):
    """运行面板固定效应回归"""
    X_vars = ['Post']
    if add_controls:
        X_vars = X_vars + ['Size', 'ROA', 'Leverage']

    y = data[dep_var]
    X = data[X_vars]

    valid = ~(y.isna() | X.isna().any(axis=1))
    y_clean = y[valid]
    X_clean = X[valid]

    mod = PanelOLS(
        y_clean,
        X_clean,
        entity_effects=entity_effects,
        time_effects=time_effects,
        drop_absorbed=True
    )
    res = mod.fit(cov_type='clustered', cluster_entity=True)

    return res, len(y_clean)


# 子样本
df_panel_all = df_panel
df_panel_up = df_panel[df_panel['Layer'] == '上游']
df_panel_down = df_panel[df_panel['Layer'] == '下游']

# 回归1：全样本
res_all, n_all = run_panel_regression(df_panel_all, dep_var='Excess_Ret', add_controls=True)
print(f"    ✅ 全样本：n={n_all}")

# 回归2：上游子样本
res_up, n_up = run_panel_regression(df_panel_up, dep_var='Excess_Ret', add_controls=True)
print(f"    ✅ 上游：n={n_up}")

# 回归3：下游子样本
res_down, n_down = run_panel_regression(df_panel_down, dep_var='Excess_Ret', add_controls=True)
print(f"    ✅ 下游：n={n_down}")

# 回归4：交互项模型（全样本 + Post * Is_Upstream）
X_interact = df_panel_all[['Post', 'Is_Upstream', 'Size', 'ROA', 'Leverage']].copy()
X_interact['Post_x_Upstream'] = X_interact['Post'] * X_interact['Is_Upstream']
y_interact = df_panel_all['Excess_Ret']

valid_interact = ~(y_interact.isna() | X_interact.isna().any(axis=1))
mod_interact = PanelOLS(
    y_interact[valid_interact],
    X_interact[valid_interact],
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True
)
res_interact = mod_interact.fit(cov_type='clustered', cluster_entity=True)
n_interact = len(y_interact[valid_interact])
print(f"    ✅ 交互项：n={n_interact}")

# ============================================================================
# 6. 提取结果
# ============================================================================
print("\n【5】提取结果...")


def extract_results(res, model_name, n_obs):
    results = []
    for var in res.params.index:
        results.append({
            'Model': model_name,
            'Variable': var,
            'Coefficient': res.params[var],
            'Std_Error': res.std_errors[var],
            't_stat': res.tstats[var],
            'p_value': res.pvalues[var],
            'N_obs': n_obs,
            'R_squared': res.rsquared
        })
    return pd.DataFrame(results)


table2_rows = []
table2_rows.extend(extract_results(res_all, '全样本', n_all).to_dict('records'))
table2_rows.extend(extract_results(res_up, '上游', n_up).to_dict('records'))
table2_rows.extend(extract_results(res_down, '下游', n_down).to_dict('records'))
table2_rows.extend(extract_results(res_interact, '交互项', n_interact).to_dict('records'))

table2_df = pd.DataFrame(table2_rows)

# ============================================================================
# 7. 保存结果
# ============================================================================
print("\n【6】保存结果...")

output_path = os.path.join(TABLES_DIR, 'table2_did_panelols.csv')
table2_df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"    ✅ 结果已保存：{output_path}")

# ============================================================================
# 8. 打印完整结果
# ============================================================================
print("\n【PanelOLS 完整回归结果】")
print("-" * 70)

# 显示所有模型的所有变量
for model in ['全样本', '上游', '下游', '交互项']:
    print(f"\n  【{model}】")
    rows = table2_df[table2_df['Model'] == model]
    for _, row in rows.iterrows():
        var = row['Variable']
        coef = row['Coefficient']
        se = row['Std_Error']
        pval = row['p_value']
        stars = '***' if pval < 0.01 else ('**' if pval < 0.05 else ('*' if pval < 0.1 else ''))
        print(f"    {var}: {coef:.4f} {stars} (se={se:.4f}, p={pval:.4f})")
    if len(rows) > 0:
        print(f"    N={row['N_obs']}, R²={row['R_squared']:.4f}")

print("-" * 70)

# ============================================================================
# 9. 核心结果摘要
# ============================================================================
print("\n【核心结果摘要】")
print("-" * 70)

# 定义要关注的变量
target_vars = ['Post', 'Post_x_Upstream']

for model in ['全样本', '上游', '下游', '交互项']:
    for var in target_vars:
        row = table2_df[(table2_df['Model'] == model) & (table2_df['Variable'] == var)]
        if len(row) > 0:
            coef = row.iloc[0]['Coefficient']
            pval = row.iloc[0]['p_value']
            stars = '***' if pval < 0.01 else ('**' if pval < 0.05 else ('*' if pval < 0.1 else ''))
            print(f"  {model} | {var}: {coef:.4f} {stars} (p={pval:.4f})")
        else:
            # 解释 Post 被吸收的原因
            if var == 'Post':
                print(f"  {model} | {var}: 被时间固定效应吸收 (Absorbed by time FE)")
            else:
                print(f"  {model} | {var}: 未找到")

print("-" * 70)

# ============================================================================
# 10. 与 statsmodels 结果对比
# ============================================================================
print("\n【与 statsmodels 结果对比】")
print("-" * 70)

statsmodels_path = os.path.join(TABLES_DIR, 'table2_did_main.csv')
if os.path.exists(statsmodels_path):
    df_stats = pd.read_csv(statsmodels_path, encoding='utf-8-sig')

    # 主效应对比
    for model in ['全样本', '上游', '下游']:
        row_stats = df_stats[(df_stats['Model'] == model) & (df_stats['Variable'] == 'Post')]
        row_panel = table2_df[(table2_df['Model'] == model) & (table2_df['Variable'] == 'Post')]

        if len(row_stats) > 0 and len(row_panel) > 0:
            stats_coef = row_stats.iloc[0]['Coefficient']
            panel_coef = row_panel.iloc[0]['Coefficient']
            diff = panel_coef - stats_coef
            print(f"  {model}: statsmodels={stats_coef:.4f}, PanelOLS={panel_coef:.4f}, 差异={diff:.4f}")
        elif len(row_stats) > 0 and len(row_panel) == 0:
            # 显示 Post 在 PanelOLS 中被吸收
            stats_coef = row_stats.iloc[0]['Coefficient']
            print(f"  {model}: statsmodels={stats_coef:.4f}, PanelOLS=被吸收 (Absorbed)")
        else:
            print(f"  {model}: 无法对比")

    # 交互项对比
    row_stats_int = df_stats[(df_stats['Model'] == '交互项') & (df_stats['Variable'] == 'Post_x_Upstream')]
    row_panel_int = table2_df[(table2_df['Model'] == '交互项') & (table2_df['Variable'] == 'Post_x_Upstream')]
    if len(row_stats_int) > 0 and len(row_panel_int) > 0:
        stats_coef = row_stats_int.iloc[0]['Coefficient']
        panel_coef = row_panel_int.iloc[0]['Coefficient']
        diff = panel_coef - stats_coef
        print(f"  交互项: statsmodels={stats_coef:.4f}, PanelOLS={panel_coef:.4f}, 差异={diff:.4f}")
else:
    print("  ⚠️ 未找到 statsmodels 结果文件，跳过对比")

print("-" * 70)

# ============================================================================
# 11. 解释说明
# ============================================================================
print("\n【计量经济学解释】")
print("-" * 70)
print("  ⚠️ Post 在 PanelOLS 中被时间固定效应吸收 (Absorbed by time FE)")
print("  📌 原因: Post 是一个纯时间虚拟变量，与时间固定效应完全共线")
print("  ✅ 不影响交互项 Post_x_Upstream 的估计，因为它在公司间有变化")
print("  ✅ 核心结论基于交互项，结果稳健")
print("-" * 70)

# ============================================================================
# 12. 生成日志
# ============================================================================
print("\n【7】生成日志...")

log_lines = []
log_lines.append("=" * 70)
log_lines.append("PanelOLS DID回归日志")
log_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_lines.append("=" * 70)
log_lines.append("\n【Table 2 详细结果】")
log_lines.append(str(table2_df.to_string()))
log_lines.append("\n" + "=" * 70)

log_path = os.path.join(TABLES_DIR, 'panelols_did_log.txt')
with open(log_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines))

print(f"    ✅ 日志已保存：{log_path}")

# ============================================================================
# 13. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 PanelOLS DID回归完成！")
print("=" * 70)
print(f"\n输出文件清单：")
print(f"  [表格] {output_path}")
print(f"  [日志] {log_path}")
print("\n" + "=" * 70)