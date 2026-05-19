from __future__ import annotations

import base64
import importlib.util
import json
import logging
import re
import sys
import time
import types
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from monitoring import SpiderMonitor, build_biz_type


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERAL_DIR = PROJECT_ROOT / "general"


MODEL_ENRICHMENT_FALLBACK_EXCEPTIONS = (
    requests.RequestException,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


BASE_URL = "http://ggzyjy.zibo.gov.cn:8082"
SITE_GUID = "7eb5f7f1-9041-43ad-8e13-8fcb82ea831a"
PROJECT_NAME = "/EpointWebBuilder_zbggzy"
ANONYMOUS_TOKEN_URL = (
    f"{BASE_URL}{PROJECT_NAME}/rest/getOauthInfoAction/getNoUserAccessToken"
)
LIST_API_URL = f"{BASE_URL}{PROJECT_NAME}/rest/frontAppCustomAction/getPageInfoListNew"
MODEL_TOKEN = "FACBED0693D0F2361DED36C4BDF35E19"
MODEL_NAME = "qwen-doc-turbo"
SUPPORTED_PROCUREMENT_METHODS = {
    "单一来源",
    "邀请招标",
    "竞争性谈判",
    "询价",
    "竞争性磋商",
    "公开招标",
}
SUPPORTED_BID_NOTICE_TYPES = {"招标公告", "采购公告", "交易公告"}

SITE_CONTEXT = {
    "province_code": "370000",
    "province_name": "山东省",
    "city_id": "370300",
    "city_name": "淄博市",
    "web_source": "淄博市公共资源交易网",
}

# 显式运行配置。测试单个一级模块 / 二级栏目时，直接改这里即可。
RUN_CONFIG = {
    # 全量
    "module_name": "全部模块",
    "notice_type": "",
    # 单测
    # "module_name": "建设工程",
    # "notice_type": "招标公告",
    # "module_name": "政府采购",
    # "notice_type": "采购公告",
    # "module_name": "国企采购",
    # "notice_type": "采购公告",
    # "module_name": "药械采购",
    # "notice_type": "采购公告",
    # "module_name": "其他交易",
    # "notice_type": "采购公告",
    # "module_name": "农村工程",
    # "notice_type": "交易公告",
    # "module_name": "农村采购",
    # "notice_type": "交易公告",
    # "module_name": "土地流转",
    # "notice_type": "交易公告",
    # "module_name": "集体资产",
    # "notice_type": "交易公告",
    # "module_name": "农业设施",
    # "notice_type": "交易公告",
    # "module_name": "其他交易(农村产权)",
    # "notice_type": "交易公告",
    "start_page": 1,
    "max_pages": 0,
    "page_size": 15,
    "timeout_seconds": 30,
    "detail_delay_seconds": 0,
    "enable_model_enrichment": True,
}

AREA_CODE_MAPPING = {
    "市本级": ("370301", "淄博市"),
    "张店区": ("370303", "淄博市张店区"),
    "淄川区": ("370302", "淄博市淄川区"),
    "博山区": ("370304", "淄博市博山区"),
    "周村区": ("370306", "淄博市周村区"),
    "临淄区": ("370305", "淄博市临淄区"),
    "桓台县": ("370321", "淄博市桓台县"),
    "高青县": ("370322", "淄博市高青县"),
    "沂源县": ("370323", "淄博市沂源县"),
    "高新区": ("370307", "淄博高新区"),
    "经开区": ("370351", "淄博经开区"),
    "文昌湖区": ("370308", "淄博文昌湖区"),
}

MODULE_SOURCES = {
    "建设工程": {"path": "/jyxx/002001/gonggongziyuan.html", "parent_type": "建设工程"},
    "政府采购": {"path": "/jyxx/002002/gonggongziyuan.html", "parent_type": "政府采购"},
    "自然资源": {
        "path": "/jyxx/002011/gonggongziyuan_zrzy.html",
        "parent_type": "自然资源",
    },
    "产权交易": {"path": "/jyxx/002004/gonggongziyuan.html", "parent_type": "产权交易"},
    "国企采购": {"path": "/jyxx/002009/gonggongziyuan.html", "parent_type": "国企采购"},
    "药械采购": {"path": "/jyxx/002007/gonggongziyuan.html", "parent_type": "药械采购"},
    "其他交易": {"path": "/jyxx/002008/gonggongziyuan.html", "parent_type": "其他交易"},
    "农村工程": {
        "path": "/nccqjyxx/027001/gonggongziyuan_nccq.html",
        "parent_type": "农村工程",
    },
    "农村采购": {
        "path": "/nccqjyxx/027002/gonggongziyuan_nccq.html",
        "parent_type": "农村采购",
    },
    "土地流转": {
        "path": "/nccqjyxx/027003/gonggongziyuan_nccq.html",
        "parent_type": "土地流转",
    },
    "集体资产": {
        "path": "/nccqjyxx/027004/gonggongziyuan_nccq.html",
        "parent_type": "集体资产",
    },
    "农业设施": {
        "path": "/nccqjyxx/027005/gonggongziyuan_nccq.html",
        "parent_type": "农业设施",
    },
    "其他交易(农村产权)": {
        "path": "/nccqjyxx/027008/gonggongziyuan_nccq.html",
        "parent_type": "其他交易(农村产权)",
    },
    "供需信息": {
        "path": "/nccqjyxx/027007/gonggongziyuan_gxxx.html",
        "parent_type": "供需信息",
    },
}

EXCLUDED_MODULE_NAMES = {
    "自然资源",
    "供需信息",
    "产权交易",
}

EXCLUDED_NOTICE_TYPES = {
    "招标项目计划",
    "变更公告",
    "澄清公告",
    "更正公告",
    "终止公告",
    "废标公告",
    "流标公告",
    "异常公告",
    "异议回复",
    "验收公告",
    "需求（意向）公示",
    "合同公告",
    "合同公示",
    "合同公示及变更",
    "土地信息",
}

NOTICE_TYPE_PATTERN = re.compile(
    r"<li\s+data-value=\"(?P<category>\d+)\">\s*(?P<name>[^<]+)\s*</li>", re.S
)
TAG_PATTERN = re.compile(r"<[^>]+>")
CONTACT_SUFFIX_PATTERN = re.compile(
    r"[;；，,\s]*(?:联系人|联系电话|电话|联系方式)\s*[:：].*$"
)


@dataclass
class ModuleTask:
    module_name: str
    parent_type: str
    category_num: str
    notice_type: str
    module_path: str


RecordBuilder = Callable[[dict[str, Any]], dict[str, Any]]
RecordEnricher = Callable[
    ["ZbggzyRuntime", dict[str, Any], dict[str, Any]], dict[str, Any]
]


def normalize_text(value: str) -> str:
    text = unescape(value or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_html_tags(value: str) -> str:
    return normalize_text(TAG_PATTERN.sub("", value))


def extract_plain_text(value: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(value, "html.parser")
        for tag in soup.find_all(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n")
    else:
        text = re.sub(r"<script\b[^>]*>.*?</script>", "", value, flags=re.I | re.S)
        text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.I | re.S)
        text = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", text, flags=re.I | re.S)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(
            r"</(?:p|div|tr|li|h1|h2|h3|h4|h5|h6|table|section)>",
            "\n",
            text,
            flags=re.I,
        )
        text = TAG_PATTERN.sub("", text)
    text = unescape(text or "").replace("\u00a0", " ")
    text = text.replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _load_python_module(module_name: str, file_path: Path) -> Any:
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_money_parser_class() -> Any:
    amount_module = _load_python_module(
        "zbggzy_bid.AmountConverter", GENERAL_DIR / "AmountConverter.py"
    )
    return getattr(amount_module, "MoneyParser")


MoneyParser = _load_money_parser_class()


def clean_procurement_unit(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    text = CONTACT_SUFFIX_PATTERN.sub("", text)
    return normalize_text(text)


def clean_detail_fragment(html: str) -> str:
    cleaned = html
    cleaned = re.sub(
        r"<div[^>]+id=\"viewGuid\"[^>]*>.*?</div>", "", cleaned, flags=re.I | re.S
    )
    cleaned = re.sub(
        r"<h2[^>]+id=\"iframetitle\"[^>]*>.*?</h2>", "", cleaned, flags=re.I | re.S
    )
    cleaned = re.sub(
        r"<div[^>]+class=\"znyd\"[^>]*>.*?</div>", "", cleaned, flags=re.I | re.S
    )
    cleaned = re.sub(
        r"<div[^>]+class=['\"][^'\"]*\bznyd-button\b[^'\"]*['\"][^>]*>.*?</div>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"<div[^>]+class=['\"][^'\"]*\bchain\b[^'\"]*['\"][^>]*>.*?</div>\s*</div>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"<div[^>]+class=['\"][^'\"]*\bchain\b[^'\"]*['\"][^>]*>.*?</div>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"<div[^>]*>\s*<a[^>]+href=['\"][^'\"]*downloadztbattach[^'\"]*['\"][^>]*>.*?</a>\s*</div>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"<a[^>]+href=['\"][^'\"]*(?:downloadztbattach|downloadfile|download\.do|attach|file)[^'\"]*['\"][^>]*>.*?</a>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"<(?:div|p)[^>]*>[^<]*(?:https?://[^\s<>'\"]+\.(?:pdf|doc|docx|xls|xlsx|zip|rar|7z))[^\n<]*</(?:div|p)>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"https?://[^\s<>'\"]+\.(?:pdf|doc|docx|xls|xlsx|zip|rar|7z)",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"</?a\b[^>]*>", "", cleaned, flags=re.I)
    cleaned = re.sub(
        r"<meta[^>]+http-equiv=['\"]Content-Type['\"][^>]*>", "", cleaned, flags=re.I
    )
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", cleaned, flags=re.I | re.S)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
    return cleaned.strip()


def _extract_attachment_entries(html: str, detail_url: str) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for anchor_html, href in re.findall(
        r"(<a\b[^>]*href=['\"]([^'\"]+)['\"][^>]*>.*?</a>)", html, flags=re.I | re.S
    ):
        href = normalize_text(href)
        if not href:
            continue
        if "downloadztbattach" not in href and not re.search(
            r"\.(pdf|doc|docx|xls|xlsx|zip|rar|7z)(?:$|[?#])", href, flags=re.I
        ):
            continue
        file_name = ""
        title_match = re.search(r"title=['\"]([^'\"]+)['\"]", anchor_html, flags=re.I)
        if title_match:
            file_name = normalize_text(title_match.group(1))
        if not file_name:
            file_name = strip_html_tags(anchor_html)
        file_url = urljoin(detail_url, href)
        file_type = Path(file_name).suffix.lower().lstrip(".")
        attachments.append(
            {"fileUrl": file_url, "fileType": file_type, "fileName": file_name}
        )
    deduplicated: list[dict[str, str]] = []
    seen: set[str] = set()
    for attachment in attachments:
        file_url = attachment["fileUrl"]
        if file_url in seen:
            continue
        seen.add(file_url)
        deduplicated.append(attachment)
    return deduplicated


def parse_table_rows(html: str) -> list[list[str]]:
    if BeautifulSoup is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    rows: list[list[str]] = []
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [
                normalize_text(cell.get_text(" ", strip=True))
                for cell in tr.find_all(["td", "th"])
            ]
            cells = [cell for cell in cells if cell]
            if cells:
                rows.append(cells)
    return rows


def parse_detail(detail_html: str, detail_url: str) -> dict[str, Any]:
    plain_text = extract_plain_text(detail_html)
    rows = parse_table_rows(detail_html)
    field_map: dict[str, str] = {}
    for row in rows:
        if len(row) >= 2 and len(row) % 2 == 0:
            for index in range(0, len(row), 2):
                key = normalize_text(row[index]).rstrip("：:")
                value = normalize_text(row[index + 1])
                if key and value and key not in field_map:
                    field_map[key] = value

    inline_patterns = [
        "项目名称",
        "项目编号",
        "采购人名称",
        "采购人",
        "采购单位",
        "采购方式",
        "预算金额",
    ]
    for key in inline_patterns:
        match = re.search(rf"{re.escape(key)}\s*[：:]\s*([^\n]+)", plain_text)
        if match and key not in field_map:
            field_map[key] = normalize_text(match.group(1))

    title = ""
    if BeautifulSoup is not None:
        soup = BeautifulSoup(detail_html, "html.parser")
        h1 = soup.find("h1")
        if h1:
            title = normalize_text(h1.get_text(" ", strip=True))
        if not title:
            title_node = soup.find(id="iframetitle")
            if title_node:
                title = normalize_text(title_node.get_text(" ", strip=True))
    if not title:
        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", detail_html, flags=re.I | re.S)
        if title_match:
            title = strip_html_tags(title_match.group(1))

    return {
        "title": title,
        "plain_text": plain_text,
        "field_map": field_map,
        "table_rows": rows,
        "detail_url": detail_url,
    }


def normalize_money(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    clean_value = (
        text.replace(",", "")
        .replace("￥", "")
        .replace("¥", "")
        .replace("元", "")
        .strip()
    )
    if re.fullmatch(r"\d+(?:\.\d+)?", clean_value):
        return f"{clean_value}元"
    try:
        return MoneyParser().convert_amount(text)
    except (ValueError, TypeError):
        pass
    return text


def normalize_procurement_method(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    if text in SUPPORTED_PROCUREMENT_METHODS:
        return text
    for item in SUPPORTED_PROCUREMENT_METHODS:
        if item in text:
            return item
    return "其他类型"


def extract_procurement_method_from_text(text: str) -> str:
    plain_text = normalize_text(text)
    if not plain_text:
        return ""
    for item in SUPPORTED_PROCUREMENT_METHODS:
        if item in plain_text:
            return item
    return ""


def pick_first_non_empty(values: list[str]) -> str:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return ""


def extract_project_num(text: str) -> str:
    patterns = [
        r"(?:项目编号|招标编号|采购文件编号)\s*[：:]\s*([A-Za-z0-9\-]+)",
        r"\b([A-Z]{2,}[A-Z0-9\-]*\d{4,}[A-Z0-9\-]*)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1))
    return ""


def extract_budget_amount(text: str) -> str:
    patterns = [
        r"(?:预算金额|合同估算价|估算价|投资额)\s*[：:]?\s*([0-9][0-9,]*(?:\.\d+)?)\s*元",
        r"([0-9][0-9,]*(?:\.\d+)?)\s*元",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_money(match.group(1))
    return ""


def extract_rural_listing_price(text: str) -> str:
    match = re.search(
        r"挂牌价格\s*[：:]\s*([0-9][0-9,]*(?:\.\d+)?\s*(?:万元|元))", text
    )
    if not match:
        return ""
    return normalize_rural_listing_price(match.group(1))


def normalize_rural_listing_price(value: str) -> str:
    text = normalize_text(value).replace(",", "")
    if not text:
        return ""
    amount_match = re.fullmatch(r"(\d+(?:\.\d+)?)(万元|元)", text)
    if not amount_match:
        return normalize_money(text)
    number = float(amount_match.group(1))
    unit = amount_match.group(2)
    if unit == "万元":
        number = number * 10000
    if number.is_integer():
        return f"{number:.1f}元"
    return f"{number}元"


def extract_rural_expected_total_price(text: str) -> str:
    match = re.search(r"预计总价\s*([0-9][0-9,]*(?:\.\d+)?\s*(?:万元|元))", text)
    if not match:
        return ""
    return normalize_rural_listing_price(match.group(1))


def extract_rural_engineering_table_info(
    rows: list[list[str]], text: str
) -> dict[str, str]:
    result = {
        "listing_price": "",
        "entity_name": "",
        "contact_name": "",
        "contact_phone": "",
    }
    in_entity_section = False
    for row in rows:
        normalized_row = [
            normalize_text(str(cell)) for cell in row if normalize_text(str(cell))
        ]
        if not normalized_row:
            continue
        if (
            normalized_row[0] == "挂牌价格"
            and len(normalized_row) >= 2
            and not result["listing_price"]
        ):
            result["listing_price"] = normalize_rural_listing_price(normalized_row[1])
            continue
        if "项目实施主体" in normalized_row[0] and "基本情况" in normalized_row[0]:
            in_entity_section = True
            pair_start = 1
        elif in_entity_section and (
            "流转（需求）标的基本情况" in normalized_row[0]
            or "流转(需求)标的基本情况" in normalized_row[0]
        ):
            break
        elif in_entity_section:
            pair_start = 0
        else:
            continue
        for index in range(pair_start, len(normalized_row) - 1, 2):
            key = normalized_row[index]
            value = normalized_row[index + 1]
            if key == "名称" and not result["entity_name"]:
                result["entity_name"] = value
            elif key == "联系人" and not result["contact_name"]:
                result["contact_name"] = value
            elif key == "联系电话" and not result["contact_phone"]:
                result["contact_phone"] = value
    if not result["listing_price"]:
        result["listing_price"] = extract_rural_listing_price(text)
    return result


def extract_procurement_unit_from_text(text: str) -> str:
    patterns = [
        r"(?:采购人名称|采购人|采购单位)\s*[：:]\s*([^\n]+)",
        r"招\s*标\s*人\s*[：:]\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_procurement_unit(match.group(1).split("法定代表人")[0])
    return ""


def extract_government_procurement_unit(text: str) -> str:
    section_match = re.search(
        r"(?:^|\n)\s*1\s*[\.、]\s*采购人信息\s*(.*?)(?=(?:\n\s*[23]\s*[\.、])|$)",
        text,
        flags=re.S,
    )
    if not section_match:
        return ""
    section_text = section_match.group(1)
    name_match = re.search(r"名\s*称\s*[：:]\s*([^\n]+)", section_text)
    if not name_match:
        return ""
    return clean_procurement_unit(name_match.group(1))


def extract_government_contact_phone(text: str) -> str:
    section_match = re.search(
        r"(?:^|\n)\s*3\s*[\.、]\s*项目联系方式\s*(.*?)(?=(?:\n\s*[45]\s*[\.、])|$)",
        text,
        flags=re.S,
    )
    if section_match:
        section_text = section_match.group(1)
        section_phone_match = re.search(
            r"(?:联\s*系\s*方\s*式|联\s*系\s*电\s*话|电\s*话)\s*[：:]\s*([0-9０-９\-—、/,，；; ]+)",
            section_text,
        )
        if section_phone_match:
            return normalize_text(section_phone_match.group(1))
    return ""


def extract_rural_entity_section_field(text: str, field_name: str) -> str:
    section_match = re.search(
        r"项目实施主体基本情况\s*(.*?)(?=(?:\n\s*[一二三四五六七八九十1234567890]+[、\.])|$)",
        text,
        flags=re.S,
    )
    if not section_match:
        return ""
    section_text = section_match.group(1)
    field_match = re.search(
        rf"{re.escape(field_name)}\s*[：:]\s*([^\n]+)", section_text
    )
    if not field_match:
        return ""
    return normalize_text(field_match.group(1))


def extract_contact_phone(text: str) -> str:
    patterns = [
        r"(?:项\s*目\s*负\s*责\s*人|项\s*目\s*联\s*系\s*人)\s*[：:]\s*[^\s，,；; ]+\s*(?:联\s*系\s*方\s*式|联\s*系\s*电\s*话|电\s*话)\s*[：:]\s*([0-9０-９\-—、/,，；; ]+)",
        r"(?:联\s*系\s*方\s*式|联\s*系\s*电\s*话|电\s*话)\s*[：:]\s*([0-9０-９\-—、/,，；; ]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1))
    return ""


def extract_contact_name(text: str) -> str:
    match = re.search(
        r"(?:项\s*目\s*负\s*责\s*人|项\s*目\s*联\s*系\s*人|联\s*系\s*人)\s*[：:]\s*([^\n，,；; ]+)",
        text,
    )
    return normalize_text(match.group(1)) if match else ""


def extract_government_contact_name(text: str) -> str:
    section_match = re.search(
        r"(?:^|\n)\s*3\s*[\.、]\s*项目联系方式\s*(.*?)(?=(?:\n\s*[45]\s*[\.、])|$)",
        text,
        flags=re.S,
    )
    if not section_match:
        return ""
    section_text = section_match.group(1)
    section_name_match = re.search(
        r"(?:项\s*目\s*联\s*系\s*人|联\s*系\s*人)\s*[：:]\s*([^\n，,；; ]+)",
        section_text,
    )
    if not section_name_match:
        return ""
    return normalize_text(section_name_match.group(1))


def build_consultation_info(
    procurement_unit: str, contact_name: str, contact_phone: str
) -> dict[str, list[str]]:
    purchasing_info: list[str] = []
    project_info: list[str] = []
    if procurement_unit:
        purchasing_info.append(f"名称：{procurement_unit}")
    if contact_name:
        project_info.append(f"项目联系人：{contact_name}")
    if contact_phone:
        project_info.append(f"电话：{contact_phone}")
    return {"purchasingInfor": purchasing_info, "projectInfo": project_info}


def encode_html_content(html: str) -> str:
    return base64.b64encode(html.encode("utf-8")).decode("utf-8")


class BaseModelClient:
    def __init__(self, url: str, timeout: int = 30) -> None:
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Test-Version": "v2",
            "Custom-Token": MODEL_TOKEN,
        }

    def request(self, text: str) -> Any:
        response = self.session.post(
            self.url,
            json={"text": text, "model": MODEL_NAME},
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("final_result", data.get("result"))


class BidModelClient(BaseModelClient):
    def __init__(self, timeout: int = 30) -> None:
        super().__init__("https://www.51qqx.com/extract/ask", timeout=timeout)

    def get_result(self, text: str) -> dict[str, Any]:
        result = self.request(text)
        if not isinstance(result, dict):
            return {}
        consultation_info = {
            "purchasingInfor": [],
            "projectInfor": [],
        }
        purchaser = normalize_text(str(result.get("采购人名称", "")))
        contact_name = normalize_text(str(result.get("项目联系人", ""))).replace(
            "、", ","
        )
        contact_phone = normalize_text(str(result.get("项目联系方式", ""))).replace(
            "、", ","
        )
        if purchaser:
            consultation_info["purchasingInfor"].append(f"名称：{purchaser}")
        if contact_name:
            consultation_info["projectInfor"].append(f"项目联系人：{contact_name}")
        if contact_phone:
            consultation_info["projectInfor"].append(f"电话：{contact_phone}")
        return {
            "projectNum": normalize_text(str(result.get("项目编号", ""))),
            "projectName": normalize_text(str(result.get("项目名称", ""))),
            "budgetAmount": normalize_money(str(result.get("预算金额", ""))),
            "procurementMethod": normalize_procurement_method(
                str(result.get("采购方式", ""))
            ),
            "releaseSource": purchaser,
            "consultationInfo": consultation_info,
        }


def load_model_client(
    enable_model_enrichment: bool, timeout_seconds: int
) -> BidModelClient | None:
    if not enable_model_enrichment:
        return None
    return BidModelClient(timeout=timeout_seconds)


class ZbggzyRuntime:
    def __init__(
        self,
        *,
        module_name: str,
        start_page: int,
        max_pages: int,
        page_size: int,
        timeout_seconds: int,
        detail_delay_seconds: float,
        enable_model_enrichment: bool,
        notice_type_filter: str = "",
    ) -> None:
        self.module_name = module_name
        self.start_page = max(start_page, 1)
        self.max_pages = max_pages
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self.detail_delay_seconds = detail_delay_seconds
        self.enable_model_enrichment = enable_model_enrichment
        self.notice_type_filter = normalize_text(notice_type_filter)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.model_client = load_model_client(enable_model_enrichment, timeout_seconds)
        self.logger = logging.getLogger("zbggzy")

    def create_monitor(self, task: ModuleTask) -> Any:
        if SpiderMonitor is None or build_biz_type is None:
            return None
        biz_type = build_biz_type(task.module_name, task.notice_type)
        return SpiderMonitor(
            province=SITE_CONTEXT["province_name"],
            city=SITE_CONTEXT["city_name"],
            webname=SITE_CONTEXT["web_source"],
            biz_type=biz_type,
            logger=self.logger,
        )

    def safe_print(self, message: str = "") -> None:
        try:
            print(message)
        except UnicodeEncodeError:
            safe_message = message.encode("gbk", errors="replace").decode(
                "gbk", errors="replace"
            )
            print(safe_message)

    def print_record(self, record: dict[str, Any]) -> None:
        payload = json.dumps(record, ensure_ascii=False, indent=2)
        self.safe_print(payload)

    def ensure_token(self) -> None:
        if self.session.headers.get("Authorization"):
            return
        response = self.session.post(
            ANONYMOUS_TOKEN_URL,
            data={"params": "{}"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        token = str(response.json().get("custom", {}).get("access_token", "")).strip()
        if not token:
            raise RuntimeError("获取匿名 access_token 失败")
        self.session.headers["Authorization"] = f"Bearer {token}"

    def fetch_module_page(self, module_path: str) -> str:
        response = self.session.get(
            urljoin(BASE_URL, module_path), timeout=self.timeout_seconds
        )
        response.raise_for_status()
        return response.text

    def discover_module_tasks(self) -> list[ModuleTask]:
        self.ensure_token()
        selected_sources = (
            MODULE_SOURCES.items()
            if self.module_name in {"全部模块", "ALL", "*"}
            else [(self.module_name, MODULE_SOURCES[self.module_name])]
        )
        tasks: list[ModuleTask] = []
        for module_name, source in selected_sources:
            if module_name in EXCLUDED_MODULE_NAMES:
                continue
            html = self.fetch_module_page(source["path"])
            matches: list[tuple[str, str]] = []
            if BeautifulSoup is not None:
                soup = BeautifulSoup(html, "html.parser")
                notice_list = soup.find("ul", id="gglx")
                if notice_list is not None:
                    for item in notice_list.find_all("li"):
                        category_num = normalize_text(str(item.get("data-value", "")))
                        notice_type = normalize_text(item.get_text(" ", strip=True))
                        if category_num and notice_type and category_num != "all":
                            matches.append((category_num, notice_type))
            if not matches:
                matches = [
                    (
                        normalize_text(match.group("category")),
                        normalize_text(match.group("name")),
                    )
                    for match in NOTICE_TYPE_PATTERN.finditer(html)
                ]
            for category_num, notice_type in matches:
                if notice_type in EXCLUDED_NOTICE_TYPES:
                    continue
                if notice_type not in SUPPORTED_BID_NOTICE_TYPES:
                    continue
                if (
                    self.notice_type_filter
                    and normalize_text(notice_type) != self.notice_type_filter
                ):
                    continue
                if category_num and notice_type:
                    tasks.append(
                        ModuleTask(
                            module_name=module_name,
                            parent_type=module_name,
                            category_num=category_num,
                            notice_type=notice_type,
                            module_path=str(source["path"]),
                        )
                    )
        return tasks

    def fetch_list_page(self, category_num: str, page_index: int) -> dict[str, Any]:
        self.ensure_token()
        params = {
            "siteGuid": SITE_GUID,
            "categoryNum": category_num,
            "kw": "",
            "startDate": "",
            "endDate": "",
            "jystauts": "",
            "areacode": "",
            "pageIndex": page_index,
            "pageSize": self.page_size,
        }
        response = self.session.post(
            LIST_API_URL,
            data={
                "params": json.dumps(params, ensure_ascii=False, separators=(",", ":"))
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        infodata = payload.get("custom", {}).get("infodata")
        if not isinstance(infodata, list):
            raise ValueError(f"列表接口返回异常: {payload}")
        return payload

    def fetch_detail_html(self, infourl: str) -> tuple[str, str]:
        detail_url = urljoin(BASE_URL, infourl)
        response = self.session.get(detail_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return detail_url, response.text

    def build_context(
        self,
        task: ModuleTask,
        card: dict[str, Any],
        detail: dict[str, Any],
        detail_html: str,
    ) -> dict[str, Any]:
        field_map = detail["field_map"]
        detail_url = detail["detail_url"]
        cleaned_html = clean_detail_fragment(detail_html)
        html_content = encode_html_content(cleaned_html)
        attachments = _extract_attachment_entries(detail_html, detail_url)
        plain_text = str(detail.get("plain_text", ""))
        table_rows = detail.get("table_rows", [])

        area_name = normalize_text(str(card.get("areacode", "")))
        region_code, region_name = AREA_CODE_MAPPING.get(
            area_name, (SITE_CONTEXT["city_id"], SITE_CONTEXT["city_name"])
        )
        is_government_module = task.module_name == "政府采购"
        is_rural_engineering_trade = (
            task.module_name == "农村工程" and task.notice_type == "交易公告"
        )
        is_rural_procurement_trade = (
            task.module_name == "农村采购" and task.notice_type == "交易公告"
        )
        is_land_transfer_trade = (
            task.module_name == "土地流转" and task.notice_type == "交易公告"
        )
        is_collective_asset_trade = (
            task.module_name == "集体资产" and task.notice_type == "交易公告"
        )
        is_agricultural_facility_trade = (
            task.module_name == "农业设施" and task.notice_type == "交易公告"
        )
        rural_engineering_info = (
            extract_rural_engineering_table_info(table_rows, plain_text)
            if is_rural_engineering_trade
            else {}
        )
        rural_procurement_info = (
            extract_rural_engineering_table_info(table_rows, plain_text)
            if is_rural_procurement_trade
            else {}
        )
        land_transfer_info = (
            extract_rural_engineering_table_info(table_rows, plain_text)
            if is_land_transfer_trade
            else {}
        )
        collective_asset_info = (
            extract_rural_engineering_table_info(table_rows, plain_text)
            if is_collective_asset_trade
            else {}
        )
        agricultural_facility_info = (
            extract_rural_engineering_table_info(table_rows, plain_text)
            if is_agricultural_facility_trade
            else {}
        )

        procurement_unit = clean_procurement_unit(
            pick_first_non_empty(
                [
                    str(agricultural_facility_info.get("entity_name", "")),
                    str(collective_asset_info.get("entity_name", "")),
                    str(land_transfer_info.get("entity_name", "")),
                    str(rural_procurement_info.get("entity_name", "")),
                    str(rural_engineering_info.get("entity_name", "")),
                    extract_government_procurement_unit(plain_text)
                    if is_government_module
                    else "",
                    str(field_map.get("采购人名称", "")),
                    str(field_map.get("采购人", "")),
                    str(field_map.get("采购单位", "")),
                    str(field_map.get("名称", "")),
                    extract_procurement_unit_from_text(plain_text),
                ]
            )
        )
        project_num = pick_first_non_empty(
            [
                str(field_map.get("项目编号", "")),
                str(field_map.get("采购文件编号", "")),
                extract_project_num(plain_text),
            ]
        )
        project_name = pick_first_non_empty(
            [
                str(field_map.get("项目名称", "")),
                str(detail.get("title", "")),
                str(card.get("realtitle", "")),
            ]
        )
        budget_amount = pick_first_non_empty(
            [
                str(agricultural_facility_info.get("listing_price", "")),
                str(collective_asset_info.get("listing_price", "")),
                str(land_transfer_info.get("listing_price", "")),
                extract_rural_expected_total_price(plain_text)
                if is_rural_procurement_trade
                else "",
                str(rural_procurement_info.get("listing_price", "")),
                str(rural_engineering_info.get("listing_price", "")),
                extract_budget_amount(str(field_map.get("预算金额", ""))),
                normalize_money(str(field_map.get("预算金额", ""))),
                extract_budget_amount(plain_text),
            ]
        )
        procurement_method = normalize_procurement_method(
            str(field_map.get("采购方式", ""))
        )
        if not procurement_method:
            procurement_method = extract_procurement_method_from_text(plain_text)
        render_date = pick_first_non_empty(
            [str(card.get("infodate", "")), str(field_map.get("公告期限", ""))]
        )
        contact_name = pick_first_non_empty(
            [
                str(agricultural_facility_info.get("contact_name", "")),
                str(collective_asset_info.get("contact_name", "")),
                str(land_transfer_info.get("contact_name", "")),
                str(rural_procurement_info.get("contact_name", "")),
                str(rural_engineering_info.get("contact_name", "")),
                extract_government_contact_name(plain_text)
                if is_government_module
                else "",
                str(field_map.get("项目联系人", "")),
                extract_contact_name(plain_text),
            ]
        )
        contact_phone = pick_first_non_empty(
            [
                str(agricultural_facility_info.get("contact_phone", "")),
                str(collective_asset_info.get("contact_phone", "")),
                str(land_transfer_info.get("contact_phone", "")),
                str(rural_procurement_info.get("contact_phone", "")),
                str(rural_engineering_info.get("contact_phone", "")),
                extract_government_contact_phone(plain_text)
                if is_government_module
                else "",
                str(field_map.get("联系方式", "")),
                str(field_map.get("电话", "")),
                extract_contact_phone(plain_text),
            ]
        )

        return {
            "task": task,
            "card": card,
            "detail": detail,
            "detail_url": detail_url,
            "field_map": field_map,
            "plain_text": plain_text,
            "cleaned_html": cleaned_html,
            "html_content": html_content,
            "attachments": attachments,
            "region_code": region_code,
            "region_name": region_name,
            "procurement_unit": procurement_unit,
            "project_num": project_num,
            "project_name": project_name,
            "budget_amount": budget_amount,
            "procurement_method": procurement_method,
            "render_date": render_date,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
        }

    def collect_records_for_task(
        self,
        task: ModuleTask,
        build_record: RecordBuilder,
        apply_model_enrichment: RecordEnricher,
    ) -> list[dict[str, Any]]:
        all_records: list[dict[str, Any]] = []
        monitor = self.create_monitor(task)
        current_page = self.start_page - 1
        page_limit = None if self.max_pages == 0 else self.max_pages
        total_pages = None
        while True:
            try:
                payload = self.fetch_list_page(task.category_num, current_page)
            except Exception:
                if monitor is not None:
                    monitor.mark_website_error()
                    monitor.mark_run_failed()
                raise
            custom = payload.get("custom", {})
            cards = custom.get("infodata", [])
            total_count = int(custom.get("count", 0) or 0)
            total_pages = (
                (total_count + self.page_size - 1) // self.page_size
                if total_count
                else 0
            )
            page_no = current_page + 1
            self.safe_print(
                f"[{task.module_name}][{task.notice_type}][第 {page_no} 页 / 共 {total_pages or '未知'} 页] 列表条数: {len(cards)}"
            )
            if not cards:
                break
            if monitor is not None:
                monitor.mark_has_content()
            for index, card in enumerate(cards, start=1):
                try:
                    detail_url, detail_html = self.fetch_detail_html(
                        str(card.get("infourl", ""))
                    )
                    detail = parse_detail(detail_html, detail_url)
                    context = self.build_context(task, card, detail, detail_html)
                    record = build_record(context)
                    record = apply_model_enrichment(self, record, context)
                    all_records.append(record)
                    if monitor is not None:
                        monitor.mark_has_new_data()
                except requests.RequestException:
                    if monitor is not None:
                        monitor.mark_website_error()
                        monitor.mark_invalid_data()
                    raise
                except Exception:
                    if monitor is not None:
                        monitor.mark_invalid_data()
                    raise
                title = pick_first_non_empty(
                    [
                        str(record.get("tenderTitle", "")),
                        str(record.get("announcementTitle", "")),
                        str(record.get("projectName", "")),
                        str(record.get("procurementTitle", "")),
                    ]
                )
                self.safe_print(
                    f"[{task.notice_type}][第 {page_no} 页][第 {index} 条] 标题: {title}"
                )
                self.print_record(record)
                if self.detail_delay_seconds > 0:
                    time.sleep(self.detail_delay_seconds)
            if total_pages and page_no >= total_pages:
                break
            if page_limit is not None and page_no >= self.start_page + page_limit - 1:
                break
            current_page += 1
        if monitor is not None:
            self.safe_print(f"网站标识统计：{monitor.logo_info}")
            monitor.flush()
        return all_records

    def run(
        self, build_record: RecordBuilder, apply_model_enrichment: RecordEnricher
    ) -> list[dict[str, Any]]:
        tasks = self.discover_module_tasks()
        all_records: list[dict[str, Any]] = []
        current_module = ""
        current_count = 0
        for task in tasks:
            if task.module_name != current_module:
                if current_module:
                    self.safe_print(
                        f"一级模块结束: {current_module}，本组记录数: {current_count}"
                    )
                current_module = task.module_name
                current_count = 0
                self.safe_print("")
                self.safe_print(f"========== 一级模块: {current_module} ==========")
            records = self.collect_records_for_task(
                task, build_record, apply_model_enrichment
            )
            current_count += len(records)
            all_records.extend(records)
            self.safe_print(
                f"二级栏目结束: {task.notice_type}，本栏记录数: {len(records)}"
            )
        if current_module:
            self.safe_print(
                f"一级模块结束: {current_module}，本组记录数: {current_count}"
            )
        self.safe_print(f"采集结束，总记录数: {len(all_records)}")
        return all_records


def get_runtime_config() -> dict[str, Any]:
    return {
        "module_name": RUN_CONFIG["module_name"],
        "notice_type": normalize_text(str(RUN_CONFIG["notice_type"])),
        "start_page": int(RUN_CONFIG["start_page"]),
        "max_pages": int(RUN_CONFIG["max_pages"]),
        "page_size": int(RUN_CONFIG["page_size"]),
        "timeout_seconds": int(RUN_CONFIG["timeout_seconds"]),
        "detail_delay_seconds": float(RUN_CONFIG["detail_delay_seconds"]),
        "enable_model_enrichment": bool(RUN_CONFIG["enable_model_enrichment"]),
    }


def run_runtime(
    argv: list[str] | None,
    *,
    build_record: RecordBuilder,
    apply_model_enrichment: RecordEnricher,
) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = get_runtime_config()
    runtime = ZbggzyRuntime(
        module_name=str(config["module_name"]),
        start_page=int(config["start_page"]),
        max_pages=int(config["max_pages"]),
        page_size=int(config["page_size"]),
        timeout_seconds=int(config["timeout_seconds"]),
        detail_delay_seconds=float(config["detail_delay_seconds"]),
        enable_model_enrichment=bool(config["enable_model_enrichment"]),
        notice_type_filter=str(config["notice_type"]),
    )
    try:
        runtime.run(build_record, apply_model_enrichment)
        return 0
    except Exception:
        runtime.logger.exception("运行失败")
        return 1


def build_bid_record(context: dict[str, Any]) -> dict[str, Any]:
    task: ModuleTask = context["task"]
    return {
        "provinceCode": str(SITE_CONTEXT["province_code"]),
        "regionCode": str(context["region_code"]),
        "regionName": str(context["region_name"]),
        "bidType": "",
        "announcementTitle": context["project_name"],
        "originalWebsiteAddress": context["detail_url"],
        "procurementMethod": context["procurement_method"],
        "parentType": task.parent_type,
        "announcementType": task.notice_type,
        "projectNum": context["project_num"],
        "projectName": context["project_name"],
        "budgetAmount": context["budget_amount"],
        "releaseSource": context["procurement_unit"],
        "releaseTime": context["render_date"],
        "consultationInfo": build_consultation_info(
            context["procurement_unit"],
            context["contact_name"],
            context["contact_phone"],
        ),
        "fileInfo": context["attachments"],
        "contentType": 1,
        "htmlContent": context["html_content"],
        "webSource": SITE_CONTEXT["web_source"],
    }


def apply_bid_model_enrichment(
    runtime: ZbggzyRuntime, record: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    client = runtime.model_client
    if client is None:
        return record
    model_input = pick_first_non_empty(
        [context["plain_text"], strip_html_tags(context["cleaned_html"])]
    )
    if not model_input:
        return record
    try:
        model_result = client.get_result(model_input)
    except MODEL_ENRICHMENT_FALLBACK_EXCEPTIONS as exc:
        runtime.logger.warning("招标公告 模型增强失败，回退基础解析: %s", exc)
        return record
    if not isinstance(model_result, dict) or not model_result:
        return record

    project_name = normalize_text(str(model_result.get("projectName", "")))
    if project_name:
        record["projectName"] = project_name
        record["announcementTitle"] = project_name

    project_num = normalize_text(str(model_result.get("projectNum", "")))
    if project_num:
        record["projectNum"] = project_num

    budget_amount = normalize_text(str(model_result.get("budgetAmount", "")))
    if budget_amount:
        record["budgetAmount"] = budget_amount

    release_source = normalize_text(str(model_result.get("releaseSource", "")))
    if release_source:
        record["releaseSource"] = release_source

    consultation_info = model_result.get("consultationInfo", {})
    if isinstance(consultation_info, dict):
        record["consultationInfo"] = {
            "purchasingInfor": consultation_info.get("purchasingInfor", [])
            if isinstance(consultation_info.get("purchasingInfor", []), list)
            else [],
            "projectInfo": consultation_info.get("projectInfor", [])
            if isinstance(consultation_info.get("projectInfor", []), list)
            else [],
        }

    return record


def main(argv: list[str] | None = None) -> int:
    return run_runtime(
        argv,
        build_record=build_bid_record,
        apply_model_enrichment=apply_bid_model_enrichment,
    )


if __name__ == "__main__":
    raise SystemExit(main())
