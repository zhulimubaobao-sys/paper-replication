# -*- coding: utf-8 -*-
"""
步骤11核验脚本

本脚本不重新回归，只读取步骤11生成的结果并按预设规则检查。
它不会覆盖或删除任何文件。
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
OUTPUT_DIR = BASE_DIR / "05_output" / "revision_audit"
TABLE_DIR = OUTPUT_DIR / "tables"

SUMMARY_PATH = TABLE_DIR / "table_a1_did_and_placebo.csv"
DYNAMIC_PATH = TABLE_DIR / "table_a2_dynamic_did.csv"
PRETREND_PATH = TABLE_DIR / "table_a3_pretrend_joint_test.csv"
ROLLING_PLACEBO_PATH = TABLE_DIR / "table_a4_rolling_placebo_diagnosis.csv"
FIGURE_PATH = OUTPUT_DIR / "figures" / "figure_a1_dynamic_did.png"
LOG_PATH = OUTPUT_DIR / "core_identification_audit_log.txt"

required_files = [
    SUMMARY_PATH,
    DYNAMIC_PATH,
    PRETREND_PATH,
    ROLLING_PLACEBO_PATH,
    FIGURE_PATH,
    LOG_PATH,
]

print("=" * 72)
print("步骤11：核心识别审计核验")
print("=" * 72)

missing = [str(path) for path in required_files if not path.exists()]
if missing:
    print("❌ 缺少以下输出文件：")
    for path in missing:
        print(f"  - {path}")
    raise SystemExit(1)

summary = pd.read_csv(SUMMARY_PATH, encoding="utf-8-sig")
dynamic = pd.read_csv(DYNAMIC_PATH, encoding="utf-8-sig")
pretrend = pd.read_csv(PRETREND_PATH, encoding="utf-8-sig")
rolling_placebo = pd.read_csv(ROLLING_PLACEBO_PATH, encoding="utf-8-sig")

true_row = summary[summary["检验"].str.startswith("真实事件")].iloc[0]
placebo_rows = summary[summary["检验"].str.startswith("伪事件")]

base_pass = true_row["系数"] > 0 and true_row["p值"] < 0.05
placebo_pass = bool((placebo_rows["p值"] >= 0.10).all())
# 主判定只读取预先指定的[-12,-2]窗口。
main_pretrend = pretrend[pretrend["检验窗口"] == "[-12, -2]"].iloc[0]
pretrend_pass = bool(main_pretrend["p值"] >= 0.05)
dynamic_complete = (
    len(dynamic) == 24
    and dynamic["事件时间"].nunique() == 24
    and not dynamic[["系数", "标准误", "p值"]].isna().any().any()
)

print("\n【文件完整性】")
for path in required_files:
    print(f"✅ {path}")

print("\n【数值核验】")
print(
    f"{'✅' if base_pass else '❌'} 基准交互项："
    f"系数={true_row['系数']:.6f}，p={true_row['p值']:.6f}"
)
print(
    f"{'✅' if placebo_pass else '❌'} 三个安慰剂均不显著（p>=0.10）"
)
print(
    f"{'✅' if pretrend_pass else '❌'} 事前系数联合检验："
    f"p={main_pretrend['p值']:.6f}"
)
print(
    f"{'✅' if dynamic_complete else '❌'} 动态DID结果完整（参考期-1不在结果表中）"
)

print("\n【失败原因诊断】")
failed_placebos = placebo_rows[placebo_rows["p值"] < 0.10]
if failed_placebos.empty:
    print("  正式安慰剂中没有p<0.10的结果。")
else:
    for _, row in failed_placebos.iterrows():
        print(
            f"  ⚠️ {row['检验']}：系数={row['系数']:.6f}，"
            f"p={row['p值']:.6f}"
        )

significant_pre = dynamic[
    (dynamic["事件时间"] < -1) & (dynamic["p值"] < 0.10)
].sort_values("事件时间")
if significant_pre.empty:
    print("  事件前没有单期p<0.10的系数。")
else:
    print("  事件前显著月份（p<0.10）：")
    for _, row in significant_pre.iterrows():
        print(
            f"    月份{int(row['事件时间'])}：系数={row['系数']:.6f}，"
            f"p={row['p值']:.6f}"
        )

print("  不同事前窗口联合检验：")
for _, row in pretrend.iterrows():
    print(
        f"    {row['检验窗口']}：Wald={row['Wald统计量']:.4f}，"
        f"p={row['p值']:.6f}，通过={row['是否通过5%标准']}"
    )

rolling_failed = rolling_placebo[rolling_placebo["p值"] < 0.10]
print(
    f"  滚动伪事件中p<0.10的月份数："
    f"{len(rolling_failed)}/{len(rolling_placebo)}"
)

overall = base_pass and placebo_pass and pretrend_pass and dynamic_complete
print("\n【最终判定】")
if overall:
    print("✅ 核心识别审计通过：可以进入稳健性检验和论文结果更新。")
else:
    print("❌ 核心识别审计未通过：暂停Jackknife和论文结论更新，先修复识别设计。")
    print("   不得表述为“平行趋势成立”“严格因果效应”或“准自然实验已验证”。")
    print("   注意：这是科学判定未通过，不是程序运行失败。")

print("=" * 72)
# 文件完整、数值可读取即视为程序成功运行；科学判定由overall单独报告。
raise SystemExit(0)
