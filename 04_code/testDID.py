import pandas as pd

# 读取数据
df = pd.read_csv("D:/thailand study/26_7_23paper/02_processed_data/03_did_panel.csv")

# 查看关键变量
print(df[['thscode', 'year_month', 'Treat', 'Post', 'DID']].head(20))

# 统计验证
print("\n=== DID 变量分布验证 ===")
print(f"AI企业事件前 (Treat=1, Post=0): DID应为0 → 实际: {((df['Treat']==1) & (df['Post']==0) & (df['DID']==0)).sum()}")
print(f"AI企业事件后 (Treat=1, Post=1): DID应为1 → 实际: {((df['Treat']==1) & (df['Post']==1) & (df['DID']==1)).sum()}")
print(f"HS300事件前 (Treat=0, Post=0): DID应为0 → 实际: {((df['Treat']==0) & (df['Post']==0) & (df['DID']==0)).sum()}")
print(f"HS300事件后 (Treat=0, Post=1): DID应为0 → 实际: {((df['Treat']==0) & (df['Post']==1) & (df['DID']==0)).sum()}")

print("\n如果有任何一项不正确，说明步骤3的DID构建有问题。")