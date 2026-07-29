# -*- coding: utf-8 -*-
"""
==============================================================
步骤 4：基准DID回归与结果输出（顶刊标准版）
【最终修正版】确保 p_values 为 Series
==============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings

warnings.filterwarnings('ignore')

# 导入统计库
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from scipy import stats

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 文件路径设置
# ============================================================
base_dir = "D:/thailand study/26_7_23paper"

input_file = os.path.join(base_dir, "02_processed_data/03_did_panel.csv")
output_data_dir = os.path.join(base_dir, "02_processed_data")
output_table_dir = os.path.join(base_dir, "05_output/tables")
output_fig_cn_dir = os.path.join(base_dir, "05_output/figures/CN")
output_fig_en_dir = os.path.join(base_dir, "05_output/figures/EN")

# 自动创建目录
for dir_path in [output_table_dir, output_fig_cn_dir, output_fig_en_dir]:
    os.makedirs(dir_path, exist_ok=True)

print("=" * 70)
print("步骤 4：基准DID回归与结果输出")
print("=" * 70)

# ============================================================
# 2. 读取DID面板
# ============================================================
print("\n【1/6】读取DID面板数据...")

df = pd.read_csv(input_file)
df['year_month_dt'] = pd.to_datetime(df['year_month'].astype(str), format='%Y%m')

# 识别股票代码列
code_col = 'thscode' if 'thscode' in df.columns else 'Stkcd'
print(f"   ✓ 使用列名: '{code_col}'")
print(f"   ✓ 总观测数: {len(df):,}")
print(f"   ✓ 股票数量: {df[code_col].nunique()}")
print(f"   ✓ 时间范围: {df['year_month'].min()} - {df['year_month'].max()}")

# ============================================================
# 3. 数据预处理
# ============================================================
print("\n【2/6】数据预处理...")

# 3.1 按股票和时间排序
df = df.sort_values([code_col, 'year_month_dt'])

# 3.2 计算滞后变量（用于控制变量）
df['L1_Excess_Ret'] = df.groupby(code_col)['Excess_Ret_monthly'].shift(1)
df['L2_Excess_Ret'] = df.groupby(code_col)['Excess_Ret_monthly'].shift(2)
df['L3_Excess_Ret'] = df.groupby(code_col)['Excess_Ret_monthly'].shift(3)

# 3.3 计算平方项（捕捉非线性效应）
df['Excess_Ret_sq'] = df['Excess_Ret_monthly'] ** 2

# 3.4 处理HS300对照组
hs300_mask = df[code_col] == 'HS300'
df.loc[hs300_mask, ['Volatility', 'L1_Excess_Ret', 'L2_Excess_Ret', 'L3_Excess_Ret', 'Excess_Ret_sq']] = 0

# 3.5 创建固定效应变量
df['stock_fe'] = df[code_col].astype('category').cat.codes
df['time_fe'] = df['year_month'].astype('category').cat.codes

# 3.6 创建时间趋势
df['time_trend'] = df.groupby(code_col).cumcount() + 1

print(f"   ✓ 滞后变量计算完成")
print(f"   ✓ 固定效应编码完成")


# ============================================================
# 4. 面板固定效应回归函数（带聚类标准误）
# ============================================================
def panel_fe_regression_with_cluster(df, y_var, x_vars, cluster_var='stock_fe'):
    """
    面板固定效应回归 + 聚类稳健标准误
    """
    # 构建完整变量列表
    all_vars = [y_var] + x_vars + ['stock_fe', 'time_fe']
    df_clean = df[all_vars].dropna()

    if len(df_clean) < 50:
        return None

    # 构建X矩阵
    X = df_clean[x_vars + ['stock_fe', 'time_fe']].copy()
    X = add_constant(X)
    y = df_clean[y_var]

    # 运行OLS
    model = OLS(y, X)
    results = model.fit()

    # 计算聚类稳健标准误
    cluster_var_values = df_clean[cluster_var].values
    vcov_cluster = _cluster_robust_covariance(results, X, cluster_var_values)

    # 【关键】确保所有结果都是 Series，使用变量名作为索引
    params = results.params

    # 标准误转换为 Series
    std_errors = pd.Series(np.sqrt(np.diag(vcov_cluster)), index=params.index)

    # t统计量
    t_stats = params / std_errors

    # p值（使用 t 分布）
    df_resid = len(df_clean) - len(params)
    p_values = pd.Series(2 * (1 - stats.t.cdf(np.abs(t_stats), df_resid)), index=params.index)

    return {
        'params': params,
        'std_errors': std_errors,
        't_stats': t_stats,
        'p_values': p_values,
        'nobs': len(df_clean),
        'r2': results.rsquared,
        'r2_adj': results.rsquared_adj
    }


def _cluster_robust_covariance(results, X, cluster):
    """计算聚类稳健标准误"""
    n_clusters = len(np.unique(cluster))
    n_obs = len(X)
    k = X.shape[1]

    residuals = results.resid

    vcov = np.zeros((k, k))
    for c in np.unique(cluster):
        idx = cluster == c
        X_c = X.iloc[idx]
        resid_c = residuals.iloc[idx]
        score_c = (X_c.T * resid_c).T
        vcov += np.dot(score_c.T, score_c)

    vcov = (n_obs - 1) / (n_obs - k) * vcov / (n_obs - 1)

    hessian = np.linalg.inv(np.dot(X.T, X))
    vcov_cluster = np.dot(np.dot(hessian, vcov), hessian)

    return vcov_cluster


# ============================================================
# 5. 运行DID回归
# ============================================================
print("\n【3/6】运行DID回归...")

y_var = 'Excess_Ret_monthly'

model_specs = [
    {'name': 'Model 1', 'name_cn': '模型1', 'x_vars': ['DID', 'Post'], 'desc': 'No Controls'},
    {'name': 'Model 2', 'name_cn': '模型2', 'x_vars': ['DID', 'Post', 'Volatility'], 'desc': '+ Volatility'},
    {'name': 'Model 3', 'name_cn': '模型3', 'x_vars': ['DID', 'Post', 'Volatility', 'L1_Excess_Ret'], 'desc': '+ L1'},
    {'name': 'Model 4', 'name_cn': '模型4', 'x_vars': ['DID', 'Post', 'Volatility', 'L1_Excess_Ret', 'L2_Excess_Ret'],
     'desc': '+ L1 + L2'},
    {'name': 'Model 5', 'name_cn': '模型5',
     'x_vars': ['DID', 'Post', 'Volatility', 'L1_Excess_Ret', 'L2_Excess_Ret', 'Excess_Ret_sq'],
     'desc': '+ Full Controls'}
]

regression_details = []

for spec in model_specs:
    print(f"   运行 {spec['name_cn']}: {spec['desc']}...")

    result = panel_fe_regression_with_cluster(df, y_var, spec['x_vars'])

    if result is None:
        print(f"      ⚠️ 样本量不足，跳过")
        continue

    # 【关键】提取DID系数 - 使用标签索引
    did_idx = 'DID'
    if did_idx not in result['params'].index:
        print(f"      ⚠️ DID系数未找到")
        continue

    # 直接使用标签索引提取
    did_coef = result['params'][did_idx]
    did_se = result['std_errors'][did_idx]  # 现在 std_errors 是 Series
    did_t = result['t_stats'][did_idx]
    did_p = result['p_values'][did_idx]

    sig = '***' if did_p < 0.01 else ('**' if did_p < 0.05 else ('*' if did_p < 0.1 else ''))

    regression_details.append({
        'Model': spec['name'],
        'Model_CN': spec['name_cn'],
        'Description': spec['desc'],
        'DID_Coeff': did_coef,
        'DID_SE': did_se,
        'DID_t': did_t,
        'DID_p': did_p,
        'N': result['nobs'],
        'R2': result['r2'],
        'R2_Adj': result['r2_adj'],
        'Controls': ', '.join([v for v in spec['x_vars'] if v not in ['DID', 'Post']]) or 'None',
        'Significance': sig
    })

    print(f"      ✓ DID = {did_coef:.6f}{sig} (p={did_p:.4f}), N={result['nobs']}")

results_df = pd.DataFrame(regression_details)

if len(results_df) == 0:
    print("❌ 所有回归均失败，请检查数据")
    exit()

print(f"\n   ✓ 成功完成 {len(results_df)} 个模型回归")

# ============================================================
# 6. 输出结果表
# ============================================================
print("\n【4/6】生成回归结果表...")


def format_p_value(p_val):
    if p_val < 0.001:
        return '<0.001'
    else:
        return f'{p_val:.3f}'


def add_significance(p_val):
    if p_val < 0.01:
        return '***'
    elif p_val < 0.05:
        return '**'
    elif p_val < 0.1:
        return '*'
    else:
        return ''


# 中文版
table_cn = results_df[['Model_CN', 'Description', 'DID_Coeff', 'DID_SE', 'DID_p', 'N', 'R2']].copy()
table_cn.columns = ['模型', '描述', 'DID系数', '标准误', 'p值', '观测数', 'R²']
table_cn['显著性'] = table_cn['p值'].apply(add_significance)
table_cn['DID系数'] = table_cn.apply(lambda x: f"{x['DID系数']:.4f}{x['显著性']}", axis=1)
table_cn['标准误'] = table_cn['标准误'].apply(lambda x: f"({x:.4f})")
table_cn['p值'] = table_cn['p值'].apply(format_p_value)
table_cn['R²'] = table_cn['R²'].apply(lambda x: f"{x:.4f}")

table_cn.to_csv(os.path.join(output_table_dir, "table2_did_results_CN.csv"),
                index=False, encoding='utf-8-sig')
print(f"   ✓ 中文结果表已保存")

# 英文版
table_en = results_df[['Model', 'Description', 'DID_Coeff', 'DID_SE', 'DID_p', 'N', 'R2']].copy()
table_en.columns = ['Model', 'Description', 'DID Coeff.', 'Std. Err.', 'p-value', 'Observations', 'R²']
table_en['Significance'] = table_en['p-value'].apply(add_significance)
table_en['DID Coeff.'] = table_en.apply(lambda x: f"{x['DID Coeff.']:.4f}{x['Significance']}", axis=1)
table_en['Std. Err.'] = table_en['Std. Err.'].apply(lambda x: f"({x:.4f})")
table_en['p-value'] = table_en['p-value'].apply(format_p_value)
table_en['R²'] = table_en['R²'].apply(lambda x: f"{x:.4f}")

table_en.to_csv(os.path.join(output_table_dir, "table2_did_results_EN.csv"),
                index=False, encoding='utf-8-sig')
print(f"   ✓ 英文结果表已保存")

# ============================================================
# 7. 打印结果
# ============================================================
print("\n" + "-" * 70)
print("回归结果摘要")
print("-" * 70)
print(table_cn.to_string(index=False))
print("-" * 70)

# ============================================================
# 8. 生成可视化图
# ============================================================
print("\n【5/6】生成系数可视化图...")


def plot_coefficients(lang='EN', save_path=None):
    plot_data = results_df.copy()

    if lang == 'CN':
        model_labels = {f'Model {i + 1}': f'M{i + 1}' for i in range(len(plot_data))}
        title = 'DID估计系数：DeepSeek事件对AI企业超额收益的影响'
        xlabel = '模型设定'
        ylabel = 'DID系数估计值'
        fig_color = '#1F4E79'
        plt.rcParams['font.family'] = 'SimHei'
    else:
        model_labels = {f'Model {i + 1}': f'M{i + 1}' for i in range(len(plot_data))}
        title = 'DID Coefficients: Impact of DeepSeek Event on Excess Returns'
        xlabel = 'Model Specification'
        ylabel = 'DID Coefficient Estimate'
        fig_color = '#377EB8'
        plt.rcParams['font.family'] = 'Times New Roman'

    plot_data['Model_Short'] = plot_data['Model'].map(model_labels)

    fig, ax = plt.subplots(figsize=(8, 5))
    y_pos = np.arange(len(plot_data))

    ax.errorbar(
        plot_data['DID_Coeff'],
        y_pos,
        xerr=1.96 * plot_data['DID_SE'],
        fmt='o',
        color=fig_color,
        capsize=5,
        elinewidth=2,
        markersize=8,
        label='95% CI'
    )

    ax.axvline(x=0, color='black', linestyle='--', alpha=0.5, linewidth=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(plot_data['Model_Short'])
    ax.set_xlabel(ylabel, fontsize=12)
    ax.set_ylabel(xlabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')

    for i, row in plot_data.iterrows():
        sig = row['Significance']
        if sig:
            x_offset = 0.005 if row['DID_Coeff'] >= 0 else -0.02
            ax.text(row['DID_Coeff'] + x_offset, y_pos[i], sig,
                    fontsize=14, va='center', fontweight='bold')

    ax.legend(loc='best')
    ax.grid(False)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=600, bbox_inches='tight')
        print(f"   ✓ 图片已保存: {save_path}")

    plt.close()


plot_coefficients('CN', os.path.join(output_fig_cn_dir, "figure2_coefficient_CN.pdf"))
plot_coefficients('EN', os.path.join(output_fig_en_dir, "figure2_coefficient_EN.pdf"))

# ============================================================
# 9. 保存回归面板
# ============================================================
print("\n【6/6】保存回归数据...")

reg_data_file = os.path.join(output_data_dir, "04_regression_data.csv")
df.to_csv(reg_data_file, index=False, encoding='utf-8-sig')
print(f"   ✓ 回归面板已保存: {reg_data_file}")

# ============================================================
# 10. 最终摘要
# ============================================================
print("\n" + "=" * 70)
print("✅ 步骤 4 执行完成！")
print("=" * 70)
print(f"\n📁 输出文件:")
print(f"   • 回归面板: {reg_data_file}")
print(f"   • 中文结果表: {os.path.join(output_table_dir, 'table2_did_results_CN.csv')}")
print(f"   • 英文结果表: {os.path.join(output_table_dir, 'table2_did_results_EN.csv')}")
print(f"   • 中文系数图: {os.path.join(output_fig_cn_dir, 'figure2_coefficient_CN.pdf')}")
print(f"   • 英文系数图: {os.path.join(output_fig_en_dir, 'figure2_coefficient_EN.pdf')}")

print(f"\n📊 关键发现:")
if len(results_df) > 0:
    main_effect = results_df.iloc[0]
    print(f"   • 基准模型 DID 系数: {main_effect['DID_Coeff']:.6f}")
    print(f"   • p值: {main_effect['DID_p']:.4f}")
    if main_effect['DID_p'] < 0.05:
        print(f"   • 统计显著性: 显著 (p < 0.05) ✅")
    else:
        print(f"   • 统计显著性: 不显著 (p >= 0.05)")

print("\n" + "=" * 70)
print("👉 下一步: 运行 step_05_robustness_checks.py")
print("=" * 70)