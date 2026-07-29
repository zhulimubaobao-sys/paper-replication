# -*- coding: utf-8 -*-
"""
================================================================================
诊断脚本：检查日度原始数据的列名和格式
项目根目录：26_7_23paper/
输入：01_raw_data/stock/zongdegupiao.csv, 01_raw_data/stock/dapanzhishu.csv
输出：在终端打印数据结构，帮助确认映射关系
================================================================================
"""

import pandas as pd
import os

# ============================================================================
# 1. 路径配置（使用您提供的准确路径）
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

# 文件路径（修正为正确的子目录）
STOCK_PATH = os.path.join(BASE_DIR, '01_raw_data', 'stock', 'zongdegupiao.csv')
INDEX_PATH = os.path.join(BASE_DIR, '01_raw_data', 'stock', 'dapanzhishu.csv')

print("=" * 70)
print("【数据侦查报告】")
print("=" * 70)
print(f"项目根目录：{BASE_DIR}")
print(f"个股文件：{STOCK_PATH}")
print(f"指数文件：{INDEX_PATH}")
print("=" * 70)

# ============================================================================
# 2. 检查个股文件
# ============================================================================
print("\n【1/2】个股文件 (zongdegupiao.csv)：")

try:
    # 检查文件是否存在
    if not os.path.exists(STOCK_PATH):
        print(f"   ❌ 文件不存在：{STOCK_PATH}")
        print(f"   💡 请确认文件是否在 '01_raw_data/stock/' 目录下")
    else:
        # 读取前10行查看数据结构
        df_stock = pd.read_csv(STOCK_PATH, encoding='utf-8-sig', nrows=10)
        print(f"   ✅ 读取成功！")
        print(f"\n   📋 列名列表：{df_stock.columns.tolist()}")
        print(f"\n   📊 前5行数据预览：")
        print(df_stock.head())
        print(f"\n   📊 数据形状（前10行）：{df_stock.shape}")

        # 检查日期列格式
        if 'time' in df_stock.columns:
            print(f"\n   📅 日期列示例：{df_stock['time'].head().tolist()}")
        elif '交易日期' in df_stock.columns:
            print(f"\n   📅 日期列示例：{df_stock['交易日期'].head().tolist()}")

        # 检查是否有股票代码列
        code_cols = [col for col in df_stock.columns if 'code' in col.lower() or 'stock' in col.lower() or 'thscode' in col.lower()]
        if code_cols:
            print(f"\n   🏷️ 股票代码列：{code_cols}")
            print(f"      示例值：{df_stock[code_cols[0]].head().tolist()}")

        # 检查收益率相关列
        ret_cols = [col for col in df_stock.columns if 'ret' in col.lower() or 'return' in col.lower() or '收益' in col]
        if ret_cols:
            print(f"\n   📈 收益率列：{ret_cols}")

        print(f"\n   📊 文件总行数（估算）：{sum(1 for _ in open(STOCK_PATH, encoding='utf-8-sig')) - 1:,}")

except Exception as e:
    print(f"   ❌ 读取失败：{e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 3. 检查指数文件
# ============================================================================
print("\n【2/2】大盘指数文件 (dapanzhishu.csv)：")

try:
    if not os.path.exists(INDEX_PATH):
        print(f"   ❌ 文件不存在：{INDEX_PATH}")
        print(f"   💡 请确认文件是否在 '01_raw_data/stock/' 目录下")
    else:
        df_index = pd.read_csv(INDEX_PATH, encoding='utf-8-sig', nrows=10)
        print(f"   ✅ 读取成功！")
        print(f"\n   📋 列名列表：{df_index.columns.tolist()}")
        print(f"\n   📊 前5行数据预览：")
        print(df_index.head())
        print(f"\n   📊 数据形状（前10行）：{df_index.shape}")

        # 检查日期列格式
        if 'time' in df_index.columns:
            print(f"\n   📅 日期列示例：{df_index['time'].head().tolist()}")
        elif '交易日期' in df_index.columns:
            print(f"\n   📅 日期列示例：{df_index['交易日期'].head().tolist()}")

        print(f"\n   📊 文件总行数（估算）：{sum(1 for _ in open(INDEX_PATH, encoding='utf-8-sig')) - 1:,}")

except Exception as e:
    print(f"   ❌ 读取失败：{e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 4. 诊断结论
# ============================================================================
print("\n" + "=" * 70)
print("【诊断结论】")
print("=" * 70)
print("\n✅ 请将以上输出的列名信息复制到对话中。")
print("\n关键信息需要确认：")
print("   1. 个股文件的列名列表（特别是：股票代码、日期、收益率、收盘价）")
print("   2. 指数文件的列名列表（特别是：日期、指数点位）")
print("   3. 日期列的名称（'time' 还是 '交易日期' 或其他）")
print("   4. 股票代码列的名称")
print("=" * 70)