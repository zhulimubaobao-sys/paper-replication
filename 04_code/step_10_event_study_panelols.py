# -*- coding: utf-8 -*-
"""
================================================================================
步骤10b：分上游/下游的平行趋势检验（PanelOLS 版本）
论文：AI产业链的非对称定价
修正：分别绘制上游和下游的事件研究系数，避免合并抵消
================================================================================
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

from linearmodels.panel import PanelOLS
import matplotlib.pyplot as plt

BASE_DIR = r"D:/thailand study/26_7_23paper"
INPUT_PATH = os.path.join(BASE_DIR, '02_processed_data', 'monthly_panel_full.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output')
FIGURES_DIR = os.path.join(OUTPUT_DIR, 'figures')
TABLES_DIR = os.path.join(OUTPUT_DIR, 'tables')

CN_DIR = os.path.join(FIGURES_DIR, 'CN')
EN_DIR = os.path.join(FIGURES_DIR, 'EN')
for dir_path in [CN_DIR, EN_DIR, TABLES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

print("=" * 70)
print("步骤10b：分上游/下游平行趋势检验")
print("=" * 70)

# ============================================================================
# 2. 读取数据
# ============================================================================
print("\n【1】读取数据...")
df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')
df['date'] = pd.to_datetime(df['date'])

def winsorize_series(s, lower=0.01, upper=0.99):
    low = s.quantile(lower)
    high = s.quantile(upper)
    return s.clip(low, high)

for col in ['Size', 'ROA', 'Leverage']:
    if col in df.columns:
        df[col] = winsorize_series(df[col])

df = df.dropna(subset=['Excess_Ret', 'Size', 'ROA', 'Leverage', 'event_time'])

# ============================================================================
# 3. 定义事件研究回归函数（分样本）
# ============================================================================
def run_event_study(df_sub, layer_name):
    """对指定层级的子样本运行事件研究回归"""
    print(f"\n  【{layer_name}】n={len(df_sub):,}")

    # 生成事件时间虚拟变量
    event_times = sorted([t for t in df_sub['event_time'].unique() if -12 <= t <= 12])
    event_times_excl_ref = [t for t in event_times if t != -1]

    for t in event_times_excl_ref:
        df_sub[f'evt_{t}'] = (df_sub['event_time'] == t).astype(int)

    # 准备面板数据
    df_sub = df_sub.drop_duplicates(subset=['Stkcd', 'date'])
    df_sub = df_sub.sort_values(['Stkcd', 'date'])
    df_panel = df_sub.set_index(['Stkcd', 'date'])

    # 构建回归
    evt_vars = [f'evt_{t}' for t in sorted(event_times_excl_ref)]
    x_vars = evt_vars + ['Size', 'ROA', 'Leverage']

    X = df_panel[x_vars]
    y = df_panel['Excess_Ret']

    valid = ~(y.isna() | X.isna().any(axis=1))
    y_clean = y[valid]
    X_clean = X[valid]

    mod = PanelOLS(
        y_clean,
        X_clean,
        entity_effects=True,
        time_effects=True,
        drop_absorbed=True
    )
    res = mod.fit(cov_type='clustered', cluster_entity=True)

    # 提取系数
    coefs = []
    cis_low = []
    cis_high = []
    for t in sorted(event_times_excl_ref):
        var = f'evt_{t}'
        if var in res.params.index:
            coefs.append(res.params[var])
            ci = res.conf_int().loc[var]
            cis_low.append(ci[0])
            cis_high.append(ci[1])
        else:
            coefs.append(np.nan)
            cis_low.append(np.nan)
            cis_high.append(np.nan)

    return {
        'layer': layer_name,
        'times': sorted(event_times_excl_ref),
        'coefs': coefs,
        'cis_low': cis_low,
        'cis_high': cis_high,
        'n': len(y_clean),
        'r2': res.rsquared
    }

# ============================================================================
# 4. 分别运行上游和下游
# ============================================================================
print("\n【2】运行事件研究回归...")

df_up = df[df['Layer'] == '上游'].copy()
df_down = df[df['Layer'] == '下游'].copy()

result_up = run_event_study(df_up, '上游')
result_down = run_event_study(df_down, '下游')

print(f"\n  上游 R² = {result_up['r2']:.4f}, n={result_up['n']}")
print(f"  下游 R² = {result_down['r2']:.4f}, n={result_down['n']}")

# ============================================================================
# 5. 绘图函数（分两条线）
# ============================================================================
def draw_event_study_two_layers(title, xlabel, ylabel, filename, is_chinese=True):
    """绘制上游和下游两条线的平行趋势图"""
    plt.figure(figsize=(12, 6))

    # 零线
    plt.axhline(y=0, color='black', linestyle='--', alpha=0.5, linewidth=1)

    # 事件线
    event_label = 'DeepSeek Event' if not is_chinese else 'DeepSeek事件'
    plt.axvline(x=0, color='red', linestyle='--', alpha=0.7, linewidth=1.5, label=event_label)

    # 上游：提取有效数据
    valid_up = ~np.isnan(result_up['coefs'])
    times_up = [result_up['times'][i] for i in range(len(result_up['times'])) if valid_up[i]]
    coefs_up = [result_up['coefs'][i] for i in range(len(result_up['coefs'])) if valid_up[i]]
    low_up = [result_up['cis_low'][i] for i in range(len(result_up['cis_low'])) if valid_up[i]]
    high_up = [result_up['cis_high'][i] for i in range(len(result_up['cis_high'])) if valid_up[i]]

    # 下游：提取有效数据
    valid_down = ~np.isnan(result_down['coefs'])
    times_down = [result_down['times'][i] for i in range(len(result_down['times'])) if valid_down[i]]
    coefs_down = [result_down['coefs'][i] for i in range(len(result_down['coefs'])) if valid_down[i]]
    low_down = [result_down['cis_low'][i] for i in range(len(result_down['cis_low'])) if valid_down[i]]
    high_down = [result_down['cis_high'][i] for i in range(len(result_down['cis_high'])) if valid_down[i]]

    # 绘制上游（蓝色）
    label_up = 'Upstream (Hardware)' if not is_chinese else '上游 (硬件/算力)'
    plt.errorbar(
        times_up, coefs_up,
        yerr=[np.array(coefs_up) - np.array(low_up), np.array(high_up) - np.array(coefs_up)],
        fmt='o-', color='#2E86AB', capsize=4, elinewidth=2, markersize=6,
        label=label_up, linewidth=2
    )

    # 绘制下游（橙色）
    label_down = 'Downstream (Application)' if not is_chinese else '下游 (应用/服务)'
    plt.errorbar(
        times_down, coefs_down,
        yerr=[np.array(coefs_down) - np.array(low_down), np.array(high_down) - np.array(coefs_down)],
        fmt='s-', color='#E67E22', capsize=4, elinewidth=2, markersize=6,
        label=label_down, linewidth=2
    )

    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"    ✅ 已保存：{filename}")

# ============================================================================
# 6. 生成中文版
# ============================================================================
print("\n【3】生成中文版...")
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

draw_event_study_two_layers(
    title='平行趋势检验：上游 vs 下游（DeepSeek事件前后）',
    xlabel='相对事件月份 (0 = 2025年1月)',
    ylabel='月度超额收益系数',
    filename=os.path.join(CN_DIR, 'figure1_parallel_trend_CN.png'),
    is_chinese=True
)

# ============================================================================
# 7. 生成英文版
# ============================================================================
print("\n【4】生成英文版...")
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False

draw_event_study_two_layers(
    title='Parallel Trends: Upstream vs Downstream (DeepSeek Event)',
    xlabel='Months Relative to Event (0 = Jan 2025)',
    ylabel='Coefficient on Excess Returns',
    filename=os.path.join(EN_DIR, 'figure1_parallel_trend_EN.png'),
    is_chinese=False
)

# ============================================================================
# 8. 打印关键结果
# ============================================================================
print("\n【5】关键结果摘要")
print("-" * 70)

# 计算事件后平均效应
post_up = [c for i, c in enumerate(result_up['coefs']) if result_up['times'][i] > 0 and not np.isnan(c)]
post_down = [c for i, c in enumerate(result_down['coefs']) if result_down['times'][i] > 0 and not np.isnan(c)]

if post_up:
    print(f"  上游事件后平均系数：{np.mean(post_up):.4f}")
if post_down:
    print(f"  下游事件后平均系数：{np.mean(post_down):.4f}")
if post_up and post_down:
    print(f"  上下游差异：{np.mean(post_up) - np.mean(post_down):.4f}")

# 检查事前趋势
pre_up = [c for i, c in enumerate(result_up['coefs']) if result_up['times'][i] < 0 and not np.isnan(c)]
pre_down = [c for i, c in enumerate(result_down['coefs']) if result_down['times'][i] < 0 and not np.isnan(c)]

if pre_up:
    print(f"\n  上游事前系数均值：{np.mean(pre_up):.4f} (接近0则平行趋势成立)")
if pre_down:
    print(f"  下游事前系数均值：{np.mean(pre_down):.4f} (接近0则平行趋势成立)")

print("-" * 70)

# ============================================================================
# 9. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 分上游/下游平行趋势检验完成！")
print("=" * 70)
print("\n输出文件清单：")
print(f"  [图表] {os.path.join(CN_DIR, 'figure1_parallel_trend_CN.png')}")
print(f"  [图表] {os.path.join(EN_DIR, 'figure1_parallel_trend_EN.png')}")
print("\n" + "=" * 70)