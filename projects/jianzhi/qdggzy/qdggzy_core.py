from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import logging
import re
import sys
import types
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from monitoring import SpiderMonitor, build_biz_type


BASE_URL = "https://ggzy.qingdao.gov.cn"
HOME_URL = f"{BASE_URL}/PortalQDManage/"
LEFT_NAV_SOURCE_URL = f"{BASE_URL}/Tradeinfo-GGGSList/6-6-12"
LIST_API_URL = f"{BASE_URL}/PortalQDManage/PortalQD/PartialZTBNew"
CONTRACT_LIST_API_URL = f"{BASE_URL}/PortalQDManage/PortalQD/PartialHTZTBNew"
SITE_CONTEXT = {
    "province_code": "370000",
    "province_name": "山东省",
    "city_id": "370200",
    "city_name": "青岛市",
    "web_source": "青岛市公共资源交易电子服务系统",
}
RUN_CONFIG = {
    "module_name": "全部模块",
    "notice_type": "",
    "output_board": "",
    "start_page": 1,
    "max_pages": 1,
    "page_size": 10,
    "timeout_seconds": 20,
    "detail_delay_seconds": 0.0,
}
PARENT_TYPE_MAPPING = {
    "建设工程": "工程建设",
    "政府采购": "政府采购",
    "资源交易": "资源交易",
    "产权交易": "产权交易",
    "国企采购": "国有企业采购",
    "其他项目": "其他项目",
    "无形资产": "无形资产",
    "环境权": "环境权",
}
TAG_PATTERN = re.compile(r"<[^>]+>")
MONEY_PATTERN = re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?)")
EXCLUDED_NOTICE_KEYWORDS = ("发票开具", "支付公开")
STATIC_LIST_MODULES = {"资源交易", "产权交易", "国企采购"}
SUPPORTED_MODEL_BOARDS = {"招标公告", "中标公告", "候选人公告"}
GENERAL_MODEL_DIR = Path(__file__).resolve().parents[1] / "general"
ALLOWED_NOTICE_TYPES_BY_MODULE: dict[str, set[str]] = {
    "建设工程": {"招标公告", "入围投标人公示（评定分离）", "预中标公示", "中标公告", "合同签订公示"},
    "政府采购": {"采购公告", "中标公告", "合同签订公示"},
    "国企采购": {"采购公告", "中标公告"},
    "无形资产": {"招标公告", "预中标公示", "中标公告", "合同签订公示"},
}
LEFT_NAV_TASK_CONFIG: dict[str, tuple[str, str, str]] = {
    "/Tradeinfo-GGGSList/4-4-0": ("矿业权交易", "2", "0"),
    "/Tradeinfo-GGGSList/4-4-2": ("矿业权交易", "2", "2"),
    "/Tradeinfo-GGGSList/4-4-3": ("矿业权交易", "2", "3"),
    "/Tradeinfo-GGGSList/5-5-0": ("综合交易", "5", "0"),
    "/Tradeinfo-GGGSList/5-5-2": ("综合交易", "5", "2"),
    "/Tradeinfo-GGGSList/6-6-12": ("其它交易", "6", "12"),
    "/Tradeinfo-GGGSList/7-7-0": ("国企采购", "7", "0"),
    "/Tradeinfo-GGGSList/7-7-2": ("国企采购", "7", "2"),
    "/Tradeinfo-GGGSList/0-99-0": ("无形资产", "99", "0"),
    "/Tradeinfo-GGGSList/0-99-4": ("无形资产", "99", "4"),
    "/Tradeinfo-GGGSList/0-99-2": ("无形资产", "99", "2"),
    "/Tradeinfo-GGGSList/0-99-3": ("无形资产", "99", "3"),
    "/Tradeinfo-GGGSList/0-99-8": ("无形资产", "99", "8"),
    "/Tradeinfo-GGGSList/0-99-18": ("无形资产", "99", "18"),
}


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


def _parse_chinese_integer(text: str) -> int:
    digit_map = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "壹": 1,
        "二": 2,
        "贰": 2,
        "两": 2,
        "三": 3,
        "叁": 3,
        "四": 4,
        "肆": 4,
        "五": 5,
        "伍": 5,
        "六": 6,
        "陆": 6,
        "七": 7,
        "柒": 7,
        "八": 8,
        "捌": 8,
        "九": 9,
        "玖": 9,
    }
    small_units = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000}
    large_units = {"万": 10000, "萬": 10000, "亿": 100000000, "億": 100000000}

    result = 0
    section = 0
    number = 0
    for char in text:
        if char in digit_map:
            number = digit_map[char]
            continue
        if char in small_units:
            if number == 0:
                number = 1
            section += number * small_units[char]
            number = 0
            continue
        if char in large_units:
            section += number
            result += section * large_units[char]
            section = 0
            number = 0
    return result + section + number


def _parse_chinese_money_value(text: str) -> float:
    normalized = (
        text.replace("人民币", "")
        .replace("圆", "元")
        .replace("整", "")
        .replace("正", "")
        .replace(" ", "")
    )
    integer_part = normalized
    decimal_part = ""
    if "元" in normalized:
        integer_part, decimal_part = normalized.split("元", 1)
    integer_value = float(_parse_chinese_integer(integer_part)) if integer_part else 0.0
    if not decimal_part:
        return integer_value

    digit_map = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "壹": 1,
        "二": 2,
        "贰": 2,
        "两": 2,
        "三": 3,
        "叁": 3,
        "四": 4,
        "肆": 4,
        "五": 5,
        "伍": 5,
        "六": 6,
        "陆": 6,
        "七": 7,
        "柒": 7,
        "八": 8,
        "捌": 8,
        "九": 9,
        "玖": 9,
    }
    jiao_match = re.search(r"([零〇一壹二贰两三叁四肆五伍六陆七柒八捌九玖])角", decimal_part)
    fen_match = re.search(r"([零〇一壹二贰两三叁四肆五伍六陆七柒八捌九玖])分", decimal_part)
    if jiao_match:
        integer_value += digit_map[jiao_match.group(1)] / 10
    if fen_match:
        integer_value += digit_map[fen_match.group(1)] / 100
    return integer_value


def _ensure_cn2an_compat_module() -> None:
    if importlib.util.find_spec("cn2an") is not None:
        return
    if "cn2an" in sys.modules:
        return

    compat_module = types.ModuleType("cn2an")

    def _cn2an(value: str, mode: str = "smart") -> float:
        text = normalize_text(value)
        if not text:
            raise ValueError("empty amount text")
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
            return float(text)
        arabic_unit_match = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)([十百千万亿])元?", text)
        if arabic_unit_match:
            multiplier = {
                "十": 10,
                "百": 100,
                "千": 1000,
                "万": 10000,
                "亿": 100000000,
            }[arabic_unit_match.group(2)]
            return float(arabic_unit_match.group(1)) * multiplier
        return _parse_chinese_money_value(text)

    compat_module.cn2an = _cn2an
    sys.modules["cn2an"] = compat_module


def _load_general_model_classes() -> tuple[Any, Any, Any, Any]:
    _ensure_cn2an_compat_module()
    amount_module = _load_python_module("general_model.AmountConverter", GENERAL_MODEL_DIR / "AmountConverter.py")
    package_module = sys.modules.setdefault("QGZJGG", types.ModuleType("QGZJGG"))
    utils_module = sys.modules.setdefault("QGZJGG.Utils", types.ModuleType("QGZJGG.Utils"))
    package_module.Utils = utils_module
    utils_module.AmountConverter = amount_module
    sys.modules["QGZJGG.Utils.AmountConverter"] = amount_module

    tender_module = _load_python_module("general_model.GetTenderModel", GENERAL_MODEL_DIR / "GetTenderModel.py")
    candidate_module = _load_python_module("general_model.GetCandidateModel", GENERAL_MODEL_DIR / "GetCandidateModel.py")
    bid_module = _load_python_module("general_model.GetBidModel", GENERAL_MODEL_DIR / "GetBidModel.py")

    return (
        getattr(amount_module, "MoneyParser"),
        getattr(tender_module, "TenderModel"),
        getattr(candidate_module, "CandidateModel"),
        getattr(bid_module, "BiddingModel"),
    )


MoneyParser, TenderModel, CandidateModel, BiddingModel = _load_general_model_classes()


@dataclass
class SpiderTask:
    module_name: str
    notice_type: str
    type: str
    flag: str
    page_size: int
    html_id: str
    class_id: str
    list_path: str
    sub_type: str = ""


def normalize_text(value: str) -> str:
    text = unescape(value or "")
    text = text.replace("\u00a0", " ")
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_html_tags(value: str) -> str:
    return normalize_text(TAG_PATTERN.sub("", value))


def decode_maybe_numeric_html(html: str) -> str:
    lines = [line.strip() for line in (html or "").splitlines() if line.strip()]
    if not lines:
        return html or ""
    numeric_prefix: list[int] = []
    for line in lines:
        if line.isdigit():
            number = int(line)
            if 0 <= number <= 255:
                numeric_prefix.append(number)
                continue
        break
    if len(numeric_prefix) < 50:
        return html
    try:
        return bytes(numeric_prefix).decode("utf-8-sig", errors="ignore")
    except Exception:
        return html


def resolve_output_board(notice_name: str) -> str:
    name = normalize_text(notice_name)
    if not name:
        return "招标公告"
    if "需求" in name or "意向" in name or "计划" in name:
        return "采购意向"
    if any(keyword in name for keyword in ("候选人", "预中标", "入围投标人")):
        return "候选人公告"
    if any(keyword in name for keyword in ("中标", "合同", "废标", "成交")):
        return "中标公告"
    return "招标公告"


def extract_homepage_tasks(html: str) -> list[dict[str, str]]:
    if BeautifulSoup is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    module_name_by_target: dict[str, str] = {}
    for node in soup.select("li.public-upper-name[data-target]"):
        target = normalize_text(node.get("data-target", ""))
        name = normalize_text(node.get_text(" ", strip=True))
        if target and name:
            module_name_by_target[target] = name

    tasks: list[dict[str, str]] = []
    for module_box in soup.select("div.tabview[data-target]"):
        module_target = normalize_text(module_box.get("data-target", ""))
        module_name = module_name_by_target.get(module_target, "")
        notice_name_by_target: dict[str, str] = {}
        for node in module_box.select("div.tab-two li[data-target]"):
            target = normalize_text(node.get("data-target", ""))
            name = normalize_text(node.get_text(" ", strip=True))
            if target and name:
                notice_name_by_target[target] = name

        for node in module_box.select("div.notice-title[data-target][data-type][data-flag]"):
            target = normalize_text(node.get("data-target", ""))
            link = node.find("a", href=True)
            task = {
                "module_name": module_name,
                "notice_type": notice_name_by_target.get(target, ""),
                "target": target,
                "type": normalize_text(node.get("data-type", "")),
                "flag": normalize_text(node.get("data-flag", "")),
                "page_size": normalize_text(node.get("data-pagesize", "")),
                "html_id": normalize_text(node.get("data-htmlid", "")),
                "class_id": normalize_text(node.get("data-classid", "")),
                "list_path": link.get("href", "") if link else "",
                "sub_type": "",
            }
            if task["module_name"] and task["notice_type"]:
                tasks.append(task)
    return tasks


def extract_left_nav_tasks(html: str) -> list[dict[str, str]]:
    if BeautifulSoup is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    tasks: list[dict[str, str]] = []
    for title_node in soup.select("div.vtitle"):
        group_name = normalize_text(title_node.get_text(" ", strip=True))
        nav_box = title_node.find_next_sibling("div")
        if nav_box is None:
            continue
        for link in nav_box.select("a[href]"):
            href = normalize_text(link.get("href", ""))
            notice_type = normalize_text(link.get_text(" ", strip=True))
            config = LEFT_NAV_TASK_CONFIG.get(href)
            if config is None or not notice_type:
                continue
            module_name, task_type, task_flag = config
            if group_name and group_name not in (module_name, "工程建设"):
                continue
            tasks.append(
                {
                    "module_name": module_name,
                    "notice_type": notice_type,
                    "target": "",
                    "type": task_type,
                    "flag": task_flag,
                    "page_size": "10",
                    "html_id": normalize_text(link.get("id", "")),
                    "class_id": "",
                    "list_path": href,
                    "sub_type": "",
                }
            )
    return tasks


def extract_main_detail_html(html: str) -> str:
    if BeautifulSoup is None:
        return html
    soup = BeautifulSoup(html, "html.parser")
    main_node = soup.find(id="htmlTable")
    if main_node is None:
        title_node = soup.select_one("div.WordSection1") or soup.select_one("body")
        return str(title_node) if title_node is not None else html
    return str(main_node)


def extract_attachment_entries(html: str, detail_url: str) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    if BeautifulSoup is None:
        return attachments
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.find_all("a", href=True):
        href = normalize_text(node.get("href", ""))
        if not href or "GetZbDownLoad" not in href:
            continue
        text = normalize_text(node.get("title", "") or node.get_text(" ", strip=True))
        file_type = ""
        suffix_match = re.search(r"\.([A-Za-z0-9]+)$", text)
        if suffix_match:
            file_type = suffix_match.group(1).lower()
        attachments.append(
            {
                "fileUrl": urljoin(detail_url, href),
                "fileType": file_type,
                "fileName": text,
            }
        )
    deduplicated: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in attachments:
        if item["fileUrl"] in seen:
            continue
        seen.add(item["fileUrl"])
        deduplicated.append(item)
    return deduplicated


def clean_html_content(html: str) -> str:
    cleaned = html or ""
    cleaned = re.sub(
        r"<a\b[^>]*href=['\"][^'\"]*GetZbDownLoad[^'\"]*['\"][^>]*>.*?</a>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    return cleaned.strip()


def is_guoqi_shell_detail_html(html: str) -> bool:
    text = html or ""
    if "交易信息详情" not in text:
        return False
    content_markers = ("divMainContent", "big_title", "table-box", "box-content", "item-title")
    return not any(marker in text for marker in content_markers)


def normalize_money(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    if MoneyParser is not None:
        try:
            return normalize_text(str(MoneyParser().convert_amount(text)))
        except Exception:
            pass
    text = text.replace(",", "")
    match = MONEY_PATTERN.search(text)
    return f"{match.group(1)}元" if match else ""


def extract_title_from_detail(main_html: str, full_html: str) -> str:
    if BeautifulSoup is None:
        return ""
    for html in (main_html, full_html):
        soup = BeautifulSoup(html, "html.parser")
        title_node = soup.select_one(".title_p span") or soup.select_one(".title_p") or soup.select_one(".tle")
        if title_node is not None:
            return normalize_text(title_node.get_text(" ", strip=True))
        title_node = soup.find(["h1", "h2"])
        if title_node is not None:
            return normalize_text(title_node.get_text(" ", strip=True))
        if soup.title is not None:
            title_text = normalize_text(soup.title.get_text(" ", strip=True))
            if "-" in title_text:
                title_text = title_text.split("-", 1)[-1]
            return title_text
        item_title_node = soup.select_one(".box-item .item-title")
        if item_title_node is not None:
            label = normalize_text(item_title_node.get_text(" ", strip=True)).rstrip("：:")
            if label in {"项目名称", "标段名称"}:
                value_node = item_title_node.find_next(class_="item-msg")
                if value_node is not None:
                    value_text = normalize_text(value_node.get_text(" ", strip=True))
                    if value_text:
                        return value_text
    return ""


def parse_detail_field_map(main_html: str) -> dict[str, str]:
    field_map: dict[str, str] = {}
    if BeautifulSoup is None:
        return field_map
    soup = BeautifulSoup(main_html, "html.parser")

    pending_label = ""
    for row in soup.select("p.details_p"):
        labels = [normalize_text(node.get_text(" ", strip=True)).rstrip("：:") for node in row.select(".l_span")]
        values = [normalize_text(node.get_text(" ", strip=True)) for node in row.select(".r_span")]
        if pending_label and values and not labels:
            value = normalize_text(" ".join(values))
            if value and pending_label not in field_map:
                field_map[pending_label] = value
            pending_label = ""
            continue
        if labels and values:
            for index, label in enumerate(labels):
                value = values[index] if index < len(values) else values[-1]
                if label and value and label not in field_map:
                    field_map[label] = value
            pending_label = ""
            continue
        if labels and not values:
            pending_label = labels[-1]
            continue
        spans = row.find_all("span")
        if len(spans) >= 2:
            label = normalize_text(spans[0].get_text(" ", strip=True)).rstrip("：:")
            value = normalize_text(" ".join(node.get_text(" ", strip=True) for node in spans[1:]))
            if label and value and label not in field_map:
                field_map[label] = value
        pending_label = ""

    for row in soup.find_all("tr"):
        cells = [normalize_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
        if len(cells) >= 2 and len(cells) % 2 == 0:
            for index in range(0, len(cells), 2):
                key = cells[index].rstrip("：:")
                value = cells[index + 1]
                if key and value and key not in field_map:
                    field_map[key] = value
    for item in soup.select(".box-item"):
        key_node = item.select_one(".item-title, .item-titles")
        value_nodes = item.select(".item-msg, .item-msgs")
        key = normalize_text(key_node.get_text(" ", strip=True)).rstrip("：:") if key_node is not None else ""
        value = normalize_text(" ".join(node.get_text(" ", strip=True) for node in value_nodes))
        if key and value and key not in field_map:
            field_map[key] = value
    return field_map


def parse_detail(html: str, detail_url: str) -> dict[str, Any]:
    decoded_html = decode_maybe_numeric_html(html)
    main_html = extract_main_detail_html(decoded_html)
    plain_text = strip_html_tags(clean_html_content(main_html))
    field_map = parse_detail_field_map(main_html)
    attachments = extract_attachment_entries(decoded_html, detail_url)
    title = extract_title_from_detail(main_html, decoded_html)
    project_name = pick_first_non_empty(
        [
            str(field_map.get("采购项目名称", "")),
            str(field_map.get("项目名称", "")),
            str(field_map.get("标段名称", "")),
        ]
    )
    if project_name and title.endswith("公告") and project_name in title:
        title = title[title.index(project_name) :]
    return {
        "detail_url": detail_url,
        "title": title,
        "main_html": main_html,
        "plain_text": plain_text,
        "field_map": field_map,
        "attachments": attachments,
    }


def extract_region_and_method(text: str) -> tuple[str, str]:
    match = re.search(r"\[(?P<region>[^\[\]]+)\]\[(?P<method>[^\[\]]+)\]", text)
    if not match:
        return "", ""
    return normalize_text(match.group("region")), normalize_text(match.group("method"))


def extract_list_records(html: str, list_url: str) -> list[dict[str, str]]:
    decoded_html = decode_maybe_numeric_html(html)
    if BeautifulSoup is None:
        return []
    soup = BeautifulSoup(decoded_html, "html.parser")
    records: list[dict[str, str]] = []
    for anchor in soup.select(
        'a[href*="TradeDetals-ZtbShow"], '
        'a[href*="/PortalQDManage/PortalQD/ZtbShowGY/"], '
        'a[href*="/Contact-HTGS/"]'
    ):
        title = normalize_text(anchor.get("title", "")) or normalize_text(anchor.get_text(" ", strip=True))
        card_text = normalize_text(anchor.get_text(" ", strip=True))
        region, trade_method = extract_region_and_method(card_text)
        if not title:
            continue
        date_text = ""
        tr = anchor.find_parent("tr")
        if tr is not None:
            row_text = normalize_text(tr.get_text(" ", strip=True))
            date_match = re.search(r"(\d{4}[/-]\d{2}[/-]\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)", row_text)
            if date_match:
                date_text = date_match.group(1)
        records.append(
            {
                "title": title,
                "detail_url": urljoin(list_url, anchor.get("href", "")),
                "region": region,
                "trade_method": trade_method,
                "publish_time": date_text,
            }
        )
    deduplicated: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        if record["detail_url"] in seen:
            continue
        seen.add(record["detail_url"])
        deduplicated.append(record)
    return deduplicated


def extract_dynamic_list_records(payload: dict[str, Any]) -> list[dict[str, str]]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return []
    root_class_id = normalize_text(str(data.get("classId", "")))
    root_type = int(data.get("type", 0) or 0)
    root_flag = int(data.get("flag", 0) or 0)
    root_zbflag = int(data.get("zbflag", 0) or 0)
    items = data.get("Ggglist", [])
    if not isinstance(items, list):
        return []

    records: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record_id = item.get("ID")
        keyguid = normalize_text(str(item.get("keyguid", "")))
        if record_id in (None, ""):
            continue
        if root_type == 7:
            detail_url = f"{BASE_URL}/PortalQDManage/PortalQD/ZtbShowGY/{record_id}?flag={root_flag}"
        else:
            if not root_class_id or not keyguid:
                continue
            detail_url = (
                f"{BASE_URL}/TradeDetals-ZtbShow/"
                f"{record_id}-{root_class_id}-{root_type}-{root_flag}-{root_zbflag}/"
                f"{keyguid}"
            )
        title = pick_first_non_empty(
            [
                str(item.get("ProjectName", "")),
                str(item.get("ProName", "")),
                str(item.get("BidName", "")),
                str(item.get("ContractName", "")),
            ]
        )
        if not title:
            continue
        records.append(
            {
                "title": title,
                "detail_url": detail_url,
                "region": normalize_text(str(item.get("AreaName", ""))),
                "trade_method": normalize_text(str(item.get("ZBflagName", ""))),
                "publish_time": normalize_text(str(item.get("Dates", ""))),
            }
        )
    return records


def build_static_list_page_url(task: dict[str, str] | SpiderTask, page_no: int) -> str:
    list_path = task["list_path"] if isinstance(task, dict) else task.list_path
    absolute_url = urljoin(BASE_URL, list_path)
    if page_no <= 1:
        return absolute_url

    split_result = urlsplit(absolute_url)
    query_items = dict(parse_qsl(split_result.query, keep_blank_values=True))
    query_items["pageIndex"] = str(page_no)
    return urlunsplit(
        (
            split_result.scheme,
            split_result.netloc,
            split_result.path,
            urlencode(query_items),
            split_result.fragment,
        )
    )


def append_query_params_to_list_path(list_path: str, **params: str) -> str:
    split_result = urlsplit(list_path)
    query_items = dict(parse_qsl(split_result.query, keep_blank_values=True))
    for key, value in params.items():
        text = normalize_text(value)
        if text:
            query_items[key] = text
    return urlunsplit(
        (
            split_result.scheme,
            split_result.netloc,
            split_result.path,
            urlencode(query_items),
            split_result.fragment,
        )
    )


def expand_contract_secondary_tasks(task: SpiderTask, html: str) -> list[dict[str, str]]:
    if BeautifulSoup is None:
        return []
    if task.notice_type != "合同签订公示":
        return []

    if task.module_name == "建设工程":
        select_id = "slClassId"
        query_key = "ClassId"
    elif task.module_name == "政府采购":
        select_id = "ZCzbflag"
        query_key = "ZBFlag"
    else:
        return []

    soup = BeautifulSoup(decode_maybe_numeric_html(html), "html.parser")
    select_node = soup.select_one(f"select#{select_id}")
    if select_node is None:
        return []

    expanded_tasks: list[dict[str, str]] = []
    for option in select_node.select("option"):
        value = normalize_text(option.get("value", ""))
        sub_type = normalize_text(option.get_text(" ", strip=True))
        if not value or not sub_type or sub_type == "不限":
            continue
        expanded_tasks.append(
            {
                "module_name": task.module_name,
                "notice_type": task.notice_type,
                "type": task.type,
                "flag": task.flag,
                "page_size": str(task.page_size),
                "html_id": task.html_id,
                "class_id": task.class_id,
                "list_path": append_query_params_to_list_path(task.list_path, **{query_key: value}),
                "sub_type": sub_type,
            }
        )
    return expanded_tasks


def pick_first_non_empty(values: list[str]) -> str:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return ""


def normalize_candidate_sort_items(value: Any) -> list[Any]:
    if isinstance(value, list):
        normalized_items: list[Any] = []
        for item in value:
            if isinstance(item, dict):
                normalized_items.append(
                    {
                        key: item_value
                        for key, item_value in item.items()
                        if key not in {"包号", "候选人名称"}
                    }
                )
            else:
                normalized_items.append(item)
        return normalized_items
    if value in ("", None):
        return []
    return [value]


def extract_budget_amount(detail: dict[str, Any]) -> str:
    field_map = detail["field_map"]
    return normalize_money(
        pick_first_non_empty(
            [
                str(field_map.get("预算金额与最高限价", "")),
                str(field_map.get("预算金额", "")),
                str(field_map.get("最高投标限价(元)", "")),
                str(field_map.get("工程造价", "")),
            ]
        )
    )


def normalize_consultation_info(consultation: Any) -> dict[str, list[str]]:
    if not isinstance(consultation, dict):
        consultation = {}
    purchasing_info = consultation.get("purchasingInfor", [])
    if not isinstance(purchasing_info, list):
        purchasing_info = []
    project_info = consultation.get("projectInfor", [])
    if not isinstance(project_info, list):
        project_info = []
    return {
        "purchasingInfor": [normalize_text(str(item)) for item in purchasing_info if normalize_text(str(item))],
        "projectInfor": [normalize_text(str(item)) for item in project_info if normalize_text(str(item))],
    }


def encode_html_content(html: str) -> str:
    return base64.b64encode(clean_html_content(html).encode("utf-8")).decode("utf-8")


def get_parent_type(module_name: str) -> str:
    return PARENT_TYPE_MAPPING.get(module_name, module_name)


def build_model_input(detail: dict[str, Any]) -> str:
    return pick_first_non_empty(
        [
            str(detail.get("plain_text", "")),
            strip_html_tags(str(detail.get("main_html", ""))),
        ]
    )


def load_model_clients(timeout_seconds: int) -> dict[str, Any]:
    return {
        "招标公告": BiddingModel(timeout=timeout_seconds),
        "中标公告": TenderModel(timeout=timeout_seconds),
        "候选人公告": CandidateModel(timeout=max(timeout_seconds, 60)),
    }


def build_bid_record(task: dict[str, str], card: dict[str, str], detail: dict[str, Any], model_result: dict[str, Any]) -> dict[str, Any]:
    parent_type = get_parent_type(task["module_name"])
    attachments = detail["attachments"]
    html_content = encode_html_content(detail["main_html"])
    project_name = normalize_text(str(model_result.get("projectName", "")))
    project_num = normalize_text(str(model_result.get("projectNum", "")))
    budget_amount = normalize_text(str(model_result.get("budgetAmount", "")))
    release_source = normalize_text(str(model_result.get("releaseSource", "")))
    procurement_method = normalize_text(str(model_result.get("procurementMethod", "")))
    purchaser_address = normalize_text(str(model_result.get("purchaserAddress", "")))
    consultation = normalize_consultation_info(model_result.get("consultationInfo", {}))

    return {
        "provinceCode": SITE_CONTEXT["province_code"],
        "regionCode": SITE_CONTEXT["city_id"],
        "regionName": SITE_CONTEXT["city_name"],
        "bidType": "",
        "announcementTitle": project_name,
        "originalWebsiteAddress": detail["detail_url"],
        "procurementMethod": procurement_method,
        "parentType": parent_type,
        "announcementType": task["notice_type"],
        "projectNum": project_num,
        "projectName": project_name,
        "budgetAmount": budget_amount,
        "releaseSource": release_source,
        "purchaserAddress": purchaser_address,
        "releaseTime": normalize_text(card.get("publish_time", "")),
        "consultationInfo": consultation,
        "fileInfo": attachments,
        "contentType": 1,
        "htmlContent": html_content,
        "webSource": SITE_CONTEXT["web_source"],
    }


def build_intention_record(task: dict[str, str], detail: dict[str, Any]) -> dict[str, Any]:
    field_map = detail["field_map"]
    project_name = pick_first_non_empty(
        [
            str(field_map.get("采购项目名称", "")),
            str(field_map.get("项目名称", "")),
            detail["title"].replace("需求公示", "").replace("采购意向", "").strip(),
        ]
    )
    procurement_unit = pick_first_non_empty(
        [
            str(field_map.get("联系人（采购人）", "")),
            str(field_map.get("采购人", "")),
            str(field_map.get("采购单位", "")),
            str(field_map.get("建设单位", "")),
            str(field_map.get("招标单位", "")),
        ]
    )
    render_date = pick_first_non_empty(
        [
            str(field_map.get("发布时间", "")),
            str(field_map.get("公告发布日期", "")),
        ]
    )
    return {
        "provinceCode": SITE_CONTEXT["province_code"],
        "cityId": SITE_CONTEXT["city_id"],
        "cityName": SITE_CONTEXT["city_name"],
        "procurementTitle": project_name,
        "releaseSource": procurement_unit,
        "releaseDatetime": render_date,
        "releaseContentMix": {
            "html": clean_html_content(detail["main_html"]),
            "text": detail["plain_text"],
        },
        "fileInfo": detail["attachments"],
        "originalWebsiteAddress": detail["detail_url"],
        "extra": {},
        "parentType": get_parent_type(task["module_name"]),
        "bidType": task["notice_type"],
        "webSource": SITE_CONTEXT["web_source"],
    }


def build_candidate_records(
    task: dict[str, str],
    card: dict[str, str],
    detail: dict[str, Any],
    model_result: dict[str, Any],
) -> list[dict[str, Any]]:
    parent_type = get_parent_type(task["module_name"])
    attachments = detail["attachments"]
    html_content = encode_html_content(detail["main_html"])
    extra = model_result.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    result_items = model_result.get("result", [])
    first_item = result_items[0] if isinstance(result_items, list) and result_items else {}
    if not isinstance(first_item, dict):
        first_item = {}
    candidate_sort = normalize_candidate_sort_items(first_item.get("candidateSort", []))
    normalized_extra: dict[str, Any] = {}
    if candidate_sort:
        normalized_extra["candidateSort"] = candidate_sort
    tender_number = normalize_text(str(extra.get("tenderNumber", "")))
    if tender_number:
        normalized_extra["tenderNumber"] = tender_number

    return [
        {
            "tenderTitle": normalize_text(str(model_result.get("tenderTitle", ""))),
            "renderDate": normalize_text(card.get("publish_time", "")),
            "renderType": "中标候选人",
            "procurementUnit": normalize_text(str(model_result.get("procurementUnit", ""))),
            "relationCompanyName": normalize_text(str(first_item.get("relationCompanyName", ""))),
            "uploadFileUrl": attachments,
            "provinceCode": SITE_CONTEXT["province_code"],
            "provinceName": SITE_CONTEXT["province_name"],
            "cityId": SITE_CONTEXT["city_id"],
            "cityName": SITE_CONTEXT["city_name"],
            "announcementType": "候选人公告",
            "originalWebsiteAddress": detail["detail_url"],
            "htmlContent": html_content,
            "contentType": 1,
            "parentType": parent_type,
            "extra": normalized_extra,
            "webSource": SITE_CONTEXT["web_source"],
        }
    ]


def build_win_records(
    task: dict[str, str],
    card: dict[str, str],
    detail: dict[str, Any],
    model_result: dict[str, Any],
) -> list[dict[str, Any]]:
    parent_type = get_parent_type(task["module_name"])
    attachments = detail["attachments"]
    attachment_urls = [item["fileUrl"] for item in attachments]
    html_content = encode_html_content(detail["main_html"])
    result_items = model_result.get("result", [])
    first_item = result_items[0] if isinstance(result_items, list) and result_items else {}
    if not isinstance(first_item, dict):
        first_item = {}
    relation_company_name = normalize_text(str(first_item.get("relationCompanyName", "")))
    render_money = normalize_text(str(first_item.get("renderMoney", "")))
    contact_name = normalize_text(str(first_item.get("contactName", "")))
    contact_phone = normalize_text(str(first_item.get("contactTelephone", "")))

    return [
        {
            "tenderTitle": normalize_text(str(model_result.get("tenderTitle", ""))),
            "tenderNumber": normalize_text(str(model_result.get("tenderNumber", ""))),
            "cityId": SITE_CONTEXT["city_id"],
            "cityName": SITE_CONTEXT["city_name"],
            "renderMoney": render_money,
            "renderDate": normalize_text(card.get("publish_time", "")),
            "renderType": "",
            "procurementUnit": normalize_text(str(model_result.get("procurementUnit", ""))),
            "relationCompanyName": relation_company_name,
            "uploadFileUrl": attachment_urls,
            "provinceCode": SITE_CONTEXT["province_code"],
            "announcementType": 2,
            "originalWebsiteAddress": detail["detail_url"],
            "projectClassification": "[5]",
            "tenderAdditionalInfoStr": "",
            "htmlContent": html_content,
            "contentType": 1,
            "isUnion": 1 if "," in relation_company_name else 0,
            "contactName": contact_name,
            "contactTelephone": contact_phone,
            "parentType": parent_type,
        }
    ]


def build_records(
    task: dict[str, str],
    card: dict[str, str],
        detail: dict[str, Any],
        model_clients: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    board = resolve_output_board(task["notice_type"])
    if board == "采购意向":
        return [build_intention_record(task, detail)]
    if board not in SUPPORTED_MODEL_BOARDS:
        return []

    client = (model_clients or {}).get(board)
    if client is None:
        return []

    model_input = build_model_input(detail)
    if not model_input:
        return []

    try:
        model_result = client.get_result(model_input)
    except Exception:
        model_result = {}

    if not isinstance(model_result, dict):
        model_result = {}

    if board == "招标公告":
        return [build_bid_record(task, card, detail, model_result)]
    if board == "候选人公告":
        return build_candidate_records(task, card, detail, model_result)
    return build_win_records(task, card, detail, model_result)


def build_record(
    task: dict[str, str],
    card: dict[str, str],
    detail: dict[str, Any],
    model_clients: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = build_records(task, card, detail, model_clients=model_clients)
    return records[0] if records else {}


def task_from_dict(value: dict[str, str]) -> SpiderTask:
    return SpiderTask(
        module_name=value["module_name"],
        notice_type=value["notice_type"],
        type=value["type"],
        flag=value["flag"],
        page_size=int(value["page_size"] or 10),
        html_id=value["html_id"],
        class_id=value["class_id"],
        list_path=value["list_path"],
        sub_type=normalize_text(value.get("sub_type", "")),
    )


class QdggzySpider:
    def __init__(
        self,
        module_name: str | None = None,
        notice_type_filter: str | None = None,
        output_board_filter: str | None = None,
        start_page: int = 1,
        max_pages: int = 1,
        page_size: int = 10,
        timeout_seconds: int = 20,
        detail_delay_seconds: float = 0.0,
    ) -> None:
        self.module_name = module_name
        self.notice_type_filter = normalize_text(notice_type_filter or "")
        self.output_board_filter = normalize_text(output_board_filter or "")
        self.start_page = start_page
        self.max_pages = max_pages
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self.detail_delay_seconds = detail_delay_seconds
        self._session_ready = False
        self.session = requests.Session()
        self.logger = logging.getLogger("qdggzy")
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            }
        )
        self.model_clients = load_model_clients(timeout_seconds)

    def create_monitor(self, task: SpiderTask) -> Any:
        if SpiderMonitor is None or build_biz_type is None:
            return None
        biz_type = build_biz_type(task.module_name, task.notice_type, getattr(task, "sub_type", ""))
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
            safe_message = message.encode("gbk", errors="replace").decode("gbk", errors="replace")
            print(safe_message)

    def print_record(self, record: dict[str, Any]) -> None:
        self.safe_print(json.dumps(record, ensure_ascii=False, indent=2))

    def ensure_session_ready(self) -> None:
        if self._session_ready:
            return
        response = self.session.get(HOME_URL, timeout=self.timeout_seconds)
        response.raise_for_status()
        self._session_ready = True

    def filter_tasks(self, tasks: list[dict[str, str]] | list[SpiderTask]) -> list[SpiderTask]:
        filtered: list[SpiderTask] = []
        for task in tasks:
            task_obj = task if isinstance(task, SpiderTask) else task_from_dict(task)
            if self.module_name and task_obj.module_name != self.module_name:
                continue
            if any(keyword in task_obj.notice_type for keyword in EXCLUDED_NOTICE_KEYWORDS):
                continue
            if task_obj.module_name not in PARENT_TYPE_MAPPING:
                continue
            allowed_notice_types = ALLOWED_NOTICE_TYPES_BY_MODULE.get(task_obj.module_name)
            if not allowed_notice_types:
                continue
            if task_obj.notice_type not in allowed_notice_types:
                continue
            if self.notice_type_filter and normalize_text(task_obj.notice_type) != self.notice_type_filter:
                continue
            if self.output_board_filter and resolve_output_board(task_obj.notice_type) != self.output_board_filter:
                continue
            filtered.append(task_obj)
        return filtered

    def fetch_homepage_tasks(self) -> list[SpiderTask]:
        self.ensure_session_ready()
        response = self.session.get(HOME_URL, timeout=self.timeout_seconds)
        response.raise_for_status()
        homepage_tasks = extract_homepage_tasks(response.text)
        left_nav_tasks: list[dict[str, str]] = []
        try:
            left_nav_response = self.session.get(LEFT_NAV_SOURCE_URL, timeout=self.timeout_seconds)
            left_nav_response.raise_for_status()
            left_nav_tasks = extract_left_nav_tasks(left_nav_response.text)
        except Exception:
            left_nav_tasks = extract_left_nav_tasks(response.text)
        tasks_by_path: dict[str, dict[str, str]] = {}
        for task in homepage_tasks + left_nav_tasks:
            list_path = normalize_text(task.get("list_path", ""))
            key = list_path or f"{task.get('module_name','')}|{task.get('notice_type','')}|{task.get('type','')}|{task.get('flag','')}"
            if key not in tasks_by_path:
                tasks_by_path[key] = task
                continue
            current_task = tasks_by_path[key]
            current_notice = normalize_text(current_task.get("notice_type", ""))
            new_notice = normalize_text(task.get("notice_type", ""))
            current_module = normalize_text(current_task.get("module_name", ""))
            new_module = normalize_text(task.get("module_name", ""))
            if " " in current_notice and new_notice and new_notice in current_notice:
                tasks_by_path[key] = task
                continue
            if current_notice == current_module and new_notice:
                tasks_by_path[key] = task
                continue
            if current_notice == "国企采购" and new_module == "国企采购" and new_notice:
                tasks_by_path[key] = task
                continue
            if "合同签订公示" in new_notice and "中标公告" in current_notice:
                continue
        base_tasks = self.filter_tasks(list(tasks_by_path.values()))
        expanded_tasks: list[SpiderTask] = []
        for task in base_tasks:
            if task.notice_type == "合同签订公示" and task.module_name == "建设工程":
                try:
                    list_html = self.fetch_list_page(task, 1)
                    secondary_tasks = self.filter_tasks(expand_contract_secondary_tasks(task, list_html))
                except Exception:
                    secondary_tasks = []
                if secondary_tasks:
                    expanded_tasks.extend(secondary_tasks)
                    continue
            expanded_tasks.append(task)
        return expanded_tasks

    def fetch_list_page(self, task: SpiderTask, page_no: int) -> str:
        self.ensure_session_ready()
        if task.module_name in STATIC_LIST_MODULES or task.notice_type == "合同签订公示":
            response = self.session.get(build_static_list_page_url(task, page_no), timeout=self.timeout_seconds)
            response.raise_for_status()
            return response.text
        api_url = CONTRACT_LIST_API_URL if "合同" in task.notice_type else LIST_API_URL
        payload = {
            "type": task.type,
            "flag": task.flag,
            "page": str(page_no),
            "pageSize": str(self.page_size or task.page_size or 10),
        }
        response = self.session.post(api_url, data=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.text

    def fetch_detail(self, detail_url: str) -> dict[str, Any]:
        self.ensure_session_ready()
        if "/PortalQDManage/PortalQD/ZtbShowGY/" not in detail_url:
            response = self.session.get(detail_url, timeout=self.timeout_seconds)
            response.raise_for_status()
            return parse_detail(response.text, detail_url)

        headers = {"Referer": HOME_URL}
        last_html = ""
        last_error: Exception | None = None
        for _ in range(6):
            try:
                response = self.session.get(detail_url, headers=headers, timeout=self.timeout_seconds)
                response.raise_for_status()
            except requests.RequestException as exc:
                last_error = exc
                continue
            last_html = response.text
            if not is_guoqi_shell_detail_html(last_html):
                return parse_detail(last_html, detail_url)
        if last_html and is_guoqi_shell_detail_html(last_html):
            raise RuntimeError(f"国企采购详情连续命中壳页: {detail_url}")
        if last_error is not None:
            raise RuntimeError(f"国企采购详情连续请求失败: {detail_url}") from last_error
        return parse_detail(last_html, detail_url)

    def run(self) -> list[dict[str, Any]]:
        all_records: list[dict[str, Any]] = []
        tasks = self.fetch_homepage_tasks()
        for task in tasks:
            monitor = self.create_monitor(task)
            header = f"========== 一级模块: {task.module_name}"
            if getattr(task, "sub_type", ""):
                header += f" / 二级类型: {task.sub_type}"
            header += f" / {task.notice_type} =========="
            self.safe_print(header)
            for page_no in range(self.start_page, self.start_page + self.max_pages):
                try:
                    html = self.fetch_list_page(task, page_no)
                    if task.module_name in STATIC_LIST_MODULES or task.notice_type == "合同签订公示":
                        cards = extract_list_records(html, urljoin(BASE_URL, task.list_path))
                    else:
                        try:
                            cards = extract_dynamic_list_records(json.loads(html))
                        except Exception:
                            cards = []
                except Exception:
                    if monitor is not None:
                        monitor.mark_website_error()
                        monitor.mark_run_failed()
                    raise
                self.safe_print(f"[{task.notice_type}][第 {page_no} 页] 列表条数: {len(cards)}")
                if cards and monitor is not None:
                    monitor.mark_has_content()
                for index, card in enumerate(cards, start=1):
                    try:
                        detail = self.fetch_detail(card["detail_url"])
                        records = build_records(
                            {
                                "module_name": task.module_name,
                                "notice_type": task.notice_type,
                            },
                            card,
                            detail,
                            model_clients=self.model_clients,
                        )
                    except requests.RequestException:
                        if monitor is not None:
                            monitor.mark_website_error()
                            monitor.mark_invalid_data()
                        raise
                    except Exception:
                        if monitor is not None:
                            monitor.mark_invalid_data()
                        raise
                    if records and monitor is not None:
                        monitor.mark_has_new_data()
                    for expanded_index, record in enumerate(records, start=1):
                        title = record.get("projectName") or record.get("tenderTitle") or record.get("procurementTitle")
                        suffix = f"-{expanded_index}" if len(records) > 1 else ""
                        self.safe_print(f"[{task.notice_type}][第 {page_no} 页][第 {index} 条{suffix}] 标题: {title}")
                        self.print_record(record)
                        all_records.append(record)
            if monitor is not None:
                self.safe_print(f"网站标识统计：{monitor.logo_info}")
                monitor.flush()
        return all_records


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="青岛市公共资源交易电子服务系统采集脚本")
    parser.add_argument("--module-name", default="", help="一级模块名称，如 建设工程 / 政府采购")
    parser.add_argument("--notice-type", default="", help="公告类型，如 招标公告 / 中标公告 / 合同签订公示")
    parser.add_argument("--output-board", default="", help="输出板块，如 招标公告 / 中标公告 / 候选人公告 / 采购意向")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--detail-delay-seconds", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        spider = QdggzySpider(
            module_name=RUN_CONFIG["module_name"] if RUN_CONFIG["module_name"] != "全部模块" else None,
            notice_type_filter=RUN_CONFIG["notice_type"] or None,
            output_board_filter=RUN_CONFIG["output_board"] or None,
            start_page=int(RUN_CONFIG["start_page"]),
            max_pages=int(RUN_CONFIG["max_pages"]),
            page_size=int(RUN_CONFIG["page_size"]),
            timeout_seconds=int(RUN_CONFIG["timeout_seconds"]),
            detail_delay_seconds=float(RUN_CONFIG["detail_delay_seconds"]),
        )
        spider.run()
        return 0

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    spider = QdggzySpider(
        module_name=args.module_name or None,
        notice_type_filter=args.notice_type or None,
        output_board_filter=args.output_board or None,
        start_page=args.start_page,
        max_pages=args.max_pages,
        page_size=args.page_size,
        timeout_seconds=args.timeout_seconds,
        detail_delay_seconds=args.detail_delay_seconds,
    )
    spider.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
