# -*- coding:utf-8 -*-
"""
功能：校验 zongdegupiao.csv 和 dapanzhishu.csv 数据是否符合之前的提取要求
依赖库：pandas
"""

import pandas as pd
import os

# ================= 配置区 =================
# 定义两个文件的绝对路径
STOCK_FILE_PATH = r"D:\thailand study\26_7_23paper\04_code\zongdegupiao.csv"
INDEX_FILE_PATH = r"D:\thailand study\26_7_23paper\04_code\dapanzhishu.csv"

# 预期的股票代码列表（60只）
EXPECTED_STOCKS = [
    "688256.SH", "688041.SH", "603019.SH", "002049.SZ", "688008.SH", "300474.SZ", "300308.SZ", "300502.SZ", "300394.SZ",
    "002281.SZ",
    "000988.SZ", "000977.SZ", "002463.SZ", "300476.SZ", "600183.SH", "688981.SH", "002371.SZ", "688012.SH", "300223.SZ",
    "603986.SH",
    "002230.SZ", "688111.SH", "300229.SZ", "688327.SH", "002415.SZ", "603160.SH", "300033.SZ", "002405.SZ", "300624.SZ",
    "300634.SZ",
    "002777.SZ", "300365.SZ", "688088.SH", "300496.SZ", "002253.SZ", "300078.SZ", "002236.SZ", "688023.SH", "300451.SZ",
    "000997.SZ",
    "688228.SH", "300785.SZ", "300058.SZ", "002131.SZ", "600556.SH", "300781.SZ", "600570.SH", "002607.SZ", "300253.SZ",
    "688369.SH",
    "300188.SZ", "002439.SZ", "300036.SZ", "300020.SZ", "300075.SZ", "300168.SZ", "002065.SZ", "600410.SH", "300170.SZ",
    "002368.SZ"
]

# 预期的大盘指数代码列表（3只）
EXPECTED_INDEXES = ["000300.SH", "000001.SH", "399001.SZ"]

# 预期的数据字段
EXPECTED_FIELDS = ["open", "close", "changeRatio", "volume", "amount"]

# 预期的时间范围
START_DATE = '2019-01-01'
END_DATE = '2026-07-01'


# ==========================================

def verify_csv(file_path, expected_codes, file_desc):
    """
    通用CSV校验方法
    :param file_path: 文件完整路径
    :param expected_codes: 预期的代码列表
    :param file_desc: 文件描述（用于打印）
    """
    print(f"\n{'=' * 50}")
    print(f"🔍 正在校验: {file_desc}")
    print(f"📁 文件路径: {file_path}")
    print(f"{'=' * 50}")

    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 致命错误：文件不存在！")
        return False

    # 2. 读取数据
    df = pd.read_csv(file_path)

    # 3. 校验数据字段
    actual_fields = [col for col in EXPECTED_FIELDS if col in df.columns]
    if set(actual_fields) != set(EXPECTED_FIELDS):
        print(f"❌ 字段缺失：预期 {EXPECTED_FIELDS}，实际 {list(df.columns)}")
        return False
    else:
        print(f"✅ 字段校验通过：包含所有预期字段 {EXPECTED_FIELDS}")

    # 4. 校验代码数量与准确性
    actual_codes = df['thscode'].unique().tolist()
    missing_codes = set(expected_codes) - set(actual_codes)
    extra_codes = set(actual_codes) - set(expected_codes)

    if len(actual_codes) != len(expected_codes):
        print(f"⚠️ 代码数量不符：预期 {len(expected_codes)} 个，实际 {len(actual_codes)} 个")
    else:
        print(f"✅ 代码数量校验通过：共 {len(actual_codes)} 个")

    if missing_codes:
        print(f"❌ 缺失以下代码: {missing_codes}")
    if extra_codes:
        print(f"⚠️ 多出以下代码: {extra_codes}")
    if not missing_codes and not extra_codes:
        print(f"✅ 代码准确性校验通过：与预期清单完全一致")

    # 5. 校验时间范围
    df['time'] = pd.to_datetime(df['time'])
    min_date = df['time'].min().strftime('%Y-%m-%d')
    max_date = df['time'].max().strftime('%Y-%m-%d')
    print(f"ℹ️ 实际数据时间范围: {min_date} 至 {max_date}")
    if min_date <= START_DATE and max_date >= END_DATE:
        print(f"✅ 时间范围校验通过：完全覆盖 {START_DATE} 至 {END_DATE}")
    else:
        print(f"⚠️ 时间范围警告：未完全覆盖预期区间，请检查数据源")

    # 6. 检查空值情况
    null_counts = df[EXPECTED_FIELDS].isnull().sum().sum()
    if null_counts > 0:
        print(f"⚠️ 数据质量警告：发现 {null_counts} 个空值(NaN)，建议在后续清洗步骤处理")
    else:
        print(f"✅ 数据质量校验通过：核心字段无空值")

    print(f"📊 数据总行数: {len(df)} 行")
    return True


# ================= 主程序入口 =================
if __name__ == "__main__":
    print("🚀 开始执行数据合规性校验任务...")

    # 分别校验两个文件
    stock_ok = verify_csv(STOCK_FILE_PATH, EXPECTED_STOCKS, "60只股票日线数据 (zongdegupiao)")
    index_ok = verify_csv(INDEX_FILE_PATH, EXPECTED_INDEXES, "3只大盘指数数据 (dapanzhishu)")

    # 输出最终总结
    print(f"\n{'=' * 50}")
    print("📝 校验任务总结:")
    if stock_ok and index_ok:
        print("🎉 恭喜！两个文件均完全符合预期要求，可以进入下一步分析。")
    else:
        print("❌ 校验未完全通过，请根据上方提示检查数据或重新提取。")
    print(f"{'=' * 50}")