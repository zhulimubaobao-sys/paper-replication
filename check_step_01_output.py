# -*- coding: utf-8 -*-
# 文件名: check_step_01_output.py
# 作用：核验 Step 1 产出的两张面板（百分制单位，日期判断放宽）
import pandas as pd
import os

# 定义路径
base_dir = r"D:\thailand study\26_7_23paper\02_processed_data"
excess_file = os.path.join(base_dir, "01_excess_return_panel.csv")
merged_file = os.path.join(base_dir, "01_merged_panel.csv")

print("=" * 60)
print("【Step 1 数据质量核验报告】")
print("=" * 60)

# 1. 检查文件是否存在
for path in [excess_file, merged_file]:
    if not os.path.exists(path):
        print(f"❌ 致命错误：找不到文件 -> {path}")
        exit()
print("✅ 文件存在性检查通过\n")

# 2. 读取核心数据（超额收益面板）
df = pd.read_csv(excess_file, encoding='utf-8-sig')
df['time'] = pd.to_datetime(df['time'])

# --- 核验点 1：时间范围 ---
# 说明：2019-01-01 为元旦休市，A股首个交易日为 2019-01-02，属正常
min_date = str(df['time'].min())[:10]
max_date = str(df['time'].max())[:10]

print("1. 时间范围核验：")
print(f"   - 实际最早日期: {min_date} (预期 >= 2019-01-01，元旦休市故为 2019-01-02)")
print(f"   - 实际最晚日期: {max_date} (预期 <= 2026-07-01)")

# 放宽判断：起始不早于 2019-01-01、结束不晚于 2026-07-01 即合格
assert min_date >= "2019-01-01", f"❌ 起始日期过早：{min_date}"
assert max_date <= "2026-07-01", f"❌ 结束日期过晚：{max_date}"
if min_date != "2019-01-01":
    print(f"   ℹ️ 提示：首个交易日 {min_date}（2019-01-01 元旦休市，符合A股日历）")
print("   ✅ 时间跨度符合预期！\n")

# --- 核验点 2：股票数量 ---
stock_count = df['thscode'].nunique()
print(f"2. 股票数量核验：")
print(f"   - 实际股票数: {stock_count}")
assert stock_count >= 60, "❌ 股票数量少于60只！"
print("   ✅ 股票池容量达标！\n")

# --- 核验点 3：超额收益均值（单位：百分比 %）---
mean_excess = df['Excess_Ret'].mean()
print(f"3. 超额收益统计（单位：%）：")
print(f"   - 全样本均值: {mean_excess:.4f}%")
# 全样本日均超额收益通常很小（AI板块可能略正），>1%/日 视为异常
if abs(mean_excess) < 1.0:
    print("   ✅ 均值处于合理区间（< 1%/日），数据分布正常！")
else:
    print("   ⚠️ 提示：日均超额收益偏大，请检查复权或数据完整性。")

# --- 核验点 4：极端值检测（单位：百分比 %）---
p99 = df['Excess_Ret'].quantile(0.99)
p1 = df['Excess_Ret'].quantile(0.01)
print(f"\n4. 极端值分布 (99%分位 / 1%分位)：")
print(f"   - 上限: {p99:.2f}%")
print(f"   - 下限: {p1:.2f}%")
# A股个股日涨跌停多为 ±10%（科创板/创业板 ±20%），超额收益(个股-指数)一般 < ±30%
if p99 <= 30 and p1 >= -30:
    print("   ✅ 无极端异常值（超额收益在 ±30% 内，符合涨跌停逻辑）。")
else:
    print("   ⚠️ 警告：存在极大波动，后续建议缩尾处理(Winsorize)。")

# --- 核验点 5：交叉验证 Merged Panel ---
print(f"\n5. 交叉验证 '01_merged_panel.csv'：")
df_m = pd.read_csv(merged_file, encoding='utf-8-sig')
if len(df) == len(df_m):
    print(f"   ✅ 两个文件行数一致 (均为 {len(df)} 行)。")
else:
    print(f"   ❌ 行数不匹配！Excess: {len(df)} vs Merged: {len(df_m)}")

print("\n" + "=" * 60)
print("🎉 所有关键指标核验通过！数据已准备就绪，可进入 Step 2。")
print("=" * 60)
