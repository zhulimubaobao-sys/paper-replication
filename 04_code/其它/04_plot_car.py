# -*- coding: utf-8 -*-
"""
功能：绘制上游 vs 下游 月度平均 CAR 对比图
输入：03_clean_data/panel_final.csv
输出：05_output/upstream_downstream_CAR.png
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 第一步：读取数据
# ============================================================
BASE_DIR = Path(r"D:\thailand study\26_7_23paper")
INPUT_FILE = BASE_DIR / "03_clean_data" / "panel_final.csv"
OUTPUT_DIR = BASE_DIR / "05_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "upstream_downstream_CAR.png"

print("=" * 60)
print("开始绘制上下游月度CAR对比图...")

df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
df['月份_dt'] = pd.to_datetime(df['月份_dt'])

print(f"✅ 读取数据: {len(df)} 条观测值")

# ============================================================
# 第二步：按月份和产业链位置分组，计算平均CAR
# ============================================================
monthly_avg = df.groupby(['月份_dt', '产业链位置']).agg({
    'CAR': 'mean',
    '股票代码': 'count'  # 用于统计每月的股票数量
}).rename(columns={'股票代码': '股票数量'}).reset_index()

# 分开上游和下游
upstream = monthly_avg[monthly_avg['产业链位置'] == '上游'].copy()
downstream = monthly_avg[monthly_avg['产业链位置'] == '下游'].copy()

# 排序
upstream = upstream.sort_values('月份_dt')
downstream = downstream.sort_values('月份_dt')

print(f"  上游: {len(upstream)} 个月份数据")
print(f"  下游: {len(downstream)} 个月份数据")

# ============================================================
# 第三步：绘图
# ============================================================
fig, ax = plt.subplots(figsize=(14, 8))

# 颜色设置
color_up = '#2E86AB'   # 上游 - 蓝色
color_down = '#A23B72'  # 下游 - 紫红色
color_event = '#F18F01' # 事件标记 - 橙色

# 画两条折线
ax.plot(upstream['月份_dt'], upstream['CAR'] * 100,
        marker='o', linewidth=2.5, markersize=8,
        color=color_up, label='上游（算力硬件）', markeredgecolor='white', markeredgewidth=1)

ax.plot(downstream['月份_dt'], downstream['CAR'] * 100,
        marker='s', linewidth=2.5, markersize=8,
        color=color_down, label='下游（场景应用）', markeredgecolor='white', markeredgewidth=1)

# 标记 DeepSeek 事件（2025年1月）
event_date = pd.Timestamp('2025-01-01')
ax.axvline(x=event_date, color=color_event, linestyle='--', linewidth=2.5, alpha=0.8, label='DeepSeek 事件 (2025年1月)')

# 添加文字标注
ax.text(event_date, ax.get_ylim()[1] * 0.95, 'DeepSeek\n发布',
        ha='center', va='top', fontsize=12, color=color_event, fontweight='bold')

# 添加零线
ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.8, alpha=0.5)

# 设置标题和标签
ax.set_title('DeepSeek 事件后 AI 产业链上下游月度 CAR 对比',
             fontsize=18, fontweight='bold', pad=20)
ax.set_xlabel('月份', fontsize=14, fontweight='bold')
ax.set_ylabel('月度平均 CAR (%)', fontsize=14, fontweight='bold')

# 设置图例
ax.legend(loc='upper left', fontsize=12, framealpha=0.9, shadow=True)

# 设置网格
ax.grid(True, alpha=0.3, linestyle='--')

# 自动调整x轴日期格式
fig.autofmt_xdate(rotation=45)

# 添加数据标签（在最后一个数据点上显示数值）
if len(upstream) > 0:
    last_up = upstream.iloc[-1]
    ax.annotate(f'{last_up["CAR"]*100:.2f}%',
                xy=(last_up['月份_dt'], last_up['CAR']*100),
                xytext=(5, 5), textcoords='offset points',
                fontsize=10, color=color_up, fontweight='bold')

if len(downstream) > 0:
    last_down = downstream.iloc[-1]
    ax.annotate(f'{last_down["CAR"]*100:.2f}%',
                xy=(last_down['月份_dt'], last_down['CAR']*100),
                xytext=(5, -15), textcoords='offset points',
                fontsize=10, color=color_down, fontweight='bold')

# 添加统计信息到图角
stats_text = f"样本: 20只股票 (上游9只, 下游11只)\n时间: 2025-07 至 2026-07"
ax.text(0.02, 0.02, stats_text, transform=ax.transAxes,
        fontsize=10, verticalalignment='bottom',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# 调整布局
plt.tight_layout()

# ============================================================
# 第四步：保存图片
# ============================================================
plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
print(f"\n✅ 图片已保存至: {OUTPUT_FILE}")

# 也显示图片（如果你在本地运行，会弹出窗口）
plt.show()

print("\n📊 图表说明:")
print("   - 蓝线: 上游企业（算力硬件）月度平均超额收益")
print("   - 紫红线: 下游企业（场景应用）月度平均超额收益")
print("   - 虚线: DeepSeek 事件发生时间 (2025年1月)")
print("   - 零线以上为正收益，以下为负收益")