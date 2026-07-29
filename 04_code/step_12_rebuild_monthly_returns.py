# -*- coding: utf-8 -*-
"""
步骤12：重建规范月度超额收益，并自动重跑核心识别审计

重要原则：
1. 不覆盖 monthly_panel_full.csv；
2. 保留旧 Ret 和 Excess_Ret，便于追溯；
3. 个股和指数分别由日收益复合为月收益，再计算二者之差；
4. 使用修正收益自动重跑双向固定效应、安慰剂和动态DID；
5. 所有结果写入 revision_step12 新目录。
"""

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

warnings.filterwarnings("ignore")

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
STOCK_PATH = BASE_DIR / "01_raw_data" / "stock" / "zongdegupiao.csv"
INDEX_PATH = BASE_DIR / "01_raw_data" / "stock" / "dapanzhishu.csv"
# 与旧版构造程序实际保留的首个指数一致，明确指定上证综合指数，
# 禁止对多个指数按日期任意去重。其他指数可在后续作为稳健性口径。
BENCHMARK_CODE = "000001.SH"
OLD_PANEL_PATH = BASE_DIR / "02_processed_data" / "monthly_panel_full.csv"
NEW_PANEL_PATH = (
    BASE_DIR / "02_processed_data" / "monthly_panel_return_corrected.csv"
)

OUTPUT_DIR = BASE_DIR / "05_output" / "revision_step12"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
LOG_PATH = OUTPUT_DIR / "step12_rebuild_and_identification_log.txt"
TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def read_csv_flexible(path):
    """依次尝试常见编码，避免中文Windows环境下读取失败。"""
    for encoding in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"无法识别编码：{path}")


def normalize_stock_code(series):
    """统一为6位股票代码，去除交易所后缀。"""
    return (
        series.astype(str)
        .str.replace(r"\.SZ|\.SH", "", regex=True)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )


def compound_return(series):
    """把小数形式的日收益复合为月收益。"""
    clean = series.dropna()
    if clean.empty:
        return np.nan
    return (1.0 + clean).prod() - 1.0


def winsorize(series, lower=0.01, upper=0.99):
    """按1%和99%分位数缩尾。"""
    return series.clip(series.quantile(lower), series.quantile(upper))


def prepare_panel(data):
    """设置公司—月份面板索引。"""
    data = data.drop_duplicates(["Stkcd", "date"]).copy()
    return data.sort_values(["Stkcd", "date"]).set_index(["Stkcd", "date"])


def run_did(panel, post_name, dependent="Excess_Ret"):
    """企业固定效应、月份固定效应及企业聚类标准误。"""
    x = panel[["Size", "ROA", "Leverage"]].copy()
    x["Post_x_Upstream"] = panel[post_name] * panel["Is_Upstream"]
    model = PanelOLS(
        panel[dependent],
        x,
        entity_effects=True,
        time_effects=True,
        drop_absorbed=True,
    )
    return model.fit(cov_type="clustered", cluster_entity=True)


def result_row(result, label):
    """提取核心交互项。"""
    key = "Post_x_Upstream"
    ci = result.conf_int().loc[key]
    return {
        "检验": label,
        "系数": result.params[key],
        "标准误": result.std_errors[key],
        "t值": result.tstats[key],
        "p值": result.pvalues[key],
        "95%CI下限": ci.iloc[0],
        "95%CI上限": ci.iloc[1],
        "观测值": int(result.nobs),
    }


print("=" * 76)
print("步骤12：重建规范月度超额收益并自动重跑核心识别")
print("=" * 76)

# ---------------------------------------------------------------------------
# 一、读取并清洗日度数据
# ---------------------------------------------------------------------------
stock = read_csv_flexible(STOCK_PATH)
index = read_csv_flexible(INDEX_PATH)
old_panel = read_csv_flexible(OLD_PANEL_PATH)

stock["date_daily"] = pd.to_datetime(stock["time"], errors="coerce")
index["date_daily"] = pd.to_datetime(index["time"], errors="coerce")
stock["Stkcd"] = normalize_stock_code(stock["thscode"])
old_panel["Stkcd"] = normalize_stock_code(old_panel["Stkcd"])

# changeRatio是百分数，例如1.5表示1.5%，必须除以100。
stock["Daily_Stock_Ret"] = pd.to_numeric(
    stock["changeRatio"], errors="coerce"
) / 100.0
index["Daily_Index_Ret"] = pd.to_numeric(
    index["changeRatio"], errors="coerce"
) / 100.0

available_index_codes = sorted(index["thscode"].dropna().astype(str).unique())
if BENCHMARK_CODE not in available_index_codes:
    raise ValueError(
        f"指数文件中不存在指定基准{BENCHMARK_CODE}；"
        f"可用代码为{available_index_codes}"
    )
index = index[index["thscode"].astype(str) == BENCHMARK_CODE].copy()

stock = stock.dropna(subset=["date_daily", "Stkcd", "Daily_Stock_Ret"])
index = index.dropna(subset=["date_daily", "Daily_Index_Ret"])
stock["year"] = stock["date_daily"].dt.year
stock["month"] = stock["date_daily"].dt.month
index["year"] = index["date_daily"].dt.year
index["month"] = index["date_daily"].dt.month

# 同一股票同一交易日只能有一条记录。
stock_duplicate_days = int(stock.duplicated(["Stkcd", "date_daily"]).sum())
index_duplicate_days = int(index.duplicated(["date_daily"]).sum())
if stock_duplicate_days:
    stock = stock.drop_duplicates(["Stkcd", "date_daily"], keep="last")
if index_duplicate_days:
    index = index.drop_duplicates(["date_daily"], keep="last")

# ---------------------------------------------------------------------------
# 二、分别复合个股和指数月收益
# ---------------------------------------------------------------------------
stock_monthly = (
    stock.groupby(["Stkcd", "year", "month"], as_index=False)
    .agg(
        Stock_Ret_Corrected=("Daily_Stock_Ret", compound_return),
        Stock_Trading_Days=("Daily_Stock_Ret", "count"),
    )
)

index_monthly = (
    index.groupby(["year", "month"], as_index=False)
    .agg(
        Index_Ret_Corrected=("Daily_Index_Ret", compound_return),
        Index_Trading_Days=("Daily_Index_Ret", "count"),
    )
)

returns = stock_monthly.merge(
    index_monthly,
    on=["year", "month"],
    how="left",
    validate="many_to_one",
)
returns["Excess_Ret_Corrected"] = (
    returns["Stock_Ret_Corrected"] - returns["Index_Ret_Corrected"]
)

# ---------------------------------------------------------------------------
# 三、合并到旧面板并保留旧口径
# ---------------------------------------------------------------------------
old_panel["Ret_Old"] = old_panel["Ret"]
old_panel["Excess_Ret_Old"] = old_panel["Excess_Ret"]

new_panel = old_panel.merge(
    returns,
    on=["Stkcd", "year", "month"],
    how="left",
    validate="one_to_one",
)

unmatched = int(new_panel["Excess_Ret_Corrected"].isna().sum())
if unmatched:
    raise ValueError(f"有{unmatched}条月度面板记录未匹配到修正收益，停止输出。")

# 为兼容后续PanelOLS程序，Ret和Excess_Ret替换为新口径；
# 原值已经保存在Ret_Old和Excess_Ret_Old中。
new_panel["Ret"] = new_panel["Stock_Ret_Corrected"]
new_panel["Excess_Ret"] = new_panel["Excess_Ret_Corrected"]
new_panel.to_csv(NEW_PANEL_PATH, index=False, encoding="utf-8-sig")

# 新旧口径差异表。
new_panel["Excess_Ret_Difference"] = (
    new_panel["Excess_Ret_Corrected"] - new_panel["Excess_Ret_Old"]
)
comparison = pd.DataFrame(
    {
        "指标": [
            "观测值",
            "旧口径均值",
            "新口径均值",
            "差值均值",
            "差值绝对值均值",
            "差值绝对值最大值",
            "新旧口径相关系数",
        ],
        "数值": [
            len(new_panel),
            new_panel["Excess_Ret_Old"].mean(),
            new_panel["Excess_Ret_Corrected"].mean(),
            new_panel["Excess_Ret_Difference"].mean(),
            new_panel["Excess_Ret_Difference"].abs().mean(),
            new_panel["Excess_Ret_Difference"].abs().max(),
            new_panel[
                ["Excess_Ret_Old", "Excess_Ret_Corrected"]
            ].corr().iloc[0, 1],
        ],
    }
)
comparison.to_csv(
    TABLE_DIR / "table_b1_old_new_return_comparison.csv",
    index=False,
    encoding="utf-8-sig",
)

largest_differences = new_panel.nlargest(
    20, "Excess_Ret_Difference", keep="all"
)[
    [
        "Stkcd", "Layer", "date", "Excess_Ret_Old",
        "Excess_Ret_Corrected", "Excess_Ret_Difference",
    ]
]
largest_differences.to_csv(
    TABLE_DIR / "table_b2_largest_return_differences.csv",
    index=False,
    encoding="utf-8-sig",
)

# ---------------------------------------------------------------------------
# 四、用修正收益重跑基准DID和安慰剂
# ---------------------------------------------------------------------------
audit = new_panel[new_panel["Layer"].isin(["上游", "下游"])].copy()
audit["date"] = pd.to_datetime(audit["date"])
audit["Is_Upstream"] = (audit["Layer"] == "上游").astype(int)
audit["Post"] = audit["Post"].astype(int)
for column in ["Size", "ROA", "Leverage"]:
    audit[column] = winsorize(audit[column])
audit = audit.dropna(
    subset=[
        "Excess_Ret", "Size", "ROA", "Leverage",
        "Post", "event_time", "date",
    ]
)

audit_panel = prepare_panel(audit)
base_result = run_did(audit_panel, "Post")
did_rows = [result_row(base_result, "真实事件：2025年1月")]

placebo_source = audit[
    (audit["date"] >= "2023-01-01") & (audit["date"] < "2025-01-01")
].copy()

for date_text in ["2024-01-01", "2024-06-01", "2024-09-01"]:
    temp = placebo_source.copy()
    temp["Placebo_Post"] = (
        temp["date"] >= pd.Timestamp(date_text)
    ).astype(int)
    result = run_did(prepare_panel(temp), "Placebo_Post")
    did_rows.append(result_row(result, f"伪事件：{date_text[:7]}"))

did_table = pd.DataFrame(did_rows)
did_table.to_csv(
    TABLE_DIR / "table_b3_corrected_did_and_placebo.csv",
    index=False,
    encoding="utf-8-sig",
)

# 滚动伪事件仅用于诊断，不能用于事后挑选日期。
rolling_rows = []
for placebo_date in pd.date_range("2023-04-01", "2024-09-01", freq="MS"):
    temp = placebo_source.copy()
    temp["Placebo_Post"] = (temp["date"] >= placebo_date).astype(int)
    pre_months = temp.loc[temp["Placebo_Post"] == 0, "date"].nunique()
    post_months = temp.loc[temp["Placebo_Post"] == 1, "date"].nunique()
    if pre_months < 3 or post_months < 3:
        continue
    row = result_row(
        run_did(prepare_panel(temp), "Placebo_Post"),
        f"滚动伪事件：{placebo_date:%Y-%m}",
    )
    row["伪事件前月份数"] = pre_months
    row["伪事件后月份数"] = post_months
    rolling_rows.append(row)

rolling_table = pd.DataFrame(rolling_rows)
rolling_table.to_csv(
    TABLE_DIR / "table_b4_corrected_rolling_placebo.csv",
    index=False,
    encoding="utf-8-sig",
)

# ---------------------------------------------------------------------------
# 五、用修正收益重跑动态DID和平行趋势联合检验
# ---------------------------------------------------------------------------
event_data = audit[audit["event_time"].between(-12, 12)].copy()
event_panel = prepare_panel(event_data)
event_times = [month for month in range(-12, 13) if month != -1]
event_x = event_panel[["Size", "ROA", "Leverage"]].copy()

for month in event_times:
    event_x[f"Event_{month}_x_Upstream"] = (
        (event_panel["event_time"] == month).astype(int)
        * event_panel["Is_Upstream"]
    )

event_result = PanelOLS(
    event_panel["Excess_Ret"],
    event_x,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
).fit(cov_type="clustered", cluster_entity=True)

event_rows = []
event_ci = event_result.conf_int()
for month in event_times:
    variable = f"Event_{month}_x_Upstream"
    event_rows.append(
        {
            "事件时间": month,
            "系数": event_result.params[variable],
            "标准误": event_result.std_errors[variable],
            "p值": event_result.pvalues[variable],
            "95%CI下限": event_ci.loc[variable].iloc[0],
            "95%CI上限": event_ci.loc[variable].iloc[1],
        }
    )
event_table = pd.DataFrame(event_rows)
event_table.to_csv(
    TABLE_DIR / "table_b5_corrected_dynamic_did.csv",
    index=False,
    encoding="utf-8-sig",
)


def joint_test(start_month):
    """联合检验指定事前窗口。"""
    variables = [
        f"Event_{month}_x_Upstream"
        for month in range(start_month, -1)
    ]
    restriction = np.zeros((len(variables), len(event_result.params)))
    for row_number, variable in enumerate(variables):
        restriction[
            row_number, event_result.params.index.get_loc(variable)
        ] = 1
    test = event_result.wald_test(restriction)
    return {
        "检验窗口": f"[{start_month}, -2]",
        "Wald统计量": float(test.stat),
        "自由度": int(test.df),
        "p值": float(test.pval),
        "是否通过5%标准": "是" if test.pval >= 0.05 else "否",
    }


pretrend_table = pd.DataFrame(
    [joint_test(start) for start in [-12, -8, -6, -5, -4]]
)
pretrend_table.to_csv(
    TABLE_DIR / "table_b6_corrected_pretrend_tests.csv",
    index=False,
    encoding="utf-8-sig",
)

# ---------------------------------------------------------------------------
# 六、绘图
# ---------------------------------------------------------------------------
plot_table = pd.concat(
    [
        event_table,
        pd.DataFrame(
            [{
                "事件时间": -1,
                "系数": 0.0,
                "标准误": np.nan,
                "p值": np.nan,
                "95%CI下限": 0.0,
                "95%CI上限": 0.0,
            }]
        ),
    ],
    ignore_index=True,
).sort_values("事件时间")

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"
]
plt.rcParams["axes.unicode_minus"] = False
plt.figure(figsize=(11, 6))
plt.axhline(0, color="black", linestyle="--", linewidth=1)
plt.axvline(0, color="#C0392B", linestyle="--", linewidth=1.3)
plt.errorbar(
    plot_table["事件时间"],
    plot_table["系数"],
    yerr=[
        plot_table["系数"] - plot_table["95%CI下限"],
        plot_table["95%CI上限"] - plot_table["系数"],
    ],
    fmt="o",
    color="#2E86AB",
    ecolor="#2E86AB",
    capsize=3,
)
plt.xlabel("相对事件月份（-1月为参考期）")
plt.ylabel("上游相对下游的修正月度超额收益差异")
plt.title("修正收益口径后的动态DID")
plt.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(
    FIGURE_DIR / "figure_b1_corrected_dynamic_did.png",
    dpi=300,
    bbox_inches="tight",
)
plt.close()

# ---------------------------------------------------------------------------
# 七、日志及自动判定
# ---------------------------------------------------------------------------
formal_placebos = did_table[did_table["检验"].str.startswith("伪事件")]
base_pass = bool(
    did_table.iloc[0]["系数"] > 0 and did_table.iloc[0]["p值"] < 0.05
)
placebo_pass = bool((formal_placebos["p值"] >= 0.10).all())
main_pretrend = pretrend_table[
    pretrend_table["检验窗口"] == "[-12, -2]"
].iloc[0]
pretrend_pass = bool(main_pretrend["p值"] >= 0.05)
overall = base_pass and placebo_pass and pretrend_pass

lines = [
    "=" * 76,
    "步骤12：修正收益口径与核心识别日志",
    "=" * 76,
    f"旧面板：{OLD_PANEL_PATH}",
    f"新面板：{NEW_PANEL_PATH}",
    f"指数文件包含：{available_index_codes}",
    f"本次明确使用的基准指数：{BENCHMARK_CODE}",
    f"日度个股重复记录：{stock_duplicate_days}",
    f"日度指数重复记录：{index_duplicate_days}",
    f"未匹配月度收益记录：{unmatched}",
    "",
    "【新旧收益口径比较】",
    comparison.to_string(index=False),
    "",
    "【修正收益后的DID与正式安慰剂】",
    did_table.to_string(index=False),
    "",
    "【修正收益后的事前联合检验】",
    pretrend_table.to_string(index=False),
    "",
    f"滚动伪事件显著数（p<0.10）："
    f"{int((rolling_table['p值'] < 0.10).sum())}/{len(rolling_table)}",
    "",
    "【最终判定】",
    f"基准交互项：{'通过' if base_pass else '未通过'}",
    f"三个正式安慰剂：{'通过' if placebo_pass else '未通过'}",
    f"事前联合检验：{'通过' if pretrend_pass else '未通过'}",
    f"总体：{'通过' if overall else '未通过'}",
    "=" * 76,
]
LOG_PATH.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(f"\n全部输出目录：{OUTPUT_DIR}")
