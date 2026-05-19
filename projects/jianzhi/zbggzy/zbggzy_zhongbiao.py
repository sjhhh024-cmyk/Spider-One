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
SUPPORTED_WIN_NOTICE_TYPES = {
    "中标结果公告",
    "中标（成交）公告",
    "成交结果公告",
    "结果公示",
}
CONTRACT_GONGGAO_MODULES = {
    "政府采购",
    "国企采购",
    "药械采购",
    "其他交易",
}
CONTRACT_GONGSHI_MODULES = {
    "农村工程",
    "农村采购",
    "土地流转",
    "集体资产",
    "农业设施",
    "其他交易(农村产权)",
}

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
    # "module_name": "全部模块",
    # "notice_type": "",
    # 单测
    # "module_name": "建设工程",
    # "notice_type": "中标结果公告",
    # "module_name": "政府采购",
    # "notice_type": "合同公告",
    # "module_name": "国企采购",
    # "notice_type": "中标（成交）公告",
    # "module_name": "药械采购",
    # "notice_type": "中标（成交）公告",
    # "module_name": "其他交易",
    # "notice_type": "中标（成交）公告",
    # "module_name": "农村工程",
    # "notice_type": "合同公示",
    # "module_name": "农村采购",
    # "notice_type": "结果公示",
    "module_name": "土地流转",
    "notice_type": "合同公示",
    # "module_name": "集体资产",
    # "notice_type": "结果公示",
    # "module_name": "农业设施",
    # "notice_type": "结果公示",
    # "module_name": "其他交易(农村产权)",
    # "notice_type": "结果公示",
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
    ["ZbggzyRuntime", dict[str, Any], dict[str, Any]], list[dict[str, Any]]
]


def normalize_text(value: str) -> str:
    text = unescape(value or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_optional_text(value: Any) -> str:
    if value is None:
        return ""
    text = normalize_text(str(value))
    return "" if text in {"None", "null", "NULL"} else text


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


def _load_general_dependencies() -> tuple[Any, Any]:
    amount_module = _load_python_module(
        "zbggzy_win.AmountConverter", GENERAL_DIR / "AmountConverter.py"
    )
    package_module = sys.modules.setdefault("QGZJGG", types.ModuleType("QGZJGG"))
    utils_module = sys.modules.setdefault(
        "QGZJGG.Utils", types.ModuleType("QGZJGG.Utils")
    )
    package_module.Utils = utils_module
    utils_module.AmountConverter = amount_module
    sys.modules["QGZJGG.Utils.AmountConverter"] = amount_module

    tender_module = _load_python_module(
        "zbggzy_win.GetTenderModel", GENERAL_DIR / "GetTenderModel.py"
    )
    return getattr(amount_module, "MoneyParser"), getattr(tender_module, "TenderModel")


MoneyParser, TenderModel = _load_general_dependencies()


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


def extract_attachment_urls(html: str, detail_url: str) -> list[str]:
    return [item["fileUrl"] for item in _extract_attachment_entries(html, detail_url)]


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
        "中标（成交）金额",
        "中标金额",
        "成交金额",
        "供应商名称",
        "供应商地址",
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


def extract_construction_result_table_info(rows: list[list[str]]) -> dict[str, str]:
    result = {
        "relation_company_name": "",
        "render_money": "",
    }
    for index, row in enumerate(rows):
        normalized_row = [
            normalize_text(str(cell)) for cell in row if normalize_text(str(cell))
        ]
        if not normalized_row:
            continue
        if "中标单位名称" not in normalized_row or not any(
            "中标金额" in cell for cell in normalized_row
        ):
            continue
        if index + 1 >= len(rows):
            continue
        value_row = [
            normalize_text(str(cell))
            for cell in rows[index + 1]
            if normalize_text(str(cell))
        ]
        if len(value_row) < 3:
            continue
        result["relation_company_name"] = value_row[1]
        result["render_money"] = normalize_money(value_row[2])
        break
    return result


def encode_html_content(html: str) -> str:
    return base64.b64encode(html.encode("utf-8")).decode("utf-8")


def load_model_client(enable_model_enrichment: bool, timeout_seconds: int) -> Any:
    if not enable_model_enrichment:
        return None
    return TenderModel(timeout=timeout_seconds)


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
                is_contract_win_notice = (
                    module_name in CONTRACT_GONGGAO_MODULES
                    and notice_type == "合同公告"
                ) or (
                    module_name in CONTRACT_GONGSHI_MODULES
                    and notice_type == "合同公示"
                )
                if notice_type in EXCLUDED_NOTICE_TYPES and not is_contract_win_notice:
                    continue
                if (
                    notice_type not in SUPPORTED_WIN_NOTICE_TYPES
                    and not is_contract_win_notice
                ):
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
        attachment_urls = extract_attachment_urls(detail_html, detail_url)
        plain_text = str(detail.get("plain_text", ""))
        table_rows = detail.get("table_rows", [])
        construction_result_info = (
            extract_construction_result_table_info(table_rows)
            if task.module_name == "建设工程"
            else {}
        )

        area_name = normalize_text(str(card.get("areacode", "")))
        region_code, region_name = AREA_CODE_MAPPING.get(
            area_name, (SITE_CONTEXT["city_id"], SITE_CONTEXT["city_name"])
        )

        procurement_unit = clean_procurement_unit(
            pick_first_non_empty(
                [
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
        render_date = pick_first_non_empty(
            [str(card.get("infodate", "")), str(field_map.get("公告期限", ""))]
        )
        contact_name = pick_first_non_empty(
            [str(field_map.get("项目联系人", "")), extract_contact_name(plain_text)]
        )
        contact_phone = pick_first_non_empty(
            [
                str(field_map.get("联系方式", "")),
                str(field_map.get("电话", "")),
                extract_contact_phone(plain_text),
            ]
        )
        render_money = normalize_money(
            pick_first_non_empty(
                [
                    str(construction_result_info.get("render_money", "")),
                    str(field_map.get("中标（成交）金额", "")),
                    str(field_map.get("中标金额", "")),
                    str(field_map.get("成交金额", "")),
                ]
            )
        )
        relation_company_name = pick_first_non_empty(
            [
                str(construction_result_info.get("relation_company_name", "")),
                str(field_map.get("供应商名称", "")),
                str(field_map.get("中标单位名称", "")),
                str(field_map.get("中标人", "")),
                str(field_map.get("中标单位", "")),
                str(field_map.get("成交供应商", "")),
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
            "attachment_urls": attachment_urls,
            "region_code": region_code,
            "region_name": region_name,
            "procurement_unit": procurement_unit,
            "project_num": project_num,
            "project_name": project_name,
            "render_date": render_date,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "render_money": render_money,
            "relation_company_name": relation_company_name,
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
                    base_record = build_record(context)
                    records = apply_model_enrichment(self, base_record, context)
                    all_records.extend(records)
                    if monitor is not None and records:
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
                for expanded_index, record in enumerate(records, start=1):
                    title = pick_first_non_empty(
                        [
                            str(record.get("tenderTitle", "")),
                            str(record.get("announcementTitle", "")),
                            str(record.get("projectName", "")),
                            str(record.get("procurementTitle", "")),
                        ]
                    )
                    suffix = f"-{expanded_index}" if len(records) > 1 else ""
                    self.safe_print(
                        f"[{task.notice_type}][第 {page_no} 页][第 {index} 条{suffix}] 标题: {title}"
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


def detect_union_flag_by_company_name(company_name: str) -> int:
    text = normalize_text(company_name)
    if not text:
        return 0
    return 1 if "," in text or "，" in text or "联合体" in text else 0


def get_result_announcement_type(notice_type: str) -> int:
    return 1 if "合同" in normalize_text(notice_type) else 2


def build_win_record(context: dict[str, Any]) -> dict[str, Any]:
    task: ModuleTask = context["task"]
    return {
        "tenderTitle": "",
        "tenderNumber": "",
        "cityId": str(context["region_code"]),
        "cityName": str(context["region_name"]),
        "renderMoney": "",
        "renderDate": context["render_date"],
        "renderType": "",
        "procurementUnit": "",
        "relationCompanyName": "",
        "uploadFileUrl": context["attachment_urls"],
        "provinceCode": SITE_CONTEXT["province_code"],
        "announcementType": get_result_announcement_type(task.notice_type),
        "originalWebsiteAddress": context["detail_url"],
        "projectClassification": "[5]",
        "tenderAdditionalInfoStr": "",
        "htmlContent": context["html_content"],
        "contentType": 1,
        "isUnion": 0,
        "contactName": "",
        "contactTelephone": "",
        "parentType": task.parent_type,
    }


def build_model_result_record(
    base_record: dict[str, Any],
    model_result: dict[str, Any],
    item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = dict(base_record)

    tender_title = normalize_optional_text(model_result.get("tenderTitle"))
    if tender_title:
        record["tenderTitle"] = tender_title

    tender_number = normalize_optional_text(model_result.get("tenderNumber"))
    if tender_number:
        record["tenderNumber"] = tender_number

    procurement_unit = normalize_optional_text(model_result.get("procurementUnit"))
    if procurement_unit:
        record["procurementUnit"] = procurement_unit

    if item is None:
        return record

    relation_company_name = normalize_optional_text(item.get("relationCompanyName"))
    if relation_company_name:
        record["relationCompanyName"] = relation_company_name
        record["isUnion"] = detect_union_flag_by_company_name(relation_company_name)

    contact_name = normalize_optional_text(item.get("contactName"))
    if contact_name:
        record["contactName"] = contact_name

    contact_telephone = normalize_optional_text(item.get("contactTelephone"))
    if contact_telephone:
        record["contactTelephone"] = contact_telephone

    render_money = normalize_optional_text(item.get("renderMoney"))
    if render_money:
        record["renderMoney"] = render_money

    return record


def normalize_raw_model_response(model_result: dict[str, Any]) -> dict[str, Any]:
    raw_result = model_result.get("result")
    if not isinstance(raw_result, dict):
        return model_result

    normalized_result = {
        "tenderTitle": normalize_optional_text(raw_result.get("项目名称")),
        "tenderNumber": normalize_optional_text(raw_result.get("项目编号")),
        "procurementUnit": normalize_optional_text(raw_result.get("采购人名称")),
        "result": [],
    }
    purchase_results = raw_result.get("采购结果", [])
    if isinstance(purchase_results, list):
        for item in purchase_results:
            if not isinstance(item, dict):
                continue
            normalized_result["result"].append(
                {
                    "relationCompanyName": normalize_optional_text(
                        item.get("供应商名称")
                    ),
                    "contactName": normalize_optional_text(item.get("联系人姓名")),
                    "contactTelephone": normalize_optional_text(
                        item.get("联系人电话")
                    ),
                    "renderMoney": normalize_optional_text(item.get("中标金额")),
                }
            )
    return normalized_result


def apply_win_model_enrichment(
    runtime: ZbggzyRuntime, record: dict[str, Any], context: dict[str, Any]
) -> list[dict[str, Any]]:
    client = runtime.model_client
    if client is None:
        return [record]
    model_input = pick_first_non_empty(
        [context["plain_text"], strip_html_tags(context["cleaned_html"])]
    )
    if not model_input:
        return [record]
    try:
        model_result = client.get_result(model_input)
    except MODEL_ENRICHMENT_FALLBACK_EXCEPTIONS as exc:
        runtime.logger.warning("中标公告 模型增强失败，回退基础解析: %s", exc)
        return [record]
    if not isinstance(model_result, dict) or not model_result:
        return [record]
    model_result = normalize_raw_model_response(model_result)

    model_results = model_result.get("result", [])
    if isinstance(model_results, list) and model_results:
        records: list[dict[str, Any]] = []
        for item in model_results:
            if isinstance(item, dict):
                records.append(build_model_result_record(record, model_result, item))
        if records:
            return records

    return [build_model_result_record(record, model_result)]


def main(argv: list[str] | None = None) -> int:
    return run_runtime(
        argv,
        build_record=build_win_record,
        apply_model_enrichment=apply_win_model_enrichment,
    )


if __name__ == "__main__":
    raise SystemExit(main())
