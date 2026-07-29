"""
极简方案：手动计算事件前后平均超额收益
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

BASE_DIR = r"D:/thailand study/26_7_23paper"
df = pd.read_csv(os.path.join(BASE_DIR, '02_processed_data', 'monthly_panel_full.csv'), encoding='utf-8-sig')
df['date'] = pd.to_datetime(df['date'])

# 只保留上游和下游
df = df[df['Layer'].isin(['上游', '下游'])].copy()

# 只保留事件前后12个月
df = df[(df['event_time'] >= -12) & (df['event_time'] <= 12)]

print("=" * 70)
print("手动计算事件前后平均超额收益")
print("=" * 70)

# 按层级和事件时间分组，计算平均超额收益
grouped = df.groupby(['Layer', 'event_time'])['Excess_Ret'].mean().reset_index()

# 分别提取上游和下游
up = grouped[grouped['Layer'] == '上游']
down = grouped[grouped['Layer'] == '下游']

print(f"上游有效时间点: {len(up)}")
print(f"下游有效时间点: {len(down)}")

# 绘图
plt.figure(figsize=(12, 6))
plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
plt.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='DeepSeek事件')

# 上游（蓝色）
plt.plot(up['event_time'], up['Excess_Ret'], 'o-', color='#2E86AB', linewidth=2, markersize=6, label='上游 (硬件/算力)')

# 下游（橙色）
plt.plot(down['event_time'], down['Excess_Ret'], 's-', color='#E67E22', linewidth=2, markersize=6, label='下游 (应用/服务)')

plt.xlabel('相对事件月份 (0 = 2025年1月)', fontsize=12)
plt.ylabel('平均月度超额收益', fontsize=12)
plt.title('上游 vs 下游：DeepSeek事件前后平均超额收益', fontsize=14, fontweight='bold')
plt.legend(fontsize=10)
plt.grid(True, alpha=0.3)
plt.tight_layout()

# 保存
out_dir = os.path.join(BASE_DIR, '05_output', 'figures', 'CN')
os.makedirs(out_dir, exist_ok=True)
plt.savefig(os.path.join(out_dir, 'figure1_parallel_trend_CN.png'), dpi=300, bbox_inches='tight')
print(f"✅ 已保存：{os.path.join(out_dir, 'figure1_parallel_trend_CN.png')}")

# 英文版
plt.figure(figsize=(12, 6))
plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
plt.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='DeepSeek Event')
plt.plot(up['event_time'], up['Excess_Ret'], 'o-', color='#2E86AB', linewidth=2, markersize=6, label='Upstream (Hardware)')
plt.plot(down['event_time'], down['Excess_Ret'], 's-', color='#E67E22', linewidth=2, markersize=6, label='Downstream (Application)')
plt.xlabel('Months Relative to Event (0 = Jan 2025)', fontsize=12)
plt.ylabel('Average Excess Returns', fontsize=12)
plt.title('Upstream vs Downstream: Average Excess Returns around DeepSeek Event', fontsize=14, fontweight='bold')
plt.legend(fontsize=10)
plt.grid(True, alpha=0.3)
plt.tight_layout()

out_dir_en = os.path.join(BASE_DIR, '05_output', 'figures', 'EN')
os.makedirs(out_dir_en, exist_ok=True)
plt.savefig(os.path.join(out_dir_en, 'figure1_parallel_trend_EN.png'), dpi=300, bbox_inches='tight')
print(f"✅ 已保存：{os.path.join(out_dir_en, 'figure1_parallel_trend_EN.png')}")

print("\n" + "=" * 70)
print("🎉 完成！请打开图片查看。")
print("=" * 70)

# 打印关键数据
print("\n【关键数据】")
print(f"  上游事件后平均收益: {up[up['event_time'] > 0]['Excess_Ret'].mean():.4f}")
print(f"  下游事件后平均收益: {down[down['event_time'] > 0]['Excess_Ret'].mean():.4f}")
print(f"  上游事件前平均收益: {up[up['event_time'] < 0]['Excess_Ret'].mean():.4f}")
print(f"  下游事件前平均收益: {down[down['event_time'] < 0]['Excess_Ret'].mean():.4f}")