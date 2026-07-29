# -*- coding: utf-8 -*-
"""
功能：读取 Book1.xlsx（20只股票日度数据），合并产业链位置和AI_exposure
输入：01_raw_data/stock/stock_returns_raw.xlsx
输出：02_intermediate_data/stock_with_meta.csv
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"D:\thailand study\26_7_23paper")
INPUT_FILE = BASE_DIR / "01_raw_data" / "stock" / "stock_returns_raw.xlsx"
OUTPUT_DIR = BASE_DIR / "02_intermediate_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "stock_with_meta.csv"

print("=" * 60)
print("开始执行 01_data_cleaning.py ...")
print(f"输入文件: {INPUT_FILE}")

# 1. 检查文件是否存在
if not INPUT_FILE.exists():
    print(f"❌ 找不到文件: {INPUT_FILE}")
    print("请确保 Book1.xlsx 已放到 01_raw_data/stock/ 文件夹下")
    exit()

# 2. 读取Excel
df = pd.read_excel(INPUT_FILE)
print(f"✅ 读取成功，共 {len(df)} 行，{df['thscode'].nunique()} 只股票")

# 3. 查看列名确认
print(f"列名: {df.columns.tolist()}")

# 4. 标准列名（你的Excel列名是：time, thscode, changeRatio 等）
df.rename(columns={
    'time': '日期',
    'thscode': '股票代码',
    'open': '开盘价',
    'close': '收盘价',
    'changeRatio': '涨跌幅',
    'volume': '成交量'
}, inplace=True, errors='ignore')

# 5. 日期格式化
df['日期'] = pd.to_datetime(df['日期'])

# 6. 删除涨跌幅为空的行
df = df.dropna(subset=['涨跌幅'])

# 7. 检查产业链位置列是否存在
if '产业链位置' not in df.columns:
    print("❌ Excel中缺少'产业链位置'列，请确认已添加")
    exit()

if 'AI_exposure' not in df.columns:
    print("❌ Excel中缺少'AI_exposure'列，请确认已添加")
    exit()

# 8. 统计
print(f"\n📊 数据统计:")
print(f"  上游股票: {len(df[df['产业链位置'] == '上游']['股票代码'].unique())} 只")
print(f"  下游股票: {len(df[df['产业链位置'] == '下游']['股票代码'].unique())} 只")
print(f"  时间范围: {df['日期'].min()} 至 {df['日期'].max()}")

# 9. 保存中间数据
df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print(f"\n✅ 清洗完成！输出文件: {OUTPUT_FILE}")
print(f"   总行数: {len(df)}")