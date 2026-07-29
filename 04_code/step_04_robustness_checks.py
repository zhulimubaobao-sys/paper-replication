"""
================================================================================
步骤4：稳健性检验（三项核心）
论文：AI产业链的非对称定价
项目根目录：D:/thailand study/26_7_23paper/
================================================================================
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from datetime import datetime
import matplotlib.pyplot as plt

# ============================================================================
# 1. 路径配置
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"

INPUT_PATH = os.path.join(BASE_DIR, '02_processed_data', 'monthly_panel_full.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output')
TABLES_DIR = os.path.join(OUTPUT_DIR, 'tables')
FIGURES_DIR = os.path.join(OUTPUT_DIR, 'figures')

# 创建中英文子文件夹
CN_DIR = os.path.join(FIGURES_DIR, 'CN')
EN_DIR = os.path.join(FIGURES_DIR, 'EN')
for dir_path in [TABLES_DIR, FIGURES_DIR, CN_DIR, EN_DIR]:
    os.makedirs(dir_path, exist_ok=True)

print("=" * 70)
print("步骤4：稳健性检验（三项核心）")
print("=" * 70)
print(f"输入文件：{INPUT_PATH}")

# ============================================================================
# 2. 读取数据
# ============================================================================
print("\n【1】读取数据...")
df = pd.read_csv(INPUT_PATH, encoding='utf-8-sig')
df['date'] = pd.to_datetime(df['date'])

print(f"数据行数：{len(df):,}")
print(f"公司数：{df['Stkcd'].nunique()}")
print(f"时间范围：{df['date'].min()} 至 {df['date'].max()}")

# 数据预处理
df['Post'] = df['Post'].astype(int)
df['Is_Upstream'] = (df['Layer'] == '上游').astype(int)

def winsorize_series(s, lower=0.01, upper=0.99):
    low = s.quantile(lower)
    high = s.quantile(upper)
    return s.clip(low, high)

for col in ['Size', 'ROA', 'Leverage']:
    if col in df.columns:
        df[col] = winsorize_series(df[col])

df_clean = df.dropna(subset=['Excess_Ret', 'Ret', 'Size', 'ROA', 'Leverage', 'Post'])
print(f"清洗后行数：{len(df_clean):,}")

# ============================================================================
# 3. 面板固定效应回归函数
# ============================================================================
def panel_fe_regression(df_sub, y_var='Excess_Ret', x_vars=['Post'], time_effects=True):
    """面板固定效应回归，支持聚类标准误"""
    df_temp = df_sub.copy()
    df_temp['Stkcd_fe'] = df_temp['Stkcd'].astype('category').cat.codes
    if time_effects:
        df_temp['time_fe'] = df_temp['date'].dt.strftime('%Y%m').astype('category').cat.codes
        all_x = x_vars + ['Stkcd_fe', 'time_fe']
    else:
        all_x = x_vars + ['Stkcd_fe']

    all_vars = [y_var] + all_x + ['Stkcd']
    df_reg = df_temp[all_vars].dropna()

    if len(df_reg) < 50:
        return None, 0

    X = df_reg[all_x].copy()
    X = add_constant(X)
    y = df_reg[y_var]

    try:
        results = OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': df_reg['Stkcd']})
    except:
        results = OLS(y, X).fit()
    return results, len(df_reg)

def get_post_result(df_sub, y_var='Excess_Ret', time_effects=True):
    """运行回归并提取Post系数"""
    res, n = panel_fe_regression(df_sub, y_var, ['Post', 'Size', 'ROA', 'Leverage'], time_effects)
    if res is None:
        return None, None, None, n
    if 'Post' in res.params.index:
        return res.params['Post'], res.bse['Post'], res.pvalues['Post'], n
    return None, None, None, n

def get_interact_result(df_sub, y_var='Excess_Ret', time_effects=True):
    """运行交互项回归并提取Post_x_Upstream系数"""
    df_temp = df_sub.copy()
    df_temp['Post_x_Upstream'] = df_temp['Post'] * df_temp['Is_Upstream']
    res, n = panel_fe_regression(df_temp, y_var,
                                 ['Post', 'Is_Upstream', 'Post_x_Upstream', 'Size', 'ROA', 'Leverage'],
                                 time_effects)
    if res is None:
        return None, None, None, n
    if 'Post_x_Upstream' in res.params.index:
        return res.params['Post_x_Upstream'], res.bse['Post_x_Upstream'], res.pvalues['Post_x_Upstream'], n
    return None, None, None, n

# ============================================================================
# 4. 基准结果（从table2读取）
# ============================================================================
print("\n【2】读取基准结果...")
table2_path = os.path.join(TABLES_DIR, 'table2_did_main.csv')
table2 = pd.read_csv(table2_path, encoding='utf-8-sig')

base_up = table2[(table2['Model'] == '上游') & (table2['Variable'] == 'Post')]
base_down = table2[(table2['Model'] == '下游') & (table2['Variable'] == 'Post')]
base_interact = table2[(table2['Model'] == '交互项') & (table2['Variable'] == 'Post_x_Upstream')]

if len(base_up) > 0:
    base_up_coef = base_up.iloc[0]['Coefficient']
    base_up_p = base_up.iloc[0]['p_value']
else:
    base_up_coef, base_up_p = np.nan, np.nan

if len(base_down) > 0:
    base_down_coef = base_down.iloc[0]['Coefficient']
    base_down_p = base_down.iloc[0]['p_value']
else:
    base_down_coef, base_down_p = np.nan, np.nan

if len(base_interact) > 0:
    base_int_coef = base_interact.iloc[0]['Coefficient']
    base_int_p = base_interact.iloc[0]['p_value']
else:
    base_int_coef, base_int_p = np.nan, np.nan

print(f"  基准 - 上游: {base_up_coef:.4f} (p={base_up_p:.4f})")
print(f"  基准 - 下游: {base_down_coef:.4f} (p={base_down_p:.4f})")
print(f"  基准 - 交互项: {base_int_coef:.4f} (p={base_int_p:.4f})")

# ============================================================================
# 5. 检验①：替换被解释变量（使用 Ret）
# ============================================================================
print("\n【3】检验①：替换被解释变量（使用 Ret）...")

df_all = df_clean

# 全样本 - Ret
res_all_ret, n_all_ret = panel_fe_regression(df_all, 'Ret', ['Post', 'Size', 'ROA', 'Leverage'])
if res_all_ret is not None and 'Post' in res_all_ret.params.index:
    ret_all_coef = res_all_ret.params['Post']
    ret_all_p = res_all_ret.pvalues['Post']
else:
    ret_all_coef, ret_all_p = np.nan, np.nan

# 上游 - Ret
df_up = df_clean[df_clean['Layer'] == '上游']
res_up_ret, n_up_ret = panel_fe_regression(df_up, 'Ret', ['Post', 'Size', 'ROA', 'Leverage'])
if res_up_ret is not None and 'Post' in res_up_ret.params.index:
    ret_up_coef = res_up_ret.params['Post']
    ret_up_p = res_up_ret.pvalues['Post']
else:
    ret_up_coef, ret_up_p = np.nan, np.nan

# 下游 - Ret
df_down = df_clean[df_clean['Layer'] == '下游']
res_down_ret, n_down_ret = panel_fe_regression(df_down, 'Ret', ['Post', 'Size', 'ROA', 'Leverage'])
if res_down_ret is not None and 'Post' in res_down_ret.params.index:
    ret_down_coef = res_down_ret.params['Post']
    ret_down_p = res_down_ret.pvalues['Post']
else:
    ret_down_coef, ret_down_p = np.nan, np.nan

# 交互项 - Ret
df_temp_ret = df_all.copy()
df_temp_ret['Post_x_Upstream'] = df_temp_ret['Post'] * df_temp_ret['Is_Upstream']
res_interact_ret, n_interact_ret = panel_fe_regression(df_temp_ret, 'Ret',
                                                       ['Post', 'Is_Upstream', 'Post_x_Upstream', 'Size', 'ROA', 'Leverage'])
if res_interact_ret is not None and 'Post_x_Upstream' in res_interact_ret.params.index:
    ret_int_coef = res_interact_ret.params['Post_x_Upstream']
    ret_int_p = res_interact_ret.pvalues['Post_x_Upstream']
else:
    ret_int_coef, ret_int_p = np.nan, np.nan

print(f"    Ret - 上游: {ret_up_coef:.4f} (p={ret_up_p:.4f})")
print(f"    Ret - 下游: {ret_down_coef:.4f} (p={ret_down_p:.4f})")
print(f"    Ret - 交互项: {ret_int_coef:.4f} (p={ret_int_p:.4f})")

# ============================================================================
# 6. 检验②：时间安慰剂（事件提前到2024年1月）
# ============================================================================
print("\n【4】检验②：时间安慰剂（事件提前到2024年1月）...")

# 只使用2023-2024年数据
df_placebo = df_clean[(df_clean['date'] >= '2023-01-01') & (df_clean['date'] < '2025-01-01')].copy()
df_placebo['Post_placebo'] = (df_placebo['date'] >= '2024-01-01').astype(int)
df_placebo['Is_Upstream'] = (df_placebo['Layer'] == '上游').astype(int)

# 全样本
res_pl_all, n_pl_all = panel_fe_regression(df_placebo, 'Excess_Ret', ['Post_placebo', 'Size', 'ROA', 'Leverage'])
if res_pl_all is not None and 'Post_placebo' in res_pl_all.params.index:
    pl_all_coef = res_pl_all.params['Post_placebo']
    pl_all_p = res_pl_all.pvalues['Post_placebo']
else:
    pl_all_coef, pl_all_p = np.nan, np.nan

# 上游
df_pl_up = df_placebo[df_placebo['Layer'] == '上游']
res_pl_up, n_pl_up = panel_fe_regression(df_pl_up, 'Excess_Ret', ['Post_placebo', 'Size', 'ROA', 'Leverage'])
if res_pl_up is not None and 'Post_placebo' in res_pl_up.params.index:
    pl_up_coef = res_pl_up.params['Post_placebo']
    pl_up_p = res_pl_up.pvalues['Post_placebo']
else:
    pl_up_coef, pl_up_p = np.nan, np.nan

# 下游
df_pl_down = df_placebo[df_placebo['Layer'] == '下游']
res_pl_down, n_pl_down = panel_fe_regression(df_pl_down, 'Excess_Ret', ['Post_placebo', 'Size', 'ROA', 'Leverage'])
if res_pl_down is not None and 'Post_placebo' in res_pl_down.params.index:
    pl_down_coef = res_pl_down.params['Post_placebo']
    pl_down_p = res_pl_down.pvalues['Post_placebo']
else:
    pl_down_coef, pl_down_p = np.nan, np.nan

# 交互项
df_pl_temp = df_placebo.copy()
df_pl_temp['Post_x_Upstream_pl'] = df_pl_temp['Post_placebo'] * df_pl_temp['Is_Upstream']
res_pl_int, n_pl_int = panel_fe_regression(df_pl_temp, 'Excess_Ret',
                                           ['Post_placebo', 'Is_Upstream', 'Post_x_Upstream_pl', 'Size', 'ROA', 'Leverage'])
if res_pl_int is not None and 'Post_x_Upstream_pl' in res_pl_int.params.index:
    pl_int_coef = res_pl_int.params['Post_x_Upstream_pl']
    pl_int_p = res_pl_int.pvalues['Post_x_Upstream_pl']
else:
    pl_int_coef, pl_int_p = np.nan, np.nan

print(f"    安慰剂 - 上游: {pl_up_coef:.4f} (p={pl_up_p:.4f})")
print(f"    安慰剂 - 下游: {pl_down_coef:.4f} (p={pl_down_p:.4f})")
print(f"    安慰剂 - 交互项: {pl_int_coef:.4f} (p={pl_int_p:.4f})")

# ============================================================================
# 7. 检验③：排除新冠疫情期（2020-2021）
# ============================================================================
print("\n【5】检验③：排除新冠疫情期（2020-2021）...")

df_no_covid = df_clean[~((df_clean['year'] == 2020) | (df_clean['year'] == 2021))].copy()
print(f"    排除后行数：{len(df_no_covid):,}")

# 全样本
res_nc_all, n_nc_all = panel_fe_regression(df_no_covid, 'Excess_Ret', ['Post', 'Size', 'ROA', 'Leverage'])
if res_nc_all is not None and 'Post' in res_nc_all.params.index:
    nc_all_coef = res_nc_all.params['Post']
    nc_all_p = res_nc_all.pvalues['Post']
else:
    nc_all_coef, nc_all_p = np.nan, np.nan

# 上游
df_nc_up = df_no_covid[df_no_covid['Layer'] == '上游']
res_nc_up, n_nc_up = panel_fe_regression(df_nc_up, 'Excess_Ret', ['Post', 'Size', 'ROA', 'Leverage'])
if res_nc_up is not None and 'Post' in res_nc_up.params.index:
    nc_up_coef = res_nc_up.params['Post']
    nc_up_p = res_nc_up.pvalues['Post']
else:
    nc_up_coef, nc_up_p = np.nan, np.nan

# 下游
df_nc_down = df_no_covid[df_no_covid['Layer'] == '下游']
res_nc_down, n_nc_down = panel_fe_regression(df_nc_down, 'Excess_Ret', ['Post', 'Size', 'ROA', 'Leverage'])
if res_nc_down is not None and 'Post' in res_nc_down.params.index:
    nc_down_coef = res_nc_down.params['Post']
    nc_down_p = res_nc_down.pvalues['Post']
else:
    nc_down_coef, nc_down_p = np.nan, np.nan

# 交互项
df_nc_temp = df_no_covid.copy()
df_nc_temp['Post_x_Upstream'] = df_nc_temp['Post'] * df_nc_temp['Is_Upstream']
res_nc_int, n_nc_int = panel_fe_regression(df_nc_temp, 'Excess_Ret',
                                           ['Post', 'Is_Upstream', 'Post_x_Upstream', 'Size', 'ROA', 'Leverage'])
if res_nc_int is not None and 'Post_x_Upstream' in res_nc_int.params.index:
    nc_int_coef = res_nc_int.params['Post_x_Upstream']
    nc_int_p = res_nc_int.pvalues['Post_x_Upstream']
else:
    nc_int_coef, nc_int_p = np.nan, np.nan

print(f"    排除COVID - 上游: {nc_up_coef:.4f} (p={nc_up_p:.4f})")
print(f"    排除COVID - 下游: {nc_down_coef:.4f} (p={nc_down_p:.4f})")
print(f"    排除COVID - 交互项: {nc_int_coef:.4f} (p={nc_int_p:.4f})")

# ============================================================================
# 8. 汇总生成 Table 4
# ============================================================================
print("\n【6】汇总生成 Table 4...")

table4_rows = []

# 基准结果
table4_rows.append({
    '检验': '基准模型 (Excess_Ret)',
    '上游系数': base_up_coef,
    '上游p值': base_up_p,
    '下游系数': base_down_coef,
    '下游p值': base_down_p,
    '交互项系数': base_int_coef,
    '交互项p值': base_int_p,
    '通过': '—'
})

# 检验①
table4_rows.append({
    '检验': '① 替换被解释变量 (Ret)',
    '上游系数': ret_up_coef,
    '上游p值': ret_up_p,
    '下游系数': ret_down_coef,
    '下游p值': ret_down_p,
    '交互项系数': ret_int_coef,
    '交互项p值': ret_int_p,
    '通过': '✅' if (ret_up_p < 0.1 and ret_int_p < 0.1) else '⚠️'
})

# 检验②
table4_rows.append({
    '检验': '② 时间安慰剂 (2024年1月)',
    '上游系数': pl_up_coef,
    '上游p值': pl_up_p,
    '下游系数': pl_down_coef,
    '下游p值': pl_down_p,
    '交互项系数': pl_int_coef,
    '交互项p值': pl_int_p,
    '通过': '✅' if (pl_up_p >= 0.1 and pl_int_p >= 0.1) else '⚠️'
})

# 检验③
table4_rows.append({
    '检验': '③ 排除COVID期 (2020-2021)',
    '上游系数': nc_up_coef,
    '上游p值': nc_up_p,
    '下游系数': nc_down_coef,
    '下游p值': nc_down_p,
    '交互项系数': nc_int_coef,
    '交互项p值': nc_int_p,
    '通过': '✅' if (nc_up_p < 0.1 and nc_int_p < 0.1) else '⚠️'
})

table4_df = pd.DataFrame(table4_rows)
table4_path = os.path.join(TABLES_DIR, 'table4_robustness_checks.csv')
table4_df.to_csv(table4_path, index=False, encoding='utf-8-sig')
print(f"    ✅ Table 4已保存：{table4_path}")

# ============================================================================
# 9. Figure 3：稳健性检验系数对比图（中英文双版）
# ============================================================================
print("\n【7】生成Figure 3：稳健性检验系数对比图（中英文双版）...")

# 准备绘图数据
labels = ['基准模型', '① 替换DepVar', '② 时间安慰剂', '③ 排除COVID']
up_coefs = [base_up_coef, ret_up_coef, pl_up_coef, nc_up_coef]
down_coefs = [base_down_coef, ret_down_coef, pl_down_coef, nc_down_coef]
int_coefs = [base_int_coef, ret_int_coef, pl_int_coef, nc_int_coef]
up_p_values = [base_up_p, ret_up_p, pl_up_p, nc_up_p]
int_p_values = [base_int_p, ret_int_p, pl_int_p, nc_int_p]

def draw_figure3(title, filename, filepath, is_chinese=True):
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    width = 0.25

    ax.bar(x - width, up_coefs, width, label='上游' if is_chinese else 'Upstream', color='#2E86AB', alpha=0.8)
    ax.bar(x, down_coefs, width, label='下游' if is_chinese else 'Downstream', color='#E67E22', alpha=0.8)
    ax.bar(x + width, int_coefs, width, label='交互项' if is_chinese else 'Interaction', color='#27AE60', alpha=0.8)

    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax.set_ylabel('DID系数' if is_chinese else 'DID Coefficient', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # 添加显著性标记
    for i, (up, intc) in enumerate(zip(up_coefs, int_coefs)):
        if not np.isnan(up) and i < len(up_p_values) and up_p_values[i] < 0.1:
            ax.text(i - width, up + 0.002, '*', ha='center', va='bottom', fontsize=14, color='#2E86AB', fontweight='bold')
        if not np.isnan(intc) and i < len(int_p_values) and int_p_values[i] < 0.1:
            ax.text(i + width, intc + 0.002, '*', ha='center', va='bottom', fontsize=14, color='#27AE60', fontweight='bold')

    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"    ✅ {filename} 已保存")

# 中文版
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
draw_figure3(
    title='稳健性检验：三项检验的DID系数对比',
    filename='figure3_robustness_cn.png',
    filepath=os.path.join(CN_DIR, 'figure3_robustness_cn.png'),
    is_chinese=True
)

# 英文版
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False
draw_figure3(
    title='Robustness Checks: DID Coefficients Comparison',
    filename='figure3_robustness_en.png',
    filepath=os.path.join(EN_DIR, 'figure3_robustness_en.png'),
    is_chinese=False
)

print(f"    ✅ Figure 3 中英文双版已保存至 CN/ 和 EN/ 文件夹")

# ============================================================================
# 10. 保存安慰剂详细结果
# ============================================================================
placebo_detail = pd.DataFrame({
    '模型': ['全样本', '上游', '下游', '交互项'],
    'Post_placebo系数': [pl_all_coef, pl_up_coef, pl_down_coef, pl_int_coef],
    'p值': [pl_all_p, pl_up_p, pl_down_p, pl_int_p]
})
placebo_detail.to_csv(os.path.join(TABLES_DIR, 'placebo_results_summary.csv'), index=False, encoding='utf-8-sig')
print(f"    ✅ 安慰剂详细结果已保存")

# ============================================================================
# 11. 完整日志
# ============================================================================
print("\n【8】生成完整日志...")

log_lines = []
log_lines.append("=" * 70)
log_lines.append("稳健性检验完整日志")
log_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_lines.append("=" * 70)
log_lines.append("")
log_lines.append("【Table 4 汇总】")
log_lines.append(str(table4_df.to_string()))
log_lines.append("")
log_lines.append("【安慰剂详细结果】")
log_lines.append(str(placebo_detail.to_string()))
log_lines.append("")
log_lines.append("=" * 70)

with open(os.path.join(TABLES_DIR, 'robustness_checks_log.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines))

print(f"    ✅ 完整日志已保存")

# ============================================================================
# 12. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 稳健性检验全部完成！")
print("=" * 70)
print("\n输出文件清单：")
print(f"  [表格] {os.path.join(TABLES_DIR, 'table4_robustness_checks.csv')}")
print(f"  [表格] {os.path.join(TABLES_DIR, 'placebo_results_summary.csv')}")
print(f"  [表格] {os.path.join(TABLES_DIR, 'robustness_checks_log.txt')}")
print(f"  [图表] {os.path.join(CN_DIR, 'figure3_robustness_cn.png')}")
print(f"  [图表] {os.path.join(EN_DIR, 'figure3_robustness_en.png')}")
print("\n" + "=" * 70)