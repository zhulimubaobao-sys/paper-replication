# -*- coding: utf-8 -*-
"""
功能：从Excel文件中自动提取100只股票代码，生成 stock_list.py
输入：AI股票100只测试样本（上游50+下游50）.xlsx
输出：04_code/stock_list.py
"""
import pandas as pd
from pathlib import Path

# ============================================================
# 第一步：设置路径（直接用你给的文件路径）
# ============================================================
EXCEL_FILE = Path(r"D:\thailand study\26_7_23paper\AI股票100只测试样本（上游50+下游50）.xlsx")
OUTPUT_FILE = Path(r"D:\thailand study\26_7_23paper\04_code\stock_list.py")

print("=" * 60)
print("🚀 开始从Excel生成 stock_list.py ...")
print(f"📂 Excel路径: {EXCEL_FILE}")

# 检查Excel文件是否存在
if not EXCEL_FILE.exists():
    print(f"❌ 找不到Excel文件！请确认路径正确：")
    print(f"   {EXCEL_FILE}")
    exit()

# ============================================================
# 第二步：读取Excel
# ============================================================
df = pd.read_excel(EXCEL_FILE)
print(f"✅ Excel读取成功，共 {len(df)} 行")
print(f"📋 Excel列名: {df.columns.tolist()}")

# 找到"股票代码"列
code_col = None
for col in df.columns:
    if '代码' in col:
        code_col = col
        break

if code_col is None:
    print("❌ 未找到'股票代码'列，请检查Excel")
    exit()

# 找到"产业链位置"列
position_col = None
for col in df.columns:
    if '产业链' in col or '位置' in col:
        position_col = col
        break

if position_col is None:
    print("❌ 未找到'产业链位置'列，请检查Excel")
    exit()

# ============================================================
# 第三步：提取上游和下游股票代码
# ============================================================
df['股票代码'] = df[code_col].astype(str).str.strip()
df['产业链位置'] = df[position_col].astype(str).str.strip()

upstream = df[df['产业链位置'] == '上游']['股票代码'].tolist()
downstream = df[df['产业链位置'] == '下游']['股票代码'].tolist()

print(f"\n📊 统计结果：")
print(f"   ✅ 上游股票: {len(upstream)} 只")
print(f"   ✅ 下游股票: {len(downstream)} 只")
print(f"   ✅ 总计: {len(upstream) + len(downstream)} 只")

if len(upstream) == 0 or len(downstream) == 0:
    print("⚠️ 警告：上游或下游股票数为0，请检查Excel中的分组是否正确")
    print(f"   产业链位置列的值: {df['产业链位置'].unique().tolist()}")

# ============================================================
# 第四步：生成 stock_list.py
# ============================================================
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""\n')
    f.write('stock_list.py — 100只AI概念股股票代码列表\n')
    f.write(f'自动生成时间: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
    f.write(f'上游: {len(upstream)} 只, 下游: {len(downstream)} 只\n')
    f.write('"""\n\n')

    # 写入上游列表
    f.write('# === 上游股票 ===\n')
    f.write('UPSTREAM_STOCKS = [\n')
    for i, code in enumerate(upstream):
        comma = ',' if i < len(upstream) - 1 else ''
        f.write(f'    "{code}"{comma}\n')
    f.write(']\n\n')

    # 写入下游列表
    f.write('# === 下游股票 ===\n')
    f.write('DOWNSTREAM_STOCKS = [\n')
    for i, code in enumerate(downstream):
        comma = ',' if i < len(downstream) - 1 else ''
        f.write(f'    "{code}"{comma}\n')
    f.write(']\n\n')

    # 写入全部列表
    f.write('# === 全部股票（合并） ===\n')
    f.write('ALL_STOCKS = UPSTREAM_STOCKS + DOWNSTREAM_STOCKS\n\n')

    # 写入测试代码（注意：这里去掉了 f 前缀，作为纯文本写入文件）
    f.write('if __name__ == "__main__":\n')
    f.write('    print(f"上游股票: {len(UPSTREAM_STOCKS)} 只")\n')
    f.write('    print(f"下游股票: {len(DOWNSTREAM_STOCKS)} 只")\n')
    f.write('    print(f"总计: {len(ALL_STOCKS)} 只")\n')

print(f"\n✅ 生成成功！")
print(f"📄 输出文件: {OUTPUT_FILE}")
print("\n请打开 04_code/stock_list.py 查看生成结果")