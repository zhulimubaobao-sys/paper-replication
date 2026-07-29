# -*- coding: utf-8 -*-
"""
步骤14C：使用暂定冻结Layer重跑事件研究横截面检验

输出两套结果：
1. 全部60家公司（原始硬编码Layer暂定冻结）；
2. 剔除机器建议与原始Layer冲突的敏感性样本。
所有p值同时报告BH-FDR与Bonferroni校正。
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
import statsmodels.api as sm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
CAR_PATH = BASE / "05_output/revision_step13b/tables/table_d1_firm_level_car.csv"
LAYER_PATH = (
    BASE / "05_output/revision_step14b/tables/"
    "table_f1_layer_audit_and_provisional_freeze.csv"
)
OUT_DIR = BASE / "05_output/revision_step14c/tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def norm_code(value):
    return str(value).split(".")[0].replace(".0", "").zfill(6)


def bh_adjust(values):
    """Benjamini-Hochberg FDR校正，保证调整值单调且不超过1。"""
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * len(p) / np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.clip(adjusted, 0, 1)
    return result


def run_tests(data, sample_name):
    """对18个事件×指数×窗口规格运行三组比较和一个梯度回归。"""
    pair_rows, gradient_rows = [], []
    windows = ["CAR[-1,+1]", "CAR[-3,+3]", "CAR[-5,+5]"]
    comparisons = [("上游", "下游"), ("中游", "下游"), ("上游", "中游")]
    for (event, event_date, index), group in data.groupby(
        ["事件", "事件日期", "基准指数"]
    ):
        for window in windows:
            clean = group.dropna(subset=[window, "冻结Layer"]).copy()
            for layer_a, layer_b in comparisons:
                a = clean.loc[clean["冻结Layer"].eq(layer_a), window]
                b = clean.loc[clean["冻结Layer"].eq(layer_b), window]
                test = ttest_ind(a, b, equal_var=False, nan_policy="omit")
                pair_rows.append({
                    "样本方案": sample_name, "事件": event,
                    "事件日期": event_date, "基准指数": index,
                    "事件窗口": window.replace("CAR", ""),
                    "比较名称": f"{layer_a} vs {layer_b}",
                    "A样本数": len(a), "B样本数": len(b),
                    "A均值": a.mean(), "B均值": b.mean(),
                    "A减B差异": a.mean() - b.mean(),
                    "Welch_t值": test.statistic, "原始p值": test.pvalue,
                })
            clean["梯度编码"] = clean["冻结Layer"].map(
                {"下游": 0, "中游": 1, "上游": 2}
            )
            model = sm.OLS(
                clean[window], sm.add_constant(clean["梯度编码"])
            ).fit(cov_type="HC1")
            gradient_rows.append({
                "样本方案": sample_name, "事件": event,
                "事件日期": event_date, "基准指数": index,
                "事件窗口": window.replace("CAR", ""),
                "样本数": len(clean),
                "产业链梯度斜率": model.params["梯度编码"],
                "HC1标准误": model.bse["梯度编码"],
                "t值": model.tvalues["梯度编码"],
                "原始p值": model.pvalues["梯度编码"],
            })
    return pd.DataFrame(pair_rows), pd.DataFrame(gradient_rows)


car = pd.read_csv(CAR_PATH, encoding="utf-8-sig")
layer = pd.read_csv(LAYER_PATH, encoding="utf-8-sig", dtype={"股票代码": str})
car["股票代码"] = car["Stkcd"].map(norm_code)
layer_map = layer[[
    "股票代码", "暂定冻结Layer", "机器建议与原始Layer是否冲突"
]].rename(columns={"暂定冻结Layer": "冻结Layer"})
merged = car.drop(columns=["Layer"]).merge(layer_map, on="股票代码", how="left")

all_pairs, all_gradients = run_tests(merged, "全60家公司")
reduced = merged.loc[
    merged["机器建议与原始Layer是否冲突"].ne("是")
].copy()
reduced_pairs, reduced_gradients = run_tests(reduced, "剔除机器冲突公司")
pairs = pd.concat([all_pairs, reduced_pairs], ignore_index=True)
gradients = pd.concat([all_gradients, reduced_gradients], ignore_index=True)

for frame in (pairs, gradients):
    # 主样本与敏感性样本回答不同问题，分别构成各自的检验族，
    # 不能合并后把校正次数错误地翻倍。
    frame["p_BH全局"] = frame.groupby("样本方案")["原始p值"].transform(
        lambda values: bh_adjust(values.to_numpy())
    )
    family_size = frame.groupby("样本方案")["原始p值"].transform("size")
    frame["p_Bonferroni全局"] = np.minimum(
        frame["原始p值"] * family_size, 1
    )
    frame["BH全局5%显著"] = frame["p_BH全局"] < 0.05
    frame["Bonferroni全局5%显著"] = frame["p_Bonferroni全局"] < 0.05

main_filter_pairs = (
    pairs["事件"].eq("DeepSeek-V3_2024-12-26")
    & pairs["基准指数"].eq("000300.SH")
    & pairs["事件窗口"].eq("[-1,+1]")
    & pairs["比较名称"].eq("上游 vs 下游")
)
main_filter_gradients = (
    gradients["事件"].eq("DeepSeek-V3_2024-12-26")
    & gradients["基准指数"].eq("000300.SH")
    & gradients["事件窗口"].eq("[-1,+1]")
)
main = pd.concat([
    pairs.loc[main_filter_pairs].assign(检验类型="上游与下游比较"),
    gradients.loc[main_filter_gradients].assign(检验类型="产业链梯度"),
], ignore_index=True, sort=False)

pairs.to_csv(OUT_DIR / "table_g1_pairwise_frozen_layer.csv",
             index=False, encoding="utf-8-sig")
gradients.to_csv(OUT_DIR / "table_g2_gradient_frozen_layer.csv",
                 index=False, encoding="utf-8-sig")
main.to_csv(OUT_DIR / "table_g3_main_and_sensitivity.csv",
            index=False, encoding="utf-8-sig")
merged.to_csv(OUT_DIR / "table_g4_car_with_frozen_layer.csv",
              index=False, encoding="utf-8-sig")

print("=" * 76)
print("步骤14C：暂定冻结Layer复跑")
print("=" * 76)
print(f"全样本公司数：{merged['股票代码'].nunique()}")
print(f"剔除冲突后公司数：{reduced['股票代码'].nunique()}")
print("\n主规格与敏感性：")
display_cols = [
    "样本方案", "检验类型", "A减B差异", "产业链梯度斜率",
    "原始p值", "p_BH全局", "p_Bonferroni全局",
]
print(main.reindex(columns=display_cols).to_string(index=False))
print(f"\n输出目录：{OUT_DIR}")
