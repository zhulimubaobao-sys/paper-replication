# -*- coding: utf-8 -*-
"""步骤14D文件、日期、PDF和证据提取核验。"""

from pathlib import Path
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper/05_output/revision_step14d")
MAIN = BASE / "tables/table_h1_event_pre_annual_report_evidence.csv"
REVIEW = BASE / "tables/table_h2_priority_manual_review.csv"
SUMMARY = BASE / "tables/table_h3_step14d_summary.csv"

print("=" * 76)
print("步骤14D联合核验")
print("=" * 76)
if not all(path.exists() for path in (MAIN, REVIEW, SUMMARY)):
    print("❌ 缺少步骤14D输出文件。")
    raise SystemExit(1)

df = pd.read_csv(MAIN, encoding="utf-8-sig", dtype={"股票代码": str})
dates = pd.to_datetime(df["年报公告日期"], errors="coerce")
checks = {
    "60家公司与代码唯一": len(df) == 60 and df["股票代码"].nunique() == 60,
    "事件前年报链接60/60": df["年报检索状态"].eq("成功").all(),
    "公告日期均早于2024-12-26":
        dates.notna().all() and dates.lt(pd.Timestamp("2024-12-26")).all(),
    "PDF下载60/60": df["PDF下载状态"].eq("成功").all(),
    "本地PDF均存在":
        df["本地PDF路径"].map(lambda value: Path(value).exists()).all(),
    "业务证据提取60/60": df["文本提取状态"].eq("成功").all(),
}
for name, passed in checks.items():
    print(f"{'✅' if passed else '❌'} {name}")

print(
    f"\n年报建议与原始Layer冲突："
    f"{int(df['年报建议与原始Layer是否冲突'].eq('是').sum())}"
)
print(
    f"机器无法自动判断："
    f"{int(df['年报证据机器建议Layer'].eq('无法自动判断').sum())}"
)
frozen = int(df["最终分类是否冻结"].eq("是").sum())
print(f"人工最终冻结：{frozen}/60")

print("\n【最终判定】")
if all(checks.values()):
    print("✅ 事件前正式年报证据文件与自动提取通过。")
else:
    print("❌ 年报覆盖或证据提取未全部通过，需查看失败公司。")
if frozen < 60:
    print("⚠️ 自动证据不能替代作者判断；逐公司人工确认完成前不生成最终Layer。")

raise SystemExit(0 if all(checks.values()) else 1)
