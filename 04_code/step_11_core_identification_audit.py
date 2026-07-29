# -*- coding: utf-8 -*-
"""
步骤11：核心识别审计（导师意见优先版）

目的：
1. 使用 linearmodels.PanelOLS 正确估计企业固定效应和月份固定效应；
2. 只比较上游与下游，避免把中游混入对照组；
3. 核心模型只解释 Post × Upstream，Post 和 Upstream 主效应分别被时间、
   企业固定效应吸收，不强行报告；
4. 使用三个伪事件日期做安慰剂检验；
5. 使用“事件月份虚拟变量 × 上游”的动态交互项检验平行趋势；
6. 对全部事件前交互项进行联合 Wald 检验；
7. 所有结果写入新目录，不覆盖旧表、旧图和旧日志。
"""

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# 一、路径设置
# ---------------------------------------------------------------------------
BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
INPUT_PATH = BASE_DIR / "02_processed_data" / "monthly_panel_full.csv"
OUTPUT_DIR = BASE_DIR / "05_output" / "revision_audit"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
LOG_PATH = OUTPUT_DIR / "core_identification_audit_log.txt"

TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 二、辅助函数
# ---------------------------------------------------------------------------
def winsorize(series, lower=0.01, upper=0.99):
    """按全样本1%和99%分位数进行缩尾。"""
    return series.clip(series.quantile(lower), series.quantile(upper))


def prepare_panel(data):
    """清洗并设置 PanelOLS 所需的公司—月份双索引。"""
    data = data.drop_duplicates(["Stkcd", "date"]).copy()
    data = data.sort_values(["Stkcd", "date"])
    return data.set_index(["Stkcd", "date"])


def run_did(panel, post_name, dependent="Excess_Ret"):
    """
    估计：
    Y_it = β(Post_t × Upstream_i) + Controls_it + Firm FE + Month FE + ε_it

    注意：
    Post_t 被月份固定效应吸收；
    Upstream_i 被企业固定效应吸收；
    因此只估计并解释二者交互项。
    """
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


def one_result(result, test_name):
    """把核心交互项整理成一行结果。"""
    key = "Post_x_Upstream"
    ci = result.conf_int().loc[key]
    return {
        "检验": test_name,
        "系数": result.params[key],
        "标准误": result.std_errors[key],
        "t值": result.tstats[key],
        "p值": result.pvalues[key],
        "95%CI下限": ci.iloc[0],
        "95%CI上限": ci.iloc[1],
        "观测值": int(result.nobs),
        "公司数": int(result.entity_info["total"]),
    }


# ---------------------------------------------------------------------------
# 三、读取和清洗数据
# ---------------------------------------------------------------------------
df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
df["date"] = pd.to_datetime(df["date"])

required = {
    "Stkcd", "Layer", "date", "Excess_Ret", "Size", "ROA",
    "Leverage", "Post", "event_time"
}
missing = sorted(required.difference(df.columns))
if missing:
    raise ValueError(f"输入文件缺少必要字段：{missing}")

# 本文标题和假说是“上游 vs 下游”，故主模型不混入中游。
df = df[df["Layer"].isin(["上游", "下游"])].copy()
df["Is_Upstream"] = (df["Layer"] == "上游").astype(int)
df["Post"] = df["Post"].astype(int)

for column in ["Size", "ROA", "Leverage"]:
    df[column] = winsorize(df[column])

df = df.dropna(
    subset=[
        "Stkcd", "Layer", "date", "Excess_Ret",
        "Size", "ROA", "Leverage", "Post", "event_time"
    ]
)
panel = prepare_panel(df)

# ---------------------------------------------------------------------------
# 四、正确的双向固定效应基准模型
# ---------------------------------------------------------------------------
base_result = run_did(panel, "Post")
summary_rows = [one_result(base_result, "真实事件：2025年1月")]

# ---------------------------------------------------------------------------
# 五、三个伪事件日期
# ---------------------------------------------------------------------------
# 安慰剂仅使用真实事件发生前的2023—2024年，避免真实冲击污染。
placebo_source = df[
    (df["date"] >= "2023-01-01") & (df["date"] < "2025-01-01")
].copy()

placebo_dates = ["2024-01-01", "2024-06-01", "2024-09-01"]
for date_text in placebo_dates:
    temp = placebo_source.copy()
    temp["Placebo_Post"] = (temp["date"] >= pd.Timestamp(date_text)).astype(int)
    temp_panel = prepare_panel(temp)
    placebo_result = run_did(temp_panel, "Placebo_Post")
    summary_rows.append(
        one_result(placebo_result, f"伪事件：{date_text[:7]}")
    )

summary = pd.DataFrame(summary_rows)
summary.to_csv(
    TABLE_DIR / "table_a1_did_and_placebo.csv",
    index=False,
    encoding="utf-8-sig",
)

# 追加滚动伪事件诊断：用于识别显著伪效应集中在哪些月份。
# 该诊断不替代预先指定的三个正式安慰剂，也不用于挑选“有利日期”。
rolling_rows = []
for placebo_date in pd.date_range("2023-04-01", "2024-09-01", freq="MS"):
    temp = placebo_source.copy()
    temp["Placebo_Post"] = (temp["date"] >= placebo_date).astype(int)
    # 伪事件前后至少各保留3个月，避免极端不平衡窗口。
    pre_months = temp.loc[temp["Placebo_Post"] == 0, "date"].nunique()
    post_months = temp.loc[temp["Placebo_Post"] == 1, "date"].nunique()
    if pre_months < 3 or post_months < 3:
        continue
    result = run_did(prepare_panel(temp), "Placebo_Post")
    row = one_result(result, f"滚动伪事件：{placebo_date:%Y-%m}")
    row["伪事件前月份数"] = pre_months
    row["伪事件后月份数"] = post_months
    rolling_rows.append(row)

rolling_placebo = pd.DataFrame(rolling_rows)
rolling_placebo.to_csv(
    TABLE_DIR / "table_a4_rolling_placebo_diagnosis.csv",
    index=False,
    encoding="utf-8-sig",
)

# ---------------------------------------------------------------------------
# 六、动态DID与平行趋势联合检验
# ---------------------------------------------------------------------------
# 限定对称窗口，避免窗口外月份被错误并入参考组。
event_df = df[df["event_time"].between(-12, 12)].copy()
event_panel = prepare_panel(event_df)

# -1月作为唯一参考期。
event_times = [month for month in range(-12, 13) if month != -1]
event_x = event_panel[["Size", "ROA", "Leverage"]].copy()

for month in event_times:
    event_x[f"Event_{month}_x_Upstream"] = (
        (event_panel["event_time"] == month).astype(int)
        * event_panel["Is_Upstream"]
    )

event_model = PanelOLS(
    event_panel["Excess_Ret"],
    event_x,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
event_result = event_model.fit(
    cov_type="clustered",
    cluster_entity=True,
)

event_rows = []
confidence = event_result.conf_int()
for month in event_times:
    variable = f"Event_{month}_x_Upstream"
    event_rows.append(
        {
            "事件时间": month,
            "系数": event_result.params[variable],
            "标准误": event_result.std_errors[variable],
            "p值": event_result.pvalues[variable],
            "95%CI下限": confidence.loc[variable].iloc[0],
            "95%CI上限": confidence.loc[variable].iloc[1],
        }
    )

event_table = pd.DataFrame(event_rows)
event_table.to_csv(
    TABLE_DIR / "table_a2_dynamic_did.csv",
    index=False,
    encoding="utf-8-sig",
)

# 联合检验 H0：所有事件前交互项系数均为0。
pre_variables = [
    f"Event_{month}_x_Upstream" for month in range(-12, -1)
]
restriction = np.zeros((len(pre_variables), len(event_result.params)))
for row_number, variable in enumerate(pre_variables):
    restriction[row_number, event_result.params.index.get_loc(variable)] = 1

def joint_pretrend_test(start_month):
    """检验从start_month至-2月的所有事前交互项是否联合为0。"""
    variables = [
        f"Event_{month}_x_Upstream"
        for month in range(start_month, -1)
    ]
    matrix = np.zeros((len(variables), len(event_result.params)))
    for row_number, variable in enumerate(variables):
        matrix[row_number, event_result.params.index.get_loc(variable)] = 1
    test = event_result.wald_test(matrix)
    return {
        "检验窗口": f"[{start_month}, -2]",
        "原假设": f"事件前{start_month}月至-2月的交互项系数联合等于0",
        "Wald统计量": float(test.stat),
        "自由度": int(test.df),
        "p值": float(test.pval),
        "是否通过5%标准": "是" if test.pval >= 0.05 else "否",
    }


# 主判定仍使用[-12,-2]；较短窗口只用于定位预趋势来源，不能替代主检验。
pretrend = pd.DataFrame(
    [joint_pretrend_test(start) for start in [-12, -8, -6, -5, -4]]
)
pretrend.to_csv(
    TABLE_DIR / "table_a3_pretrend_joint_test.csv",
    index=False,
    encoding="utf-8-sig",
)

# ---------------------------------------------------------------------------
# 七、绘制合规的动态交互项图
# ---------------------------------------------------------------------------
plot_table = pd.concat(
    [
        event_table,
        pd.DataFrame([{
            "事件时间": -1,
            "系数": 0.0,
            "标准误": np.nan,
            "p值": np.nan,
            "95%CI下限": 0.0,
            "95%CI上限": 0.0,
        }]),
    ],
    ignore_index=True,
).sort_values("事件时间")

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
plt.ylabel("上游相对下游的月度超额收益差异")
plt.title("动态DID与平行趋势检验")
plt.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(
    FIGURE_DIR / "figure_a1_dynamic_did.png",
    dpi=300,
    bbox_inches="tight",
)
plt.close()

# ---------------------------------------------------------------------------
# 八、生成文字日志
# ---------------------------------------------------------------------------
lines = [
    "=" * 72,
    "核心识别审计日志",
    "=" * 72,
    f"输入文件：{INPUT_PATH}",
    f"样本期间：{df['date'].min().date()} 至 {df['date'].max().date()}",
    f"样本公司：{df['Stkcd'].nunique()}家（上游与下游）",
    f"观测值：{len(df)}",
    "",
    "【基准DID与安慰剂】",
    summary.to_string(index=False),
    "",
    "【平行趋势联合检验】",
    pretrend.to_string(index=False),
    "",
    "【显著的滚动伪事件（p<0.10）】",
    rolling_placebo.loc[
        rolling_placebo["p值"] < 0.10,
        ["检验", "系数", "标准误", "p值", "伪事件前月份数", "伪事件后月份数"],
    ].to_string(index=False),
    "",
    "判定规则：",
    "1. 基准交互项方向与理论一致且p<0.05；",
    "2. 三个安慰剂交互项原则上均应p>=0.10；",
    "3. 事件前联合Wald检验应p>=0.05；",
    "4. 若第2或第3项失败，不得宣称严格因果效应或平行趋势成立。",
    "=" * 72,
]
LOG_PATH.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print(f"\n结果目录：{OUTPUT_DIR}")
