# -*- coding: utf-8 -*-
"""
步骤14A：生成60家公司Layer分类证据模板

原则：
1. 不修改当前Layer；
2. 只从本地文件提取能够匹配的信息；
3. 本地候选来源与当前Layer冲突时必须标红式标记，不自动采用；
4. 缺失信息保持空白，留待作者基于事件前公开资料审核。
"""

from pathlib import Path
import re
import pandas as pd

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
FIRM_PATH = (
    BASE_DIR / "05_output" / "revision_step13a" / "tables"
    / "table_c1_firm_layer_and_coverage.csv"
)
CANDIDATE_PATH = BASE_DIR / "AI股票100只测试样本（上游50+下游50）.xlsx"
OUTPUT_DIR = BASE_DIR / "05_output" / "revision_step14"
TABLE_DIR = OUTPUT_DIR / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = TABLE_DIR / "table_e1_layer_classification_evidence_template.csv"
SUMMARY_PATH = TABLE_DIR / "table_e1_evidence_completeness_summary.csv"


def normalize_code(series):
    """统一为6位纯数字股票代码。"""
    return (
        series.astype(str)
        .str.replace(r"\.SZ|\.SH|\.BJ", "", regex=True)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )


def extract_evidence_date(text):
    """从中文证据文本中提取第一个明确日期；无法确定则留空。"""
    if pd.isna(text):
        return pd.NaT
    text = str(text)
    match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", text)
    if match:
        return pd.Timestamp(
            year=int(match.group(1)),
            month=int(match.group(2)),
            day=int(match.group(3)),
        )
    match = re.search(r"(20\d{2})年(?:年度报告|年报)", text)
    if match:
        # 年报只提供年度，采用该年末作为保守的信息可得日期。
        return pd.Timestamp(year=int(match.group(1)), month=12, day=31)
    return pd.NaT


firms = pd.read_csv(FIRM_PATH, encoding="utf-8-sig")
firms["股票代码"] = normalize_code(firms["Stkcd"])
firms = firms[["股票代码", "Layer"]].drop_duplicates("股票代码")
firms = firms.rename(columns={"Layer": "当前Layer"})

candidate = pd.read_excel(CANDIDATE_PATH)
candidate["股票代码"] = normalize_code(candidate["股票代码"])
candidate = candidate[
    [
        "股票代码", "股票简称", "所属同花顺行业", "所属概念",
        "纳入概念原因", "产业链位置", "AI_exposure",
    ]
].drop_duplicates("股票代码")
candidate = candidate.rename(
    columns={
        "产业链位置": "候选来源Layer",
        "所属同花顺行业": "候选行业",
        "纳入概念原因": "候选分类证据",
    }
)

evidence = firms.merge(candidate, on="股票代码", how="left")
evidence["本地候选来源是否匹配"] = evidence["股票简称"].notna().map(
    {True: "是", False: "否"}
)
evidence["候选Layer是否冲突"] = (
    evidence["候选来源Layer"].notna()
    & (evidence["候选来源Layer"] != evidence["当前Layer"])
).map({True: "是", False: "否"})
evidence["候选证据日期"] = evidence["候选分类证据"].apply(
    extract_evidence_date
)
event_date = pd.Timestamp("2024-12-26")
evidence["候选证据是否早于V3事件"] = evidence["候选证据日期"].apply(
    lambda value: (
        "待核验" if pd.isna(value)
        else ("是" if value < event_date else "否")
    )
)

# 以下字段必须由作者依据事件前公开资料审核，程序不能自动编造。
evidence["最终公司名称"] = evidence["股票简称"]
evidence["最终主营业务"] = ""
evidence["最终Layer"] = evidence["当前Layer"]
evidence["最终分类理由"] = ""
evidence["最终证据来源名称"] = ""
evidence["最终证据URL或数据库字段"] = ""
evidence["最终证据发布日期"] = ""
evidence["证据是否早于2024-12-26"] = "待审核"
evidence["是否使用事件后信息"] = "待审核"
evidence["人工复核状态"] = "待审核"
evidence["审核人备注"] = ""

columns = [
    "股票代码", "当前Layer", "最终公司名称", "最终主营业务",
    "最终Layer", "最终分类理由", "最终证据来源名称",
    "最终证据URL或数据库字段", "最终证据发布日期",
    "证据是否早于2024-12-26", "是否使用事件后信息",
    "人工复核状态", "审核人备注",
    "本地候选来源是否匹配", "股票简称", "候选行业",
    "候选来源Layer", "候选Layer是否冲突", "候选证据日期",
    "候选证据是否早于V3事件", "候选分类证据",
    "所属概念", "AI_exposure",
]
evidence = evidence[columns].sort_values(["当前Layer", "股票代码"])
evidence.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

summary = pd.DataFrame(
    [
        {"核验项": "公司总数", "数量": len(evidence)},
        {
            "核验项": "本地候选来源匹配公司数",
            "数量": int((evidence["本地候选来源是否匹配"] == "是").sum()),
        },
        {
            "核验项": "候选Layer冲突公司数",
            "数量": int((evidence["候选Layer是否冲突"] == "是").sum()),
        },
        {
            "核验项": "最终公司名称缺失数",
            "数量": int(evidence["最终公司名称"].isna().sum()),
        },
        {
            "核验项": "最终分类理由缺失数",
            "数量": int((evidence["最终分类理由"].str.strip() == "").sum()),
        },
        {
            "核验项": "最终证据来源缺失数",
            "数量": int(
                (evidence["最终证据来源名称"].str.strip() == "").sum()
            ),
        },
    ]
)
summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

print("=" * 76)
print("步骤14A：Layer分类证据模板")
print("=" * 76)
print(summary.to_string(index=False))
print("\n候选Layer冲突记录：")
conflicts = evidence[evidence["候选Layer是否冲突"] == "是"]
if conflicts.empty:
    print("无")
else:
    print(
        conflicts[
            ["股票代码", "最终公司名称", "当前Layer", "候选来源Layer"]
        ].to_string(index=False)
    )
print(f"\n模板输出：{OUTPUT_PATH}")
print("注意：程序未自动改变任何公司的Layer。")

