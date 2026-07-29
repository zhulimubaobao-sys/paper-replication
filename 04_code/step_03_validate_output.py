# -*- coding: utf-8 -*-
"""
================================================================================
核验脚本：验证步骤三的所有输出（修正版）
适配中英文双版本图片（CN/EN 子文件夹）
================================================================================
"""

import pandas as pd
import os
from datetime import datetime

BASE_DIR = r"D:/thailand study/26_7_23paper"
TABLES_DIR = os.path.join(BASE_DIR, '05_output', 'tables')
FIGURES_DIR = os.path.join(BASE_DIR, '05_output', 'figures')

print("=" * 70)
print("步骤三输出结果核验")
print("=" * 70)
print(f"核验时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================================================
# 核验1：检查所有文件是否存在（适配子文件夹）
# ============================================================================
print("\n【核验1】文件完整性检查")

# 表格文件
table_files = [
    'table1_descriptive.csv',
    'table2_did_main.csv',
    'table3_mechanism.csv',
    'did_regression_full_log.txt'
]

# 图片文件（位于子文件夹）
figure_files = {
    'CN': 'figure1_parallel_trend_CN.png',
    'EN': 'figure1_parallel_trend_EN.png',
    'CN': 'figure2_layer_comparison_CN.png',  # 注意：CN 和 EN 各两张，这里用列表方便
}
# 改用列表
figure_files_list = [
    ('CN', 'figure1_parallel_trend_CN.png'),
    ('EN', 'figure1_parallel_trend_EN.png'),
    ('CN', 'figure2_layer_comparison_CN.png'),
    ('EN', 'figure2_layer_comparison_EN.png'),
]

all_passed = True

# 检查表格
for f in table_files:
    file_path = os.path.join(TABLES_DIR, f)
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"  {status} {f}")
    if not exists:
        all_passed = False

# 检查图片
for lang, fname in figure_files_list:
    file_path = os.path.join(FIGURES_DIR, lang, fname)
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"  {status} {fname} (in {lang}/)")
    if not exists:
        all_passed = False

# ============================================================================
# 核验2：Table 2 回归结果
# ============================================================================
print("\n【核验2】DID回归结果验证")

table2_path = os.path.join(TABLES_DIR, 'table2_did_main.csv')
df = pd.read_csv(table2_path, encoding='utf-8-sig')

print("\n【Table 2 完整结果】")
print("-" * 70)

# 核心变量
core_vars = ['Post', 'Post_x_Upstream']
for model in ['全样本', '上游', '下游', '交互项']:
    for var in core_vars:
        row = df[(df['Model'] == model) & (df['Variable'] == var)]
        if len(row) > 0:
            coef = row.iloc[0]['Coefficient']
            pval = row.iloc[0]['p_value']
            stars = '***' if pval < 0.01 else ('**' if pval < 0.05 else ('*' if pval < 0.1 else ''))
            print(f"  {model} | {var}: {coef:.4f} {stars} (p={pval:.4f})")

# ============================================================================
# 核验3：H1假设检验
# ============================================================================
print("\n【核验3】H1假设检验")

up_row = df[(df['Model'] == '上游') & (df['Variable'] == 'Post')]
down_row = df[(df['Model'] == '下游') & (df['Variable'] == 'Post')]
interact_row = df[(df['Model'] == '交互项') & (df['Variable'] == 'Post_x_Upstream')]

results = []

if len(up_row) > 0:
    up_p = up_row.iloc[0]['p_value']
    up_coef = up_row.iloc[0]['Coefficient']
    up_pass = up_p < 0.1 and up_coef > 0
    results.append(("H1a: 上游Post系数显著为正", "✅ 通过" if up_pass else "❌ 失败"))
else:
    results.append(("H1a: 上游Post系数显著为正", "❌ 未找到"))

if len(down_row) > 0:
    down_p = down_row.iloc[0]['p_value']
    down_coef = down_row.iloc[0]['Coefficient']
    down_pass = down_p >= 0.1
    results.append(("H1b: 下游Post系数不显著", "✅ 通过" if down_pass else "❌ 失败"))
else:
    results.append(("H1b: 下游Post系数不显著", "❌ 未找到"))

if len(interact_row) > 0:
    interact_p = interact_row.iloc[0]['p_value']
    interact_coef = interact_row.iloc[0]['Coefficient']
    interact_pass = interact_p < 0.1 and interact_coef > 0
    results.append(("H1c: 交互项Post×上游显著为正", "✅ 通过" if interact_pass else "❌ 失败"))
else:
    results.append(("H1c: 交互项Post×上游显著为正", "❌ 未找到"))

# 方向一致性
if len(up_row) > 0 and len(down_row) > 0:
    direction_pass = up_coef > down_coef
    results.append(("H1d: 上游系数 > 下游系数", "✅ 通过" if direction_pass else "❌ 失败"))

for label, status in results:
    print(f"  {status} {label}")

# ============================================================================
# 核验4：图片文件信息
# ============================================================================
print("\n【核验4】图片文件信息")

for lang, fname in figure_files_list:
    file_path = os.path.join(FIGURES_DIR, lang, fname)
    if os.path.exists(file_path):
        size_kb = os.path.getsize(file_path) / 1024
        print(f"  ✅ {lang}/{fname} ({size_kb:.1f} KB)")
    else:
        print(f"  ❌ {lang}/{fname} 不存在")

# ============================================================================
# 综合结论
# ============================================================================
print("\n" + "=" * 70)
print("【综合核验结论】")
print("=" * 70)

all_h1_pass = all([status == "✅ 通过" for _, status in results])

if all_passed and all_h1_pass:
    print("✅ 所有核验通过！")
    print("   - 所有文件完整生成")
    print("   - H1假设全部通过验证")
    print("   - 可进入步骤四：稳健性检验")
elif all_passed and not all_h1_pass:
    print("⚠️ 文件完整，但部分H1假设未通过")
    print("   请检查回归结果是否符合预期")
else:
    print("❌ 部分文件缺失，请重新运行 step_03_did_regression.py")

print("\n" + "=" * 70)

# ============================================================================
# 保存核验报告（修复变量冲突）
# ============================================================================
report_path = os.path.join(BASE_DIR, '05_output', 'validation_report.txt')
with open(report_path, 'w', encoding='utf-8') as report_file:
    report_file.write("=" * 70 + "\n")
    report_file.write("步骤三核验报告\n")
    report_file.write(f"核验时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_file.write("=" * 70 + "\n\n")
    report_file.write("【Table 2 核心结果】\n")
    for model in ['全样本', '上游', '下游', '交互项']:
        for var in core_vars:
            row = df[(df['Model'] == model) & (df['Variable'] == var)]
            if len(row) > 0:
                report_file.write(f"  {model} | {var}: {row.iloc[0]['Coefficient']:.4f} (p={row.iloc[0]['p_value']:.4f})\n")
    report_file.write("\n【H1假设检验】\n")
    for label, status in results:
        report_file.write(f"  {status} {label}\n")
    report_file.write("\n【文件完整性】\n")
    for f in table_files:
        file_path = os.path.join(TABLES_DIR, f)
        status = "✅" if os.path.exists(file_path) else "❌"
        report_file.write(f"  {status} {f}\n")
    for lang, fname in figure_files_list:
        file_path = os.path.join(FIGURES_DIR, lang, fname)
        status = "✅" if os.path.exists(file_path) else "❌"
        report_file.write(f"  {status} {lang}/{fname}\n")
    report_file.write("\n" + "=" * 70 + "\n")

print(f"\n核验报告已保存：{report_path}")