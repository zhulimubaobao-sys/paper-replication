# -*- coding: utf-8 -*-
"""
==============================================================
iFinD 财务数据批量获取（所有季度：2019Q1 - 2026Q2）
账号：yxwgy037
功能：批量获取60只股票的所有季度财务数据
==============================================================
"""

from iFinDPy import *
import pandas as pd
import json
import os

# ============================================================
# 1. 登录iFinD
# ============================================================
print("=" * 60)
print("正在登录iFinD...")

username = "yxwgy037"
password = "124228Xf"

ths_login = THS_iFinDLogin(username, password)
if ths_login != 0:
    print(f"❌ 登录失败，错误码: {ths_login}")
    exit()
else:
    print("✅ 登录成功！")

# ============================================================
# 2. 定义所有股票代码
# ============================================================
print("\n定义股票代码列表...")

# 上游（20只）
UPSTREAM = [
    '688256.SH', '688041.SH', '603019.SH', '002049.SZ', '688008.SH',
    '300474.SZ', '300308.SZ', '300502.SZ', '300394.SZ', '002281.SZ',
    '000988.SZ', '000977.SZ', '002463.SZ', '300476.SZ', '600183.SH',
    '688981.SH', '002371.SZ', '688012.SH', '300223.SZ', '603986.SH'
]

# 中游（20只）
MIDSTREAM = [
    '002230.SZ', '688111.SH', '300229.SZ', '688327.SH', '002415.SZ',
    '603160.SH', '300033.SZ', '002405.SZ', '300624.SZ', '300634.SZ',
    '002777.SZ', '300365.SZ', '688088.SH', '300496.SZ', '002253.SZ',
    '300078.SZ', '002236.SZ', '688023.SH', '300451.SZ', '000997.SZ'
]

# 下游（20只）
DOWNSTREAM = [
    '688228.SH', '300785.SZ', '300058.SZ', '002131.SZ', '600556.SH',
    '300781.SZ', '600570.SH', '002607.SZ', '300253.SZ', '688369.SH',
    '300188.SZ', '002439.SZ', '300036.SZ', '300020.SZ', '300075.SZ',
    '300168.SZ', '002065.SZ', '600410.SH', '300170.SZ', '002368.SZ'
]

ALL_CODES = UPSTREAM + MIDSTREAM + DOWNSTREAM
CODES_STR = ','.join(ALL_CODES)

print(f"   ✅ 股票总数: {len(ALL_CODES)} 只")

# ============================================================
# 3. 定义所有季度参数
# ============================================================
print("\n生成季度参数...")

# 生成所有季度列表（2019Q1 到 2026Q2）
quarters = []
year = 2019
quarter = 1

# 季度结束日期映射
quarter_end_dates = {
    1: '0331',  # Q1 -> 3月31日
    2: '0630',  # Q2 -> 6月30日
    3: '0930',  # Q3 -> 9月30日
    4: '1231'  # Q4 -> 12月31日
}

while year < 2026 or (year == 2026 and quarter <= 2):
    end_date = f"{year}{quarter_end_dates[quarter]}"
    quarters.append(end_date)

    # 下一个季度
    quarter += 1
    if quarter > 4:
        quarter = 1
        year += 1

print(f"   ✅ 共 {len(quarters)} 个季度")
print(f"   📅 从: {quarters[0]} 到: {quarters[-1]}")


# ============================================================
# 4. 获取单季度数据的函数
# ============================================================
def get_quarter_data(stock_codes, quarter_end, indicators):
    """
    获取单个季度的财务数据

    参数:
        stock_codes: 逗号分隔的股票代码
        quarter_end: 季度结束日期（如 '20190630'）
        indicators: 指标字符串

    返回:
        DataFrame: 该季度的数据
    """
    # 日期参数格式：'20190630,100' 表示获取2019Q2数据，每次取100条
    date_param = f'{quarter_end},100'

    # 每个指标使用相同的日期参数
    date_params = ';'.join([date_param] * len(indicators.split(';')))

    # 调用接口
    result = THS_BD(
        stock_codes,
        indicators,
        date_params,
        'format:json'
    )

    if result.errorcode != 0:
        print(f"   ❌ 季度 {quarter_end} 获取失败！错误码: {result.errorcode}")
        return None

    raw_data = result.data

    # 处理bytes类型
    if isinstance(raw_data, bytes):
        try:
            json_str = raw_data.decode('utf-8')
            json_data = json.loads(json_str)

            # 检查是否有错误
            if json_data.get('errorcode', 0) != 0:
                print(f"   ❌ JSON返回错误: {json_data.get('errmsg', '未知错误')}")
                return None

            # 提取数据
            rows = []
            if 'tables' in json_data:
                for table in json_data['tables']:
                    thscode = table.get('thscode', '')
                    table_data = table.get('table', {})

                    row = {'thscode': thscode, 'report_date': quarter_end}
                    for key, values in table_data.items():
                        if isinstance(values, list) and len(values) > 0:
                            row[key] = values[0]
                        else:
                            row[key] = values
                    rows.append(row)

                return pd.DataFrame(rows)
            else:
                return None

        except Exception as e:
            print(f"   ❌ 解析失败: {str(e)[:100]}")
            return None
    else:
        return None


# ============================================================
# 5. 逐季度获取数据
# ============================================================
print("\n" + "=" * 60)
print("开始逐季度获取财务数据...")
print("=" * 60)

# 指标列表
INDICATORS = 'ths_total_assets_stock;ths_asset_liab_ratio_stock;ths_np_stock;ths_revenue_stock;ths_total_liab_stock;ths_total_owner_equity_stock'

# 存储所有数据
all_data = []
success_count = 0
fail_count = 0

for i, quarter_end in enumerate(quarters, 1):
    print(f"\n【{i}/{len(quarters)}】获取季度: {quarter_end}")

    # 分批获取（每批30只股票，避免请求过大）
    BATCH_SIZE = 30
    batch_dfs = []

    for j in range(0, len(ALL_CODES), BATCH_SIZE):
        batch_codes = ALL_CODES[j:j + BATCH_SIZE]
        codes_str = ','.join(batch_codes)

        df_batch = get_quarter_data(codes_str, quarter_end, INDICATORS)

        if df_batch is not None and not df_batch.empty:
            batch_dfs.append(df_batch)

    # 合并批次
    if batch_dfs:
        df_quarter = pd.concat(batch_dfs, ignore_index=True)
        all_data.append(df_quarter)
        success_count += 1
        print(f"   ✅ 成功获取 {len(df_quarter)} 条记录")
    else:
        fail_count += 1
        print(f"   ❌ 该季度无数据")

print(f"\n   ✅ 成功: {success_count} 个季度")
print(f"   ❌ 失败: {fail_count} 个季度")

# ============================================================
# 6. 合并所有季度数据
# ============================================================
print("\n" + "=" * 60)
print("合并所有季度数据...")
print("=" * 60)

if not all_data:
    print("❌ 没有获取到任何数据！")
    THS_iFinDLogout()
    exit()

df_all = pd.concat(all_data, ignore_index=True)
print(f"   ✅ 合并完成！总记录数: {len(df_all):,}")

# ============================================================
# 7. 处理数据
# ============================================================
print("\n处理数据...")

# 重命名列为中文
col_mapping = {
    'ths_total_assets_stock': '资产总计',
    'ths_asset_liab_ratio_stock': '资产负债率',
    'ths_np_stock': '净利润',
    'ths_revenue_stock': '营业收入',
    'ths_total_liab_stock': '负债合计',
    'ths_total_owner_equity_stock': '所有者权益合计'
}

for old_name, new_name in col_mapping.items():
    if old_name in df_all.columns:
        df_all.rename(columns={old_name: new_name}, inplace=True)


# 添加层级信息
def get_layer(code):
    if code in UPSTREAM:
        return '上游'
    elif code in MIDSTREAM:
        return '中游'
    elif code in DOWNSTREAM:
        return '下游'
    else:
        return '未知'


if 'thscode' in df_all.columns:
    df_all['Layer'] = df_all['thscode'].apply(get_layer)

print(f"   ✅ 数据处理完成")

# ============================================================
# 8. 数据概览
# ============================================================
print("\n" + "=" * 60)
print("数据概览")
print("=" * 60)

print(f"   📊 总记录数: {len(df_all):,}")

if 'thscode' in df_all.columns:
    print(f"   📊 股票数量: {df_all['thscode'].nunique()}")

if 'report_date' in df_all.columns:
    print(f"   📅 时间范围: {df_all['report_date'].min()} 至 {df_all['report_date'].max()}")
    print(f"   📅 季度数: {df_all['report_date'].nunique()}")

print(f"\n   📋 数据列:")
for col in df_all.columns:
    print(f"      • {col}")

print(f"\n   前5行数据:")
print(df_all.head())

# ============================================================
# 9. 保存数据
# ============================================================
print("\n保存数据...")

output_dir = "D:/thailand study/26_7_23paper/01_raw_data"
os.makedirs(output_dir, exist_ok=True)

# 保存合并文件
output_path = os.path.join(output_dir, "financial_data_all_quarters.csv")
df_all.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"   ✅ 合并数据已保存: {output_path}")

# 按层级保存
if 'Layer' in df_all.columns:
    for layer in ['上游', '中游', '下游']:
        layer_df = df_all[df_all['Layer'] == layer]
        if len(layer_df) > 0:
            layer_path = os.path.join(output_dir, f"financial_data_{layer}_all_quarters.csv")
            layer_df.to_csv(layer_path, index=False, encoding='utf-8-sig')
            print(f"   ✅ {layer}数据已保存: {layer_path}")

# 按季度保存
if 'report_date' in df_all.columns:
    for quarter in sorted(df_all['report_date'].unique()):
        quarter_df = df_all[df_all['report_date'] == quarter]
        if len(quarter_df) > 0:
            quarter_path = os.path.join(output_dir, f"quarterly", f"financial_{quarter}.csv")
            os.makedirs(os.path.dirname(quarter_path), exist_ok=True)
            quarter_df.to_csv(quarter_path, index=False, encoding='utf-8-sig')
    print(f"   ✅ 各季度数据已保存")

# ============================================================
# 10. 统计摘要
# ============================================================
print("\n" + "=" * 60)
print("统计摘要")
print("=" * 60)

if 'report_date' in df_all.columns:
    print(f"\n各季度记录数:")
    quarter_counts = df_all.groupby('report_date').size()
    for quarter, count in quarter_counts.items():
        print(f"   • {quarter}: {count:,} 条")

numeric_cols = ['资产总计', '资产负债率', '净利润', '营业收入', '负债合计', '所有者权益合计']
numeric_cols = [col for col in numeric_cols if col in df_all.columns]

if numeric_cols:
    print(f"\n财务指标统计:")
    for col in numeric_cols:
        print(f"   • {col}:")
        print(f"     均值: {df_all[col].mean():.2e}")
        print(f"     中位数: {df_all[col].median():.2e}")

# ============================================================
# 11. 退出登录
# ============================================================
print("\n登出iFinD...")
THS_iFinDLogout()
print("   ✅ 已登出")

print("\n" + "=" * 60)
print("✅ 全部完成！")
print("=" * 60)
print(f"\n📁 输出文件:")
print(f"   • 合并所有季度: {output_path}")
print(f"   • 各季度文件: {output_dir}/quarterly/")
print("=" * 60)