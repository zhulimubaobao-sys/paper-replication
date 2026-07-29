# -*- coding: utf-8 -*-
"""
步骤14B：多重检验校正与主规格锁定

主规格预先锁定为：
- 主事件：DeepSeek-V3，2024-12-26
- 主指数：沪深300（000300.SH）
- 主窗口：[-1,+1]
- 主两两比较：上游 vs 下游
- 主梯度：下游=0、中游=1、上游=2

同时输出：
- BH-FDR全局校正；
- 按事件分组BH-FDR校正；
- Bonferroni全局校正；
- 全部非主规格，禁止只保留显著结果。
"""

from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
PAIR_PATH = (
    BASE_DIR / "05_output" / "revision_step13b" / "tables"
    / "table_d2_upstream_downstream_car_comparison.csv"
)
GRADIENT_PATH = (
    BASE_DIR / "05_output" / "revision_step13b" / "tables"
    / "table_d3_layer_gradient_tests.csv"
)
FIRM_CAR_PATH = (
    BASE_DIR / "05_output" / "revision_step13b" / "tables"
    / "table_d1_firm_level_car.csv"
)
OUTPUT_DIR = BASE_DIR / "05_output" / "revision_step14"
TABLE_DIR = OUTPUT_DIR / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def bh_adjust(p_values):
    """Benjamini-Hochberg FDR校正，保持原始行序。"""
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adjusted_ranked = ranked * n / np.arange(1, n + 1)
    adjusted_ranked = np.minimum.accumulate(adjusted_ranked[::-1])[::-1]
    adjusted_ranked = np.clip(adjusted_ranked, 0, 1)
    adjusted = np.empty(n, dtype=float)
    adjusted[order] = adjusted_ranked
    return adjusted


def add_adjustments(data, p_column, family_column):
    """增加全局、事件族内BH-FDR和Bonferroni校正。"""
    result = data.copy()
    result["p_BH全局"] = bh_adjust(result[p_column])
    result["p_Bonferroni全局"] = np.minimum(
        result[p_column] * len(result), 1.0
    )
    result["p_BH事件内"] = np.nan
    for _, index_values in result.groupby(family_column).groups.items():
        result.loc[index_values, "p_BH事件内"] = bh_adjust(
            result.loc[index_values, p_column]
        )
    result["原始p小于0.05"] = result[p_column] < 0.05
    result["BH全局通过5%"] = result["p_BH全局"] < 0.05
    result["BH事件内通过5%"] = result["p_BH事件内"] < 0.05
    result["Bonferroni通过5%"] = result["p_Bonferroni全局"] < 0.05
    return result


pairs = pd.read_csv(PAIR_PATH, encoding="utf-8-sig")
gradients = pd.read_csv(GRADIENT_PATH, encoding="utf-8-sig")
firm_car = pd.read_csv(FIRM_CAR_PATH, encoding="utf-8-sig")

pairs = add_adjustments(pairs, "Welch_p值", "事件")
gradients = add_adjustments(gradients, "p值", "事件")

pairs["是否主规格"] = (
    (pairs["事件"] == "DeepSeek-V3_2024-12-26")
    & (pairs["基准指数"] == "000300.SH")
    & (pairs["事件窗口"] == "[-1,+1]")
    & (pairs["比较名称"] == "上游 vs 下游")
).map({True: "是", False: "否"})

gradients["是否主规格"] = (
    (gradients["事件"] == "DeepSeek-V3_2024-12-26")
    & (gradients["基准指数"] == "000300.SH")
    & (gradients["事件窗口"] == "[-1,+1]")
).map({True: "是", False: "否"})

pairs.to_csv(
    TABLE_DIR / "table_e2_pairwise_fdr_results.csv",
    index=False, encoding="utf-8-sig",
)
gradients.to_csv(
    TABLE_DIR / "table_e3_gradient_fdr_results.csv",
    index=False, encoding="utf-8-sig",
)

# 生成主规格表，包含三层平均CAR、主比较和主梯度。
main_firms = firm_car[
    (firm_car["事件"] == "DeepSeek-V3_2024-12-26")
    & (firm_car["基准指数"] == "000300.SH")
]
layer_means = (
    main_firms.groupby("Layer")["CAR[-1,+1]"].agg(["count", "mean", "std"])
    .reset_index()
    .rename(
        columns={
            "count": "公司数",
            "mean": "平均CAR",
            "std": "CAR标准差",
        }
    )
)
layer_means["结果类型"] = "三层描述"
layer_means["主规格说明"] = "V3；沪深300；[-1,+1]"

main_pair = pairs[pairs["是否主规格"] == "是"].copy()
main_pair["结果类型"] = "主两两比较"
main_gradient = gradients[gradients["是否主规格"] == "是"].copy()
main_gradient["结果类型"] = "主梯度检验"

main_results = pd.concat(
    [
        layer_means,
        main_pair,
        main_gradient,
    ],
    ignore_index=True,
    sort=False,
)
main_results.to_csv(
    TABLE_DIR / "table_e4_prespecified_main_results.csv",
    index=False, encoding="utf-8-sig",
)

robustness = pd.concat(
    [
        pairs[pairs["是否主规格"] == "否"].assign(结果类别="两两比较稳健性"),
        gradients[gradients["是否主规格"] == "否"].assign(
            结果类别="梯度检验稳健性"
        ),
    ],
    ignore_index=True,
    sort=False,
)
robustness.to_csv(
    TABLE_DIR / "table_e5_robustness_results.csv",
    index=False, encoding="utf-8-sig",
)

print("=" * 76)
print("步骤14B：多重检验与主规格")
print("=" * 76)
print(
    f"两两比较：原始p<0.05 {int(pairs['原始p小于0.05'].sum())}/54；"
    f"BH全局后 {int(pairs['BH全局通过5%'].sum())}/54；"
    f"Bonferroni后 {int(pairs['Bonferroni通过5%'].sum())}/54"
)
print(
    f"梯度检验：原始p<0.05 {int(gradients['原始p小于0.05'].sum())}/18；"
    f"BH全局后 {int(gradients['BH全局通过5%'].sum())}/18；"
    f"Bonferroni后 {int(gradients['Bonferroni通过5%'].sum())}/18"
)
print("\n主两两比较：")
print(
    main_pair[
        [
            "事件", "基准指数", "事件窗口", "比较名称",
            "A减B差异", "Welch_p值", "p_BH全局",
            "p_Bonferroni全局",
        ]
    ].to_string(index=False)
)
print("\n主梯度检验：")
print(
    main_gradient[
        [
            "事件", "基准指数", "事件窗口", "产业链梯度斜率",
            "p值", "p_BH全局", "p_Bonferroni全局",
        ]
    ].to_string(index=False)
)
print(f"\n输出目录：{OUTPUT_DIR}")

