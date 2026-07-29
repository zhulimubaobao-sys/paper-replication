import pandas as pd

df = pd.read_csv("D:/thailand study/26_7_23paper/02_processed_data/03_did_panel.csv")

print("=" * 60)
print("完整数据检查报告")
print("=" * 60)

print("\n1. 股票数量统计:")
print(f"   总股票数: {df['thscode'].nunique()}")
print(f"   处理组(Treat=1): {df[df['Treat']==1]['thscode'].nunique()}")
print(f"   对照组(Treat=0): {df[df['Treat']==0]['thscode'].nunique()}")

print("\n2. AI企业列表（前20家）:")
ai_firms = df[df['Treat']==1]['thscode'].unique()
print(f"   {ai_firms[:20]}")

print("\n3. 各AI企业的观测数量:")
firm_counts = df[df['Treat']==1].groupby('thscode').size()
print(f"   - 最少观测数: {firm_counts.min()}")
print(f"   - 最多观测数: {firm_counts.max()}")
print(f"   - 平均观测数: {firm_counts.mean():.1f}")
print(f"\n   观测数少于60个月的企业:")
print(f"   {firm_counts[firm_counts < 60]}")

print("\n4. HS300对照组的观测数:")
hs300_data = df[df['thscode'] == 'HS300']
print(f"   - HS300观测数: {len(hs300_data)}")
print(f"   - 时间范围: {hs300_data['year_month'].min()} - {hs300_data['year_month'].max()}")