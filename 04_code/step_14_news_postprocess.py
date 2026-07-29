# -*- coding: utf-8 -*-
"""
步骤14：新闻舆情数据后处理与论文附录生成（修复版）
"""

import pandas as pd
import os
from datetime import datetime

# ============================================================================
# 1. 路径配置
# ============================================================================
BASE_DIR = r"D:/thailand study/26_7_23paper"
RAW_DIR = os.path.join(BASE_DIR, '01_raw_data', 'qidongcha')
OUTPUT_DIR = os.path.join(BASE_DIR, '05_output', 'tables')
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("步骤14：新闻舆情数据后处理与论文附录生成（修复版）")
print("=" * 70)

# ============================================================================
# 2. 加载数据
# ============================================================================
print("\n【1】加载新闻数据...")

v3_path = os.path.join(RAW_DIR, 'news_deepseek_v3.csv')
r1_path = os.path.join(RAW_DIR, 'news_deepseek_r1.csv')

df_v3 = pd.read_csv(v3_path, encoding='utf-8-sig')
df_r1 = pd.read_csv(r1_path, encoding='utf-8-sig')

print(f"    V3新闻：{len(df_v3)} 条")
print(f"    R1新闻：{len(df_r1)} 条")
print(f"    合计：{len(df_v3) + len(df_r1)} 条")

# ============================================================================
# 3. 合并与排序
# ============================================================================
print("\n【2】合并并排序新闻...")

df_v3['event'] = 'V3 (2024-12-21~2024-12-31)'
df_r1['event'] = 'R1 (2025-01-15~2025-01-25)'

df_combined = pd.concat([df_v3, df_r1], ignore_index=True)
df_combined = df_combined.sort_values('display_time').reset_index(drop=True)

# 转换时间戳
df_combined['date'] = pd.to_datetime(df_combined['display_time'], unit='s').dt.strftime('%Y-%m-%d')
df_combined['datetime'] = pd.to_datetime(df_combined['display_time'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')

print(f"    合并后共 {len(df_combined)} 条新闻")
print(f"    时间范围：{df_combined['date'].min()} 至 {df_combined['date'].max()}")

# 保存合并后的数据
combined_path = os.path.join(OUTPUT_DIR, 'news_combined_sorted.csv')
df_combined.to_csv(combined_path, index=False, encoding='utf-8-sig')
print(f"    ✅ 已保存：{combined_path}")

# ============================================================================
# 4. 关键词定义
# ============================================================================
AI_KEYWORDS = [
    'ChatGPT', 'OpenAI', 'GPT-4', 'GPT-5', 'Gemini', 'Bard',
    'Claude', 'Anthropic', 'Llama', 'Mistral',
    '文心一言', '通义千问', '豆包', 'Kimi', '智谱', 'ChatGLM',
    '百川', 'MiniMax', '零一万物', '讯飞星火', '腾讯混元'
]


def contains_keywords(text, keywords):
    if pd.isna(text):
        return False
    text_lower = str(text).lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False


def match_keywords(text, keywords):
    if pd.isna(text):
        return []
    text_lower = str(text).lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


# ============================================================================
# 5. 标记竞品新闻（在合并数据上操作）
# ============================================================================
print("\n【3】识别AI竞品新闻...")

df_combined['search_text'] = df_combined['title'].fillna('') + ' ' + df_combined['host_source'].fillna('')
df_combined['is_ai_related'] = df_combined['search_text'].apply(lambda x: contains_keywords(x, AI_KEYWORDS))
df_combined['matched_keywords'] = df_combined['search_text'].apply(lambda x: ', '.join(match_keywords(x, AI_KEYWORDS)))

ai_count = df_combined['is_ai_related'].sum()
print(f"    AI竞品相关新闻：{ai_count} 条")

# 保存竞品新闻
ai_df = df_combined[df_combined['is_ai_related']].copy()
ai_path = os.path.join(OUTPUT_DIR, 'news_competitive_ai.csv')
ai_df.to_csv(ai_path, index=False, encoding='utf-8-sig')
print(f"    ✅ 已保存：{ai_path}")

# ============================================================================
# 6. 生成附录格式（从合并数据中按事件筛选）
# ============================================================================
print("\n【4】生成论文附录...")


def generate_appendix(df_sub, event_name, start_date, end_date):
    lines = []
    lines.append("=" * 80)
    lines.append(f"附录：DeepSeek-{event_name} 事件窗口新闻事件日志")
    lines.append(f"窗口时间：{start_date} 至 {end_date}")
    lines.append("=" * 80)
    lines.append("")
    lines.append("| 序号 | 日期 | 企业 | 新闻标题 | 来源 | AI竞品 |")
    lines.append("|------|------|------|----------|------|--------|")

    df_sorted = df_sub.sort_values('display_time')
    for idx, row in df_sorted.iterrows():
        seq = idx + 1
        date = row.get('date', '未知')
        company = row.get('company_name', '未知')[:15]
        title = row.get('title', '无标题')
        if len(title) > 45:
            title = title[:45] + '...'
        source = row.get('host_source', '未知')[:15]
        is_ai = '是' if row.get('is_ai_related', False) else '否'
        lines.append(f"| {seq} | {date} | {company} | {title} | {source} | {is_ai} |")

    lines.append("")
    lines.append(f"新闻总数：{len(df_sub)} 条")
    lines.append("=" * 80)
    return '\n'.join(lines)


# 筛选各事件数据
v3_sub = df_combined[df_combined['event'] == 'V3 (2024-12-21~2024-12-31)'].copy()
r1_sub = df_combined[df_combined['event'] == 'R1 (2025-01-15~2025-01-25)'].copy()

v3_appendix = generate_appendix(v3_sub, 'V3', '2024-12-21', '2024-12-31')
r1_appendix = generate_appendix(r1_sub, 'R1', '2025-01-15', '2025-01-25')

appendix_path = os.path.join(OUTPUT_DIR, 'news_events_appendix.txt')
with open(appendix_path, 'w', encoding='utf-8') as f:
    f.write(v3_appendix + '\n\n' + r1_appendix)
print(f"    ✅ 已保存：{appendix_path}")

# ============================================================================
# 7. 生成统计摘要
# ============================================================================
print("\n【5】生成统计摘要...")

# 从合并数据中统计各事件
v3_count = len(v3_sub)
r1_count = len(r1_sub)
v3_ai = v3_sub['is_ai_related'].sum()
r1_ai = r1_sub['is_ai_related'].sum()

summary = []
summary.append("=" * 70)
summary.append("新闻舆情事件窗口统计摘要")
summary.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
summary.append("=" * 70)
summary.append("")
summary.append(f"【V3窗口】新闻 {v3_count} 条，AI竞品 {v3_ai} 条")
summary.append(f"【R1窗口】新闻 {r1_count} 条，AI竞品 {r1_ai} 条")
summary.append(f"【合计】新闻 {len(df_combined)} 条，AI竞品 {ai_count} 条")
summary.append("")
summary.append(f"AI竞品占比：{ai_count / len(df_combined) * 100:.2f}%")
if ai_count < 20:
    summary.append("✅ 竞品新闻极少，DeepSeek事件具有独特性")
else:
    summary.append("⚠️ 需进一步人工复核竞品新闻内容")
summary.append("=" * 70)

summary_path = os.path.join(OUTPUT_DIR, 'news_events_summary.txt')
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(summary))
print(f"    ✅ 已保存：{summary_path}")

# ============================================================================
# 8. 打印摘要
# ============================================================================
print("\n" + "=" * 70)
print("📊 统计摘要")
print("=" * 70)
for line in summary:
    print(line)

print("\n" + "=" * 70)
print("🎉 数据后处理完成！")
print("=" * 70)