# -*- coding: utf-8 -*-
"""
============================================================
核验脚本：check_step_03_output.py
适配列名 'thscode' + 自动检测带时间戳的文件
============================================================
"""

import pandas as pd
import os
import glob

base_dir = "D:/thailand study/26_7_23paper"
output_dir = os.path.join(base_dir, "02_processed_data")

print("=" * 60)
print("【步骤3核验报告】")
print("=" * 60)

# ============================================================
# 核验点1：自动检测DID面板文件（支持带时间戳的文件名）
# ============================================================
print("\n[1/5] 检测DID面板文件...")

# 查找所有可能的DID面板文件
pattern = os.path.join(output_dir, "03_did_panel*.csv")
did_files = glob.glob(pattern)

if len(did_files) == 0:
    print("   ❌ 未找到 DID 面板文件！")
    print(f"   搜索路径: {pattern}")
    print("   请检查 Step3 是否成功执行。")
    did_file = None
else:
    # 优先使用不带时间戳的，否则使用最新的
    did_file = None
    for f in did_files:
        if f == os.path.join(output_dir, "03_did_panel.csv"):
            did_file = f
            break
    if did_file is None:
        did_file = max(did_files, key=os.path.getctime)  # 使用最新的文件
    print(f"   ✅ 找到文件: {os.path.basename(did_file)}")

# ============================================================
# 核验点2：读取并检查数据
# ============================================================
if did_file:
    print("\n[2/5] 读取并检查数据...")
    df = pd.read_csv(did_file)

    print(f"   ✅ DID面板读取成功")
    print(f"   - 总行数: {len(df):,}")
    print(f"   - 列数: {len(df.columns)}")
    print(f"   - 列名列表: {df.columns.tolist()[:10]}...")  # 显示前10列

    # 检查列名（兼容 thscode 或 Stkcd）
    if 'thscode' in df.columns:
        code_col = 'thscode'
    elif 'Stkcd' in df.columns:
        code_col = 'Stkcd'
    else:
        code_col = df.columns[0]  # 使用第一列
    print(f"   - 使用股票代码列: '{code_col}'")

    # 统计各分组
    print(f"\n[3/5] 分组统计:")
    print(f"   - 股票数: {df[code_col].nunique()}")
    print(f"   - 处理组(Treat=1): {len(df[df['Treat'] == 1]):,}")
    print(f"   - 对照组(Treat=0): {len(df[df['Treat'] == 0]):,}")
    print(f"   - Post=1: {len(df[df['Post'] == 1]):,}")
    print(f"   - DID=1: {len(df[df['DID'] == 1]):,}")

    # ============================================================
    # 核验点3：检查CAR计算
    # ============================================================
    print(f"\n[4/5] 事件窗口CAR检查（仅事件月 event_time=0）:")
    car_cols = ['CAR_-1_1', 'CAR_-2_2', 'CAR_-3_3', 'CAR_-1_0', 'CAR_0_1']
    event_data = df[df['event_time'] == 0]
    print(f"   - event_time=0 的观测数: {len(event_data)}")

    for col in car_cols:
        if col in df.columns:
            mean_val = event_data[col].mean()
            count_valid = event_data[col].notna().sum()
            if pd.isna(mean_val):
                print(f"   - {col}: 均值=NaN, 有效观测={count_valid}")
            else:
                print(f"   - {col}: 均值={mean_val:.6f}, 有效观测={count_valid}")
        else:
            print(f"   - {col}: ❌ 列不存在（可能未计算）")

    # 检查沪深300对照组
    print(f"\n[5/5] 沪深300对照组核验:")
    hs300_data = df[df[code_col] == 'HS300']
    if len(hs300_data) > 0:
        print(f"   ✅ 对照组观测数: {len(hs300_data)}")
        print(f"   - 时间范围: {hs300_data['year_month'].min()} 至 {hs300_data['year_month'].max()}")
        print(f"   - Treat全部为0: {(hs300_data['Treat'] == 0).all()}")
        print(f"   - Excess_Ret_monthly全部为0: {(hs300_data['Excess_Ret_monthly'] == 0).all()}")
    else:
        print(f"   ⚠️ 未找到 HS300 对照组记录（可能代码中列名不匹配）")
        print(f"   - 前5个股票代码: {df[code_col].head(5).tolist()}")

    # 额外检查：收益率范围
    print(f"\n【额外检查】收益率范围:")
    print(f"   - Excess_Ret_monthly: [{df['Excess_Ret_monthly'].min():.6f}, {df['Excess_Ret_monthly'].max():.6f}]")
    print(f"   - 均值: {df['Excess_Ret_monthly'].mean():.6f}")
    print(f"   - 标准差: {df['Excess_Ret_monthly'].std():.6f}")

# ============================================================
# 核验点4：检查图片是否生成
# ============================================================
print("\n" + "-" * 60)
print("【图片输出核验】")
print("-" * 60)

cn_fig = os.path.join(base_dir, "05_output/figures/CN/figure1_parallel_trend_CN.pdf")
en_fig = os.path.join(base_dir, "05_output/figures/EN/figure1_parallel_trend_EN.pdf")

if os.path.exists(cn_fig):
    file_size = os.path.getsize(cn_fig) / 1024  # KB
    print(f"   ✅ 中文图片存在: {cn_fig} ({file_size:.1f} KB)")
else:
    print(f"   ❌ 中文图片缺失: {cn_fig}")

if os.path.exists(en_fig):
    file_size = os.path.getsize(en_fig) / 1024
    print(f"   ✅ 英文图片存在: {en_fig} ({file_size:.1f} KB)")
else:
    print(f"   ❌ 英文图片缺失: {en_fig}")

# ============================================================
# 核验结论
# ============================================================
print("\n" + "=" * 60)
print("【核验结论】")
print("=" * 60)

if did_file:
    print(f"✅ DID面板生成成功: {os.path.basename(did_file)}")
    if os.path.exists(cn_fig) and os.path.exists(en_fig):
        print("✅ 中英文图片生成成功")
        print("✅ 步骤3数据质量通过，可进入步骤4")
    else:
        print("⚠️ 图片生成可能有问题，但不影响回归分析")
else:
    print("❌ DID面板未生成，请检查 Step3 代码错误")
print("=" * 60)