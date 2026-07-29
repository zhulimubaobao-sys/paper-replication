# -*- coding: utf-8 -*-
"""
步骤13B：两个预先指定事件日的日度事件研究

事件：
1. 2024-12-26：DeepSeek-V3更新；
2. 2025-01-20：DeepSeek-R1发布。

三个指数全部报告，不根据显著性选择：
000001.SH、000300.SH、399001.SZ。
市场模型估计窗口：[-250,-30]个基准指数交易日。
事件窗口：[-1,+1]、[-3,+3]、[-5,+5]。
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
STOCK_PATH = BASE_DIR / "01_raw_data" / "stock" / "zongdegupiao.csv"
INDEX_PATH = BASE_DIR / "01_raw_data" / "stock" / "dapanzhishu.csv"
PANEL_PATH = (
    BASE_DIR / "02_processed_data" / "monthly_panel_return_corrected.csv"
)
OUTPUT_DIR = BASE_DIR / "05_output" / "revision_step13b"
TABLE_DIR = OUTPUT_DIR / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)

EVENTS = {
    "DeepSeek-V3_2024-12-26": pd.Timestamp("2024-12-26"),
    "DeepSeek-R1_2025-01-20": pd.Timestamp("2025-01-20"),
}
BENCHMARKS = ["000001.SH", "000300.SH", "399001.SZ"]
WINDOWS = [1, 3, 5]


def normalize_code(s):
    return (
        s.astype(str).str.replace(r"\.SZ|\.SH", "", regex=True)
        .str.replace(r"\.0$", "", regex=True).str.zfill(6)
    )


stock = pd.read_csv(STOCK_PATH, encoding="utf-8-sig")
index = pd.read_csv(INDEX_PATH, encoding="utf-8-sig")
panel = pd.read_csv(PANEL_PATH, encoding="utf-8-sig")

stock["date"] = pd.to_datetime(stock["time"])
index["date"] = pd.to_datetime(index["time"])
stock["Stkcd"] = normalize_code(stock["thscode"])
panel["Stkcd"] = normalize_code(panel["Stkcd"])
stock["Stock_Ret"] = pd.to_numeric(stock["changeRatio"], errors="coerce") / 100
index["Market_Ret"] = pd.to_numeric(index["changeRatio"], errors="coerce") / 100

layer_map = (
    panel[panel["Layer"].isin(["上游", "中游", "下游"])]
    [["Stkcd", "Layer"]].drop_duplicates("Stkcd")
)
stock = stock.merge(layer_map, on="Stkcd", how="inner")

firm_rows = []
comparison_rows = []
trend_rows = []
quality_rows = []

for benchmark in BENCHMARKS:
    market = (
        index[index["thscode"].astype(str) == benchmark]
        [["date", "Market_Ret"]].dropna().drop_duplicates("date")
        .sort_values("date").reset_index(drop=True)
    )
    market["market_day"] = np.arange(len(market))

    for event_name, event_date in EVENTS.items():
        if event_date not in set(market["date"]):
            raise ValueError(f"{event_name}不是{benchmark}的交易日。")
        event_day = int(
            market.loc[market["date"] == event_date, "market_day"].iloc[0]
        )
        market_event = market.copy()
        market_event["relative_day"] = market_event["market_day"] - event_day
        merged = stock.merge(market_event, on="date", how="inner")

        event_firm_rows = []
        for (code, layer), firm in merged.groupby(["Stkcd", "Layer"]):
            estimation = firm[
                firm["relative_day"].between(-250, -30)
            ].dropna(subset=["Stock_Ret", "Market_Ret"])
            if len(estimation) < 120:
                quality_rows.append({
                    "事件": event_name, "基准指数": benchmark,
                    "Stkcd": code, "Layer": layer,
                    "估计窗口观测值": len(estimation), "状态": "不足120",
                })
                continue
            x = estimation["Market_Ret"].to_numpy()
            y = estimation["Stock_Ret"].to_numpy()
            design = np.column_stack([np.ones(len(x)), x])
            alpha, beta = np.linalg.lstsq(design, y, rcond=None)[0]

            event_part = firm[
                firm["relative_day"].between(-5, 5)
            ].copy()
            event_part["Abnormal_Ret"] = (
                event_part["Stock_Ret"]
                - alpha - beta * event_part["Market_Ret"]
            )
            row = {
                "事件": event_name, "事件日期": event_date.date(),
                "基准指数": benchmark, "Stkcd": code, "Layer": layer,
                "Alpha": alpha, "Beta": beta,
                "估计窗口观测值": len(estimation),
            }
            for w in WINDOWS:
                values = event_part.loc[
                    event_part["relative_day"].between(-w, w),
                    "Abnormal_Ret",
                ]
                row[f"CAR[-{w},+{w}]"] = values.sum()
                row[f"窗口交易日数[-{w},+{w}]"] = len(values)
            event_firm_rows.append(row)
            firm_rows.append(row)

        event_firms = pd.DataFrame(event_firm_rows)
        for w in WINDOWS:
            car_col = f"CAR[-{w},+{w}]"
            for group_a, group_b in [
                ("上游", "下游"), ("上游", "中游"), ("中游", "下游")
            ]:
                a = event_firms.loc[event_firms["Layer"] == group_a, car_col]
                b = event_firms.loc[event_firms["Layer"] == group_b, car_col]
                test = stats.ttest_ind(
                    a, b, equal_var=False, nan_policy="omit"
                )
                diff = a.mean() - b.mean()
                se = np.sqrt(
                    a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)
                )
                comparison_rows.append({
                    "事件": event_name,
                    "事件日期": event_date.date(),
                    "基准指数": benchmark,
                    "事件窗口": f"[-{w},+{w}]",
                    "比较组A": group_a,
                    "比较组B": group_b,
                    "比较名称": f"{group_a} vs {group_b}",
                    "A组公司数": a.notna().sum(),
                    "B组公司数": b.notna().sum(),
                    "A组平均CAR": a.mean(),
                    "B组平均CAR": b.mean(),
                    "A减B差异": diff,
                    "差异标准误": se,
                    "Welch_t值": test.statistic,
                    "Welch_p值": test.pvalue,
                })

            # 下游=0、中游=1、上游=2，仅检验单调梯度。
            trend_data = event_firms[["Layer", car_col]].dropna().copy()
            trend_data["Layer_Score"] = trend_data["Layer"].map(
                {"下游": 0, "中游": 1, "上游": 2}
            )
            trend = stats.linregress(
                trend_data["Layer_Score"], trend_data[car_col]
            )
            trend_rows.append({
                "事件": event_name,
                "事件日期": event_date.date(),
                "基准指数": benchmark,
                "事件窗口": f"[-{w},+{w}]",
                "公司数": len(trend_data),
                "产业链梯度斜率": trend.slope,
                "标准误": trend.stderr,
                "t值": trend.slope / trend.stderr,
                "p值": trend.pvalue,
                "R平方": trend.rvalue ** 2,
            })

firm_car = pd.DataFrame(firm_rows)
comparisons = pd.DataFrame(comparison_rows)
trends = pd.DataFrame(trend_rows)
quality = pd.DataFrame(
    quality_rows,
    columns=[
        "事件", "基准指数", "Stkcd", "Layer",
        "估计窗口观测值", "状态",
    ],
)

firm_car.to_csv(
    TABLE_DIR / "table_d1_firm_level_car.csv",
    index=False, encoding="utf-8-sig",
)
comparisons.to_csv(
    TABLE_DIR / "table_d2_upstream_downstream_car_comparison.csv",
    index=False, encoding="utf-8-sig",
)
trends.to_csv(
    TABLE_DIR / "table_d3_layer_gradient_tests.csv",
    index=False, encoding="utf-8-sig",
)
quality.to_csv(
    TABLE_DIR / "table_d4_daily_data_quality_exclusions.csv",
    index=False, encoding="utf-8-sig",
)

print("=" * 76)
print("步骤13B：日度事件研究")
print("=" * 76)
print(f"公司层CAR记录：{len(firm_car)}")
print(f"两两比较规格数量：{len(comparisons)}")
print(f"产业链梯度规格数量：{len(trends)}")
print(f"估计窗口不足的公司—事件—指数：{len(quality)}")
print("\n全部54个两两比较规格：")
print(comparisons.to_string(index=False))
print("\n全部18个产业链梯度规格：")
print(trends.to_string(index=False))
print(f"\n输出目录：{OUTPUT_DIR}")
