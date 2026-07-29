# -*- coding: utf-8 -*-
"""
================================================================================
步骤13：企洞察API新闻舆情数据获取（修订版）
论文：DeepSeek模型发布与AI产业链的非对称市场反应
项目根目录：D:/thailand study/26_7_23paper/

API信息：
  平台：企洞察（同花顺旗下企业征信平台）
  appKey: 6A63041F0146
  appSecret: 1E768F54DD717C7339D6CDED0F48C5B7
  有效期：15天（2026-07-24起）
  日限额：1000次/天
  QPS限制：10次/秒

修订说明：
  企洞察API不支持模糊匹配，必须使用企业工商注册全称。
  已将60家企业全部替换为A股上市公司全称。
  行业新闻接口（news_concept: 300345）已失效，本版跳过。

功能：
  1. 获取API访问令牌（token）
  2. 查询DeepSeek-V3事件前后（2024-12-21至2024-12-31）的企业新闻
  3. 查询DeepSeek-R1事件前后（2025-01-15至2025-01-25）的企业新闻
================================================================================
"""

import requests
import pandas as pd
import json
import time
import os
from datetime import datetime
import urllib3

# 禁用SSL警告（如有需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# 1. API配置（已填写）
# ============================================================================
APP_KEY = "6A63041F0146"
APP_SECRET = "1E768F54DD717C7339D6CDED0F48C5B7"

# API端点
TOKEN_URL = "https://b2b-api.10jqka.com.cn/gateway/service-mana/app/login-appkey"
NEWS_SEARCH_URL = "https://b2b-api.10jqka.com.cn/gateway/arsenal/yq_qdc/enterprise_info_api/v3/news_search"

# 路径配置
BASE_DIR = r"D:/thailand study/26_7_23paper"
RAW_DIR = os.path.join(BASE_DIR, '01_raw_data', 'qidongcha')
os.makedirs(RAW_DIR, exist_ok=True)

print("=" * 70)
print("步骤13：企洞察API新闻舆情数据获取（修订版）")
print("=" * 70)
print(f"appKey: {APP_KEY}")
print(f"appSecret: {APP_SECRET[:10]}...")
print(f"输出目录：{RAW_DIR}")


# ============================================================================
# 2. 获取Token
# ============================================================================
def get_token():
    """获取API访问令牌"""
    try:
        url = f"{TOKEN_URL}?appKey={APP_KEY}&appSecret={APP_SECRET}"
        response = requests.get(url, timeout=30)
        data = response.json()

        if data.get('flag') == 0 and 'data' in data:
            token = data['data'].get('access_token')
            print(f"    ✅ Token获取成功")
            print(f"    Token预览：{token[:50]}...")
            return token
        else:
            print(f"    ❌ Token获取失败：{data}")
            return None
    except Exception as e:
        print(f"    ❌ Token获取异常：{e}")
        return None


# ============================================================================
# 3. 新闻搜索函数
# ============================================================================
def search_news_by_company(token, corp_name, start_date, end_date, page=1, page_size=10):
    """
    按企业名称查询新闻

    参数：
        token: API访问令牌
        corp_name: 企业名称（必须使用工商注册全称）
        start_date: 开始时间戳（10位）
        end_date: 结束时间戳（10位）
        page: 页码
        page_size: 每页数量

    返回：
        新闻列表
    """
    headers = {
        'open-authorization': f'Bearer {token}'
    }
    params = {
        'corp_name': corp_name,
        'sdate': start_date,
        'edate': end_date,
        'page': page,
        'page_size': page_size
    }

    try:
        response = requests.get(NEWS_SEARCH_URL, headers=headers, params=params, timeout=30)
        data = response.json()

        if data.get('status_code') == 0:
            return data.get('data', {})
        else:
            print(f"        ⚠️ 查询失败：{data.get('status_msg', '未知错误')}")
            return None
    except Exception as e:
        print(f"        ❌ 请求异常：{e}")
        return None


# ============================================================================
# 4. 时间戳转换函数
# ============================================================================
def date_to_timestamp(date_str):
    """将日期字符串转换为10位时间戳"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return int(dt.timestamp())


# ============================================================================
# 5. 企业名单（60家）- 使用工商注册全称
# ============================================================================
FIRMS = [
    # 上游（20家）
    '中科寒武纪科技股份有限公司',
    '海光信息技术股份有限公司',
    '曙光信息产业股份有限公司',
    '紫光国芯微电子股份有限公司',
    '澜起科技股份有限公司',
    '长沙景嘉微电子股份有限公司',
    '中际旭创股份有限公司',
    '成都新易盛通信技术股份有限公司',
    '苏州天孚光通信股份有限公司',
    '光迅科技股份有限公司',
    '华工科技产业股份有限公司',
    '浪潮电子信息产业股份有限公司',
    '沪士电子股份有限公司',
    '胜宏科技股份有限公司',
    '广东生益科技股份有限公司',
    '中芯国际集成电路制造有限公司',
    '北方华创科技集团股份有限公司',
    '中微半导体设备（上海）股份有限公司',
    '北京君正集成电路股份有限公司',
    '兆易创新科技集团股份有限公司',
    # 中游（20家）
    '科大讯飞股份有限公司',
    '北京金山办公软件股份有限公司',
    '拓尔思信息技术股份有限公司',
    '云从科技集团股份有限公司',
    '杭州海康威视数字技术股份有限公司',
    '深圳市汇顶科技股份有限公司',
    '浙江核新同花顺网络信息股份有限公司',
    '北京四维图新科技股份有限公司',
    '万兴科技集团股份有限公司',
    '彩讯科技股份有限公司',
    '四川久远银海软件股份有限公司',
    '北京恒华伟业科技股份有限公司',
    '虹软科技股份有限公司',
    '中科创达软件股份有限公司',
    '四川川大智胜软件股份有限公司',
    '思创医惠科技股份有限公司',
    '浙江大华技术股份有限公司',
    '杭州安恒信息技术股份有限公司',
    '创业慧康科技股份有限公司',
    '新大陆科技股份有限公司',
    # 下游（20家）
    '开普云信息科技股份有限公司',
    '北京值得买科技股份有限公司',
    '北京蓝色光标数据科技股份有限公司',
    '利欧集团股份有限公司',
    '北京天下秀科技股份有限公司',
    '广东因赛品牌营销集团股份有限公司',
    '恒生电子股份有限公司',
    '中公教育科技股份有限公司',
    '卫宁健康科技集团股份有限公司',
    '北京致远互联软件股份有限公司',
    '国投智能（厦门）信息股份有限公司',
    '启明星辰信息技术集团股份有限公司',
    '北京超图软件股份有限公司',
    '银江技术股份有限公司',
    '北京数字政通科技股份有限公司',
    '万达信息股份有限公司',
    '东华软件股份公司',
    '北京华胜天成科技股份有限公司',
    '汉得信息科技股份有限公司',
    '太极计算机股份有限公司'
]

# ============================================================================
# 6. 主执行流程
# ============================================================================
print("\n【1】获取Token...")
token = get_token()
if token is None:
    print("❌ 无法获取Token，请检查网络或账号权限")
    exit(1)

# ============================================================================
# 6.1 查询DeepSeek-V3事件前后新闻（2024-12-21至2024-12-31）
# ============================================================================
print("\n【2】查询DeepSeek-V3事件前后新闻（2024-12-21至2024-12-31）...")

V3_START = date_to_timestamp('2024-12-21')
V3_END = date_to_timestamp('2024-12-31')

v3_results = []
v3_success = 0
v3_fail = 0

for i, firm in enumerate(FIRMS):
    print(f"    [{i + 1}/{len(FIRMS)}] 查询：{firm[:20]}...", end=" ")
    result = search_news_by_company(token, firm, V3_START, V3_END, page=1, page_size=10)

    if result and result.get('list'):
        for news in result.get('list', []):
            news['company_name'] = firm
            v3_results.append(news)
        v3_success += 1
        print(f"✅ 获取 {len(result.get('list', []))} 条")
    else:
        v3_fail += 1
        print("⏭️ 无新闻")

    # 控制请求频率（QPS限制10次/秒）
    time.sleep(0.2)

print(f"\n    V3统计：成功 {v3_success} 家企业，失败 {v3_fail} 家，共 {len(v3_results)} 条新闻")

# 保存V3结果
if v3_results:
    df_v3 = pd.DataFrame(v3_results)
    v3_path = os.path.join(RAW_DIR, 'news_deepseek_v3.csv')
    df_v3.to_csv(v3_path, index=False, encoding='utf-8-sig')
    print(f"    ✅ 已保存：{v3_path}")
else:
    print("    ⚠️ 无V3新闻数据")

# ============================================================================
# 6.2 查询DeepSeek-R1事件前后新闻（2025-01-15至2025-01-25）
# ============================================================================
print("\n【3】查询DeepSeek-R1事件前后新闻（2025-01-15至2025-01-25）...")

R1_START = date_to_timestamp('2025-01-15')
R1_END = date_to_timestamp('2025-01-25')

r1_results = []
r1_success = 0
r1_fail = 0

for i, firm in enumerate(FIRMS):
    print(f"    [{i + 1}/{len(FIRMS)}] 查询：{firm[:20]}...", end=" ")
    result = search_news_by_company(token, firm, R1_START, R1_END, page=1, page_size=10)

    if result and result.get('list'):
        for news in result.get('list', []):
            news['company_name'] = firm
            r1_results.append(news)
        r1_success += 1
        print(f"✅ 获取 {len(result.get('list', []))} 条")
    else:
        r1_fail += 1
        print("⏭️ 无新闻")

    time.sleep(0.2)

print(f"\n    R1统计：成功 {r1_success} 家企业，失败 {r1_fail} 家，共 {len(r1_results)} 条新闻")

if r1_results:
    df_r1 = pd.DataFrame(r1_results)
    r1_path = os.path.join(RAW_DIR, 'news_deepseek_r1.csv')
    df_r1.to_csv(r1_path, index=False, encoding='utf-8-sig')
    print(f"    ✅ 已保存：{r1_path}")
else:
    print("    ⚠️ 无R1新闻数据")

# ============================================================================
# 7. 生成API调用日志
# ============================================================================
print("\n【4】生成API调用日志...")

log_lines = []
log_lines.append("=" * 70)
log_lines.append("企洞察API调用日志")
log_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_lines.append("=" * 70)
log_lines.append(f"appKey: {APP_KEY}")
log_lines.append(f"有效期限：15天（自2026-07-24起）")
log_lines.append("")
log_lines.append("【V3事件（2024-12-21至2024-12-31）】")
log_lines.append(f"  查询企业数：{len(FIRMS)}")
log_lines.append(f"  成功查询：{v3_success}")
log_lines.append(f"  失败查询：{v3_fail}")
log_lines.append(f"  新闻总数：{len(v3_results)}")
log_lines.append("")
log_lines.append("【R1事件（2025-01-15至2025-01-25）】")
log_lines.append(f"  查询企业数：{len(FIRMS)}")
log_lines.append(f"  成功查询：{r1_success}")
log_lines.append(f"  失败查询：{r1_fail}")
log_lines.append(f"  新闻总数：{len(r1_results)}")
log_lines.append("")
log_lines.append("【行业新闻】")
log_lines.append("  说明：同花顺AI概念接口（news_concept: 300345）已失效，本版跳过")
log_lines.append("  替代方案：从60家企业新闻中提取AI竞品相关内容")
log_lines.append("")
log_lines.append("=" * 70)

log_path = os.path.join(RAW_DIR, 'api_call_log.txt')
with open(log_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines))

print(f"    ✅ 日志已保存：{log_path}")

# ============================================================================
# 8. 完成
# ============================================================================
print("\n" + "=" * 70)
print("🎉 企洞察API数据获取完成！")
print("=" * 70)
print("\n输出文件清单：")
print(f"  [新闻] {os.path.join(RAW_DIR, 'news_deepseek_v3.csv')}")
print(f"  [新闻] {os.path.join(RAW_DIR, 'news_deepseek_r1.csv')}")
print(f"  [日志] {os.path.join(RAW_DIR, 'api_call_log.txt')}")
print("\n" + "=" * 70)