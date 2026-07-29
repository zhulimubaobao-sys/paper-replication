# -*- coding: utf-8 -*-
"""
步骤14E：基于2023年年报的Layer复核建议

注意：
1. 本表是供作者审核的“证据分类方案”，不会覆盖原始Layer；
2. 决策依据是企业在AI价值链中的主要经济功能，而不是关键词数量；
3. 最终发表版本仍需作者在“作者是否批准”列确认。
"""

from pathlib import Path
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
INPUT = (
    BASE / "05_output/revision_step14d/tables/"
    "table_h1_event_pre_annual_report_evidence.csv"
)
OUT_DIR = BASE / "05_output/revision_step14e/tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 仅列出需要人工经济判断的25家公司。
# 未列出的公司沿用原始Layer，并标记为“年报关键词建议与原始分类一致”。
REVIEWS = {
    "000988": ("上游", "保留", "激光装备、光联接和传感器属于AI硬件及基础部件供给。"),
    "002065": ("中游", "调整", "核心为应用软件、数字基础设施和IT解决方案，属于通用软件与集成层。"),
    "002253": ("中游", "保留", "提供空管指挥控制及仿真软件系统，核心能力为专业软件与算法系统。"),
    "002368": ("中游", "调整", "主营数字政府、数据平台和软件信息服务，属于平台与系统集成层。"),
    "002405": ("中游", "保留", "核心为地图数据、位置服务和汽车智能化平台，具有数据平台属性。"),
    "002439": ("中游", "调整", "主营网络、数据和AI安全产品及运营平台，属于通用技术支撑层。"),
    "002463": ("上游", "保留", "主营PCB生产销售，是服务器、数据中心和通信设备的基础硬件部件。"),
    "300020": ("下游", "保留", "主营智慧城市、交通和健康等具体行业应用与运营服务。"),
    "300033": ("下游", "调整", "主要向金融机构和投资者提供金融信息、投顾与交易应用服务。"),
    "300036": ("中游", "调整", "主营GIS基础软件与空间智能平台，可被多个下游行业复用。"),
    "300075": ("下游", "保留", "主营数字政府与城市治理场景应用，属于终端行业解决方案。"),
    "300078": ("下游", "调整", "业务主要落在商业零售、物联网门店等具体终端应用场景。"),
    "300170": ("中游", "调整", "主营企业数字化软件、平台及实施服务，属于通用软件与集成层。"),
    "300188": ("中游", "调整", "主营数字取证、网络空间安全和数据智能平台，属于技术支撑层。"),
    "300451": ("下游", "调整", "主营医疗卫生信息化和智慧医疗应用，属于医疗终端场景。"),
    "300476": ("上游", "保留", "主营PCB制造，是计算、通信和数据中心设备的基础硬件部件。"),
    "300785": ("下游", "保留", "主营消费内容、营销服务和消费数据应用，面向终端消费场景。"),
    "600410": ("中游", "调整", "主营云计算、IT基础架构和系统集成服务，属于平台集成层。"),
    "600556": ("下游", "保留", "主营红人营销和数字广告服务，属于营销终端应用。"),
    "600570": ("下游", "保留", "产品直接服务证券、基金等金融业务流程，属于金融行业应用。"),
    "603019": ("上游", "保留", "主营高端计算机、服务器、存储和智算中心基础设施。"),
    "603160": ("上游", "调整", "Fabless芯片设计企业，核心产品为传感、触控和连接芯片。"),
    "688111": ("下游", "调整", "WPS及WPS AI直接面向个人与机构办公场景，属于终端应用。"),
    "688228": ("中游", "调整", "主营大模型、算力管理、内容安全与应用中台，核心为AI平台能力。"),
    "688369": ("中游", "调整", "主营企业级协同管理软件、平台和云服务，属于通用软件层。"),
}

df = pd.read_csv(INPUT, encoding="utf-8-sig", dtype={"股票代码": str})
df["证据分类建议Layer"] = df["原始Layer"]
df["复核处理"] = "保留"
df["经济功能分类理由"] = "年报机器建议与原始Layer一致，暂按原始分类保留。"

for code, (layer, action, reason) in REVIEWS.items():
    mask = df["股票代码"].eq(code)
    if mask.sum() != 1:
        raise ValueError(f"复核公司代码缺失或重复：{code}")
    df.loc[mask, "证据分类建议Layer"] = layer
    df.loc[mask, "复核处理"] = action
    df.loc[mask, "经济功能分类理由"] = reason

df["是否改变原始Layer"] = (
    df["证据分类建议Layer"].ne(df["原始Layer"])
).map({True: "是", False: "否"})
df["证据来源等级"] = "事件前2023年年度报告正文"
df["作者是否批准"] = "待批准"
df["作者最终Layer"] = ""
df["最终冻结状态"] = "未冻结"
df["审核备注"] = ""

columns = [
    "股票代码", "证券简称", "公司全称", "原始Layer",
    "年报证据机器建议Layer", "证据分类建议Layer", "复核处理",
    "是否改变原始Layer", "经济功能分类理由", "年报标题",
    "年报公告日期", "年报PDF_URL", "证据文本文件",
    "年报业务证据摘录", "证据来源等级", "作者是否批准",
    "作者最终Layer", "最终冻结状态", "审核备注",
]
review = df[columns].sort_values(["证据分类建议Layer", "股票代码"])
review.to_csv(
    OUT_DIR / "table_i1_evidence_based_layer_review.csv",
    index=False, encoding="utf-8-sig",
)

changes = review.loc[review["是否改变原始Layer"].eq("是")].copy()
changes.to_csv(
    OUT_DIR / "table_i2_proposed_layer_changes.csv",
    index=False, encoding="utf-8-sig",
)

balance = pd.concat([
    review.groupby("原始Layer")["股票代码"].count().rename("原始数量"),
    review.groupby("证据分类建议Layer")["股票代码"].count().rename("建议数量"),
], axis=1).fillna(0).reset_index(names="Layer")
balance.to_csv(
    OUT_DIR / "table_i3_layer_balance_before_after.csv",
    index=False, encoding="utf-8-sig",
)

print("=" * 76)
print("步骤14E：事件前年报经济功能分类复核建议")
print("=" * 76)
print(f"公司总数：{len(review)}")
print(f"建议改变Layer：{len(changes)}")
print("\n调整前后分层数量：")
print(balance.to_string(index=False))
print("\n注意：该表尚待作者批准，不覆盖原始Layer。")

