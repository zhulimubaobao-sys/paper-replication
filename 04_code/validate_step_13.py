# -*- coding: utf-8 -*-
"""步骤13A与13B联合核验。"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"D:/thailand study/26_7_23paper")
A = BASE_DIR / "05_output" / "revision_step13a" / "tables"
B = BASE_DIR / "05_output" / "revision_step13b" / "tables"

files = [
    A / "table_c1_firm_layer_and_coverage.csv",
    A / "table_c2_layer_balance.csv",
    A / "table_c3_pretrend_firm_contribution.csv",
    A / "table_c4_leave_one_firm_out.csv",
    A / "table_c5_classification_evidence_gap.csv",
    B / "table_d1_firm_level_car.csv",
    B / "table_d2_upstream_downstream_car_comparison.csv",
    B / "table_d3_layer_gradient_tests.csv",
    B / "table_d4_daily_data_quality_exclusions.csv",
]

print("=" * 76)
print("步骤13联合核验")
print("=" * 76)
missing = [p for p in files if not p.exists()]
if missing:
    print("❌ 缺少文件：")
    for p in missing:
        print(p)
    raise SystemExit(1)

firm = pd.read_csv(files[0], encoding="utf-8-sig")
loo = pd.read_csv(files[3], encoding="utf-8-sig")
gaps = pd.read_csv(files[4], encoding="utf-8-sig")
car = pd.read_csv(files[5], encoding="utf-8-sig")
cmp = pd.read_csv(files[6], encoding="utf-8-sig")
trends = pd.read_csv(files[7], encoding="utf-8-sig")
try:
    quality = pd.read_csv(files[8], encoding="utf-8-sig")
except pd.errors.EmptyDataError:
    quality = pd.DataFrame(
        columns=[
            "事件", "基准指数", "Stkcd", "Layer",
            "估计窗口观测值", "状态",
        ]
    )

print("\n【样本分类审计】")
print(f"{'✅' if firm['Stkcd'].nunique() == 60 else '❌'} 公司数：{firm['Stkcd'].nunique()}")
print(f"上游/中游/下游：{firm.groupby('Layer')['Stkcd'].nunique().to_dict()}")
print(
    f"留一公司上游系数范围：{loo['上游相对下游系数'].min():.6f} 至 "
    f"{loo['上游相对下游系数'].max():.6f}"
)
print(
    f"留一后上游差异p>=0.05："
    f"{int((loo['上游相对下游p值'] >= 0.05).sum())}/{len(loo)}"
)
print(
    f"{'❌' if (gaps['当前文件是否具备'] == '否').any() else '✅'} "
    "分类证据字段完整性"
)

print("\n【日度事件研究完整性】")
print(f"{'✅' if len(cmp) == 54 else '❌'} 两两比较规格：{len(cmp)}/54")
print(f"{'✅' if len(trends) == 18 else '❌'} 梯度检验规格：{len(trends)}/18")
print(f"公司层CAR记录：{len(car)}")
print(f"估计窗口不足记录：{len(quality)}")
print(f"两两比较p<0.05：{int((cmp['Welch_p值'] < 0.05).sum())}/54")
print(f"梯度检验p<0.05：{int((trends['p值'] < 0.05).sum())}/18")

print("\n【全部规格简表】")
print(
    cmp[
        ["事件", "基准指数", "事件窗口", "比较名称", "A减B差异", "Welch_p值"]
    ].to_string(index=False)
)
print("\n【产业链梯度检验】")
print(
    trends[
        ["事件", "基准指数", "事件窗口", "产业链梯度斜率", "p值"]
    ].to_string(index=False)
)

print("\n【最终判定】")
if (gaps["当前文件是否具备"] == "否").any():
    print("❌ Layer经济分类证据尚不完整，必须补公司名称、分类理由、来源和事件前日期。")
if len(cmp) == 54 and len(trends) == 18 and len(car) == 360 and quality.empty:
    print("✅ 日度事件研究计算规格完整。")
else:
    print("❌ 日度事件研究存在缺失规格或估计窗口不足。")
print(
    "统计显著不等同于因果识别通过，最终措辞需结合"
    "54个两两比较和18个梯度规格。"
)
print("=" * 76)
raise SystemExit(0)
