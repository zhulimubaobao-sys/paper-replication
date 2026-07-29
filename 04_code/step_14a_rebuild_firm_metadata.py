# -*- coding: utf-8 -*-
"""
步骤14A：重建60家公司基础信息表

本程序只做可验证的事实采集：
1. 从步骤13A母表读取60个股票代码和原始Layer；
2. 从东方财富公开公司概况接口读取证券简称、公司全称、行业、公司简介和经营范围；
3. 保存逐公司来源URL与抓取日期；
4. 不依据当前网页内容自动修改Layer，也不把当前网页信息冒充事件前证据。
"""

from datetime import date
from pathlib import Path
import json
import gzip
import time
from urllib.request import Request, urlopen
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
INPUT = BASE / "05_output/revision_step13a/tables/table_c1_firm_layer_and_coverage.csv"
OUT_DIR = BASE / "05_output/revision_step14a/tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "table_e1_firm_metadata_60.csv"
SUMMARY = OUT_DIR / "table_e2_metadata_summary.csv"


def norm_code(value):
    """统一为6位股票代码。"""
    return str(value).split(".")[0].replace(".0", "").zfill(6)


def exchange_prefix(code):
    """生成东方财富公司概况接口需要的市场前缀。"""
    return ("SH" if code.startswith(("5", "6", "9")) else "SZ") + code


def fetch_profile(code, retries=3):
    """读取单家公司公开概况；失败时重试并返回可诊断错误。"""
    sec_code = exchange_prefix(code)
    url = (
        "https://emweb.securities.eastmoney.com/"
        f"PC_HSF10/CompanySurvey/PageAjax?code={sec_code}"
    )
    last_error = ""
    for attempt in range(retries):
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept-Encoding": "identity",
                },
            )
            with urlopen(req, timeout=20) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding", "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                payload = json.loads(raw.decode("utf-8"))
            rows = payload.get("jbzl") or []
            if not rows:
                raise ValueError("接口未返回jbzl公司概况")
            row = rows[0]
            return {
                "股票代码": code,
                "证券简称": row.get("SECURITY_NAME_ABBR", ""),
                "公司全称": row.get("ORG_NAME", ""),
                "交易所": row.get("TRADE_MARKET", ""),
                "东方财富行业": row.get("EM2016", ""),
                "证监会行业": row.get("INDUSTRYCSRC1", ""),
                "公司简介": row.get("ORG_PROFILE", ""),
                "经营范围": row.get("BUSINESS_SCOPE", ""),
                "公司官网": row.get("ORG_WEB", ""),
                "基础信息来源URL": url,
                "抓取日期": date.today().isoformat(),
                "抓取状态": "成功",
                "抓取错误": "",
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(1.0 + attempt)
    return {
        "股票代码": code,
        "抓取状态": "失败",
        "抓取错误": last_error,
        "基础信息来源URL": url,
        "抓取日期": date.today().isoformat(),
    }


firms = pd.read_csv(INPUT, encoding="utf-8-sig")
firms["股票代码"] = firms["Stkcd"].map(norm_code)
firms = (
    firms[["股票代码", "Layer"]]
    .drop_duplicates("股票代码")
    .rename(columns={"Layer": "原始Layer"})
)

cached = {}
if OUT.exists():
    old = pd.read_csv(OUT, encoding="utf-8-sig", dtype={"股票代码": str})
    old = old.loc[old["抓取状态"].eq("成功")]
    cached = {row["股票代码"]: row.to_dict() for _, row in old.iterrows()}

profiles = []
for number, code in enumerate(firms["股票代码"], start=1):
    if code in cached:
        print(f"[{number:02d}/60] 使用缓存 {code}")
        profiles.append(cached[code])
        continue
    print(f"[{number:02d}/60] 读取 {code}")
    profiles.append(fetch_profile(code))
    time.sleep(0.15)

profile_frame = pd.DataFrame(profiles)
# 缓存文件可能带有上次合并后的原始Layer等列；这里只允许元数据字段参与合并，
# 避免生成“原始Layer_x/原始Layer_y”并污染下游审计。
metadata_columns = [
    "股票代码", "证券简称", "公司全称", "交易所", "东方财富行业",
    "证监会行业", "公司简介", "经营范围", "公司官网",
    "基础信息来源URL", "抓取日期", "抓取状态", "抓取错误",
]
for column in metadata_columns:
    if column not in profile_frame.columns:
        profile_frame[column] = ""
metadata = firms.merge(
    profile_frame[metadata_columns], on="股票代码", how="left"
)
metadata["原始Layer来源"] = (
    "04_code/60gupiao.py与04_code/financialtest60.py中的硬编码名单"
)
metadata["是否属于事件前分类证据"] = "否（当前公司概况仅用于补齐基础信息）"
metadata.to_csv(OUT, index=False, encoding="utf-8-sig")

summary = pd.DataFrame([
    {"核验项": "公司总数", "数量": len(metadata)},
    {"核验项": "代码唯一数", "数量": metadata["股票代码"].nunique()},
    {"核验项": "成功获取公司信息数",
     "数量": int((metadata["抓取状态"] == "成功").sum())},
    {"核验项": "证券简称缺失数",
     "数量": int(metadata["证券简称"].fillna("").eq("").sum())},
    {"核验项": "公司简介缺失数",
     "数量": int(metadata["公司简介"].fillna("").eq("").sum())},
])
summary.to_csv(SUMMARY, index=False, encoding="utf-8-sig")

print("=" * 76)
print("步骤14A：60家公司基础信息重建")
print("=" * 76)
print(summary.to_string(index=False))
print(f"\n输出：{OUT}")
