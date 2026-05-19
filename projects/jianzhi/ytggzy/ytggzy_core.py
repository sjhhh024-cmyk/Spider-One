from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import math
import logging
import re
import sys
import time
import types
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from monitoring import SpiderMonitor, build_biz_type


BASE_URL = "https://ggzyjy.yantai.gov.cn"
LIST_API_URL = f"{BASE_URL}/inteligentsearch/rest/esinteligentsearch/getFullTextDataNew"
SITE_CONTEXT = {
    "province_code": "370000",
    "province_name": "山东省",
    "city_id": "370600",
    "city_name": "烟台市",
    "web_source": "烟台市公共资源交易网",
}
MODULE_PAGES = {
    "工程建设": "/jyxx/003001/transaction-list.html",
    "政府采购": "/jyxx/003002/transaction-list.html",
    "自主选择进场-工程项目": "/zzjyxx/013001/013001001/zzjctransaction-list.html",
    "自主选择进场-采购项目": "/zzjyxx/013001/013001002/zzjctransaction-list.html",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERAL_DIR = PROJECT_ROOT / "general"
TAG_PATTERN = re.compile(r"<[^>]+>")
YEAR_PREFIX_PATTERN = re.compile(r"^(.*?)(?:20\d{2}|202\d)")
TRADE_TYPE_WHITELIST = {"施工", "监理", "勘察", "设计", "其他"}
TRADE_TYPE_MODULES = {"工程建设", "自主选择进场-工程项目"}
INTENTION_MODULES = {"政府采购", "自主选择进场-采购项目"}
ALLOWED_NOTICE_TYPES = {
    "工程建设": {"招标公告", "中（定）标候选人公示", "中标结果公示", "合同及履约"},
    "政府采购": {"采购需求(意向)", "采购公告", "采购合同"},
    "自主选择进场-工程项目": {"招标公告", "中（定）标候选人公示", "中标结果公示", "合同及履约"},
    "自主选择进场-采购项目": {"采购需求(意向)", "采购公告", "采购合同"},
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


def _load_model_classes() -> tuple[Any, Any, Any]:
    amount_module = _load_python_module("ytggzy_general.AmountConverter", GENERAL_DIR / "AmountConverter.py")
    package_module = sys.modules.setdefault("QGZJGG", types.ModuleType("QGZJGG"))
    utils_module = sys.modules.setdefault("QGZJGG.Utils", types.ModuleType("QGZJGG.Utils"))
    package_module.Utils = utils_module
    utils_module.AmountConverter = amount_module
    sys.modules["QGZJGG.Utils.AmountConverter"] = amount_module

    bid_module = _load_python_module("ytggzy_general.GetBidModel", GENERAL_DIR / "GetBidModel.py")
    candidate_module = _load_python_module("ytggzy_general.GetCandidateModel", GENERAL_DIR / "GetCandidateModel.py")
    tender_module = _load_python_module("ytggzy_general.GetTenderModel", GENERAL_DIR / "GetTenderModel.py")
    return (
        getattr(bid_module, "BiddingModel", None),
        getattr(candidate_module, "CandidateModel", None),
        getattr(tender_module, "TenderModel", None),
    )


BiddingModel, CandidateModel, TenderModel = _load_model_classes()


@dataclass
class SpiderTask:
    module_name: str
    notice_type: str
    categorynum: str
    output_board: str
    page_url: str


def normalize_text(value: Any) -> str:
    text = unescape("" if value is None else str(value))
    text = text.replace("\u00a0", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def join_text_lines(text: str) -> str:
    lines = [normalize_text(line) for line in (text or "").splitlines()]
    return "\n".join(line for line in lines if line)


def strip_html_tags(value: str) -> str:
    return normalize_text(TAG_PATTERN.sub("", value))


def make_absolute_url(url: str) -> str:
    return urljoin(BASE_URL, normalize_text(url))


def encode_html_content(html: str) -> str:
    if not html:
        return ""
    return base64.b64encode(html.encode("utf-8")).decode("utf-8")


def resolve_output_board(module_name: str, notice_name: str) -> str:
    module = normalize_text(module_name)
    name = normalize_text(notice_name)
    if module in INTENTION_MODULES and ("需求" in name or "意向" in name):
        return "采购意向"
    if any(keyword in name for keyword in ("候选人", "预中标", "入围投标人")):
        return "候选人公告"
    if any(keyword in name for keyword in ("中标", "成交", "合同", "履约", "结果")):
        return "中标公告"
    return "招标公告"


def get_announcement_type(notice_type: str) -> int:
    return 1 if any(keyword in normalize_text(notice_type) for keyword in ("合同", "履约")) else 2


def get_trade_type(task: SpiderTask, list_record: dict[str, Any]) -> str:
    trade_type = normalize_text(list_record.get("zbtype", ""))
    if task.module_name in TRADE_TYPE_MODULES:
        return trade_type if trade_type in TRADE_TYPE_WHITELIST else ""
    return trade_type


def detect_union_flag(company_name: str) -> int:
    return 1 if "," in normalize_text(company_name) else 0


def pick_main_node(soup: BeautifulSoup) -> Any:
    return (
        soup.select_one(".txt-content")
        or soup.select_one(".com-table")
        or soup.select_one("#infolist")
        or soup.select_one("body")
    )


def extract_attachment_entries(soup: BeautifulSoup) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for node in soup.select(".com-files a[href]"):
        file_url = make_absolute_url(node.get("href", ""))
        if not file_url:
            continue
        file_name = normalize_text(node.get_text(" ", strip=True)) or Path(file_url.split("?", 1)[0]).name
        file_type = Path(file_url.split("?", 1)[0]).suffix.lstrip(".").lower()
        entries.append(
            {
                "fileUrl": file_url,
                "fileType": file_type,
                "fileName": file_name,
            }
        )
    return entries


def normalize_consultation_info(consultation: Any) -> dict[str, list[str]]:
    if not isinstance(consultation, dict):
        consultation = {}
    purchasing = consultation.get("purchasingInfor", [])
    project = consultation.get("projectInfor", [])
    if not isinstance(purchasing, list):
        purchasing = []
    if not isinstance(project, list):
        project = []
    return {
        "purchasingInfor": [normalize_text(item) for item in purchasing if normalize_text(item)],
        "projectInfor": [normalize_text(item) for item in project if normalize_text(item)],
    }


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


def extract_procurement_unit_for_intention(title: str) -> str:
    name = normalize_text(title)
    match = YEAR_PREFIX_PATTERN.match(name)
    if match:
        return normalize_text(match.group(1))
    return ""


def _collect_release_text_parts(node: Any, *, title: str, before_parts: list[str], after_parts: list[str], state: dict[str, bool]) -> None:
    if isinstance(node, NavigableString):
        text = join_text_lines(str(node))
        if text and text != title:
            target = after_parts if state["table_seen"] else before_parts
            target.append(text)
        return

    if not isinstance(node, Tag):
        return

    if node.name == "table":
        state["table_seen"] = True
        return

    if node.find("table") is not None:
        for child in node.children:
            _collect_release_text_parts(
                child,
                title=title,
                before_parts=before_parts,
                after_parts=after_parts,
                state=state,
            )
        return

    text = join_text_lines(node.get_text("\n", strip=True))
    if text and text != title:
        target = after_parts if state["table_seen"] else before_parts
        target.append(text)


def build_release_content_mix(main_html: str, title: str = "") -> dict[str, Any]:
    soup = BeautifulSoup(main_html or "", "html.parser")
    table = soup.find("table")
    title_text = normalize_text(title)
    if table is None:
        text = join_text_lines(soup.get_text("\n", strip=True))
        lines = [line for line in text.splitlines() if normalize_text(line) != title_text]
        return {"1": "\n".join(lines)} if lines else {}

    root = soup.find() or soup
    before_parts: list[str] = []
    after_parts: list[str] = []
    state = {"table_seen": False}
    for child in getattr(root, "children", []):
        _collect_release_text_parts(
            child,
            title=title_text,
            before_parts=before_parts,
            after_parts=after_parts,
            state=state,
        )

    rows = table.find_all("tr")
    head: list[str] = []
    body: list[list[str]] = []
    if rows:
        head = [
            normalize_text(cell.get_text(" ", strip=True))
            for cell in rows[0].find_all(["th", "td"])
        ]
        for row in rows[1:]:
            values = [
                normalize_text(cell.get_text(" ", strip=True))
                for cell in row.find_all(["th", "td"])
            ]
            if any(values):
                body.append(values)

    result: dict[str, Any] = {}
    if before_parts:
        result["1"] = "\n".join(before_parts)
    table_block: dict[str, Any] = {}
    if head:
        table_block["head"] = head
    if body:
        table_block["body"] = body
    if table_block:
        result["2"] = table_block
    if after_parts:
        result["3"] = "\n".join(after_parts)
    return result


def pick_first_result_item(model_result: dict[str, Any]) -> dict[str, Any]:
    result_items = model_result.get("result", [])
    if isinstance(result_items, list) and result_items:
        first_item = result_items[0]
        if isinstance(first_item, dict):
            return first_item
    return {}


def extract_module_tasks(html: str, module_name: str, page_url: str) -> list[SpiderTask]:
    soup = BeautifulSoup(html, "html.parser")
    tasks: list[SpiderTask] = []
    allowed_notice_types = ALLOWED_NOTICE_TYPES.get(module_name)
    for node in soup.select("#sx-ggtype a[data-categorynum]"):
        categorynum = normalize_text(node.get("data-categorynum", ""))
        notice_type = normalize_text(node.get_text(" ", strip=True))
        if not categorynum or notice_type == "全部":
            continue
        if allowed_notice_types is not None and notice_type not in allowed_notice_types:
            continue
        tasks.append(
            SpiderTask(
                module_name=module_name,
                notice_type=notice_type,
                categorynum=categorynum,
                output_board=resolve_output_board(module_name, notice_type),
                page_url=page_url,
            )
        )
    return tasks


def parse_detail(html: str, detail_url: str, list_record: dict[str, Any]) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    main_node = pick_main_node(soup)
    main_html = str(main_node) if main_node is not None else ""
    plain_text = join_text_lines(main_node.get_text("\n", strip=True) if main_node is not None else "")
    title_node = soup.select_one(".title-txt")
    source_node = soup.select_one("#info_ly")
    return {
        "title": normalize_text(title_node.get_text(" ", strip=True) if title_node else list_record.get("title", "")),
        "detail_url": detail_url,
        "main_html": main_html,
        "plain_text": plain_text,
        "attachments": extract_attachment_entries(soup),
        "source": normalize_text(source_node.get_text(" ", strip=True) if source_node else list_record.get("xiaquname", "")),
        "publish_time": normalize_text(list_record.get("webdate", "")),
    }


def build_bid_record(
    task: SpiderTask,
    list_record: dict[str, Any],
    detail: dict[str, Any],
    model_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "provinceCode": SITE_CONTEXT["province_code"],
        "regionCode": normalize_text(list_record.get("xiaqucode", "")),
        "regionName": normalize_text(list_record.get("xiaquname", "")),
        "bidType": get_trade_type(task, list_record),
        "announcementTitle": detail["title"],
        "originalWebsiteAddress": detail["detail_url"],
        "procurementMethod": "",
        "parentType": task.module_name,
        "announcementType": task.notice_type,
        "projectNum": normalize_text(list_record.get("projectnumber", "")),
        "projectName": detail["title"],
        "budgetAmount": "",
        "releaseSource": detail["source"],
        "releaseTime": detail["publish_time"],
        "consultationInfo": {"purchasingInfor": [], "projectInfor": []},
        "fileInfo": detail["attachments"],
        "contentType": 1 if detail["main_html"] else 0,
        "htmlContent": encode_html_content(detail["main_html"]),
        "webSource": SITE_CONTEXT["web_source"],
    }
    if not isinstance(model_result, dict) or not model_result:
        return record

    project_num = normalize_text(model_result.get("projectNum", ""))
    project_name = normalize_text(model_result.get("projectName", ""))
    budget_amount = normalize_text(model_result.get("budgetAmount", ""))
    procurement_method = normalize_text(model_result.get("procurementMethod", ""))
    release_source = normalize_text(model_result.get("releaseSource", ""))
    purchaser_address = normalize_text(model_result.get("purchaserAddress", ""))
    consultation_info = normalize_consultation_info(model_result.get("consultationInfo", {}))

    if project_num:
        record["projectNum"] = project_num
    if project_name:
        record["projectName"] = project_name
        record["announcementTitle"] = project_name
    if budget_amount:
        record["budgetAmount"] = budget_amount
    if procurement_method:
        record["procurementMethod"] = procurement_method
    if release_source:
        record["releaseSource"] = release_source
    if purchaser_address:
        record["purchaserAddress"] = purchaser_address
    record["consultationInfo"] = consultation_info
    return record


def build_win_record(
    task: SpiderTask,
    list_record: dict[str, Any],
    detail: dict[str, Any],
    model_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "tenderTitle": detail["title"],
        "tenderNumber": normalize_text(list_record.get("projectnumber", "")),
        "cityId": SITE_CONTEXT["city_id"],
        "cityName": SITE_CONTEXT["city_name"],
        "renderMoney": "",
        "renderDate": detail["publish_time"],
        "renderType": get_trade_type(task, list_record) if task.module_name in TRADE_TYPE_MODULES else "",
        "procurementUnit": "",
        "relationCompanyName": "",
        "uploadFileUrl": [item["fileUrl"] for item in detail["attachments"]],
        "provinceCode": SITE_CONTEXT["province_code"],
        "announcementType": get_announcement_type(task.notice_type),
        "originalWebsiteAddress": detail["detail_url"],
        "projectClassification": "[5]",
        "tenderAdditionalInfoStr": "",
        "htmlContent": encode_html_content(detail["main_html"]),
        "contentType": 1 if detail["main_html"] else 0,
        "isUnion": 0,
        "contactName": "",
        "contactTelephone": "",
        "parentType": task.module_name,
    }
    if not isinstance(model_result, dict) or not model_result:
        return record

    tender_title = normalize_text(model_result.get("tenderTitle", ""))
    tender_number = normalize_text(model_result.get("tenderNumber", ""))
    procurement_unit = normalize_text(model_result.get("procurementUnit", ""))
    result_item = pick_first_result_item(model_result)
    relation_company_name = normalize_text(result_item.get("relationCompanyName", ""))
    render_money = normalize_text(result_item.get("renderMoney", ""))
    contact_name = normalize_text(result_item.get("contactName", ""))
    contact_telephone = normalize_text(result_item.get("contactTelephone", ""))

    if tender_title:
        record["tenderTitle"] = tender_title
    if tender_number:
        record["tenderNumber"] = tender_number
    if procurement_unit:
        record["procurementUnit"] = procurement_unit
    if relation_company_name:
        record["relationCompanyName"] = relation_company_name
        record["isUnion"] = detect_union_flag(relation_company_name)
    if render_money:
        record["renderMoney"] = render_money
    if contact_name:
        record["contactName"] = contact_name
    if contact_telephone:
        record["contactTelephone"] = contact_telephone
    return record


def build_candidate_record(
    task: SpiderTask,
    list_record: dict[str, Any],
    detail: dict[str, Any],
    model_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "tenderTitle": detail["title"],
        "renderDate": detail["publish_time"],
        "renderType": "中标候选人",
        "procurementUnit": "",
        "relationCompanyName": "",
        "uploadFileUrl": detail["attachments"],
        "provinceCode": SITE_CONTEXT["province_code"],
        "provinceName": SITE_CONTEXT["province_name"],
        "cityId": SITE_CONTEXT["city_id"],
        "cityName": SITE_CONTEXT["city_name"],
        "announcementType": "候选人公告",
        "originalWebsiteAddress": detail["detail_url"],
        "htmlContent": encode_html_content(detail["main_html"]),
        "contentType": 1 if detail["main_html"] else 0,
        "parentType": task.module_name,
        "extra": {},
        "webSource": SITE_CONTEXT["web_source"],
    }
    if not isinstance(model_result, dict) or not model_result:
        return record

    tender_title = normalize_text(model_result.get("tenderTitle", ""))
    procurement_unit = normalize_text(model_result.get("procurementUnit", ""))
    result_item = pick_first_result_item(model_result)
    relation_company_name = normalize_text(result_item.get("relationCompanyName", ""))
    candidate_sort = normalize_candidate_sort_items(result_item.get("candidateSort", []))
    extra_value = model_result.get("extra", {})
    tender_number = ""
    if isinstance(extra_value, dict):
        tender_number = normalize_text(extra_value.get("tenderNumber", ""))

    if tender_title:
        record["tenderTitle"] = tender_title
    if procurement_unit:
        record["procurementUnit"] = procurement_unit
    if relation_company_name:
        record["relationCompanyName"] = relation_company_name
    extra: dict[str, Any] = {}
    if candidate_sort:
        extra["candidateSort"] = candidate_sort
    if tender_number:
        extra["tenderNumber"] = tender_number
    record["extra"] = extra
    return record


def build_procurement_intention_record(task: SpiderTask, list_record: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "provinceCode": SITE_CONTEXT["province_code"],
        "cityId": SITE_CONTEXT["city_id"],
        "cityName": SITE_CONTEXT["city_name"],
        "procurementTitle": detail["title"],
        "releaseSource": extract_procurement_unit_for_intention(detail["title"]),
        "releaseDatetime": detail["publish_time"],
        "releaseContentMix": build_release_content_mix(detail["main_html"], detail["title"]),
        "fileInfo": detail["attachments"],
        "originalWebsiteAddress": detail["detail_url"],
        "extra": {},
        "parentType": task.module_name,
        "bidType": task.notice_type,
        "webSource": SITE_CONTEXT["web_source"],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="烟台市公共资源交易网采集脚本")
    parser.add_argument("--module-name", default="", help="一级模块名称")
    parser.add_argument("--notice-type", default="", help="二级栏目名称")
    parser.add_argument("--output-board", default="", help="输出板块")
    parser.add_argument("--start-page", type=int, default=1, help="起始页")
    parser.add_argument("--max-pages", type=int, default=1, help="最多抓取页数，0 表示不限制")
    parser.add_argument("--page-size", type=int, default=10, help="每页条数")
    parser.add_argument("--timeout-seconds", type=int, default=20, help="请求超时秒数")
    parser.add_argument("--detail-delay-seconds", type=float, default=0.0, help="详情间隔秒数")
    return parser


class YtggzySpider:
    def __init__(
        self,
        *,
        module_name: str | None = None,
        notice_type_filter: str | None = None,
        output_board_filter: str | None = None,
        start_page: int = 1,
        max_pages: int = 1,
        page_size: int = 10,
        timeout_seconds: int = 20,
        detail_delay_seconds: float = 0.0,
    ) -> None:
        self.module_name = normalize_text(module_name)
        self.notice_type_filter = normalize_text(notice_type_filter)
        self.output_board_filter = normalize_text(output_board_filter)
        self.start_page = max(1, int(start_page))
        self.max_pages = max(0, int(max_pages))
        self.page_size = max(1, int(page_size))
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.detail_delay_seconds = max(0.0, float(detail_delay_seconds))
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.model_clients = self.load_model_clients()

    def load_model_clients(self) -> dict[str, Any]:
        return {
            "招标公告": BiddingModel(timeout=self.timeout_seconds),
            "候选人公告": CandidateModel(timeout=max(self.timeout_seconds, 60)),
            "中标公告": TenderModel(timeout=self.timeout_seconds),
        }

    def create_monitor(self, task: SpiderTask) -> Any:
        biz_type = build_biz_type(task.module_name, task.notice_type, getattr(task, "sub_type", ""))
        return SpiderMonitor(
            province=SITE_CONTEXT["province_name"],
            city=SITE_CONTEXT["city_name"],
            webname=SITE_CONTEXT["web_source"],
            biz_type=biz_type,
            logger=self.logger,
        )

    def discover_tasks(self) -> list[SpiderTask]:
        tasks: list[SpiderTask] = []
        for module_name, page_path in MODULE_PAGES.items():
            if self.module_name and self.module_name != module_name:
                continue
            page_url = make_absolute_url(page_path)
            response = self.session.get(page_url, timeout=self.timeout_seconds)
            response.raise_for_status()
            tasks.extend(extract_module_tasks(response.text, module_name, page_url))

        filtered: list[SpiderTask] = []
        for task in tasks:
            if self.notice_type_filter and task.notice_type != self.notice_type_filter:
                continue
            if self.output_board_filter and task.output_board != self.output_board_filter:
                continue
            filtered.append(task)
        return filtered

    def build_list_payload(self, task: SpiderTask, page_number: int) -> dict[str, Any]:
        return {
            "token": "",
            "pn": (page_number - 1) * self.page_size,
            "rn": self.page_size,
            "sdt": "",
            "edt": "",
            "wd": "",
            "inc_wd": "",
            "exc_wd": "",
            "fields": "",
            "cnum": "001",
            "sort": '{"webdate":"0","id":"0"}',
            "ssort": "",
            "cl": 200,
            "terminal": "",
            "condition": [
                {
                    "fieldName": "categorynum",
                    "equal": task.categorynum,
                    "notEqual": None,
                    "equalList": None,
                    "notEqualList": None,
                    "isLike": True,
                    "likeType": 2,
                }
            ],
            "time": [],
            "highlights": "",
            "statistics": None,
            "unionCondition": None,
            "accuracy": "",
            "noParticiple": "1",
            "searchRange": None,
            "noWd": True,
        }

    def fetch_list_records(self, task: SpiderTask, page_number: int) -> tuple[list[dict[str, Any]], int]:
        payload = self.build_list_payload(task, page_number)
        response = self.session.post(LIST_API_URL, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        outer = response.json()
        inner = json.loads(outer["content"])
        result = inner.get("result", {})
        records = result.get("records", [])
        if not isinstance(records, list):
            records = []
        totalcount = int(result.get("totalcount", 0) or 0)
        return records, totalcount

    def fetch_detail(self, detail_url: str, list_record: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(detail_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return parse_detail(response.text, detail_url, list_record)

    def get_model_result(self, board: str, detail: dict[str, Any]) -> dict[str, Any]:
        client = self.model_clients.get(board)
        if client is None:
            return {}
        model_input = detail["plain_text"] or strip_html_tags(detail["main_html"])
        if not model_input:
            return {}
        try:
            result = client.get_result(model_input)
        except Exception:
            return {}
        return result if isinstance(result, dict) else {}

    def build_records(self, task: SpiderTask, list_record: dict[str, Any], detail: dict[str, Any]) -> list[dict[str, Any]]:
        if task.output_board == "采购意向":
            return [build_procurement_intention_record(task, list_record, detail)]

        model_result = self.get_model_result(task.output_board, detail)
        if task.output_board == "招标公告":
            return [build_bid_record(task, list_record, detail, model_result)]

        if task.output_board == "候选人公告":
            return [build_candidate_record(task, list_record, detail, model_result)]

        return [build_win_record(task, list_record, detail, model_result)]

    def collect_records_for_task(self, task: SpiderTask) -> list[dict[str, Any]]:
        page_number = self.start_page
        collected: list[dict[str, Any]] = []
        fetched_pages = 0
        monitor = self.create_monitor(task)
        try:
            while True:
                records, totalcount = self.fetch_list_records(task, page_number)
                total_pages = max(1, math.ceil(totalcount / self.page_size)) if totalcount else 1
                print(
                    f"[{task.output_board}][{task.module_name} -> {task.notice_type}]"
                    f"[第 {page_number} 页 / 共 {total_pages} 页] 列表条数: {len(records)}"
                )
                if not records:
                    break
                if monitor is not None:
                    monitor.mark_has_content()

                for index, list_record in enumerate(records, 1):
                    detail_url = make_absolute_url(list_record.get("linkurl", ""))
                    try:
                        detail = self.fetch_detail(detail_url, list_record)
                        built_records = self.build_records(task, list_record, detail)
                    except requests.RequestException:
                        if monitor is not None:
                            monitor.mark_website_error()
                            monitor.mark_invalid_data()
                        raise
                    except Exception:
                        if monitor is not None:
                            monitor.mark_invalid_data()
                        raise
                    print(f"详情 {index}: {detail_url}")
                    if built_records:
                        print("字段:", ", ".join(built_records[0].keys()))
                        if monitor is not None:
                            monitor.mark_has_new_data()
                    for record in built_records:
                        print(json.dumps(record, ensure_ascii=False, indent=2))
                        print()
                    collected.extend(built_records)
                    if self.detail_delay_seconds:
                        time.sleep(self.detail_delay_seconds)

                fetched_pages += 1
                if self.max_pages and fetched_pages >= self.max_pages:
                    break
                if page_number >= total_pages:
                    break
                page_number += 1
        except requests.RequestException:
            if monitor is not None:
                monitor.mark_website_error()
                monitor.mark_run_failed()
            raise
        except Exception:
            if monitor is not None:
                monitor.mark_run_failed()
            raise
        finally:
            if monitor is not None:
                print(f"网站标识统计：{monitor.logo_info}")
                monitor.flush()
        return collected

    def run(self) -> list[dict[str, Any]]:
        tasks = self.discover_tasks()
        print(f"任务数: {len(tasks)}")
        all_records: list[dict[str, Any]] = []
        for task in tasks:
            print(f"开始: {task.module_name} -> {task.notice_type} -> {task.output_board}")
            all_records.extend(self.collect_records_for_task(task))
        print(f"总记录数: {len(all_records)}")
        return all_records


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    spider = YtggzySpider(
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
