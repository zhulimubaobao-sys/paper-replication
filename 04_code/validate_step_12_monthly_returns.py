# -*- coding: utf-8 -*-
"""
步骤12独立核验程序

核验内容：
1. 输出文件是否完整；
2. 新面板是否保持公司—月份唯一；
3. 修正超额收益是否严格等于个股月收益减指数月收益；
4. 随机抽取10个公司—月份，直接用原始日度数据重新复合；
5. 汇总修正后的DID、安慰剂和平行趋势结论。
"""

from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
STOCK_PATH = BASE_DIR / "01_raw_data" / "stock" / "zongdegupiao.csv"
INDEX_PATH = BASE_DIR / "01_raw_data" / "stock" / "dapanzhishu.csv"
BENCHMARK_CODE = "000001.SH"
PANEL_PATH = (
    BASE_DIR / "02_processed_data" / "monthly_panel_return_corrected.csv"
)
OUTPUT_DIR = BASE_DIR / "05_output" / "revision_step12"
TABLE_DIR = OUTPUT_DIR / "tables"

required_files = [
    PANEL_PATH,
    TABLE_DIR / "table_b1_old_new_return_comparison.csv",
    TABLE_DIR / "table_b2_largest_return_differences.csv",
    TABLE_DIR / "table_b3_corrected_did_and_placebo.csv",
    TABLE_DIR / "table_b4_corrected_rolling_placebo.csv",
    TABLE_DIR / "table_b5_corrected_dynamic_did.csv",
    TABLE_DIR / "table_b6_corrected_pretrend_tests.csv",
    OUTPUT_DIR / "figures" / "figure_b1_corrected_dynamic_did.png",
    OUTPUT_DIR / "step12_rebuild_and_identification_log.txt",
]


def normalize_code(series):
    """统一股票代码格式。"""
    return (
        series.astype(str)
        .str.replace(r"\.SZ|\.SH", "", regex=True)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )


def compound(series):
    """复合日收益。"""
    return (1.0 + series.dropna()).prod() - 1.0


print("=" * 76)
print("步骤12：月度收益重建核验")
print("=" * 76)

missing = [path for path in required_files if not path.exists()]
if missing:
    print("❌ 缺少输出文件：")
    for path in missing:
        print(f"  - {path}")
    raise SystemExit(1)

print("\n【文件完整性】")
for path in required_files:
    print(f"✅ {path}")

panel = pd.read_csv(PANEL_PATH, encoding="utf-8-sig")
panel["Stkcd"] = normalize_code(panel["Stkcd"])
panel["date"] = pd.to_datetime(panel["date"])

duplicate_count = int(panel.duplicated(["Stkcd", "date"]).sum())
identity_error = (
    panel["Excess_Ret_Corrected"]
    - (
        panel["Stock_Ret_Corrected"]
        - panel["Index_Ret_Corrected"]
    )
).abs()
identity_pass = bool(identity_error.max() < 1e-12)

# 固定随机种子，保证每次抽样核验一致。
sample = panel.sample(n=min(10, len(panel)), random_state=20250727)
stock = pd.read_csv(STOCK_PATH, encoding="utf-8-sig")
index = pd.read_csv(INDEX_PATH, encoding="utf-8-sig")
index = index[index["thscode"].astype(str) == BENCHMARK_CODE].copy()
stock["Stkcd"] = normalize_code(stock["thscode"])
stock["date_daily"] = pd.to_datetime(stock["time"])
index["date_daily"] = pd.to_datetime(index["time"])
stock["ret_daily"] = pd.to_numeric(
    stock["changeRatio"], errors="coerce"
) / 100.0
index["ret_daily"] = pd.to_numeric(
    index["changeRatio"], errors="coerce"
) / 100.0

sample_rows = []
for _, row in sample.iterrows():
    year = row["date"].year
    month = row["date"].month
    stock_days = stock[
        (stock["Stkcd"] == row["Stkcd"])
        & (stock["date_daily"].dt.year == year)
        & (stock["date_daily"].dt.month == month)
    ]
    index_days = index[
        (index["date_daily"].dt.year == year)
        & (index["date_daily"].dt.month == month)
    ]
    stock_recalculated = compound(stock_days["ret_daily"])
    index_recalculated = compound(index_days["ret_daily"])
    excess_recalculated = stock_recalculated - index_recalculated
    error = abs(excess_recalculated - row["Excess_Ret_Corrected"])
    sample_rows.append(
        {
            "Stkcd": row["Stkcd"],
            "date": row["date"].strftime("%Y-%m"),
            "面板修正超额收益": row["Excess_Ret_Corrected"],
            "日度数据重算值": excess_recalculated,
            "绝对误差": error,
            "通过": "是" if error < 1e-12 else "否",
        }
    )

sample_check = pd.DataFrame(sample_rows)
sample_check.to_csv(
    TABLE_DIR / "table_b7_manual_recalculation_check.csv",
    index=False,
    encoding="utf-8-sig",
)
sample_pass = bool((sample_check["绝对误差"] < 1e-12).all())

did = pd.read_csv(
    TABLE_DIR / "table_b3_corrected_did_and_placebo.csv",
    encoding="utf-8-sig",
)
rolling = pd.read_csv(
    TABLE_DIR / "table_b4_corrected_rolling_placebo.csv",
    encoding="utf-8-sig",
)
dynamic = pd.read_csv(
    TABLE_DIR / "table_b5_corrected_dynamic_did.csv",
    encoding="utf-8-sig",
)
pretrend = pd.read_csv(
    TABLE_DIR / "table_b6_corrected_pretrend_tests.csv",
    encoding="utf-8-sig",
)

true_row = did[did["检验"].str.startswith("真实事件")].iloc[0]
placebos = did[did["检验"].str.startswith("伪事件")]
main_pretrend = pretrend[
    pretrend["检验窗口"] == "[-12, -2]"
].iloc[0]

base_pass = bool(true_row["系数"] > 0 and true_row["p值"] < 0.05)
placebo_pass = bool((placebos["p值"] >= 0.10).all())
pretrend_pass = bool(main_pretrend["p值"] >= 0.05)
dynamic_complete = bool(
    len(dynamic) == 24
    and dynamic["事件时间"].nunique() == 24
    and not dynamic[["系数", "标准误", "p值"]].isna().any().any()
)

print("\n【数据结构与计算核验】")
print(f"{'✅' if duplicate_count == 0 else '❌'} 公司—月份重复数：{duplicate_count}")
print(
    f"{'✅' if identity_pass else '❌'} 收益恒等式最大误差："
    f"{identity_error.max():.16f}"
)
print(
    f"{'✅' if sample_pass else '❌'} 10个公司—月份日度重算："
    f"{'全部通过' if sample_pass else '存在不一致'}"
)

print("\n【修正收益后的核心识别】")
print(
    f"{'✅' if base_pass else '❌'} 基准交互项："
    f"系数={true_row['系数']:.6f}，p={true_row['p值']:.6f}"
)
for _, row in placebos.iterrows():
    passed = row["p值"] >= 0.10
    print(
        f"{'✅' if passed else '❌'} {row['检验']}："
        f"系数={row['系数']:.6f}，p={row['p值']:.6f}"
    )
print(
    f"{'✅' if pretrend_pass else '❌'} 主平行趋势联合检验："
    f"p={main_pretrend['p值']:.6f}"
)
print(
    f"{'✅' if dynamic_complete else '❌'} 动态DID结果完整"
)
print(
    f"滚动伪事件显著数（p<0.10）："
    f"{int((rolling['p值'] < 0.10).sum())}/{len(rolling)}"
)

calculation_pass = duplicate_count == 0 and identity_pass and sample_pass
identification_pass = (
    base_pass and placebo_pass and pretrend_pass and dynamic_complete
)

print("\n【最终判定】")
if calculation_pass:
    print("✅ 月度超额收益重建通过计算核验。")
else:
    print("❌ 月度超额收益重建未通过计算核验，不能继续使用。")

if identification_pass:
    print("✅ 修正收益后的核心识别通过，可以进入下一项稳健性检验。")
else:
    print("❌ 修正收益后的核心识别仍未通过。")
    print("   若计算核验已通过，说明识别问题并非由旧收益公式单独造成。")
    print("   下一步应转向样本分类审计和日度事件研究。")

print("=" * 76)
# 程序本身正常完成时返回0；科学判定另行展示。
raise SystemExit(0)
