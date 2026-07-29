# -*- coding: utf-8 -*-
"""
功能：运行连续型DID回归，检验DeepSeek事件对上下游的非对称影响
输入：03_clean_data/panel_final.csv
输出：05_output/regression_results.txt
"""
import pandas as pd
import numpy as np
from pathlib import Path
import statsmodels.formula.api as smf

BASE_DIR = Path(r"D:\thailand study\26_7_23paper")
INPUT_FILE = BASE_DIR / "03_clean_data" / "panel_final.csv"
OUTPUT_DIR = BASE_DIR / "05_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "regression_results.txt"

print("=" * 60)
print("开始执行 03_regression.py ...")

df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
df['月份_dt'] = pd.to_datetime(df['月份_dt'])

# 设置固定效应
df['股票FE'] = df['股票代码'].astype('category')
df['月份FE'] = df['月份'].astype('category')

print(f"✅ 读取面板数据: {len(df)} 条观测值")
print(f"   股票数: {df['股票代码'].nunique()} 只")
print(f"   月份数: {df['月份'].nunique()} 个月")

# ====== 全样本DID回归 ======
model_full = smf.ols(
    "CAR ~ DID + Post + AI_exposure + C(股票FE) + C(月份FE)",
    data=df
).fit()

# ====== 分组回归 ======
df_up = df[df['产业链位置'] == '上游']
df_down = df[df['产业链位置'] == '下游']

model_up = smf.ols(
    "CAR ~ DID + Post + AI_exposure + C(股票FE) + C(月份FE)",
    data=df_up
).fit() if len(df_up) > 0 else None

model_down = smf.ols(
    "CAR ~ DID + Post + AI_exposure + C(股票FE) + C(月份FE)",
    data=df_down
).fit() if len(df_down) > 0 else None

# ====== 输出结果 ======
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("      AI产业链非对称定价 - DID回归结果\n")
    f.write("=" * 80 + "\n\n")

    f.write("【1. 全样本结果】\n")
    f.write(f"观测值: {int(model_full.nobs)}\n")
    f.write(f"R²: {model_full.rsquared:.4f}\n")
    f.write(f"调整R²: {model_full.rsquared_adj:.4f}\n\n")
    f.write(str(model_full.summary()) + "\n\n")

    if model_up:
        f.write("=" * 80 + "\n")
        f.write("【2. 上游企业分组】\n")
        f.write(f"观测值: {int(model_up.nobs)}\n")
        f.write(f"R²: {model_up.rsquared:.4f}\n\n")
        f.write(str(model_up.summary()) + "\n\n")

    if model_down:
        f.write("=" * 80 + "\n")
        f.write("【3. 下游企业分组】\n")
        f.write(f"观测值: {int(model_down.nobs)}\n")
        f.write(f"R²: {model_down.rsquared:.4f}\n\n")
        f.write(str(model_down.summary()) + "\n\n")

print(f"\n✅ 回归完成！结果保存至: {OUTPUT_FILE}")

# 打印关键结果
print(f"\n📊 关键结果:")
print(f"   全样本 DID 系数: {model_full.params['DID']:.4f} (p值: {model_full.pvalues['DID']:.4f})")
if model_full.pvalues['DID'] < 0.05:
    print("   ✅ DID系数在5%水平上显著！")
else:
    print("   ⚠️ DID系数不显著，继续检查数据质量")

if model_up:
    print(f"   上游 DID 系数: {model_up.params['DID']:.4f} (p值: {model_up.pvalues['DID']:.4f})")
if model_down:
    print(f"   下游 DID 系数: {model_down.params['DID']:.4f} (p值: {model_down.pvalues['DID']:.4f})")