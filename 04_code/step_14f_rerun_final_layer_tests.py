# -*- coding: utf-8 -*-
"""步骤14F：使用最终冻结Layer独立重跑54项比较和18项梯度检验。"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
import statsmodels.api as sm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
CAR_PATH = BASE / "05_output/revision_step13b/tables/table_d1_firm_level_car.csv"
LAYER_PATH = (
    BASE / "05_output/revision_step14f/tables/"
    "table_j1_final_frozen_layer.csv"
)
OUT_DIR = BASE / "05_output/revision_step14f/tables"


def norm_code(value):
    return str(value).split(".")[0].replace(".0", "").zfill(6)


def bh_adjust(values):
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * len(p) / np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.clip(adjusted, 0, 1)
    return result


car = pd.read_csv(CAR_PATH, encoding="utf-8-sig")
layers = pd.read_csv(
    LAYER_PATH, encoding="utf-8-sig", dtype={"股票代码": str}
)
car["股票代码"] = car["Stkcd"].map(norm_code)
data = car.drop(columns=["Layer"]).merge(
    layers[["股票代码", "作者最终Layer", "冻结版本"]],
    on="股票代码", how="left",
).rename(columns={"作者最终Layer": "Layer"})
if data["Layer"].isna().any():
    raise ValueError("CAR数据存在无法匹配最终Layer的公司。")

pair_rows, gradient_rows = [], []
windows = ["CAR[-1,+1]", "CAR[-3,+3]", "CAR[-5,+5]"]
comparisons = [("上游", "下游"), ("中游", "下游"), ("上游", "中游")]
for (event, event_date, index), group in data.groupby(
    ["事件", "事件日期", "基准指数"]
):
    for window in windows:
        clean = group.dropna(subset=[window]).copy()
        for name_a, name_b in comparisons:
            values_a = clean.loc[clean["Layer"].eq(name_a), window]
            values_b = clean.loc[clean["Layer"].eq(name_b), window]
            test = ttest_ind(values_a, values_b, equal_var=False)
            pair_rows.append({
                "冻结版本": clean["冻结版本"].iloc[0],
                "事件": event, "事件日期": event_date, "基准指数": index,
                "事件窗口": window.replace("CAR", ""),
                "比较名称": f"{name_a} vs {name_b}",
                "A样本数": len(values_a), "B样本数": len(values_b),
                "A均值": values_a.mean(), "B均值": values_b.mean(),
                "A减B差异": values_a.mean() - values_b.mean(),
                "Welch_t值": test.statistic, "原始p值": test.pvalue,
            })
        clean["产业链梯度"] = clean["Layer"].map(
            {"下游": 0, "中游": 1, "上游": 2}
        )
        model = sm.OLS(
            clean[window], sm.add_constant(clean["产业链梯度"])
        ).fit(cov_type="HC1")
        gradient_rows.append({
            "冻结版本": clean["冻结版本"].iloc[0],
            "事件": event, "事件日期": event_date, "基准指数": index,
            "事件窗口": window.replace("CAR", ""), "样本数": len(clean),
            "产业链梯度斜率": model.params["产业链梯度"],
            "HC1标准误": model.bse["产业链梯度"],
            "t值": model.tvalues["产业链梯度"],
            "原始p值": model.pvalues["产业链梯度"],
        })

pairs = pd.DataFrame(pair_rows)
gradients = pd.DataFrame(gradient_rows)
for frame in (pairs, gradients):
    frame["p_BH全局"] = bh_adjust(frame["原始p值"])
    frame["p_Bonferroni全局"] = np.minimum(
        frame["原始p值"] * len(frame), 1
    )
    frame["BH全局5%显著"] = frame["p_BH全局"].lt(0.05)
    frame["Bonferroni全局5%显著"] = frame["p_Bonferroni全局"].lt(0.05)

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

pairs.to_csv(OUT_DIR / "table_j3_final_pairwise_results.csv",
             index=False, encoding="utf-8-sig")
gradients.to_csv(OUT_DIR / "table_j4_final_gradient_results.csv",
                 index=False, encoding="utf-8-sig")
main.to_csv(OUT_DIR / "table_j5_final_main_results.csv",
            index=False, encoding="utf-8-sig")
data.to_csv(OUT_DIR / "table_j6_final_car_with_layer.csv",
            index=False, encoding="utf-8-sig")

print("=" * 76)
print("步骤14F：最终冻结Layer结果")
print("=" * 76)
print(main[[
    "检验类型", "A减B差异", "产业链梯度斜率", "原始p值",
    "p_BH全局", "p_Bonferroni全局",
]].to_string(index=False))

