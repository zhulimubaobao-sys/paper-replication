# -*- coding: utf-8 -*-
"""
步骤14F：冻结最终产业链分类

用户已明确批准采用步骤14E的事件前年报经济功能分类建议。
本程序：
1. 将“证据分类建议Layer”写入“作者最终Layer”；
2. 将60家公司标记为已批准、已冻结；
3. 保存原始Layer，确保所有调整可追溯；
4. 计算输入表和冻结表的SHA-256，形成版本清单。
"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
INPUT = (
    BASE / "05_output/revision_step14e/tables/"
    "table_i1_evidence_based_layer_review.csv"
)
OUT_DIR = BASE / "05_output/revision_step14f"
TABLE_DIR = OUT_DIR / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)
FROZEN = TABLE_DIR / "table_j1_final_frozen_layer.csv"
CHANGES = TABLE_DIR / "table_j2_final_layer_changes.csv"
MANIFEST = OUT_DIR / "layer_freeze_manifest.json"


def file_hash(path):
    """流式计算SHA-256，避免大文件一次性读入内存。"""
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


df = pd.read_csv(INPUT, encoding="utf-8-sig", dtype={"股票代码": str})
if len(df) != 60 or df["股票代码"].nunique() != 60:
    raise ValueError("步骤14E复核表不是60家唯一公司，禁止冻结。")
if not df["证据分类建议Layer"].isin(["上游", "中游", "下游"]).all():
    raise ValueError("证据分类建议Layer存在非法值，禁止冻结。")
if df["年报PDF_URL"].fillna("").eq("").any():
    raise ValueError("存在缺少年报链接的公司，禁止冻结。")
if df["经济功能分类理由"].fillna("").eq("").any():
    raise ValueError("存在缺少分类理由的公司，禁止冻结。")

freeze_time = datetime.now().astimezone().isoformat(timespec="seconds")
df["作者是否批准"] = "是"
df["作者最终Layer"] = df["证据分类建议Layer"]
df["最终冻结状态"] = "已冻结"
df["冻结版本"] = "layer_final_v1_2023_annual_report"
df["冻结时间"] = freeze_time
df["冻结原则"] = (
    "依据2024-12-26前公告的2023年年度报告，按企业在AI价值链中的"
    "主要经济功能分类；不依据事件后收益或回归显著性调整。"
)
df["最终是否改变原始Layer"] = (
    df["作者最终Layer"].ne(df["原始Layer"])
).map({True: "是", False: "否"})

df = df.sort_values("股票代码")
df.to_csv(FROZEN, index=False, encoding="utf-8-sig")
df.loc[df["最终是否改变原始Layer"].eq("是")].to_csv(
    CHANGES, index=False, encoding="utf-8-sig"
)

manifest = {
    "freeze_version": "layer_final_v1_2023_annual_report",
    "freeze_time": freeze_time,
    "company_count": int(len(df)),
    "layer_counts": {
        key: int(value)
        for key, value in df["作者最终Layer"].value_counts().to_dict().items()
    },
    "changed_from_original_count": int(
        df["最终是否改变原始Layer"].eq("是").sum()
    ),
    "input_path": str(INPUT),
    "input_sha256": file_hash(INPUT),
    "frozen_path": str(FROZEN),
    "frozen_sha256": file_hash(FROZEN),
    "classification_rule": (
        "2023年年度报告事件前证据+AI价值链主要经济功能；"
        "禁止根据统计显著性重新分类"
    ),
}
MANIFEST.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("=" * 76)
print("步骤14F：最终Layer冻结")
print("=" * 76)
print(f"冻结版本：{manifest['freeze_version']}")
print(f"公司总数：{manifest['company_count']}")
print(f"最终分层：{manifest['layer_counts']}")
print(f"相对原始Layer调整：{manifest['changed_from_original_count']}家")
print(f"冻结表SHA-256：{manifest['frozen_sha256']}")
print(f"冻结表：{FROZEN}")
print(f"清单：{MANIFEST}")

