# -*- coding: utf-8 -*-
"""
补救脚本：生成 validation_log.csv
功能：对清洗后的财务数据进行全面核验，生成标准化的校验日志
"""

import pandas as pd
import os

# ============================================================================
# 1. 路径配置（使用绝对路径，修复路径错误）
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

# 输入路径
INPUT_PATH = os.path.join(BASE_DIR, '03_clean_data', 'financial_panel_clean.csv')

# 输出路径
OUTPUT_PATH = os.path.join(BASE_DIR, '05_output', 'validation_log.csv')

print("=" * 70)
print("生成财务数据核验日志 (validation_log.csv)")
print("=" * 70)
print(f"输入文件：{INPUT_PATH}")
print(f"输出文件：{OUTPUT_PATH}")
print("=" * 70)

# ============================================================================
# 2. 读取数据
# ============================================================================
print("\n【1/3】读取清洗后的财务面板...")

df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')

print(f"   ✅ 总行数：{len(df):,}")
print(f"   ✅ 股票数量：{df['thscode'].nunique()}")
print(f"   ✅ 季度数量：{df['year_quarter'].nunique()}")

# ============================================================================
# 3. 执行各项核验
# ============================================================================
print("\n【2/3】执行数据核验...")

# 核验1：关键变量空值
null_asset = df['资产总计_亿'].isna().sum()
null_profit = df['净利润_亿'].isna().sum()
null_revenue = df['营业收入_亿'].isna().sum()
null_size = df['Size'].isna().sum()
null_roa = df['ROA'].isna().sum()
null_leverage = df['Leverage'].isna().sum()
total_null = null_asset + null_profit + null_revenue + null_size + null_roa + null_leverage

# 核验2：资产负债率异常（Leverage范围0-1.5）
invalid_lev = ((df['Leverage'] < 0) | (df['Leverage'] > 1.5)).sum()

# 核验3：ROA异常
extreme_roa = ((df['ROA'] > 1) | (df['ROA'] < -1)).sum()

# 核验4：Size异常
invalid_size = ((df['Size'] < 0) | (df['Size'] > 30)).sum()

# 核验5：观测值不足的公司（<20个季度）
firm_counts = df.groupby('thscode').size()
low_count_firms = (firm_counts < 20).sum()

# 核验6：各层级覆盖情况
layer_counts = df.groupby('Layer').size()

# 核验7：Equity_Multiplier异常
invalid_equity = ((df['Equity_Multiplier'] < 1) | (df['Equity_Multiplier'] > 10)).sum()

# 核验8：Log_Revenue异常
invalid_log_rev = df['Log_Revenue'].isna().sum()

# ============================================================================
# 4. 汇总结果
# ============================================================================
print("\n【3/3】生成核验结果...")

validation_log = pd.DataFrame({
    '核验项': [
        '关键变量空值总数（资产/净利润/营业收入/Size/ROA/Leverage）',
        '资产负债率超出0-150%范围的记录数',
        'ROA > 100% 或 < -100% 的记录数',
        'Size < 0 或 > 30 的记录数',
        '观测值少于20个季度的公司数',
        '权益乘数 < 1 或 > 10 的记录数',
        'Log_Revenue 缺失数'
    ],
    '检测结果': [
        total_null,
        invalid_lev,
        extreme_roa,
        invalid_size,
        low_count_firms,
        invalid_equity,
        invalid_log_rev
    ],
    '通过标准': [
        '应为0',
        '应为0',
        '应为0',
        '应为0',
        '应为0',
        '应为0',
        '应为0'
    ],
    '是否通过': [
        '✅ 通过' if total_null == 0 else '❌ 失败',
        '✅ 通过' if invalid_lev == 0 else '❌ 失败',
        '✅ 通过' if extreme_roa == 0 else '❌ 失败',
        '✅ 通过' if invalid_size == 0 else '❌ 失败',
        '✅ 通过' if low_count_firms == 0 else '❌ 失败',
        '✅ 通过' if invalid_equity == 0 else '❌ 失败',
        '✅ 通过' if invalid_log_rev == 0 else '❌ 失败'
    ]
})

# ============================================================================
# 5. 保存
# ============================================================================
validation_log.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
print(f"\n   ✅ validation_log.csv 已生成：{OUTPUT_PATH}")

print("\n" + "=" * 70)
print("核验结果汇总")
print("=" * 70)
print(validation_log.to_string(index=False))
print("=" * 70)

# ============================================================================
# 6. 额外统计信息
# ============================================================================
print("\n📊 额外统计信息：")
print(f"   • 总观测值：{len(df):,}")
print(f"   • 股票数量：{df['thscode'].nunique()}")
print(f"   • 季度数量：{df['year_quarter'].nunique()}")
print(f"   • 各层级分布：")
for layer, count in layer_counts.items():
    print(f"      - {layer}：{count} 条")

print("\n   ✅ 全部完成！")