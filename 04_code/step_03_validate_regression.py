"""
核验脚本：检验DID回归结果是否符合预期
"""
import pandas as pd
import os

BASE_DIR = os.getcwd()
TABLE_PATH = os.path.join(BASE_DIR, '05_output', 'tables', 'table2_did_main.csv')

print("=" * 70)
print("DID回归结果核验")
print("=" * 70)

df = pd.read_csv(TABLE_PATH, encoding='utf-8-sig')
print(df.to_string(index=False))

print("\n【核验标准】")
print("  ✅ 上游 Post 系数显著为正 (p < 0.1)")
print("  ✅ 下游 Post 系数不显著 (p >= 0.1)")
print("  ✅ 交互项 Post×上游 显著为正 (p < 0.1)")
print("  ✅ 上游系数 > 下游系数")

print("\n【核验结果】")
up_row = df[(df['Model'] == '上游') & (df['Variable'] == 'Post')]
down_row = df[(df['Model'] == '下游') & (df['Variable'] == 'Post')]
interact_row = df[(df['Model'] == '交互项') & (df['Variable'] == 'Post_x_Upstream')]

if len(up_row) > 0:
    print(f"  上游: 系数={up_row.iloc[0]['Coefficient']:.4f}, p={up_row.iloc[0]['p_value']:.4f}")
if len(down_row) > 0:
    print(f"  下游: 系数={down_row.iloc[0]['Coefficient']:.4f}, p={down_row.iloc[0]['p_value']:.4f}")
if len(interact_row) > 0:
    print(f"  交互项: 系数={interact_row.iloc[0]['Coefficient']:.4f}, p={interact_row.iloc[0]['p_value']:.4f}")

print("\n" + "=" * 70)