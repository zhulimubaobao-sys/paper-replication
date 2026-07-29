# -*- coding: utf-8 -*-
"""步骤14E分类复核建议与重跑结果核验。"""

from pathlib import Path
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper/05_output/revision_step14e/tables")
review = pd.read_csv(
    BASE / "table_i1_evidence_based_layer_review.csv",
    encoding="utf-8-sig", dtype={"股票代码": str},
)
pairs = pd.read_csv(BASE / "table_i4_pairwise_evidence_layer.csv",
                    encoding="utf-8-sig")
gradients = pd.read_csv(BASE / "table_i5_gradient_evidence_layer.csv",
                        encoding="utf-8-sig")
main = pd.read_csv(BASE / "table_i6_main_evidence_layer.csv",
                   encoding="utf-8-sig")

checks = {
    "复核表60家公司唯一":
        len(review) == 60 and review["股票代码"].nunique() == 60,
    "每家公司均有事件前年报链接":
        review["年报PDF_URL"].fillna("").ne("").all(),
    "每家公司均有经济功能分类理由":
        review["经济功能分类理由"].fillna("").ne("").all(),
    "证据分类建议无缺失":
        review["证据分类建议Layer"].isin(["上游", "中游", "下游"]).all(),
    "两两检验54项": len(pairs) == 54,
    "梯度检验18项": len(gradients) == 18,
    "主结果2项": len(main) == 2,
}
print("=" * 76)
print("步骤14E联合核验")
print("=" * 76)
for name, passed in checks.items():
    print(f"{'✅' if passed else '❌'} {name}")

changes = int(review["是否改变原始Layer"].eq("是").sum())
approved = int(review["作者是否批准"].eq("是").sum())
print(f"\n建议改变原始Layer：{changes}")
print(f"作者已批准：{approved}/60")
print("\n【最终判定】")
if all(checks.values()):
    print("✅ 事件前年报证据分类建议及敏感性重跑通过。")
else:
    print("❌ 步骤14E存在结构或计算问题。")
if approved < 60:
    print("⚠️ 这是可审核建议方案，不是作者最终冻结分类。")

raise SystemExit(0 if all(checks.values()) else 1)
