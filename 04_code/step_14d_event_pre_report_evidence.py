# -*- coding: utf-8 -*-
"""
步骤14D：检索并提取事件前年度报告分类证据

数据来源：巨潮资讯网（深圳证券交易所法定信息披露平台）。
目标报告：在2024-12-26之前公告的《2023年年度报告》正文。
程序不会根据显著性修改分类；自动Layer仅为审核建议。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import re
import sys
import time
import pandas as pd
import requests
from pypdf import PdfReader

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(r"D:/thailand study/26_7_23paper")
META = BASE / "05_output/revision_step14a/tables/table_e1_firm_metadata_60.csv"
AUDIT = (
    BASE / "05_output/revision_step14b/tables/"
    "table_f1_layer_audit_and_provisional_freeze.csv"
)
OUT_ROOT = BASE / "05_output/revision_step14d"
TABLE_DIR = OUT_ROOT / "tables"
REPORT_DIR = OUT_ROOT / "reports_2023"
TEXT_DIR = OUT_ROOT / "evidence_text"
for directory in (TABLE_DIR, REPORT_DIR, TEXT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

CNINFO_QUERY = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_MAP = "https://www.cninfo.com.cn/new/data/szse_stock.json"
STATIC_ROOT = "https://static.cninfo.com.cn/"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.cninfo.com.cn/",
}
EVENT_DATE = pd.Timestamp("2024-12-26")

RULES = {
    "上游": [
        "芯片", "半导体", "集成电路", "处理器", "服务器", "光模块",
        "光通信", "印制电路", "数据中心", "算力", "存储器", "GPU",
    ],
    "中游": [
        "人工智能", "软件", "信息技术", "系统集成", "云计算", "大数据",
        "算法", "平台", "计算机视觉", "网络安全", "数据库",
    ],
    "下游": [
        "教育", "医疗", "金融", "传媒", "游戏", "办公", "汽车",
        "智慧城市", "零售", "政务", "广告", "应用服务",
    ],
}
EVIDENCE_TERMS = [
    "主营业务", "主要业务", "核心业务", "主要产品", "主要服务",
    "业务模式", "产品及服务",
]


def get_org_map():
    """取得巨潮股票代码与机构ID映射。"""
    response = requests.get(CNINFO_MAP, headers=HEADERS, timeout=30)
    response.raise_for_status()
    rows = response.json()["stockList"]
    return {str(row["code"]).zfill(6): row["orgId"] for row in rows}


def find_report(code, org_id):
    """查询单家公司2023年年度报告正文。"""
    column = "sse" if code.startswith(("5", "6", "9")) else "szse"
    form = {
        "stock": f"{code},{org_id}", "searchkey": "", "plate": "",
        "category": "category_ndbg_szsh", "trade": "", "column": column,
        "pageNum": "1", "pageSize": "30", "tabName": "fulltext",
        "seDate": "2024-01-01~2024-12-25", "isHLtitle": "true",
    }
    response = requests.post(
        CNINFO_QUERY, headers=HEADERS, data=form, timeout=30
    )
    response.raise_for_status()
    announcements = response.json().get("announcements") or []
    candidates = []
    for item in announcements:
        title = re.sub(r"<[^>]+>", "", str(item.get("announcementTitle", "")))
        # 个别公司标题存在“2023年年年度报告”等披露端原始写法，
        # 因此允许“2023年”与“年度报告”之间出现少量文字。
        if not re.search(r"2023年.{0,8}年度报告", title):
            continue
        if any(word in title for word in ("摘要", "英文", "取消", "更正后")):
            continue
        report_date = pd.to_datetime(
            item.get("announcementTime"), unit="ms", errors="coerce"
        )
        candidates.append((report_date, title, item))
    if not candidates:
        return {"股票代码": code, "年报检索状态": "未找到"}
    candidates.sort(key=lambda item: item[0], reverse=True)
    report_date, title, item = candidates[0]
    relative = str(item["adjunctUrl"])
    return {
        "股票代码": code,
        "年报标题": title,
        "年报公告日期": report_date.date().isoformat(),
        "年报PDF_URL": STATIC_ROOT + relative,
        "年报检索状态": "成功",
        "公告是否早于V3事件": "是" if report_date < EVENT_DATE else "否",
    }


def download_report(row):
    """下载单份年报，已存在且有效时直接使用缓存。"""
    code = row["股票代码"]
    if row.get("年报检索状态") != "成功":
        return code, "未下载", ""
    target = REPORT_DIR / f"{code}_2023_annual_report.pdf"
    try:
        if not target.exists() or target.stat().st_size < 10_000:
            response = requests.get(
                row["年报PDF_URL"],
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=90,
            )
            response.raise_for_status()
            target.write_bytes(response.content)
        return code, "成功", str(target)
    except Exception as exc:
        return code, "失败", f"{type(exc).__name__}: {exc}"


def normalize_text(text):
    """清理PDF抽取文本中的连续空格和换行。"""
    return re.sub(r"\s+", "", text or "")


def extract_evidence(code, pdf_path):
    """从年报前80页提取业务关键词上下文，并保留页码。"""
    if not pdf_path:
        return {"股票代码": code, "文本提取状态": "未提取"}
    try:
        text_file = TEXT_DIR / f"{code}_business_evidence.txt"
        if text_file.exists() and text_file.stat().st_size > 0:
            excerpt = text_file.read_text(encoding="utf-8")
            return {
                "股票代码": code,
                "文本提取状态": "成功",
                "扫描页数": "缓存",
                "证据片段数": excerpt.count("[PDF第"),
                "年报业务证据摘录": excerpt,
                "证据文本文件": str(text_file),
            }
        reader = PdfReader(pdf_path)
        contexts = []
        scanned = min(len(reader.pages), 80)
        for page_number in range(scanned):
            text = normalize_text(reader.pages[page_number].extract_text())
            for term in EVIDENCE_TERMS:
                start = text.find(term)
                if start >= 0:
                    left = max(0, start - 120)
                    right = min(len(text), start + 700)
                    contexts.append(
                        f"[PDF第{page_number + 1}页]{text[left:right]}"
                    )
                    break
            if len(contexts) >= 5:
                break
        excerpt = "\n".join(contexts)
        text_file.write_text(excerpt, encoding="utf-8")
        return {
            "股票代码": code,
            "文本提取状态": "成功" if excerpt else "未找到业务关键词",
            "扫描页数": scanned,
            "证据片段数": len(contexts),
            "年报业务证据摘录": excerpt,
            "证据文本文件": str(text_file),
        }
    except Exception as exc:
        return {
            "股票代码": code,
            "文本提取状态": "失败",
            "文本提取错误": f"{type(exc).__name__}: {exc}",
        }


def suggest_layer(text):
    """对年报证据摘录进行透明关键词计分，不自动覆盖原Layer。"""
    text = str(text or "")
    scores = {
        layer: sum(text.count(word) for word in words)
        for layer, words in RULES.items()
    }
    best = max(scores.values())
    winners = [layer for layer, value in scores.items() if value == best and best > 0]
    suggestion = winners[0] if len(winners) == 1 else "无法自动判断"
    return suggestion, scores


metadata = pd.read_csv(META, encoding="utf-8-sig", dtype={"股票代码": str})
audit = pd.read_csv(AUDIT, encoding="utf-8-sig", dtype={"股票代码": str})
org_map = get_org_map()

report_rows = []
for number, code in enumerate(metadata["股票代码"], start=1):
    print(f"[检索 {number:02d}/60] {code}")
    org_id = org_map.get(code)
    if not org_id:
        report_rows.append({"股票代码": code, "年报检索状态": "缺少机构ID"})
        continue
    try:
        report_rows.append(find_report(code, org_id))
    except Exception as exc:
        report_rows.append({
            "股票代码": code, "年报检索状态": "失败",
            "年报检索错误": f"{type(exc).__name__}: {exc}",
        })
    time.sleep(0.12)

reports = pd.DataFrame(report_rows)
download_results = {}
with ThreadPoolExecutor(max_workers=5) as pool:
    futures = {
        pool.submit(download_report, row): row["股票代码"]
        for row in reports.to_dict("records")
    }
    for future in as_completed(futures):
        code, status, detail = future.result()
        download_results[code] = (status, detail)
        print(f"[下载] {code}: {status}")

reports["PDF下载状态"] = reports["股票代码"].map(
    lambda code: download_results.get(code, ("未执行", ""))[0]
)
reports["本地PDF路径"] = reports["股票代码"].map(
    lambda code: (
        download_results.get(code, ("", ""))[1]
        if download_results.get(code, ("", ""))[0] == "成功" else ""
    )
)

evidence_rows = []
for number, row in enumerate(reports.to_dict("records"), start=1):
    print(f"[提取 {number:02d}/60] {row['股票代码']}")
    evidence_rows.append(
        extract_evidence(row["股票代码"], row.get("本地PDF路径", ""))
    )
evidence = pd.DataFrame(evidence_rows)
result = (
    metadata.merge(reports, on="股票代码", how="left")
    .merge(evidence, on="股票代码", how="left")
    .merge(
        # 原始Layer已由14A元数据表携带；这里只补暂定冻结Layer，
        # 避免合并后形成原始Layer_x与原始Layer_y。
        audit[["股票代码", "暂定冻结Layer"]],
        on="股票代码", how="left",
    )
)

suggestions, scores = [], []
for text in result["年报业务证据摘录"].fillna(""):
    suggestion, score = suggest_layer(text)
    suggestions.append(suggestion)
    scores.append(score)
result["年报证据机器建议Layer"] = suggestions
for layer in ("上游", "中游", "下游"):
    result[f"年报{layer}得分"] = [score[layer] for score in scores]
result["年报建议与原始Layer是否冲突"] = (
    result["年报证据机器建议Layer"].ne("无法自动判断")
    & result["年报证据机器建议Layer"].ne(result["原始Layer"])
).map({True: "是", False: "否"})
result["人工最终Layer"] = ""
result["人工审核状态"] = "待审核"
result["最终分类理由"] = ""
result["最终证据页码"] = ""
result["最终分类是否冻结"] = "否"

out = TABLE_DIR / "table_h1_event_pre_annual_report_evidence.csv"
result.to_csv(out, index=False, encoding="utf-8-sig")
conflicts = result.loc[
    result["年报建议与原始Layer是否冲突"].eq("是")
    | result["年报证据机器建议Layer"].eq("无法自动判断")
].copy()
conflicts.to_csv(
    TABLE_DIR / "table_h2_priority_manual_review.csv",
    index=False, encoding="utf-8-sig",
)
summary = pd.DataFrame([
    {"核验项": "公司总数", "数量": len(result)},
    {"核验项": "事件前年报链接成功数",
     "数量": int(result["年报检索状态"].eq("成功").sum())},
    {"核验项": "PDF下载成功数",
     "数量": int(result["PDF下载状态"].eq("成功").sum())},
    {"核验项": "业务证据提取成功数",
     "数量": int(result["文本提取状态"].eq("成功").sum())},
    {"核验项": "年报机器建议与原始Layer冲突数",
     "数量": int(result["年报建议与原始Layer是否冲突"].eq("是").sum())},
    {"核验项": "机器无法自动判断数",
     "数量": int(result["年报证据机器建议Layer"].eq("无法自动判断").sum())},
    {"核验项": "人工最终冻结数",
     "数量": int(result["最终分类是否冻结"].eq("是").sum())},
])
summary.to_csv(
    TABLE_DIR / "table_h3_step14d_summary.csv",
    index=False, encoding="utf-8-sig",
)

print("=" * 76)
print("步骤14D：事件前年报证据固化")
print("=" * 76)
print(summary.to_string(index=False))
print(f"\n输出：{out}")
