# -*- coding: utf-8 -*-
"""
步骤14B：审计原始Layer并形成可复现的暂定冻结表

机器建议仅用于发现可疑分类，不自动覆盖原始Layer。
原始Layer来自旧代码的硬编码名单，证据等级明确标为“待补事件前证据”。
"""

from pathlib import Path
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
INPUT = BASE / "05_output/revision_step14a/tables/table_e1_firm_metadata_60.csv"
OUT_DIR = BASE / "05_output/revision_step14b/tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "table_f1_layer_audit_and_provisional_freeze.csv"
RULES_OUT = OUT_DIR / "table_f2_classification_rules.csv"
SUMMARY = OUT_DIR / "table_f3_layer_audit_summary.csv"

RULES = {
    "上游": [
        "芯片", "半导体", "集成电路", "处理器", "服务器", "光模块",
        "光通信", "印制电路", "数据中心", "算力", "存储器", "GPU",
    ],
    "中游": [
        "人工智能", "软件", "信息技术", "系统集成", "云计算", "大数据",
        "算法", "平台", "计算机视觉", "网络安全", "数据库",
    ],
    "下游": [
        "教育", "医疗", "金融", "传媒", "游戏", "办公", "汽车",
        "智慧城市", "零售", "政务", "广告", "应用服务",
    ],
}


def score_text(text):
    """按公开、固定的关键词字典计算三个Layer得分。"""
    text = "" if pd.isna(text) else str(text)
    return {
        layer: sum(text.count(word) for word in words)
        for layer, words in RULES.items()
    }


def proposal(scores):
    """只有唯一最高且得分大于0时给出建议，否则标为无法自动判断。"""
    best = max(scores.values())
    winners = [key for key, value in scores.items() if value == best and best > 0]
    return winners[0] if len(winners) == 1 else "无法自动判断"


df = pd.read_csv(INPUT, encoding="utf-8-sig", dtype={"股票代码": str})
texts = (
    df["东方财富行业"].fillna("") + "；"
    + df["公司简介"].fillna("") + "；"
    + df["经营范围"].fillna("")
)
scores = texts.map(score_text)
for layer in ("上游", "中游", "下游"):
    df[f"{layer}关键词得分"] = scores.map(lambda item: item[layer])
df["机器建议Layer"] = scores.map(proposal)
df["机器建议与原始Layer是否冲突"] = (
    df["机器建议Layer"].ne("无法自动判断")
    & df["机器建议Layer"].ne(df["原始Layer"])
).map({True: "是", False: "否"})

# 冻结的是“原始编码方案”，并不等于分类证据已经通过。
df["暂定冻结Layer"] = df["原始Layer"]
df["冻结版本"] = "layer_v1_original_hardcoded"
df["证据状态"] = "待补事件前公司年报或公告证据"
df["是否可作为最终论文分类"] = "否"
df["人工复核结论"] = "待审核"
df["人工复核备注"] = ""
df.to_csv(OUT, index=False, encoding="utf-8-sig")

rule_rows = []
for layer, words in RULES.items():
    for word in words:
        rule_rows.append({"Layer": layer, "关键词": word})
pd.DataFrame(rule_rows).to_csv(RULES_OUT, index=False, encoding="utf-8-sig")

summary = pd.DataFrame([
    {"核验项": "公司总数", "数量": len(df)},
    {"核验项": "机器无法自动判断数",
     "数量": int(df["机器建议Layer"].eq("无法自动判断").sum())},
    {"核验项": "机器建议与原始Layer冲突数",
     "数量": int(df["机器建议与原始Layer是否冲突"].eq("是").sum())},
    {"核验项": "最终论文分类证据通过数",
     "数量": int(df["是否可作为最终论文分类"].eq("是").sum())},
])
summary.to_csv(SUMMARY, index=False, encoding="utf-8-sig")

print("=" * 76)
print("步骤14B：Layer来源审计与暂定冻结")
print("=" * 76)
print(summary.to_string(index=False))
print("\n机器冲突仅用于人工复核，不自动改Layer：")
cols = ["股票代码", "证券简称", "原始Layer", "机器建议Layer"]
print(df.loc[df["机器建议与原始Layer是否冲突"].eq("是"), cols].to_string(index=False))
print(f"\n输出：{OUT}")
