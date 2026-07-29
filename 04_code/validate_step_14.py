# -*- coding: utf-8 -*-
"""步骤14分类证据、多重检验和主规格联合核验。"""

from pathlib import Path
import sys
import pandas as pd

# Windows/PyCharm 控制台有时沿用 GBK，显式切换为 UTF-8，避免核验符号导致编码报错。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
TABLE_DIR = BASE_DIR / "05_output" / "revision_step14" / "tables"

paths = {
    "evidence": TABLE_DIR / "table_e1_layer_classification_evidence_template.csv",
    "summary": TABLE_DIR / "table_e1_evidence_completeness_summary.csv",
    "pairs": TABLE_DIR / "table_e2_pairwise_fdr_results.csv",
    "gradients": TABLE_DIR / "table_e3_gradient_fdr_results.csv",
    "main": TABLE_DIR / "table_e4_prespecified_main_results.csv",
    "robustness": TABLE_DIR / "table_e5_robustness_results.csv",
}

print("=" * 76)
print("步骤14联合核验")
print("=" * 76)

missing = [path for path in paths.values() if not path.exists()]
if missing:
    print("❌ 缺少文件：")
    for path in missing:
        print(path)
    raise SystemExit(1)

evidence = pd.read_csv(paths["evidence"], encoding="utf-8-sig")
pairs = pd.read_csv(paths["pairs"], encoding="utf-8-sig")
gradients = pd.read_csv(paths["gradients"], encoding="utf-8-sig")
main = pd.read_csv(paths["main"], encoding="utf-8-sig")
robustness = pd.read_csv(paths["robustness"], encoding="utf-8-sig")

print("\n【Layer证据模板】")
print(f"{'✅' if len(evidence) == 60 else '❌'} 公司数：{len(evidence)}/60")
print(
    f"{'✅' if evidence['股票代码'].nunique() == 60 else '❌'} "
    f"唯一股票代码：{evidence['股票代码'].nunique()}/60"
)
print(f"分层数量：{evidence.groupby('当前Layer')['股票代码'].nunique().to_dict()}")
matched = int((evidence["本地候选来源是否匹配"] == "是").sum())
conflicts = int((evidence["候选Layer是否冲突"] == "是").sum())
missing_names = int(evidence["最终公司名称"].isna().sum())
missing_reasons = int(
    evidence["最终分类理由"].fillna("").str.strip().eq("").sum()
)
print(f"本地匹配公司名称：{matched}/60")
print(f"候选Layer冲突：{conflicts}")
print(f"公司名称待补：{missing_names}")
print(f"分类理由待补：{missing_reasons}")

print("\n【多重检验】")
print(f"{'✅' if len(pairs) == 54 else '❌'} 两两比较：{len(pairs)}/54")
print(
    f"{'✅' if pairs['p_BH全局'].notna().all() else '❌'} "
    "54个BH全局校正值完整"
)
print(
    f"两两比较：原始显著{int(pairs['原始p小于0.05'].sum())}/54，"
    f"BH全局显著{int(pairs['BH全局通过5%'].sum())}/54，"
    f"Bonferroni显著{int(pairs['Bonferroni通过5%'].sum())}/54"
)
print(
    f"{'✅' if len(gradients) == 18 else '❌'} "
    f"梯度检验：{len(gradients)}/18"
)
print(
    f"梯度检验：原始显著{int(gradients['原始p小于0.05'].sum())}/18，"
    f"BH全局显著{int(gradients['BH全局通过5%'].sum())}/18，"
    f"Bonferroni显著{int(gradients['Bonferroni通过5%'].sum())}/18"
)

main_pair = pairs[pairs["是否主规格"] == "是"]
main_gradient = gradients[gradients["是否主规格"] == "是"]
print("\n【主规格锁定】")
print(f"{'✅' if len(main_pair) == 1 else '❌'} 主两两比较数量：{len(main_pair)}")
print(
    f"{'✅' if len(main_gradient) == 1 else '❌'} "
    f"主梯度检验数量：{len(main_gradient)}"
)
if len(main_pair) == 1:
    row = main_pair.iloc[0]
    print(
        f"主比较：差异={row['A减B差异']:.6f}，"
        f"原始p={row['Welch_p值']:.6f}，"
        f"BH全局p={row['p_BH全局']:.6f}，"
        f"Bonferroni p={row['p_Bonferroni全局']:.6f}"
    )
if len(main_gradient) == 1:
    row = main_gradient.iloc[0]
    print(
        f"主梯度：斜率={row['产业链梯度斜率']:.6f}，"
        f"原始p={row['p值']:.6f}，"
        f"BH全局p={row['p_BH全局']:.6f}，"
        f"Bonferroni p={row['p_Bonferroni全局']:.6f}"
    )

print("\n【最终判定】")
calculation_pass = (
    len(evidence) == 60
    and evidence["股票代码"].nunique() == 60
    and len(pairs) == 54
    and len(gradients) == 18
    and len(main_pair) == 1
    and len(main_gradient) == 1
)
print(
    "✅ 步骤14计算与文件结构通过。"
    if calculation_pass else
    "❌ 步骤14计算或文件结构未通过。"
)
if missing_names or missing_reasons or conflicts:
    print("❌ Layer证据尚未完成，不得把模板视为已经审核通过的分类表。")
    print("   必须人工核对公司名称、主营业务、分类理由、来源和事件前日期。")
else:
    print("✅ Layer证据字段完整，可进入正式表图制作。")
print("=" * 76)
raise SystemExit(0 if calculation_pass else 1)
