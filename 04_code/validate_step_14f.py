# -*- coding: utf-8 -*-
"""步骤14F冻结完整性、哈希和最终结果核验。"""

from hashlib import sha256
from pathlib import Path
import json
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper/05_output/revision_step14f")
FROZEN = BASE / "tables/table_j1_final_frozen_layer.csv"
MANIFEST = BASE / "layer_freeze_manifest.json"
PAIRS = BASE / "tables/table_j3_final_pairwise_results.csv"
GRADIENTS = BASE / "tables/table_j4_final_gradient_results.csv"
MAIN = BASE / "tables/table_j5_final_main_results.csv"


def file_hash(path):
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


frozen = pd.read_csv(FROZEN, encoding="utf-8-sig", dtype={"股票代码": str})
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
pairs = pd.read_csv(PAIRS, encoding="utf-8-sig")
gradients = pd.read_csv(GRADIENTS, encoding="utf-8-sig")
main = pd.read_csv(MAIN, encoding="utf-8-sig")

checks = {
    "冻结表60家公司唯一":
        len(frozen) == 60 and frozen["股票代码"].nunique() == 60,
    "作者批准60/60": frozen["作者是否批准"].eq("是").all(),
    "最终Layer60/60":
        frozen["作者最终Layer"].isin(["上游", "中游", "下游"]).all(),
    "冻结状态60/60": frozen["最终冻结状态"].eq("已冻结").all(),
    "事件前年报链接60/60": frozen["年报PDF_URL"].fillna("").ne("").all(),
    "分类理由60/60": frozen["经济功能分类理由"].fillna("").ne("").all(),
    "冻结表哈希一致": file_hash(FROZEN) == manifest["frozen_sha256"],
    "最终两两检验54项": len(pairs) == 54,
    "最终梯度检验18项": len(gradients) == 18,
    "最终主结果2项": len(main) == 2,
}

print("=" * 76)
print("步骤14F最终冻结核验")
print("=" * 76)
for name, passed in checks.items():
    print(f"{'✅' if passed else '❌'} {name}")
print(f"\n冻结版本：{manifest['freeze_version']}")
print(f"最终分层：{manifest['layer_counts']}")
print(f"相对原始Layer调整：{manifest['changed_from_original_count']}家")
print(f"SHA-256：{manifest['frozen_sha256']}")
print("\n【最终判定】")
if all(checks.values()):
    print("✅ 最终Layer已冻结，结构、证据、哈希和统计结果全部通过。")
    print("   后续不得根据显著性修改Layer；如需修改必须创建新版本并说明原因。")
else:
    print("❌ 最终冻结核验未通过。")

raise SystemExit(0 if all(checks.values()) else 1)
