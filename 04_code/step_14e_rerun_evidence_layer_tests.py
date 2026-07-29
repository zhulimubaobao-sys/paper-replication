# -*- coding: utf-8 -*-
"""步骤14E：使用事件前年报证据分类建议重跑全部事件研究横截面检验。"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
import statsmodels.api as sm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
CAR = BASE / "05_output/revision_step13b/tables/table_d1_firm_level_car.csv"
LAYER = (
    BASE / "05_output/revision_step14e/tables/"
    "table_i1_evidence_based_layer_review.csv"
)
OUT_DIR = BASE / "05_output/revision_step14e/tables"


def norm_code(value):
    return str(value).split(".")[0].replace(".0", "").zfill(6)


def bh(values):
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * len(p) / np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.clip(adjusted, 0, 1)
    return result


car = pd.read_csv(CAR, encoding="utf-8-sig")
layer = pd.read_csv(LAYER, encoding="utf-8-sig", dtype={"股票代码": str})
car["股票代码"] = car["Stkcd"].map(norm_code)
data = car.drop(columns=["Layer"]).merge(
    layer[["股票代码", "证据分类建议Layer"]],
    on="股票代码", how="left",
).rename(columns={"证据分类建议Layer": "Layer"})

pairs, gradients = [], []
windows = ["CAR[-1,+1]", "CAR[-3,+3]", "CAR[-5,+5]"]
comparisons = [("上游", "下游"), ("中游", "下游"), ("上游", "中游")]
for (event, event_date, index), group in data.groupby(
    ["事件", "事件日期", "基准指数"]
):
    for window in windows:
        clean = group.dropna(subset=[window, "Layer"]).copy()
        for a_name, b_name in comparisons:
            a = clean.loc[clean["Layer"].eq(a_name), window]
            b = clean.loc[clean["Layer"].eq(b_name), window]
            test = ttest_ind(a, b, equal_var=False)
            pairs.append({
                "事件": event, "事件日期": event_date, "基准指数": index,
                "事件窗口": window.replace("CAR", ""),
                "比较名称": f"{a_name} vs {b_name}",
                "A样本数": len(a), "B样本数": len(b),
                "A均值": a.mean(), "B均值": b.mean(),
                "A减B差异": a.mean() - b.mean(),
                "Welch_t值": test.statistic, "原始p值": test.pvalue,
            })
        clean["梯度"] = clean["Layer"].map({"下游": 0, "中游": 1, "上游": 2})
        model = sm.OLS(
            clean[window], sm.add_constant(clean["梯度"])
        ).fit(cov_type="HC1")
        gradients.append({
            "事件": event, "事件日期": event_date, "基准指数": index,
            "事件窗口": window.replace("CAR", ""), "样本数": len(clean),
            "梯度斜率": model.params["梯度"],
            "HC1标准误": model.bse["梯度"],
            "原始p值": model.pvalues["梯度"],
        })

pairs = pd.DataFrame(pairs)
gradients = pd.DataFrame(gradients)
for frame in (pairs, gradients):
    frame["p_BH全局"] = bh(frame["原始p值"])
    frame["p_Bonferroni全局"] = np.minimum(
        frame["原始p值"] * len(frame), 1
    )

main_pair = pairs.loc[
    pairs["事件"].eq("DeepSeek-V3_2024-12-26")
    & pairs["基准指数"].eq("000300.SH")
    & pairs["事件窗口"].eq("[-1,+1]")
    & pairs["比较名称"].eq("上游 vs 下游")
].assign(检验类型="上游与下游比较")
main_gradient = gradients.loc[
    gradients["事件"].eq("DeepSeek-V3_2024-12-26")
    & gradients["基准指数"].eq("000300.SH")
    & gradients["事件窗口"].eq("[-1,+1]")
].assign(检验类型="产业链梯度")
main = pd.concat([main_pair, main_gradient], ignore_index=True, sort=False)

pairs.to_csv(OUT_DIR / "table_i4_pairwise_evidence_layer.csv",
             index=False, encoding="utf-8-sig")
gradients.to_csv(OUT_DIR / "table_i5_gradient_evidence_layer.csv",
                 index=False, encoding="utf-8-sig")
main.to_csv(OUT_DIR / "table_i6_main_evidence_layer.csv",
            index=False, encoding="utf-8-sig")
data.to_csv(OUT_DIR / "table_i7_car_evidence_layer.csv",
            index=False, encoding="utf-8-sig")

print("=" * 76)
print("步骤14E：事件前年报证据分类方案复跑")
print("=" * 76)
print(main[[
    "检验类型", "A减B差异", "梯度斜率", "原始p值",
    "p_BH全局", "p_Bonferroni全局",
]].to_string(index=False))

