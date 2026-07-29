# -*- coding: utf-8 -*-
"""
步骤10：分上游/下游平行趋势检验（简化修复版）
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
CN_DIR = os.path.join(OUTPUT_DIR, 'figures', 'CN')
EN_DIR = os.path.join(OUTPUT_DIR, 'figures', 'EN')

for d in [CN_DIR, EN_DIR]:
    os.makedirs(d, exist_ok=True)

print("=" * 70)
print("步骤10：平行趋势检验（修复版）")
print("=" * 70)

# 读取数据
df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')
df['date'] = pd.to_datetime(df['date'])

# 只保留上游和下游
df = df[df['Layer'].isin(['上游', '下游'])].copy()

# 缩尾
def winsorize_series(s, lower=0.01, upper=0.99):
    low = s.quantile(lower)
    high = s.quantile(upper)
    return s.clip(low, high)

for col in ['Size', 'ROA', 'Leverage']:
    if col in df.columns:
        df[col] = winsorize_series(df[col])

df = df.dropna(subset=['Excess_Ret', 'Size', 'ROA', 'Leverage', 'event_time'])
print(f"样本量：{len(df)}")

# ========== 分别对上游和下游运行 ==========
results = {}

for layer in ['上游', '下游']:
    print(f"\n处理 {layer}...")
    df_sub = df[df['Layer'] == layer].copy()

    # 生成事件虚拟变量
    event_times = sorted([t for t in df_sub['event_time'].unique() if -12 <= t <= 12])
    ref_times = [t for t in event_times if t != -1]

    for t in ref_times:
        df_sub[f'evt_{t}'] = (df_sub['event_time'] == t).astype(int)

    df_sub = df_sub.drop_duplicates(subset=['Stkcd', 'date'])
    df_sub = df_sub.sort_values(['Stkcd', 'date'])
    df_panel = df_sub.set_index(['Stkcd', 'date'])

    # 回归
    evt_vars = [f'evt_{t}' for t in sorted(ref_times)]
    X = df_panel[evt_vars + ['Size', 'ROA', 'Leverage']]
    y = df_panel['Excess_Ret']

    valid = ~(y.isna() | X.isna().any(axis=1))
    mod = PanelOLS(y[valid], X[valid], entity_effects=True, time_effects=True, drop_absorbed=True)
    res = mod.fit(cov_type='clustered', cluster_entity=True)

    # 提取系数
    coefs = []
    lows = []
    highs = []
    for t in sorted(ref_times):
        var = f'evt_{t}'
        if var in res.params.index:
            coefs.append(res.params[var])
            ci = res.conf_int().loc[var]
            lows.append(ci[0])
            highs.append(ci[1])
        else:
            coefs.append(np.nan)
            lows.append(np.nan)
            highs.append(np.nan)

    results[layer] = {
        'times': sorted(ref_times),
        'coefs': coefs,
        'lows': lows,
        'highs': highs
    }

    print(f"  {layer}: 有效系数 {sum(~np.isnan(coefs))} 个")

# ========== 绘图 ==========
def draw_plot(title, xlabel, ylabel, fname, is_chinese=True):
    plt.figure(figsize=(12, 6))
    plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='DeepSeek Event' if not is_chinese else 'DeepSeek事件')

    colors = {'上游': '#2E86AB', '下游': '#E67E22'}
    markers = {'上游': 'o', '下游': 's'}
    labels = {'上游': '上游 (硬件/算力)', '下游': '下游 (应用/服务)'}
    if not is_chinese:
        labels = {'上游': 'Upstream (Hardware)', '下游': 'Downstream (Application)'}

    for layer in ['上游', '下游']:
        r = results[layer]
        valid = ~np.isnan(r['coefs'])
        if sum(valid) == 0:
            print(f"  ⚠️ {layer} 无有效数据，跳过")
            continue
        times = [r['times'][i] for i in range(len(r['times'])) if valid[i]]
        coefs = [r['coefs'][i] for i in range(len(r['coefs'])) if valid[i]]
        lows = [r['lows'][i] for i in range(len(r['lows'])) if valid[i]]
        highs = [r['highs'][i] for i in range(len(r['highs'])) if valid[i]]

        plt.errorbar(times, coefs,
                     yerr=[np.array(coefs)-np.array(lows), np.array(highs)-np.array(coefs)],
                     fmt=f'{markers[layer]}-', color=colors[layer], capsize=4,
                     elinewidth=2, markersize=6, label=labels[layer], linewidth=2)

    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(fname, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✅ 已保存：{fname}")

# 中文
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
draw_plot('平行趋势检验：上游 vs 下游（DeepSeek事件前后）',
          '相对事件月份 (0 = 2025年1月)',
          '月度超额收益系数',
          os.path.join(CN_DIR, 'figure1_parallel_trend_CN.png'),
          True)

# 英文
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False
draw_plot('Parallel Trends: Upstream vs Downstream (DeepSeek Event)',
          'Months Relative to Event (0 = Jan 2025)',
          'Coefficient on Excess Returns',
          os.path.join(EN_DIR, 'figure1_parallel_trend_EN.png'),
          False)

print("\n" + "=" * 70)
print("🎉 完成！请重新打开图片查看数据点。")
print("=" * 70)