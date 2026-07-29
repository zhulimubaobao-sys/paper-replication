# -*- coding: utf-8 -*-
"""
调试脚本：打印企洞察API原始返回结果
"""
import requests
import json
from datetime import datetime

APP_KEY = "6A63041F0146"
APP_SECRET = "1E768F54DD717C7339D6CDED0F48C5B7"
TOKEN_URL = "https://b2b-api.10jqka.com.cn/gateway/service-mana/app/login-appkey"
NEWS_SEARCH_URL = "https://b2b-api.10jqka.com.cn/gateway/arsenal/yq_qdc/enterprise_info_api/v3/news_search"
INDUSTRY_NEWS_URL = "https://b2b-api.10jqka.com.cn/gateway/arsenal/yq_qdc/info/v1/information/industry_concept_news"

# 1. 获取Token
print("【获取Token】")
resp = requests.get(f"{TOKEN_URL}?appKey={APP_KEY}&appSecret={APP_SECRET}")
token_data = resp.json()
print(f"Token响应: {json.dumps(token_data, indent=2, ensure_ascii=False)}")

if token_data.get('flag') != 0:
    print("❌ Token获取失败")
    exit()

token = token_data['data']['access_token']
headers = {'open-authorization': f'Bearer {token}'}
print(f"✅ Token: {token[:30]}...\n")

# 2. 测试企业新闻（尝试三种名称格式）
print("【测试1：企业新闻查询 - 寒武纪】")
# 尝试1：简称
params1 = {'corp_name': '寒武纪', 'sdate': '1734739200', 'edate': '1735574400', 'page': 1, 'page_size': 5}
r1 = requests.get(NEWS_SEARCH_URL, headers=headers, params=params1)
print(f"查询简称'寒武纪' -> 状态码: {r1.status_code}")
print(f"返回内容: {json.dumps(r1.json(), indent=2, ensure_ascii=False)[:500]}...\n")

# 尝试2：全称（寒武纪全称）
params2 = {'corp_name': '中科寒武纪科技股份有限公司', 'sdate': '1734739200', 'edate': '1735574400', 'page': 1,
           'page_size': 5}
r2 = requests.get(NEWS_SEARCH_URL, headers=headers, params=params2)
print(f"查询全称'中科寒武纪科技股份有限公司' -> 状态码: {r2.status_code}")
print(f"返回内容: {json.dumps(r2.json(), indent=2, ensure_ascii=False)[:500]}...\n")

# 3. 测试行业新闻
print("【测试2：行业概念新闻查询】")
params3 = {
    'stime': '1733011200',  # 2024-12-01
    'etime': '1738310400',  # 2025-01-31
    'page': 1,
    'page_size': 5,
    'data_type': 'industry_concept',
    'news_concept': '300345'
}
r3 = requests.get(INDUSTRY_NEWS_URL, headers=headers, params=params3)
print(f"查询AI概念(300345) -> 状态码: {r3.status_code}")
print(f"返回内容: {json.dumps(r3.json(), indent=2, ensure_ascii=False)[:500]}...")

# 4. 测试近期数据（看看API到底有没有数据）
print("\n【测试3：查询近期数据（2026-07-01至2026-07-29）】")
now = int(datetime.now().timestamp())
last_month = now - 30 * 24 * 3600
params4 = {'corp_name': '寒武纪', 'sdate': str(last_month), 'edate': str(now), 'page': 1, 'page_size': 5}
r4 = requests.get(NEWS_SEARCH_URL, headers=headers, params=params4)
print(f"查询近期'寒武纪' -> 状态码: {r4.status_code}")
print(f"返回内容: {json.dumps(r4.json(), indent=2, ensure_ascii=False)[:500]}...")