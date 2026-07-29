"""
核验脚本：验证企洞察API数据获取结果
"""
import pandas as pd
import os

BASE_DIR = r"D:/thailand study/26_7_23paper"
RAW_DIR = os.path.join(BASE_DIR, '01_raw_data', 'qidongcha')

print("=" * 70)
print("企洞察API数据核验")
print("=" * 70)

# 检查文件
files = ['news_deepseek_v3.csv', 'news_deepseek_r1.csv']
all_exist = True

for f in files:
    path = os.path.join(RAW_DIR, f)
    if os.path.exists(path):
        df = pd.read_csv(path, encoding='utf-8-sig')
        print(f"\n✅ {f}")
        print(f"   行数：{len(df)}")
        if 'display_time' in df.columns and len(df) > 0:
            print(f"   时间范围：{df['display_time'].min()} 至 {df['display_time'].max()}")
        if 'title' in df.columns and len(df) > 0:
            print(f"   标题示例：{df['title'].iloc[0][:50]}...")

        # 检查是否有DeepSeek相关新闻
        if 'title' in df.columns:
            ds_count = df['title'].str.contains('DeepSeek|深度求索', case=False, na=False).sum()
            print(f"   DeepSeek相关新闻：{ds_count} 条")
    else:
        print(f"\n❌ {f} 不存在")
        all_exist = False

print("\n" + "=" * 70)
if all_exist:
    print("✅ 所有文件已生成，数据获取成功！")
else:
    print("⚠️ 部分文件缺失，请检查API调用")
print("=" * 70)