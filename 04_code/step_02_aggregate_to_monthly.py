# -*- coding: utf-8 -*-
"""
==============================================================
步骤 2：日度数据聚合为月度面板（iFinD/本管线适配版 · 修正版）
==============================================================
功能：
1. 读取步骤1输出的日度超额收益面板（01_excess_return_panel.csv）
2. 按【股票 thscode + 年月 year_month】分组聚合
3. 计算月度累计收益率、月度累计超额收益、月末收盘价、月内波动率
4. 输出月度面板（02_monthly_panel.csv），供后续 DID 回归使用

关键修正：
A. Ret / Excess_Ret / Index_Ret 均为【百分比】(0.05 即 0.05%)，
   复利必须用 (1 + x/100) 再 -1，再 ×100 转回百分比，否则月收益会被放大几十倍。
B. year_month 保持 step_1 的格式 "2019-01"（字符串），
   且【不要】在 apply 返回里重复返回 year_month，
   否则 groupby.reset_index 会因重复列名报错（cannot insert year_month）。
C. 摘要的"时间范围"用 year_month 的最小/最大，避免 year 与 month 各自取极值导致的
   错误拼接（如把 2019-01 到 2026-12 拼出来）。
==============================================================
"""

# 1. 导入必要的库
import pandas as pd
import numpy as np
import os

# 2. 设置文件路径
base_dir = r"D:\thailand study\26_7_23paper"

# 输入文件（步骤1的输出）
input_file = os.path.join(base_dir, "02_processed_data", "01_excess_return_panel.csv")

# 输出文件
output_dir = os.path.join(base_dir, "02_processed_data")
output_file = os.path.join(output_dir, "02_monthly_panel.csv")
os.makedirs(output_dir, exist_ok=True)  # 输出目录不存在则自动创建

# 3. 读取数据
print("=" * 60)
print("步骤 2：日度数据聚合为月度面板")
print("=" * 60)

print(f"\n[1/4] 正在读取日度面板: {input_file}")
df = pd.read_csv(input_file, encoding='utf-8-sig')
df['time'] = pd.to_datetime(df['time'])   # 日期列名为 time（非 Trddt）
print(f"      ✓ 读取成功！总行数: {len(df):,}, 股票数: {df['thscode'].nunique()}")

# 健壮性：若 year/month/year_month 缺失则自动从 time 生成（保持 "2019-01" 格式）
if 'year_month' not in df.columns:
    df['year_month'] = df['time'].dt.to_period('M').astype(str)
if 'year' not in df.columns:
    df['year'] = df['time'].dt.year
if 'month' not in df.columns:
    df['month'] = df['time'].dt.month

# 4. 数据验证：检查是否有缺失的关键字段
required_cols = ['thscode', 'time', 'year', 'month', 'year_month',
                 'Ret', 'Excess_Ret', 'close', 'Index_Ret']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise KeyError(f"缺少必要字段: {missing_cols}，请检查步骤1的输出文件。")

# 5. 核心操作：按股票+年月分组聚合
print("\n[2/4] 正在进行月度聚合计算...")

def aggregate_monthly(group):
    """
    对单只股票的月度数据进行聚合
    参数 group: 某只股票在某个月的所有日度记录
    返回: 该月的一条汇总记录（pd.Series）
    说明：
      - Ret/Excess_Ret/Index_Ret 均为百分比，复利须 ÷100；
      - year/month 从 time 推导，不依赖 groupby 键列，避免 include_groups 差异；
      - 【不返回 year_month】，它本就是分组键，reset_index 后会自动成为列。
    """
    group = group.sort_values('time')  # 按日期排序，保证累计收益顺序正确

    # 月度累计收益（日收益几何连乘）：(1+r/100)^n - 1，最后 ×100 转回百分比
    ret_monthly = ((1 + group['Ret'] / 100).prod() - 1) * 100
    excess_monthly = ((1 + group['Excess_Ret'] / 100).prod() - 1) * 100
    hs300_monthly = ((1 + group['Index_Ret'] / 100).prod() - 1) * 100

    # 月末收盘价（取当月最后一个交易日的收盘价，列名 close）
    clsprc_end = group['close'].iloc[-1]

    # 月内波动率（超额收益的日度标准差）
    volatility = group['Excess_Ret'].std()

    # 交易天数
    trading_days = len(group)

    # 从 time 推导年月信息（分组内所有记录一致）
    year_val = group['time'].dt.year.iloc[0]
    month_val = group['time'].dt.month.iloc[0]

    return pd.Series({
        'year': year_val,
        'month': month_val,
        'Ret_monthly': ret_monthly,
        'Excess_Ret_monthly': excess_monthly,
        'Clsprc_end': clsprc_end,
        'Volatility': volatility,
        'Trading_Days': trading_days,
        'HS300_Ret_monthly': hs300_monthly
    })

# 执行分组聚合：按 thscode + year_month 分组；year_month 随 reset_index 自动成为列
df_monthly = df.groupby(['thscode', 'year_month'], group_keys=True).apply(aggregate_monthly).reset_index()

print(f"      ✓ 聚合完成！月度面板行数: {len(df_monthly):,}")

# 6. 数据质量检查
print("\n[3/4] 正在执行数据质量检查...")

# 6.1 极端月度收益（>50%或<-50%）：Ret_monthly 单位是百分比
extreme_ret = df_monthly[(df_monthly['Ret_monthly'] > 50) | (df_monthly['Ret_monthly'] < -50)]
if len(extreme_ret) > 0:
    print(f"      ⚠️ 发现 {len(extreme_ret)} 个极端月度收益观测值（>50%或<-50%）")
    print(f"         这些 AI/半导体股在牛市单月翻倍属正常，建议保留；")
    print(f"         若后续回归需稳健，可对此列做缩尾(Winsorize)处理。")
else:
    print(f"      ✓ 未发现极端月度收益（均在 ±50% 以内）")

# 6.2 每只股票覆盖的月数
stock_month_count = df_monthly.groupby('thscode').size()
min_months = stock_month_count.min()
max_months = stock_month_count.max()
print(f"      ✓ 每只股票月度数: 最少 {min_months} 个月, 最多 {max_months} 个月")

# 6.3 月度超额收益均值
mean_excess_monthly = df_monthly['Excess_Ret_monthly'].mean()
print(f"      ✓ 月度超额收益全样本均值: {mean_excess_monthly:.4f}%")

# 7. 保存月度面板
print("\n[4/4] 正在保存月度面板...")

# 按股票和时间排序
df_monthly = df_monthly.sort_values(['thscode', 'year', 'month'])
df_monthly.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"      ✓ 月度面板已保存: {output_file}")

# 8. 输出统计摘要
print("\n" + "=" * 60)
print("✅ 步骤 2 执行完成！数据摘要如下：")
print("=" * 60)
print(f"   • 股票数量: {df_monthly['thscode'].nunique():,} 只")
# 直接用 year_month 字符串取最小/最大，避免 year 与 month 各自取极值的错误拼接
print(f"   • 时间范围: {df_monthly['year_month'].min()} 至 {df_monthly['year_month'].max()}")
print(f"   • 总观测值: {len(df_monthly):,} 条 (股票-月记录)")
print(f"   • 月度超额收益均值: {df_monthly['Excess_Ret_monthly'].mean():.4f}%")
print(f"   • 月度超额收益标准差: {df_monthly['Excess_Ret_monthly'].std():.4f}%")
print("=" * 60)
print("  下一步请运行：step_03_build_did_variables.py")
print("=" * 60)
