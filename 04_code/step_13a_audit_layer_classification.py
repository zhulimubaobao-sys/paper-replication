# -*- coding: utf-8 -*-
"""
步骤13A：样本分类、数据覆盖和单家公司影响审计

本程序不删除公司，也不根据结果改变Layer。
留一公司分析仅用于识别结果是否被少数公司驱动。
"""

from pathlib import Path
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
INPUT_PATH = BASE_DIR / "02_processed_data" / "monthly_panel_return_corrected.csv"
OUTPUT_DIR = BASE_DIR / "05_output" / "revision_step13a"
TABLE_DIR = OUTPUT_DIR / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_code(s):
    return (
        s.astype(str).str.replace(r"\.SZ|\.SH", "", regex=True)
        .str.replace(r"\.0$", "", regex=True).str.zfill(6)
    )


def winsorize(s):
    return s.clip(s.quantile(0.01), s.quantile(0.99))


def fit_static(data):
    """以“下游”为参考组，估计上游和中游的双向固定效应差异。"""
    p = data.sort_values(["Stkcd", "date"]).set_index(["Stkcd", "date"])
    x = p[["Size", "ROA", "Leverage"]].copy()
    x["Post_x_Upstream"] = p["Post"] * p["Is_Upstream"]
    x["Post_x_Midstream"] = p["Post"] * p["Is_Midstream"]
    result = PanelOLS(
        p["Excess_Ret"], x,
        entity_effects=True, time_effects=True, drop_absorbed=True,
    ).fit(cov_type="clustered", cluster_entity=True)
    return result


df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
df["Stkcd"] = normalize_code(df["Stkcd"])
df["date"] = pd.to_datetime(df["date"])
df = df[df["Layer"].isin(["上游", "中游", "下游"])].copy()
df["Is_Upstream"] = (df["Layer"] == "上游").astype(int)
df["Is_Midstream"] = (df["Layer"] == "中游").astype(int)
for c in ["Size", "ROA", "Leverage"]:
    df[c] = winsorize(df[c])

# 公司层面数据覆盖和描述统计。
firm_summary = (
    df.groupby(["Stkcd", "Layer"], as_index=False)
    .agg(
        首月=("date", "min"),
        末月=("date", "max"),
        月数=("date", "nunique"),
        平均超额收益=("Excess_Ret", "mean"),
        收益标准差=("Excess_Ret", "std"),
        平均规模=("Size", "mean"),
        平均ROA=("ROA", "mean"),
        平均杠杆率=("Leverage", "mean"),
    )
)

pre = (
    df[df["Post"] == 0].groupby("Stkcd")["Excess_Ret"]
    .mean().rename("事件前平均收益")
)
post = (
    df[df["Post"] == 1].groupby("Stkcd")["Excess_Ret"]
    .mean().rename("事件后平均收益")
)
firm_summary = firm_summary.merge(pre, on="Stkcd").merge(post, on="Stkcd")
firm_summary["前后变化"] = (
    firm_summary["事件后平均收益"] - firm_summary["事件前平均收益"]
)
firm_summary.to_csv(
    TABLE_DIR / "table_c1_firm_layer_and_coverage.csv",
    index=False, encoding="utf-8-sig",
)

# 分层平衡性：只描述，不能证明分类具有经济含义。
layer_balance = (
    firm_summary.groupby("Layer", as_index=False)
    .agg(
        公司数=("Stkcd", "nunique"),
        最小月数=("月数", "min"),
        平均月数=("月数", "mean"),
        平均规模=("平均规模", "mean"),
        平均ROA=("平均ROA", "mean"),
        平均杠杆率=("平均杠杆率", "mean"),
        事件前平均收益=("事件前平均收益", "mean"),
        事件后平均收益=("事件后平均收益", "mean"),
    )
)
layer_balance.to_csv(
    TABLE_DIR / "table_c2_layer_balance.csv",
    index=False, encoding="utf-8-sig",
)

# 识别2024年8月至11月预趋势阶段中贡献较大的公司。
lead = df[df["date"].between("2024-08-01", "2024-11-01")]
baseline = df[df["date"].between("2024-01-01", "2024-07-01")]
lead_mean = lead.groupby("Stkcd")["Excess_Ret"].mean().rename("2024年8至11月")
base_mean = baseline.groupby("Stkcd")["Excess_Ret"].mean().rename("2024年1至7月")
pretrend_contribution = (
    firm_summary[["Stkcd", "Layer"]]
    .merge(base_mean, on="Stkcd", how="left")
    .merge(lead_mean, on="Stkcd", how="left")
)
pretrend_contribution["阶段变化"] = (
    pretrend_contribution["2024年8至11月"]
    - pretrend_contribution["2024年1至7月"]
)
pretrend_contribution["阶段变化绝对值"] = pretrend_contribution["阶段变化"].abs()
pretrend_contribution = pretrend_contribution.sort_values(
    "阶段变化绝对值", ascending=False
)
pretrend_contribution.to_csv(
    TABLE_DIR / "table_c3_pretrend_firm_contribution.csv",
    index=False, encoding="utf-8-sig",
)

# 留一公司：不改变样本，只记录每家公司对基准系数的影响。
full_result = fit_static(df)
full_up_coef = full_result.params["Post_x_Upstream"]
full_up_p = full_result.pvalues["Post_x_Upstream"]
full_mid_coef = full_result.params["Post_x_Midstream"]
full_mid_p = full_result.pvalues["Post_x_Midstream"]
loo_rows = []
for code in sorted(df["Stkcd"].unique()):
    result = fit_static(df[df["Stkcd"] != code])
    layer = df.loc[df["Stkcd"] == code, "Layer"].iloc[0]
    up_coef = result.params["Post_x_Upstream"]
    mid_coef = result.params["Post_x_Midstream"]
    loo_rows.append(
        {
            "剔除公司代码": code,
            "公司层级": layer,
            "上游相对下游系数": up_coef,
            "上游相对下游标准误": result.std_errors["Post_x_Upstream"],
            "上游相对下游p值": result.pvalues["Post_x_Upstream"],
            "上游系数相对全样本变化": up_coef - full_up_coef,
            "上游系数变化绝对值": abs(up_coef - full_up_coef),
            "中游相对下游系数": mid_coef,
            "中游相对下游标准误": result.std_errors["Post_x_Midstream"],
            "中游相对下游p值": result.pvalues["Post_x_Midstream"],
            "中游系数相对全样本变化": mid_coef - full_mid_coef,
            "中游系数变化绝对值": abs(mid_coef - full_mid_coef),
        }
    )
loo = pd.DataFrame(loo_rows).sort_values(
    "上游系数变化绝对值", ascending=False
)
loo.to_csv(
    TABLE_DIR / "table_c4_leave_one_firm_out.csv",
    index=False, encoding="utf-8-sig",
)

classification_fields_present = {
    "公司名称": False,
    "Layer分类理由": False,
    "分类来源": False,
    "分类日期": False,
    "是否事件前预先确定": False,
}
classification_audit = pd.DataFrame(
    [{"核验字段": k, "当前文件是否具备": "是" if v else "否"}
     for k, v in classification_fields_present.items()]
)
classification_audit.to_csv(
    TABLE_DIR / "table_c5_classification_evidence_gap.csv",
    index=False, encoding="utf-8-sig",
)

print("=" * 76)
print("步骤13A：样本分类与影响审计")
print("=" * 76)
print(f"公司数：{df['Stkcd'].nunique()}，观测值：{len(df)}")
print(
    f"上游相对下游：{full_up_coef:.6f}，p={full_up_p:.6f}"
)
print(
    f"中游相对下游：{full_mid_coef:.6f}，p={full_mid_p:.6f}"
)
print(
    f"留一公司上游系数范围：{loo['上游相对下游系数'].min():.6f} 至 "
    f"{loo['上游相对下游系数'].max():.6f}"
)
print(
    f"留一公司后上游差异不显著次数（p>=0.05）："
    f"{int((loo['上游相对下游p值'] >= 0.05).sum())}/{len(loo)}"
)
print("\n影响最大的5家公司：")
print(
    loo[
        [
            "剔除公司代码", "公司层级", "上游相对下游系数",
            "上游相对下游p值", "上游系数变化绝对值",
        ]
    ].head(5).to_string(index=False)
)
print("\n分类证据缺口：公司名称、分类理由、来源、日期均未包含在现有数据中。")
print(f"输出目录：{OUTPUT_DIR}")
