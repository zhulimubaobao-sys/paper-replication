# -*- coding: utf-8 -*-
"""步骤14A/B/C联合核验器。"""

from pathlib import Path
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper/05_output")
paths = {
    "metadata": BASE / "revision_step14a/tables/table_e1_firm_metadata_60.csv",
    "audit": BASE / "revision_step14b/tables/table_f1_layer_audit_and_provisional_freeze.csv",
    "pairs": BASE / "revision_step14c/tables/table_g1_pairwise_frozen_layer.csv",
    "gradients": BASE / "revision_step14c/tables/table_g2_gradient_frozen_layer.csv",
    "main": BASE / "revision_step14c/tables/table_g3_main_and_sensitivity.csv",
}

print("=" * 76)
print("步骤14A/B/C联合核验")
print("=" * 76)
missing = [str(path) for path in paths.values() if not path.exists()]
if missing:
    print("❌ 缺少输出文件：")
    print("\n".join(missing))
    raise SystemExit(1)

metadata = pd.read_csv(paths["metadata"], encoding="utf-8-sig",
                       dtype={"股票代码": str})
audit = pd.read_csv(paths["audit"], encoding="utf-8-sig",
                    dtype={"股票代码": str})
pairs = pd.read_csv(paths["pairs"], encoding="utf-8-sig")
gradients = pd.read_csv(paths["gradients"], encoding="utf-8-sig")
main = pd.read_csv(paths["main"], encoding="utf-8-sig")

checks = {
    "60家公司完整": len(metadata) == 60 and metadata["股票代码"].nunique() == 60,
    "公司简称全部取得": metadata["证券简称"].fillna("").ne("").all(),
    "公司简介全部取得": metadata["公司简介"].fillna("").ne("").all(),
    "冻结表60家公司完整": len(audit) == 60 and audit["股票代码"].nunique() == 60,
    "全样本两两检验54项":
        len(pairs.loc[pairs["样本方案"].eq("全60家公司")]) == 54,
    "全样本梯度检验18项":
        len(gradients.loc[gradients["样本方案"].eq("全60家公司")]) == 18,
    "两套主比较与主梯度完整": len(main) == 4,
    "多重检验值完整":
        pairs[["p_BH全局", "p_Bonferroni全局"]].notna().all().all()
        and gradients[["p_BH全局", "p_Bonferroni全局"]].notna().all().all(),
}
for name, passed in checks.items():
    print(f"{'✅' if passed else '❌'} {name}")

conflicts = int(audit["机器建议与原始Layer是否冲突"].eq("是").sum())
final_evidence = int(audit["是否可作为最终论文分类"].eq("是").sum())
print(f"\n机器建议冲突公司数：{conflicts}")
print(f"具备最终论文事件前证据公司数：{final_evidence}/60")
print("\n【最终判定】")
if all(checks.values()):
    print("✅ 步骤14A/B/C程序、公司覆盖和统计计算通过。")
else:
    print("❌ 步骤14A/B/C存在结构或计算问题。")
if final_evidence < 60:
    print("⚠️ 原始Layer仍缺事件前逐公司证据；当前只能称为暂定冻结分类。")
    print("   不得声称产业链分类已经由公开事件前资料完全验证。")

raise SystemExit(0 if all(checks.values()) else 1)
