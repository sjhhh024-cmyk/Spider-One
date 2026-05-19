from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import sys
import time
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup, Comment

PROJECT_ROOT = Path(__file__).resolve().parents[1]
from AmountConverter import MoneyParser


SHOWVIEW_PATTERN = re.compile(
    r"showview\('(?P<notice_id>[^']+)',\s*(?P<is_new>\d+)(?:,\s*'(?P<notice_type>[^']*)')?\)"
)
FIELD_PAIR_PATTERN = re.compile(
    r"<span[^>]*class=\"l_span\"[^>]*>(?P<label>.*?)</span>\s*"
    r"<span[^>]*class=\"r_span\"[^>]*>(?P<value>.*?)</span>",
    re.S,
)
TAG_PATTERN = re.compile(r"<[^>]+>")
CONTACT_SUFFIX_PATTERN = re.compile(r"[;；]\s*(?:联系人|联系电话|电话|联系方式)\s*[:：].*$")
HTML_KEEP_TEXT_MARKERS = ("发布人", "发布时间", "技术支持电话")
HTML_NOISE_EXACT_TEXTS = ("附件：", "相关附件：", "请点击此处下载", "关闭本页")
HTML_NOISE_PREFIXES = (
    "PDF版招标文件",
    "请点击“我要参与”登录济南公共资源交易中心网站",
    '请点击"我要参与"登录济南公共资源交易中心网站',
    "ca办理及相关咨询请点击",
)
HTML_CA_HELP_URL = "124.128.84.51:9000/jnggzy/jnggzyca/index.jsp#nav-7"
HTML_TRADE_LOGIN_PATH = "/new_flogin/login.do"

# 一级模块到二级栏目任务的静态映射，按站点真实栏目组织。
MODULE_TASKS = {
    "建设工程": [
        {
            "module_name": "建设工程",
            "type": "0",
            "notice_type": "招标公告",
            "list_api": "homepage",
            "list_key": "str0",
        },
        {
            "module_name": "建设工程",
            "type": "0",
            "notice_type": "中标候选人",
            "search_notice_type": "中标候选人公示",
            "list_api": "homepage",
            "list_key": "str1",
        },
        {
            "module_name": "建设工程",
            "type": "0",
            "notice_type": "中标结果公告",
            "list_api": "homepage",
            "list_key": "str4",
        },
    ],
    "政府采购": [
        {"module_name": "政府采购", "type": "1", "notice_type": "招标公告", "list_api": "homepage", "list_key": "str0"},
        {"module_name": "政府采购", "type": "1", "notice_type": "中标公告", "list_api": "homepage", "list_key": "str1"},
    ],
    "土地矿产": [
        {"module_name": "土地矿产", "type": "2", "notice_type": "招标公告", "list_api": "homepage", "list_key": "str0"},
        {
            "module_name": "土地矿产",
            "type": "2",
            "notice_type": "结果公示",
            "search_notice_type": "中标公告",
            "list_api": "homepage",
            "list_key": "str1",
        },
    ],
    "产权交易": [
        {
            "module_name": "产权交易",
            "type": "3",
            "notice_type": "项目信息",
            "search_notice_type": "招标公告",
            "list_api": "homepage",
            "list_key": "str0",
        },
        {"module_name": "产权交易", "type": "3", "notice_type": "成交公告", "list_api": "homepage", "list_key": "prequalification"},
    ],
    "水利工程": [
        {"module_name": "水利工程", "type": "4", "notice_type": "招标公告", "list_api": "homepage", "list_key": "str0"},
        {"module_name": "水利工程", "type": "4", "notice_type": "评标结果公示", "list_api": "homepage", "list_key": "str4"},
        {"module_name": "水利工程", "type": "4", "notice_type": "中标结果通知", "list_api": "homepage", "list_key": "str1"},
    ],
    "铁路工程": [
        {"module_name": "铁路工程", "type": "5", "notice_type": "招标公告", "list_api": "homepage", "list_key": "str0"},
        {
            "module_name": "铁路工程",
            "type": "5",
            "notice_type": "预中标公告",
            "search_notice_type": "中标公告",
            "list_api": "homepage",
            "list_key": "str4",
        },
        {"module_name": "铁路工程", "type": "5", "notice_type": "中标公告", "list_api": "homepage", "list_key": "str1"},
    ],
    "交通工程": [
        {"module_name": "交通工程", "type": "6", "notice_type": "招标公告", "list_api": "homepage", "list_key": "str0"},
        {"module_name": "交通工程", "type": "6", "notice_type": "中标候选人公示", "list_api": "homepage", "list_key": "str4"},
        {"module_name": "交通工程", "type": "6", "notice_type": "中标结果公告", "list_api": "homepage", "list_key": "str1"},
    ],
    "园林绿化工程": [
        {
            "module_name": "园林绿化工程",
            "type": "7",
            "notice_type": "招标公告",
            "list_api": "homepage",
            "list_key": "str0",
            "subheading": "城乡绿化",
        },
        {
            "module_name": "园林绿化工程",
            "type": "7",
            "notice_type": "中标候选人公示",
            "list_api": "homepage",
            "list_key": "str4",
            "subheading": "城乡绿化",
        },
        {
            "module_name": "园林绿化工程",
            "type": "7",
            "notice_type": "中标结果公告",
            "list_api": "homepage",
            "list_key": "str1",
            "subheading": "城乡绿化",
        },
    ],
    "排污权交易": [
        {"module_name": "排污权交易", "type": "13", "notice_type": "挂牌公告", "list_api": "homepage", "list_key": "str0"},
        {"module_name": "排污权交易", "type": "13", "notice_type": "成交公告", "list_api": "homepage", "list_key": "str1"},
    ],
    "国有企业采购": [
        {
            "module_name": "国有企业采购",
            "type": "9",
            "notice_type": "采购公告",
            "list_api": "soa",
            "list_key": "procurementHtml",
            "soa_type": "2",
        },
        {
            "module_name": "国有企业采购",
            "type": "9",
            "notice_type": "中标公告",
            "list_api": "soa",
            "list_key": "winHtml",
            "soa_type": "1",
        },
    ],
    "农村产权": [
        {
            "module_name": "农村产权",
            "type": "10",
            "notice_type": "挂牌项目",
            "list_api": "agriculture",
            "list_key": "agriculturalListing",
            "agriculture_type": "1",
        },
        {
            "module_name": "农村产权",
            "type": "10",
            "notice_type": "成交公告",
            "list_api": "agriculture",
            "list_key": "agriculturalDealAnnouncemen",
            "agriculture_type": "2",
        },
    ],
    "其他项目": [
        {"module_name": "其他项目", "type": "11", "notice_type": "招标公告", "list_api": "homepage", "list_key": "str0"},
        {
            "module_name": "其他项目",
            "type": "11",
            "notice_type": "预中标公告",
            "search_type": "7",
            "search_notice_type": "中标候选人公示",
            "list_api": "homepage",
            "list_key": "str4",
        },
        {
            "module_name": "其他项目",
            "type": "11",
            "notice_type": "中标公告",
            "search_type": "7",
            "search_notice_type": "中标公告",
            "list_api": "homepage",
            "list_key": "str1",
        },
    ],
    "电力、新能源工程": [
        {"module_name": "电力、新能源工程", "type": "15", "notice_type": "招标公告", "list_api": "homepage", "list_key": "str0"},
        {
            "module_name": "电力、新能源工程",
            "type": "15",
            "notice_type": "预中标公告",
            "search_notice_type": "中标候选人公示",
            "list_api": "homepage",
            "list_key": "str4",
        },
        {"module_name": "电力、新能源工程", "type": "15", "notice_type": "中标公告", "list_api": "homepage", "list_key": "str1"},
    ],
}

# 少数栏目优先走首页接口，其余栏目统一切到 search.do 分页链路。
HOMEPAGE_ONLY_TASKS = {
    ("农村产权", "挂牌项目"),
    ("农村产权", "成交公告"),
}

for _module_name, _tasks in MODULE_TASKS.items():
    for _task in _tasks:
        if _task.get("list_api") == "homepage" and (_module_name, _task["notice_type"]) not in HOMEPAGE_ONLY_TASKS:
            _task["list_api"] = "search"

SITE_CONTEXT = {
    "city_id": "370100",
    "city_name": "济南市",
    "province_code": "370000",
    "province_name": "山东省",
    "web_source": "济南公共资源交易中心",
}

PARENT_TYPE_MAPPING = {
    "建设工程": "工程建设",
    "政府采购": "政府采购",
    "土地矿产": "土地矿产",
    "产权交易": "产权交易",
    "水利工程": "工程建设",
    "铁路工程": "工程建设",
    "交通工程": "工程建设",
    "园林绿化工程": "工程建设",
    "排污权交易": "排污权交易",
    "国有企业采购": "国有企业采购",
    "农村产权": "农村产权",
    "其他项目": "其他项目",
    "电力、新能源工程": "工程建设",
}

PROJECT_CLASSIFICATION_MAPPING = {
    "建设工程": "[2]",
    "政府采购": "[5]",
    "土地矿产": "[5]",
    "产权交易": "[5]",
    "水利工程": "[2]",
    "铁路工程": "[2]",
    "交通工程": "[2]",
    "园林绿化工程": "[2]",
    "排污权交易": "[5]",
    "国有企业采购": "[5]",
    "农村产权": "[5]",
    "其他项目": "[5]",
    "电力、新能源工程": "[2]",
}

RESULT_NOTICE_KEYWORDS = ("中标", "成交", "结果", "候选")
# 页面显示名和最终输出板块名的映射，统一收敛成客户模板的四类。
NOTICE_BOARD_MAPPING = {
    "中标结果公告": "中标公告",
    "中标公告": "中标公告",
    "成交公告": "中标公告",
    "结果公告": "中标公告",
    "结果公示": "中标公告",
    "中标结果通知": "中标公告",
    "招标公告": "招标公告",
    "采购公告": "招标公告",
    "项目信息": "招标公告",
    "挂牌公告": "招标公告",
    "挂牌项目": "招标公告",
    "竞价公告": "招标公告",
    "竞拍公告": "招标公告",
    "采购意向": "采购意向",
    "采购意向公告": "采购意向",
    "意向公开": "采购意向",
    "中标候选人": "候选人公告",
    "候选人公示": "候选人公告",
    "候选人公告": "候选人公告",
    "中标候选人公示": "候选人公告",
    "预中标公告": "候选人公告",
    "评标结果公示": "候选人公告",
}
REQUIRED_NOTICE_BOARDS = ("中标公告", "招标公告", "采购意向", "候选人公告")
SUPPORTED_NOTICE_BOARDS = REQUIRED_NOTICE_BOARDS
CUSTOM_MODEL_TOKEN = "FACBED0693D0F2361DED36C4BDF35E19"
CUSTOM_MODEL_NAME = "qwen-doc-turbo"


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str) and value.strip().lower() in {"none", "null"}:
        return ""
    text = unescape(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_html_tags(value: str) -> str:
    return normalize_text(TAG_PATTERN.sub("", value))


def is_attachment_anchor(href: str, text: str = "") -> bool:
    href_lower = href.lower()
    text_value = normalize_text(text)
    file_suffixes = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".7z")
    if any(suffix in href_lower for suffix in file_suffixes):
        return True
    if any(keyword in href_lower for keyword in ("download", "attach", "file", "fj")):
        return True
    return text_value.startswith("PDF版招标文件")


def is_html_noise_text(text: str) -> bool:
    value = normalize_text(text)
    lower_value = value.lower()
    if not value:
        return False
    # 发布信息是客户要求保留的底部元数据，不能被附件区清理误伤。
    if any(marker in value for marker in HTML_KEEP_TEXT_MARKERS):
        return False
    if value.startswith("当前位置"):
        return True
    if value in HTML_NOISE_EXACT_TEXTS:
        return True
    if any(lower_value.startswith(prefix.lower()) for prefix in HTML_NOISE_PREFIXES):
        return True
    if HTML_CA_HELP_URL in lower_value:
        return True
    return lower_value.startswith("http") and HTML_TRADE_LOGIN_PATH in lower_value


def make_visible_if_hidden(tag: Any) -> None:
    if getattr(tag, "attrs", None) is None:
        return
    style = str(tag.get("style", ""))
    if style:
        updated_style = re.sub(r"display\s*:\s*none\s*;?", "", style, flags=re.I)
        updated_style = re.sub(r"visibility\s*:\s*hidden\s*;?", "", updated_style, flags=re.I)
        updated_style = re.sub(r"\s{2,}", " ", updated_style).strip(" ;")
        if updated_style:
            tag["style"] = updated_style
        elif "style" in tag.attrs:
            del tag.attrs["style"]
    if "hidden" in tag.attrs:
        del tag.attrs["hidden"]
    classes = tag.get("class", [])
    if isinstance(classes, list) and classes:
        filtered = [item for item in classes if str(item).lower() != "hide"]
        if filtered:
            tag["class"] = filtered
        elif "class" in tag.attrs:
            del tag.attrs["class"]


def is_noise_only_tag(tag: Any) -> bool:
    text = normalize_text(tag.get_text("", strip=True))
    if not text:
        return False
    if not (text.startswith("尊敬的用户您好！") or is_html_noise_text(text)):
        return False

    # 只删除纯提示节点，避免把同时包着正文的大容器整块误删。
    block_descendants = tag.find_all(["div", "table", "ul", "ol", "section", "article"], recursive=False)
    if block_descendants:
        return False
    return True


def extract_nested_notice_document(html: str) -> str:
    html_positions = [match.start() for match in re.finditer(r"<html\b", html, flags=re.I)]
    if len(html_positions) < 2:
        return html
    should_extract = re.search(r"\$\(\s*0\s*,\s*#cadata\d+\s*\)", html, flags=re.I) is not None
    second_html_pos = html_positions[1]
    if not should_extract:
        shell_prefix = html[:second_html_pos]
        should_extract = (
            "链接地址" in shell_prefix
            or "gtqrlj" in shell_prefix
            or 'class="table2"' in shell_prefix
            or "class='table2'" in shell_prefix
        )
    if not should_extract:
        return html

    nested_html = html[second_html_pos:]
    end = nested_html.rfind("</html>")
    if end == -1:
        return html
    nested_html = nested_html[: end + len("</html>")]
    # 这类嵌套页里经常混着模板占位符，直接交给后续清理逻辑前先抹掉。
    nested_html = re.sub(r"\$\(\s*0\s*,\s*#cadata\d+\s*\)", "", nested_html, flags=re.I)
    nested_html = re.sub(r"\$\(\s*0\s*,\s*#caid\d+\s*\)", "", nested_html, flags=re.I)
    return nested_html


def clean_html_content(html: str) -> str:
    # htmlContent 只清理客户明确不要的导航、附件入口、跳转按钮；正文和发布信息尽量保持原样。
    html = extract_nested_notice_document(html)
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")

        for comment in soup.find_all(string=lambda text: Comment is not None and isinstance(text, Comment) and "关闭本页" in str(text)):
            comment.extract()

        for tag in soup.find_all(["script", "link"]):
            tag.decompose()

        for tag in soup.find_all(True):
            if tag.attrs is None:
                continue
            value = normalize_text(tag.get("value", ""))
            onclick = normalize_text(tag.get("onclick", ""))
            tag_class = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else str(tag.get("class", ""))
            if tag.name == "li" and "bggg" in tag_class and normalize_text(tag.get_text("", strip=True)) == "变更公告":
                tag.decompose()
                continue
            if value in {"澄清答疑", "我要参与"}:
                tag.decompose()
                continue
            if onclick.startswith("window.close") and normalize_text(tag.get_text("", strip=True)) == "关闭本页":
                tag.decompose()
                continue
            if "shows" in tag_class and "hide" in tag_class and tag.find(id="cqdyifram") is not None:
                tag.decompose()

        for anchor in soup.find_all("a"):
            if is_attachment_anchor(anchor.get("href", ""), anchor.get_text("", strip=True)):
                anchor.decompose()
            else:
                anchor.unwrap()

        candidate_names = ("p", "div", "li", "span", "td")
        for tag in list(soup.find_all(candidate_names)):
            if tag.attrs is None:
                continue
            if is_noise_only_tag(tag):
                tag.decompose()

        # 客户要的是反解后直接能看到正文，因此对仍保留的正文节点去掉隐藏属性。
        for tag in soup.find_all(True):
            if tag.attrs is None:
                continue
            text = normalize_text(tag.get_text("", strip=True))
            if not text:
                continue
            if is_html_noise_text(text):
                continue
            make_visible_if_hidden(tag)

        return str(soup).strip()

    # bs4 不可用时保留降级逻辑，但限定为常见小标签，避免从大容器误删到正文。
    cleaned = re.sub(r"""<script\b[^>]*>.*?</script>""", "", html, flags=re.I | re.S)
    cleaned = re.sub(r"""<link\b[^>]*?/?>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<p[^>]*>\s*尊敬的用户您好！.*?</p>", "", cleaned, flags=re.S)
    cleaned = re.sub(r"""<div\b[^>]*>\s*当前位置：.*?</div>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(
        r"""<a[^>]*href=['"][^'"]+\.(?:pdf|doc|docx|xls|xlsx|zip|rar|7z)[^'"]*['"][^>]*>.*?</a>""",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(
        r"""<a[^>]*href=['"][^'"]*(?:download|attach|file|fj)[^'"]*['"][^>]*>.*?</a>""",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(r"""https?://[^\s<>"']*(?:download|attach|file)[^\s<>"']*""", "", cleaned, flags=re.I)
    cleaned = re.sub(r"""[^\s<>"']*(?:download|attach|file)\.do\?[^\s<>"']*""", "", cleaned, flags=re.I)
    cleaned = re.sub(r"""</?a\b[^>]*>""", "", cleaned, flags=re.I)
    cleaned = re.sub(r"""<(?:p|div|li|span|td)\b[^>]*>\s*(?:附件：|相关附件：|请点击此处下载)\s*</(?:p|div|li|span|td)>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"""<(?:p|div|li|span|td)\b[^>]*>\s*PDF版招标文件.*?</(?:p|div|li|span|td)>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(
        r"""<(?:p|div|li|span|td)\b[^>]*>\s*请点击[“"]?我要参与[”"]?登录济南公共资源交易中心网站.*?</(?:p|div|li|span|td)>""",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(r"""<(?:p|div|li|span|td)\b[^>]*>\s*ca办理及相关咨询请点击.*?</(?:p|div|li|span|td)>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"""<(?:p|div|li|span|td)\b[^>]*>\s*https?://124\.128\.84\.51:9000/jnggzy/jnggzyca/index\.jsp#nav-7查看\s*</(?:p|div|li|span|td)>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"""<input\b[^>]*value=['"]澄清答疑['"][^>]*?/?>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"""<input\b[^>]*value=['"]我要参与['"][^>]*?/?>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"""<li\b[^>]*class=['"][^'"]*\bbggg\b[^'"]*['"][^>]*>\s*变更公告\s*</li>""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(
        r"""<div\b[^>]*class=['"][^'"]*\bshows\b[^'"]*\bhide\b[^'"]*['"][^>]*>.*?<iframe\b[^>]*id=['"]cqdyifram['"][^>]*>.*?</iframe>\s*</div>""",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(r"""<!--\s*关闭本页\s*-->""", "", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"""<span\b[^>]*onclick=['"]window\.close\(\);?['"][^>]*>\s*关闭本页\s*</span>""", "", cleaned, flags=re.I | re.S)
    return cleaned.strip()


def clean_procurement_unit(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    text = CONTACT_SUFFIX_PATTERN.sub("", text)
    return normalize_text(text)


def is_blank_notice_detail(task: dict[str, str], detail: dict[str, Any], detail_html: str) -> bool:
    module_name = str(task.get("module_name", ""))
    notice_type = str(task.get("notice_type", ""))
    blank_enabled_tasks = {
        ("土地矿产", "招标公告"),
        ("土地矿产", "结果公示"),
    }
    if (module_name, notice_type) not in blank_enabled_tasks:
        return False
    title = normalize_text(str(detail.get("title", "")))
    field_map = detail.get("field_map", {})
    result_rows = detail.get("result_rows", [])
    plain_text = normalize_text(str(detail.get("plain_text", "")))
    content_text = normalize_text(str(detail.get("content_text", "")))
    html_text = normalize_text(strip_html_tags(detail_html))
    meaningful_text = pick_first_non_empty([plain_text, content_text, html_text])
    if meaningful_text == "":
        return True
    if result_rows:
        return False

    raw_text = pick_first_non_empty([str(detail.get("plain_text", "")), str(detail.get("content_text", "")), strip_html_tags(detail_html)])
    normalized_lines = [
        normalize_text(line)
        for line in re.split(r"[\r\n]+", raw_text)
        if normalize_text(line)
    ]
    if not normalized_lines:
        return True

    boilerplate_patterns = [
        r"^公告详情$",
        r"^当前位置.*$",
        r"^首页$",
        r"^>.*$",
        r"^公共资源交易编号[:：].*$",
        r"^发布日期[:：].*$",
        r"^尊敬的用户您好.*$",
        r"^链接地址$",
        r"^关闭本页$",
        r"^澄清答疑$",
        r"^我要参与$",
    ]

    non_boilerplate_lines: list[str] = []
    for line in normalized_lines:
        if title and line == title:
            continue
        if any(re.match(pattern, line) for pattern in boilerplate_patterns):
            continue
        non_boilerplate_lines.append(line)

    has_structured_content = any(key for key in field_map.keys() if key not in {"公共资源交易编号", "发布日期"})
    if has_structured_content:
        return False
    return len(non_boilerplate_lines) == 0


def sanitize_field_name(label: str) -> str:
    name = normalize_text(label)
    name = name.replace("（", "(").replace("）", ")")
    name = re.sub(r"[：:]+$", "", name)
    replacements = {
        "项目编号(建议书编号)": "project_number",
        "项目编号": "project_number",
        "项目名称": "project_name",
        "采购方式": "procurement_method",
        "预算金额": "budget_amount",
        "采购需求": "procurement_requirements",
        "合同履行期限": "contract_period",
        "截止时间": "deadline",
        "项目联系人": "project_contact",
        "采购人名称": "procurement_unit",
        "采购单位": "procurement_unit",
        "采购人": "procurement_unit",
        "招标人": "procurement_unit",
        "招标单位": "procurement_unit",
        "建设单位": "procurement_unit",
        "转让方": "procurement_unit",
        "采购单位名称": "procurement_unit",
        "中标单位": "relation_company_name",
        "中标人": "relation_company_name",
        "成交供应商": "relation_company_name",
        "中标供应商名称": "relation_company_name",
        "供应商名称": "relation_company_name",
        "成交人": "relation_company_name",
        "第一中标候选人": "relation_company_name",
        "中标金额": "render_money",
        "中标金额(元)": "render_money",
        "中标价": "render_money",
        "中标信息": "render_money",
        "成交金额": "render_money",
        "成交价": "render_money",
        "投标报价": "render_money",
        "联系人": "contact_name",
        "联系人/联系电话": "contact_name",
        "联系电话": "contact_telephone",
        "联系方式": "contact_telephone",
    }
    if name in replacements:
        return replacements[name]

    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "_", name.lower()).strip("_")


def get_module_tasks(module_name: str) -> list[dict[str, str]]:
    if module_name in {"全部模块", "ALL", "*"}:
        tasks: list[dict[str, str]] = []
        for module_tasks in MODULE_TASKS.values():
            tasks.extend(task.copy() for task in module_tasks)
        return tasks
    tasks = MODULE_TASKS.get(module_name, [])
    return [task.copy() for task in tasks]


def filter_tasks_by_notice_type(tasks: list[dict[str, str]], notice_type: str) -> list[dict[str, str]]:
    normalized_notice_type = normalize_text(notice_type)
    if not normalized_notice_type:
        return tasks
    return [task for task in tasks if normalize_text(str(task.get("notice_type", ""))) == normalized_notice_type]


def build_detail_url(
    notice_id: str,
    notice_type: str,
    is_new: int,
    detail_path: str = "showNotice.do",
) -> str:
    return (
        f"https://jnggzy.jinan.gov.cn/jnggzyztb/front/{detail_path}"
        f"?iid={notice_id}&xuanxiang={quote(notice_type)}&isnew={is_new}"
    )


def get_default_detail_path(task: dict[str, str]) -> str:
    notice_type = str(task.get("notice_type", ""))
    if notice_type in {"评标结果公示", "中标候选人公示"}:
        return "showPreparationNotice.do"
    if any(keyword in notice_type for keyword in ("中标", "成交", "结果")):
        return "showResultNotice.do"
    return "showNotice.do"


def parse_search_response(payload: dict[str, Any], source_url: str) -> list[dict[str, Any]]:
    # 解析 search.do / soa / agriculture 这类接口返回的列表 html。
    if not payload.get("success"):
        raise ValueError("列表接口返回 success=false")

    html = str(payload.get("params", {}).get("str", ""))
    return parse_list_html(html, source_url)


def parse_search_total_pages(payload: dict[str, Any]) -> int | None:
    pagesum = payload.get("params", {}).get("pagesum")
    try:
        total_pages = int(str(pagesum).strip())
    except (TypeError, ValueError):
        return None
    return total_pages if total_pages > 0 else None


def parse_list_html(html: str, source_url: str) -> list[dict[str, Any]]:
    # 把列表页里的每个 li 解析成统一卡片结构，后面再进详情页。
    list_items = re.findall(r"<li>(.*?)</li>", html, flags=re.S)
    records: list[dict[str, Any]] = []
    for item_html in list_items:
        onclick_match = SHOWVIEW_PATTERN.search(item_html)
        href_match = re.search(r"""<a[^>]*href=['"]?([^'"\s>]+)""", item_html, flags=re.S)
        title_match = re.search(r"<a[^>]*title=['\"]([^'\"]*)['\"][^>]*>(.*?)</a>", item_html, flags=re.S)
        if title_match is None:
            title_match = re.search(r"<a[^>]*href=['\"]?[^>]+>(.*?)</a>", item_html, flags=re.S)
        date_match = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9]{2}:[0-9]{2}(?::[0-9]{2})?)?)", item_html)
        place_match = re.search(r"(?:class=['\"](?:span1|dq)['\"][^>]*>)\s*(?:\[)?(.*?)(?:\])?\s*</span>", item_html, flags=re.S)
        title = ""
        if title_match:
            title = normalize_text(title_match.group(1))
            if not title and title_match.lastindex and title_match.lastindex > 1:
                title = normalize_text(title_match.group(2))

        if onclick_match is None:
            if href_match is None:
                continue
            href = normalize_text(href_match.group(1))
            detail_url = urljoin(source_url, href)
            parsed = urlparse(detail_url)
            query = parse_qs(parsed.query)
            notice_id = pick_first_non_empty(
                [
                    query.get("iid", [""])[0],
                    query.get("pid", [""])[0],
                    query.get("proCode", [""])[0],
                    query.get("code", [""])[0],
                ]
            )
            records.append(
                {
                    "notice_id": notice_id,
                    "is_new": int(query.get("isnew", ["1"])[0] or 1),
                    "notice_type": query.get("xuanxiang", [""])[0],
                    "title": title,
                    "publish_date": normalize_text(date_match.group(1)) if date_match else "",
                    "trading_place": normalize_text(place_match.group(1)) if place_match else "",
                    "source_url": source_url,
                    "detail_url": detail_url,
                }
            )
            continue

        records.append(
            {
                "notice_id": onclick_match.group("notice_id"),
                "is_new": int(onclick_match.group("is_new")),
                "notice_type": normalize_text(onclick_match.group("notice_type") or ""),
                "title": title,
                "publish_date": normalize_text(date_match.group(1)) if date_match else "",
                "trading_place": normalize_text(place_match.group(1)) if place_match else "",
                "source_url": source_url,
            }
        )
    return records


def parse_notice_detail(html: str, detail_url: str) -> dict[str, Any]:
    # 解析详情页标题、字段对、表格结果和纯文本，尽量把能复用的信息都提出来。
    title_match = re.search(r"<h1>(.*?)</h1>", html, flags=re.S)
    resource_code_match = re.search(r"公共资源交易编号：\s*([^<\s]+)", html)
    publish_date_match = re.search(r"发布日期：\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", html)

    detail = {
        "title": normalize_text(title_match.group(1)) if title_match else "",
        "public_resource_code": normalize_text(resource_code_match.group(1)) if resource_code_match else "",
        "publish_date": normalize_text(publish_date_match.group(1)) if publish_date_match else "",
        "detail_url": detail_url,
        "field_map": {},
        "result_rows": [],
    }

    for match in FIELD_PAIR_PATTERN.finditer(html):
        label = strip_html_tags(match.group("label"))
        value = strip_html_tags(match.group("value"))
        normalized_label = normalize_text(label).replace("（", "(").replace("）", ")")
        normalized_label = re.sub(r"[：:]+$", "", normalized_label)
        detail["field_map"][normalized_label] = value
        field_name = sanitize_field_name(label)
        if field_name:
            detail[field_name] = value

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        plain_text = soup.get_text("\n", strip=True)
        detail["plain_text"] = plain_text
        if not detail["title"]:
            h1 = soup.find("h1")
            if h1:
                detail["title"] = normalize_text(h1.get_text(" ", strip=True))

        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [normalize_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["td", "th"])]
                cells = [cell for cell in cells if cell]
                if cells:
                    rows.append(cells)
            if not rows:
                continue

            header_row = rows[0]
            header_text = " ".join(header_row)
            if any(keyword in header_text for keyword in ("中标供应商名称", "供应商名称", "中标单位", "中标人", "成交供应商")):
                for data_row in rows[1:]:
                    if len(data_row) < 2:
                        continue
                    result_row: dict[str, str] = {}
                    for idx, header in enumerate(header_row):
                        if idx >= len(data_row):
                            continue
                        header_name = sanitize_field_name(header)
                        if header_name:
                            result_row[header_name] = data_row[idx]
                        result_row[header] = data_row[idx]
                    if result_row:
                        detail["result_rows"].append(result_row)

            for row in rows:
                if len(row) < 2:
                    continue
                if len(row) % 2 != 0:
                    continue
                for index in range(0, len(row), 2):
                    label = row[index]
                    value = row[index + 1]
                    if not label or not value:
                        continue
                    normalized_label = re.sub(r"[：:]+$", "", label.replace("（", "(").replace("）", ")"))
                    if normalized_label not in detail["field_map"]:
                        detail["field_map"][normalized_label] = value
                    field_name = sanitize_field_name(label)
                    if field_name and not detail.get(field_name):
                        detail[field_name] = value

        for label in [
            "采购人",
            "采购单位",
            "采购单位名称",
            "招标人",
            "招标单位",
            "建设单位",
            "转让方",
            "项目编号",
            "公共资源交易编号",
            "联系人",
            "联系电话",
            "联系方式",
            "中标单位",
            "中标人",
            "成交供应商",
            "中标供应商名称",
            "供应商名称",
            "中标金额",
            "中标金额(元)",
            "中标价",
            "成交金额",
            "成交价",
            "中标信息",
        ]:
            pattern = rf"{re.escape(label)}\s*[：:]\s*([^\n]+)"
            match = re.search(pattern, plain_text)
            if match:
                value = normalize_text(match.group(1))
                if value and label not in detail["field_map"]:
                    detail["field_map"][label] = value
                    field_name = sanitize_field_name(label)
                    if field_name and not detail.get(field_name):
                        detail[field_name] = value

    detail["content_text"] = strip_html_tags(html)
    return detail


def pick_first_non_empty(values: list[str]) -> str:
    for value in values:
        if value:
            return value
    return ""


def normalize_money(value: str) -> str:
    if not value:
        return ""
    clean_value = value.replace(",", "").strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", clean_value):
        return f"{clean_value}元"
    try:
        return MoneyParser().convert_amount(value)
    except Exception:
        return value


def extract_attachment_files(html: str, detail_url: str) -> list[dict[str, str]]:
    # 附件同时保留 URL 和页面展示标题，便于 uploadFileUrl / fileInfo 分开输出。
    files: list[dict[str, str]] = []
    for anchor_html, href in re.findall(r"""(<a\b[^>]*href=['"]([^'"]+)['"][^>]*>.*?</a>)""", html, flags=re.I | re.S):
        href = normalize_text(href)
        if not href:
            continue
        anchor_text = normalize_text(strip_html_tags(anchor_html))
        if re.search(r"(?:操作手册|操作说明|供应商下载采购文件)", href + anchor_text, flags=re.I):
            continue
        is_file_link = re.search(r"\.(pdf|doc|docx|xls|xlsx|zip|rar|7z)(?:$|[?#])", href, flags=re.I)
        is_file_api = re.search(r"(?:ztbpdfbybidguid|downloadfile|download\.do|attach|file)", href, flags=re.I)
        if not is_file_link and not is_file_api:
            continue
        url = urljoin(detail_url, href)
        file_name = anchor_text
        suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
        files.append(
            {
                "fileUrl": url,
                "fileType": suffix,
                "fileName": file_name,
            }
        )
    deduplicated: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in files:
        url = item.get("fileUrl", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduplicated.append(item)
    return deduplicated


def detect_union_flag(content_text: str) -> int:
    # 中标模板里的 isUnion 直接按正文关键词判断。
    if "不接受联合体" in content_text or "非联合体" in content_text:
        return 0
    if "联合体" in content_text:
        return 1
    return 0


def detect_union_flag_by_company_name(company_name: str) -> int:
    text = normalize_text(company_name)
    if not text:
        return 0
    return 1 if "," in text else 0


def get_parent_type(module_name: str) -> str:
    return module_name


def get_project_classification(module_name: str) -> str:
    return PROJECT_CLASSIFICATION_MAPPING.get(module_name, "[5]")


def get_announcement_type(notice_type_name: str) -> int:
    if any(keyword in notice_type_name for keyword in RESULT_NOTICE_KEYWORDS):
        return 2
    return 1


def get_notice_board(notice_type_name: str) -> str:
    # 把站点栏目名统一归并到客户模板的四个板块名。
    if notice_type_name in NOTICE_BOARD_MAPPING:
        return NOTICE_BOARD_MAPPING[notice_type_name]
    if "采购意向" in notice_type_name or "意向" in notice_type_name:
        return "采购意向"
    if "候选" in notice_type_name:
        return "候选人公告"
    if any(keyword in notice_type_name for keyword in ("中标", "成交", "结果")):
        return "中标公告"
    if "招标" in notice_type_name:
        return "招标公告"
    return ""


def get_required_notice_boards() -> tuple[str, ...]:
    return REQUIRED_NOTICE_BOARDS


def get_supported_notice_boards() -> tuple[str, ...]:
    return SUPPORTED_NOTICE_BOARDS


def get_homepage_list_source_url(base_url: str) -> str:
    return f"{base_url}/newChangeHomePageList.do"


def fill_if_empty(record: dict[str, Any], key: str, value: Any, normalize: bool = True) -> None:
    if record.get(key):
        return
    if value is None:
        return
    if isinstance(value, str):
        value = normalize_text(value) if normalize else value
    if value in ("", [], {}):
        return
    record[key] = value


def set_if_present(record: dict[str, Any], key: str, value: Any, normalize: bool = True) -> None:
    if value is None:
        return
    if isinstance(value, str):
        value = normalize_text(value) if normalize else value
    if value in ("", [], {}):
        return
    record[key] = value


def reset_fields(record: dict[str, Any], keys: list[str], empty_value: Any = "") -> None:
    for key in keys:
        record[key] = [] if empty_value == [] else {} if empty_value == {} else empty_value


def extract_prefixed_value(items: list[str], prefixes: tuple[str, ...]) -> str:
    for item in items:
        normalized_item = normalize_text(str(item))
        for prefix in prefixes:
            if normalized_item.startswith(prefix):
                return normalize_text(normalized_item[len(prefix) :])
    return ""


class CustomerModelClient:
    def __init__(self, endpoint: str, timeout: int = 30) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Test-Version": "v2",
            "Custom-Token": CUSTOM_MODEL_TOKEN,
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    def post_model(self, content: str) -> dict[str, Any]:
        # 客户提供的模型接口统一走这里发请求。
        response = requests.post(
            self.endpoint,
            json={"text": content, "model": CUSTOM_MODEL_NAME},
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return payload


class BidModelClient(CustomerModelClient):
    def __init__(self, timeout: int = 30) -> None:
        super().__init__("https://www.51qqx.com/extract/ask", timeout=timeout)

    def get_result(self, content: str) -> dict[str, Any]:
        # 招标模型返回后，统一转换成当前脚本内部使用的字段名。
        payload = self.post_model(content)
        result = payload.get("final_result")
        if not result:
            raw_result = payload.get("result", [])
            if isinstance(raw_result, list) and raw_result:
                result = raw_result[0]
        if not isinstance(result, dict):
            return {}
        consultation_info = {
            "purchasingInfor": [],
            "projectInfor": [],
        }
        procurement_method = normalize_text(str(result.get("采购方式", "") or ""))
        allowed_methods = {"单一来源", "邀请招标", "竞争性谈判", "询价", "竞争性磋商", "公开招标"}
        if procurement_method and procurement_method not in allowed_methods:
            procurement_method = "其他类型"
        if result.get("采购人名称"):
            consultation_info["purchasingInfor"].append(f"名称：{result['采购人名称']}")
        if result.get("项目联系人"):
            consultation_info["projectInfor"].append(f"项目联系人：{str(result['项目联系人']).replace('、', ',')}")
        if result.get("项目联系方式"):
            consultation_info["projectInfor"].append(f"电话：{str(result['项目联系方式']).replace('、', ',')}")
        return {
            "projectNum": result.get("项目编号", "") or "",
            "projectName": result.get("项目名称", "") or "",
            "budgetAmount": normalize_money(str(result.get("预算金额", "") or "").replace("（人民币）", "").replace("¥", "")),
            "procurementMethod": procurement_method,
            "releaseSource": result.get("采购人名称", "") or "",
            "purchaserAddress": result.get("采购人地址", "") or "",
            "consultationInfo": consultation_info,
        }


class TenderModelClient(CustomerModelClient):
    def __init__(self, timeout: int = 30) -> None:
        super().__init__("https://www.51qqx.com/extract/askTender", timeout=timeout)

    def get_result(self, content: str) -> dict[str, Any]:
        # 中标模型返回后，统一转换成当前脚本内部使用的字段名。
        payload = self.post_model(content)
        result = payload.get("final_result", payload.get("result"))
        if not isinstance(result, dict):
            return {}
        output_data = {
            "tenderTitle": result.get("项目名称", "") or "",
            "tenderNumber": result.get("项目编号", "") or "",
            "procurementUnit": result.get("采购人名称", "") or "",
            "result": [],
        }
        for item in result.get("采购结果", []):
            if not isinstance(item, dict):
                continue
            output_data["result"].append(
                {
                    "relationCompanyName": item.get("供应商名称", "") or "",
                    "contactName": item.get("联系人姓名", "") or "",
                    "contactTelephone": item.get("联系人电话", "") or "",
                    "renderMoney": normalize_money(str(item.get("中标金额", "") or "")),
                }
            )
        return output_data


class CandidateModelClient(CustomerModelClient):
    def __init__(self, timeout: int = 60) -> None:
        super().__init__("https://www.51qqx.com/extract/askHxr", timeout=timeout)

    def get_result(self, content: str) -> dict[str, Any]:
        # 候选人模型返回后，统一转换成当前脚本内部使用的字段名。
        payload = self.post_model(content)
        result: Any = payload.get("final_result")
        if not result:
            raw_result = payload.get("result")
            if isinstance(raw_result, list) and raw_result:
                first_item = raw_result[0]
                if isinstance(first_item, dict):
                    result = first_item.get("extract_result") or first_item
            elif isinstance(raw_result, dict):
                result = raw_result.get("extract_result") or raw_result
        if not isinstance(result, dict):
            return {}
        candidates: list[dict[str, Any]] = []
        for item in result.get("候选人结果", []):
            if not isinstance(item, dict):
                continue
            candidate_sort = item.get("候选人排序", [])
            if not isinstance(candidate_sort, list):
                candidate_sort = [candidate_sort] if candidate_sort else []
            candidates.append(
                {
                    "relationCompanyName": item.get("候选人名称", "") or "",
                    "candidateSort": candidate_sort,
                }
            )
        return {
            "tenderTitle": result.get("项目名称", "") or "",
            "procurementUnit": result.get("采购单位", "") or "",
            "extra": {"tenderNumber": result.get("项目编号", "") or ""},
            "result": candidates,
        }


def load_model_clients(enable_model_enrichment: bool, timeout_seconds: int) -> dict[str, Any]:
    # 按板块加载对应模型；关闭模型时直接返回空字典。
    if not enable_model_enrichment:
        return {}
    return {
        "招标公告": BidModelClient(timeout=timeout_seconds),
        "中标公告": TenderModelClient(timeout=timeout_seconds),
        "候选人公告": CandidateModelClient(timeout=max(timeout_seconds, 60)),
    }


def split_contact_bundle(value: str) -> tuple[str, str]:
    text = normalize_text(value)
    if not text:
        return "", ""
    match = re.search(r"(?P<name>[^/／]+)[/／]\s*(?P<phone>1\d{10}|0\d[\d\-]+)", text)
    if match:
        return normalize_text(match.group("name")), normalize_text(match.group("phone"))
    return "", ""


def extract_text_value(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.S)
        if match:
            value = normalize_text(match.group(1))
            if value:
                return value
    return ""


def normalize_datetime_text(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    return re.sub(r":00$", "", text)


def sync_requirement_alias_fields(record: dict[str, Any]) -> dict[str, Any]:
    # 当前不做别名扩展，直接保持客户模板字段。
    return record


def is_land_result_notice_task(task: dict[str, str]) -> bool:
    return str(task.get("module_name", "")) == "土地矿产" and str(task.get("notice_type", "")) == "结果公示"


def format_land_trade_money(value: Any, unit: str = "万元") -> str:
    text = normalize_text(str(value))
    if not text:
        return ""
    try:
        amount = float(text)
    except (TypeError, ValueError):
        return text
    if unit == "万元":
        amount = amount / 10000
    if amount.is_integer():
        amount_text = f"{int(amount):,}"
    else:
        integer_part, decimal_part = f"{amount:.4f}".split(".")
        amount_text = f"{int(integer_part):,}.{decimal_part}".rstrip("0").rstrip(".")
    return f"{amount_text}{unit}"


def build_land_plot_range_text(goods: dict[str, Any], down_key: str, flag_key: str, flag2_key: str, up_key: str, middle_label: str) -> str:
    down = normalize_text(str(goods.get(down_key, "")))
    flag = normalize_text(str(goods.get(flag_key, "")))
    flag2 = normalize_text(str(goods.get(flag2_key, "")))
    up = normalize_text(str(goods.get(up_key, "")))
    if not any([down, flag, flag2, up]):
        return ""
    equal_symbol = {
        ">=": "≥",
        "=": "=",
        "<=": "≤",
        "<": "<",
        ">": ">",
    }
    parts: list[str] = []
    if down:
        parts.append(down)
    if flag:
        parts.append(equal_symbol.get(flag, flag))
    if flag2:
        parts.append(f"{middle_label} {equal_symbol.get(flag2, flag2)}")
    if up:
        parts.append(up)
    return " ".join(parts)


def build_land_earnest_money_text(payload: dict[str, Any], goods: dict[str, Any]) -> str:
    earnest_list = payload.get("earnest", []) if isinstance(payload.get("earnest"), list) else []
    deposit_price = normalize_text(str(goods.get("deposit_price", "")))
    if not deposit_price:
        return ""
    if "元" in deposit_price:
        return deposit_price

    lines: list[str] = []
    for item in earnest_list:
        if not isinstance(item, dict):
            continue
        currency = normalize_text(str(item.get("currency", "")))
        amount = normalize_text(str(item.get("amount", "")))
        if not currency or not amount:
            continue
        if currency in {"CNY", "RMB"}:
            try:
                amount_value = int(float(deposit_price) * 10000)
                lines.append(f"人民币[{currency}]：{amount_value}元")
            except (TypeError, ValueError):
                continue
        else:
            lines.append(f"{currency}：{amount}")
    return "<br/>".join(lines)


def remove_row_if_all_empty(soup: Any, element_ids: list[str]) -> None:
    for element_id in element_ids:
        node = soup.find(id=element_id)
        if node is None:
            continue
        row = node.find_parent("tr")
        if row is None:
            continue
        text = normalize_text(row.get_text(" ", strip=True))
        if not text or all(not normalize_text(item.get_text(" ", strip=True)) for item in row.find_all(["td", "th"])):
            row.decompose()
            return


def append_html_fragment(node: Any, html_fragment: str) -> None:
    fragment_soup = BeautifulSoup(f"<div>{html_fragment}</div>", "html.parser")
    wrapper = fragment_soup.find("div")
    if wrapper is None:
        return
    node.clear()
    for child in wrapper.contents:
        node.append(child)


def build_land_result_notice_html(payload: dict[str, Any], outer_url: str, template_html: str = "") -> str:
    target = payload.get("target", {}) if isinstance(payload.get("target"), dict) else {}
    goods_list = payload.get("goods", []) if isinstance(payload.get("goods"), list) else []
    first_goods = goods_list[0] if goods_list and isinstance(goods_list[0], dict) else {}
    title = normalize_text(str(target.get("name", "")) or str(first_goods.get("target_name", "")))
    if not template_html:
        rows = [
            ("项目编号", str(target.get("no", "")) or str(first_goods.get("target_no", ""))),
            ("项目名称", title),
            ("类别", str(first_goods.get("business_name", ""))),
            ("交易方式", str(target.get("trans_type_label", "")) or str(target.get("trans_type_name", ""))),
            ("竞得人", str(target.get("trans_bidder", ""))),
            ("成交价", normalize_money(str(target.get("trans_price", "")))),
            ("成交时间", normalize_datetime_text(str(target.get("end_trans_time", "")))),
            ("转让方", str(target.get("organ_his_name", ""))),
            ("宗地位置", str(first_goods.get("address", ""))),
            ("宗地面积", str(first_goods.get("land_area", ""))),
            ("土地用途", str(first_goods.get("goods_use", ""))),
            ("年限", str(first_goods.get("use_years", ""))),
            ("原始链接", outer_url),
        ]
        row_html = []
        for label, value in rows:
            clean_value = normalize_text(value)
            if not clean_value:
                continue
            row_html.append(f"<tr><th>{label}</th><td>{clean_value}</td></tr>")
        table_html = "".join(row_html)
        return (
            "<html><head><meta charset=\"utf-8\"><title>公告详情</title></head>"
            "<body>"
            f"<h1>{title}</h1>"
            "<table border=\"1\" width=\"100%\">"
            f"{table_html}"
            "</table>"
            "</body></html>"
        )

    soup = BeautifulSoup(template_html, "html.parser")
    for tag in soup.find_all(["script", "link"]):
        tag.decompose()
    popup = soup.find(id="win")
    if popup is not None:
        popup.decompose()
    kuanginfo = soup.find(id="kuanginfo")
    if kuanginfo is not None:
        kuanginfo.decompose()

    main_wrap = soup.find("div", class_="wrap")
    if main_wrap is None:
        return template_html

    body = soup.body
    if body is not None:
        body.clear()
        body.append(main_wrap)

    project_number = normalize_text(str(first_goods.get("goods_no", "")) or str(target.get("no", "")))

    values = {
        "notice_xh": f"(公告序号：{normalize_text(str(target.get('notice_xh', '')))})" if normalize_text(str(target.get("notice_xh", ""))) else "",
        "top_id": f"<li class=\"hot\">{project_number}</li>" if project_number else "",
        "goods_no": project_number,
        "goods_name": normalize_text(str(first_goods.get("goods_name", "")) or title),
        "business_name": normalize_text(str(first_goods.get("business_name", ""))),
        "trans_type": "网上挂牌" if str(first_goods.get("trans_type", "")) == "0" else "网上拍卖",
        "land_area": normalize_text(str(first_goods.get("land_area", ""))),
        "address": normalize_text(str(first_goods.get("address", ""))),
        "use_years": normalize_text(str(first_goods.get("use_years", ""))),
        "develop": normalize_text(str(first_goods.get("develop", ""))),
        "apply_time": "",
        "list_time": "",
        "begin_price": "",
        "price_step": "",
        "end_earnest_time": normalize_datetime_text(str(first_goods.get("end_earnest_time", ""))),
        "earnest_money": build_land_earnest_money_text(payload, first_goods),
        "target_maxprice_label": "",
        "target_maxprice": "",
        "th_crj": "",
        "crj_yjk": "",
        "th_zje": "",
        "yj_zje": "",
        "allow_union": "允许联合竞买" if str(first_goods.get("allow_union", "")) == "1" else "不允许联合竞买",
        "end_trans_time": normalize_datetime_text(str(first_goods.get("end_list_time", ""))),
        "trans_bidder": normalize_text(str(target.get("trans_bidder", ""))),
        "trans_price": "",
        "trans_time": normalize_datetime_text(str(target.get("end_trans_time", ""))),
        "goods_use": normalize_text(str(first_goods.get("goods_use", ""))),
        "build_height": normalize_text(str(first_goods.get("build_height", ""))),
        "plot1": build_land_plot_range_text(first_goods, "plot1_down", "plot1_flag", "plot1_flag2", "plot1_up", "地上容积率"),
        "plot2": build_land_plot_range_text(first_goods, "plot2_down", "plot2_flag", "plot2_flag2", "plot2_up", "地下容积率"),
        "build_density": build_land_plot_range_text(first_goods, "build_density_down", "build_density_flag", "build_density_flag2", "build_density_up", "建筑密度"),
        "green_ratio": build_land_plot_range_text(first_goods, "green_ratio_down", "green_ratio_flag", "green_ratio_flag2", "green_ratio_up", "绿化率"),
        "remark": normalize_text(str(first_goods.get("remark", ""))),
        "otherCondition": normalize_text(str(first_goods.get("otherCondition", ""))),
    }

    begin_apply_time = normalize_datetime_text(str(first_goods.get("begin_apply_time", "")))
    end_apply_time = normalize_datetime_text(str(first_goods.get("end_apply_time", "")))
    if begin_apply_time or end_apply_time:
        values["apply_time"] = f"{begin_apply_time} 至 {end_apply_time}".strip(" 至")
    begin_list_time = normalize_datetime_text(str(first_goods.get("begin_list_time", "")))
    end_list_time = normalize_datetime_text(str(first_goods.get("end_list_time", "")))
    if begin_list_time or end_list_time:
        values["list_time"] = f"{begin_list_time} 至 {end_list_time}".strip(" 至")

    unit = normalize_text(str(target.get("unit", ""))) or "万元"
    begin_price = format_land_trade_money(first_goods.get("begin_price") or target.get("begin_price"), unit)
    begin_above = normalize_text(str(first_goods.get("goods_begin_price_above", "")))
    begin_under = normalize_text(str(first_goods.get("goods_begin_price_under", "")))
    begin_parts: list[str] = []
    if begin_above:
        begin_parts.append(f"地上价格: {begin_above}万元")
    if begin_under:
        begin_parts.append(f"地下价格:{begin_under}万元")
    values["begin_price"] = begin_price + (f"（{','.join(begin_parts)}）" if begin_parts else "")
    values["price_step"] = format_land_trade_money(first_goods.get("price_step"), unit)

    trans_price = format_land_trade_money(first_goods.get("trans_goods_price") or target.get("trans_price"), unit)
    trans_above = normalize_text(str(first_goods.get("trans_goods_price_above", "")))
    trans_under = normalize_text(str(first_goods.get("trans_goods_price_under", "")))
    trans_parts: list[str] = []
    if trans_above:
        trans_parts.append(f"地上价格:{trans_above}万元")
    if trans_under:
        trans_parts.append(f"地下价格:{trans_under}万元")
    values["trans_price"] = trans_price + (f"({','.join(trans_parts)})" if trans_parts else "")
    values["target_maxprice_label"] = "最高价:"
    values["target_maxprice"] = format_land_trade_money(first_goods.get("trans_goods_price"), unit).replace("万元", "&nbsp;万元")

    if normalize_text(str(target.get("crjyjkhz", ""))) not in {"", "0"}:
        values["th_crj"] = "出让金预交款："
        values["th_zje"] = "缴纳总金额："

    for element_id, value in values.items():
        node = soup.find(id=element_id)
        if node is None:
            continue
        if element_id == "top_id":
            node.clear()
            if value:
                li_soup = BeautifulSoup(value, "html.parser")
                for child in li_soup.contents:
                    node.append(child)
            continue
        if element_id in {"earnest_money", "target_maxprice", "crj_yjk", "yj_zje"} and value:
            append_html_fragment(node, str(value))
            continue
        node.clear()
        if value:
            node.append(value)

    title_node = soup.find("span", id="notice_xh")
    if title_node is not None:
        title_container = title_node.parent
        if title_container is not None and title:
            title_text_span = soup.new_tag("span")
            title_text_span.string = title
            title_container.insert(0, title_text_span)
            title_container.insert(1, soup.new_string(" "))

    img_bag = soup.find(id="img_bag")
    if img_bag is not None:
        code_block = soup.new_tag("div")
        code_block["style"] = "margin: 10px 0 14px; font-size: 16px; color: #333; font-weight: bold;"
        code_block.string = f"项目编号：{project_number}" if project_number else ""
        img_bag.replace_with(code_block)

    link_tip = soup.find(string=lambda text: isinstance(text, str) and "原始链接" in text)
    if link_tip is None:
        footer = soup.new_tag("p")
        footer.string = f"原始链接：{outer_url}"
        main_wrap.append(footer)

    if not values["th_crj"] and not values["crj_yjk"] and not values["th_zje"] and not values["yj_zje"]:
        remove_row_if_all_empty(soup, ["th_crj", "crj_yjk", "th_zje", "yj_zje"])
    if not normalize_text(values["target_maxprice"]):
        remove_row_if_all_empty(soup, ["target_maxprice_label", "target_maxprice"])
    if not normalize_text(values["earnest_money"]):
        remove_row_if_all_empty(soup, ["earnest_money"])
    remove_row_if_all_empty(soup, ["goods_final_price"])
    remove_row_if_all_empty(soup, ["final_house_price"])
    return str(soup)


def build_land_result_notice_detail(payload: dict[str, Any], outer_url: str, template_html: str = "") -> tuple[dict[str, Any], str]:
    target = payload.get("target", {}) if isinstance(payload.get("target"), dict) else {}
    goods_list = payload.get("goods", []) if isinstance(payload.get("goods"), list) else []
    first_goods = goods_list[0] if goods_list and isinstance(goods_list[0], dict) else {}
    title = normalize_text(str(target.get("name", "")) or str(first_goods.get("target_name", "")))
    project_number = normalize_text(str(target.get("no", "")) or str(first_goods.get("target_no", "")))
    procurement_unit = normalize_text(str(target.get("organ_his_name", "")))
    relation_company_name = normalize_text(str(target.get("trans_bidder", "")))
    render_money = normalize_money(str(target.get("trans_price", "")))
    render_date = normalize_datetime_text(str(target.get("end_trans_time", "")))
    render_type = normalize_text(str(first_goods.get("business_name", "")))
    field_map = {
        "项目编号": project_number,
        "项目名称": title,
        "类别": render_type,
        "交易方式": normalize_text(str(target.get("trans_type_label", "")) or str(target.get("trans_type_name", ""))),
        "竞得人": relation_company_name,
        "成交价": render_money,
        "成交时间": render_date,
        "转让方": procurement_unit,
        "宗地位置": normalize_text(str(first_goods.get("address", ""))),
        "宗地面积": normalize_text(str(first_goods.get("land_area", ""))),
        "土地用途": normalize_text(str(first_goods.get("goods_use", ""))),
        "年限": normalize_text(str(first_goods.get("use_years", ""))),
    }
    field_map = {key: value for key, value in field_map.items() if value}
    detail_html = build_land_result_notice_html(payload, outer_url, template_html=template_html)
    plain_text = "\n".join(f"{key}：{value}" for key, value in field_map.items())
    detail = {
        "title": title,
        "public_resource_code": project_number,
        "publish_date": "",
        "detail_url": outer_url,
        "field_map": field_map,
        "result_rows": [],
        "plain_text": plain_text,
        "content_text": plain_text,
        "project_number": project_number,
        "project_name": title,
        "procurement_unit": procurement_unit,
        "relation_company_name": relation_company_name,
        "render_money": render_money,
        "render_date": render_date,
        "render_type": render_type,
    }
    return detail, detail_html


def build_file_info(attachment_files: list[dict[str, str]]) -> list[dict[str, str]]:
    # 文件模板统一转成 fileUrl / fileType / fileName 三段式。
    file_info: list[dict[str, str]] = []
    for item in attachment_files:
        url = normalize_text(str(item.get("fileUrl", "")))
        if not url:
            continue
        path = urlparse(url).path
        fallback_name = Path(path).name
        file_name = normalize_text(str(item.get("fileName", ""))) or fallback_name
        suffix = normalize_text(str(item.get("fileType", ""))) or Path(file_name).suffix.lower().lstrip(".")
        file_info.append(
            {
                "fileUrl": url,
                "fileType": suffix,
                "fileName": file_name,
            }
        )
    return file_info


def build_consultation_info(procurement_unit: str, contact_name: str, contact_telephone: str) -> dict[str, list[str]]:
    # 招标模板里的 consultationInfo 固定整理成采购人信息和项目联系信息两组。
    purchasing_info: list[str] = []
    project_info: list[str] = []
    if procurement_unit:
        purchasing_info.append(f"名称：{procurement_unit}")
    if contact_name:
        project_info.append(f"项目联系人：{contact_name}")
    if contact_telephone:
        project_info.append(f"电话：{contact_telephone}")
    return {
        "purchasingInfor": purchasing_info,
        "projectInfo": project_info,
    }


def build_common_context(
    card: dict[str, Any],
    detail: dict[str, Any],
    detail_html: str,
    task: dict[str, str],
    crawl_time: str,
) -> dict[str, Any]:
    # 统一抽取详情页里后续模板会复用的公共字段。
    field_map = detail.get("field_map", {})
    result_rows = detail.get("result_rows", [])
    first_result_row = result_rows[0] if result_rows else {}
    plain_text = str(detail.get("plain_text", ""))
    # 采购单位优先从结构化字段取，取不到再从正文正则兜底。
    text_procurement_unit = extract_text_value(
        plain_text,
        [
            r"采购人信息\s*名\s*称[：:]\s*([^\n]+)",
            r"采购人名称[：:]\s*([^\n]+)",
            r"采购单位[：:]\s*([^\n]+)",
            r"招标单位[：:]\s*([^\n]+)",
            r"招标人[：:]\s*([^\n]+)",
            r"建设单位[：:]\s*([^\n]+)",
            r"转让方[：:]\s*([^\n]+)",
        ],
    )
    procurement_unit = clean_procurement_unit(
        pick_first_non_empty(
        [
            str(detail.get("procurement_unit", "")),
            text_procurement_unit,
            str(field_map.get("采购人名称", "")),
            str(field_map.get("采购单位", "")),
            str(field_map.get("采购单位名称", "")),
            str(field_map.get("采购人", "")),
            str(field_map.get("招标人", "")),
            str(field_map.get("招标单位", "")),
            str(field_map.get("建设单位", "")),
            str(field_map.get("转让方", "")),
        ]
        )
    )
    # 中标/候选人名称优先取结构化字段，再从结果表第一行兜底。
    relation_company_name = pick_first_non_empty(
        [
            str(detail.get("relation_company_name", "")),
            str(field_map.get("竞得人", "")),
            str(field_map.get("中标单位", "")),
            str(field_map.get("中标人", "")),
            str(field_map.get("成交供应商", "")),
            str(field_map.get("中标供应商名称", "")),
            str(field_map.get("供应商名称", "")),
            str(field_map.get("成交人", "")),
            str(field_map.get("第一中标候选人", "")),
            str(first_result_row.get("relation_company_name", "")),
            str(first_result_row.get("中标供应商名称", "")),
            str(first_result_row.get("供应商名称", "")),
            str(first_result_row.get("中标单位", "")),
        ]
    )
    # 金额统一做规范化，避免纯数字和中文金额格式不一致。
    render_money = normalize_money(
        pick_first_non_empty(
            [
                str(detail.get("render_money", "")),
                str(field_map.get("成交价", "")),
                str(field_map.get("中标金额", "")),
                str(field_map.get("中标金额(元)", "")),
                str(field_map.get("中标价", "")),
                str(field_map.get("成交金额", "")),
                str(field_map.get("成交价", "")),
                str(field_map.get("中标信息", "")),
                str(field_map.get("投标报价", "")),
                str(first_result_row.get("render_money", "")),
                str(first_result_row.get("中标金额(元)", "")),
                str(first_result_row.get("中标金额", "")),
            ]
        )
    )
    # 联系人和联系电话优先拆结构化字段，再从正文里提。
    bundled_contact_name, bundled_contact_phone = split_contact_bundle(str(field_map.get("联系人/联系电话", "")))
    text_contact_name = extract_text_value(
        plain_text,
        [
            r"项目联系方式[：:]\s*项目联系人[：:]\s*([^\n]+)",
            r"项目联系人[：:]\s*([^\n]+)",
            r"建设单位联系人[：:]\s*([^\n]+)",
            r"招标单位联系人[：:]\s*([^\n]+)",
            r"联系人[：:]\s*([^\n]+)",
        ],
    )
    text_contact_phone = extract_text_value(
        plain_text,
        [
            r"项目联系方式[：:]\s*(?:项目联系人[：:]\s*[^\n]+\s*)?电\s*话[：:]\s*([0-9\-]+)",
            r"项目联系方式[：:]\s*(?:项目联系人[：:]\s*[^\n]+\s*)?联系方式[：:]\s*([0-9\-]+)",
            r"建设单位联系电话[：:]\s*([0-9\-]+)",
            r"招标单位联系电话[：:]\s*([0-9\-]+)",
            r"电\s*话[：:]\s*([0-9\-]+)",
            r"联系电话[：:]\s*([0-9\-]+)",
            r"联系方式[：:]\s*([0-9\-]+)",
        ],
    )
    contact_name = pick_first_non_empty(
        [
            str(detail.get("contact_name", "")),
            text_contact_name,
            str(field_map.get("联系人", "")),
            str(field_map.get("项目联系人", "")),
            bundled_contact_name,
        ]
    )
    contact_telephone = pick_first_non_empty(
        [
            str(detail.get("contact_telephone", "")),
            text_contact_phone,
            str(field_map.get("联系电话", "")),
            str(field_map.get("联系方式", "")),
            str(field_map.get("项目联系方式", "")),
            bundled_contact_phone,
        ]
    )
    # 标题、编号、预算、方式、发布日期这些字段后续会被不同模板复用。
    tender_number = pick_first_non_empty(
        [
            str(detail.get("project_number", "")),
            str(detail.get("public_resource_code", "")),
            str(field_map.get("项目编号", "")),
            str(field_map.get("项目编号(建议书编号)", "")),
            str(field_map.get("公共资源交易编号", "")),
        ]
    )
    tender_title = pick_first_non_empty(
        [
            str(detail.get("project_name", "")),
            str(detail.get("title", "")),
            str(card.get("title", "")),
        ]
    )
    budget_amount = normalize_money(
        pick_first_non_empty(
            [
                str(detail.get("budget_amount", "")),
                str(field_map.get("预算金额", "")),
            ]
        )
    )
    procurement_method = pick_first_non_empty(
        [
            str(detail.get("procurement_method", "")),
            str(field_map.get("采购方式", "")),
        ]
    )
    render_date = normalize_datetime_text(
        pick_first_non_empty(
        [
            str(detail.get("render_date", "")),
            str(field_map.get("成交时间", "")),
            str(detail.get("publish_date", "")),
            str(card.get("publish_date", "")),
        ]
        )
    )
    content_text = pick_first_non_empty(
        [
            str(detail.get("plain_text", "")),
            str(detail.get("content_text", "")),
        ]
    )
    detail_url = str(detail.get("detail_url", ""))
    notice_board = get_notice_board(task["notice_type"])
    # 附件、文件对象、额外信息统一在公共上下文里先准备好。
    attachment_files = extract_attachment_files(detail_html, detail_url)
    attachment_urls = [item["fileUrl"] for item in attachment_files if item.get("fileUrl")]
    consultation_info = build_consultation_info(procurement_unit, contact_name, contact_telephone)
    extra_info = {
        "publicResourceCode": str(detail.get("public_resource_code", "")),
        "tradingPlace": str(card.get("trading_place", "")),
        "moduleName": task["module_name"],
        "noticeTypeName": task["notice_type"],
    }
    extra_info = {key: value for key, value in extra_info.items() if value}
    html_content = base64.b64encode(clean_html_content(detail_html).encode("utf-8")).decode("utf-8")
    file_info = build_file_info(attachment_files)
    return {
        "field_map": field_map,
        "result_rows": result_rows,
        "plain_text": plain_text,
        "procurement_unit": procurement_unit,
        "relation_company_name": relation_company_name,
        "render_money": render_money,
        "contact_name": contact_name,
        "contact_telephone": contact_telephone,
        "tender_number": tender_number,
        "tender_title": tender_title,
        "budget_amount": budget_amount,
        "procurement_method": procurement_method,
        "render_date": render_date,
        "render_type": pick_first_non_empty([str(detail.get("render_type", "")), str(field_map.get("类别", ""))]),
        "content_text": content_text,
        "detail_url": detail_url,
        "notice_board": notice_board,
        "attachment_urls": attachment_urls,
        "file_info": file_info,
        "consultation_info": consultation_info,
        "extra_info": extra_info,
        "html_content": html_content,
        "crawl_time": crawl_time,
        "card": card,
        "detail": detail,
        "task": task,
    }


def build_bid_record(context: dict[str, Any]) -> dict[str, Any]:
    # 招标公告模板：只输出客户 Excel 里的招标字段。
    task = context["task"]
    return {
        "provinceCode": str(SITE_CONTEXT["province_code"]),
        "regionCode": str(SITE_CONTEXT["city_id"]),
        "regionName": SITE_CONTEXT["city_name"],
        "bidType": "",
        "announcementTitle": context["tender_title"],
        "originalWebsiteAddress": context["detail_url"],
        "procurementMethod": context["procurement_method"],
        "parentType": get_parent_type(task["module_name"]),
        "announcementType": task["notice_type"],
        "projectNum": context["tender_number"],
        "projectName": context["tender_title"],
        "budgetAmount": context["budget_amount"],
        "releaseSource": context["procurement_unit"],
        "releaseTime": context["render_date"],
        "consultationInfo": context["consultation_info"],
        "fileInfo": context["file_info"],
        "contentType": 1,
        "htmlContent": context["html_content"],
        "webSource": SITE_CONTEXT["web_source"],
    }


def build_win_record(context: dict[str, Any]) -> dict[str, Any]:
    # 中标公告模板：只输出客户 Excel 里的中标字段。
    task = context["task"]
    return {
        "tenderTitle": context["tender_title"],
        "tenderNumber": context["tender_number"],
        "cityId": SITE_CONTEXT["city_id"],
        "cityName": SITE_CONTEXT["city_name"],
        "renderMoney": context["render_money"],
        "renderDate": context["render_date"],
        "renderType": context["render_type"],
        "procurementUnit": context["procurement_unit"],
        "relationCompanyName": context["relation_company_name"],
        "uploadFileUrl": context["attachment_urls"],
        "provinceCode": SITE_CONTEXT["province_code"],
        "announcementType": get_announcement_type(task["notice_type"]),
        "originalWebsiteAddress": context["detail_url"],
        "projectClassification": "[5]",
        "tenderAdditionalInfoStr": "",
        "htmlContent": context["html_content"],
        "contentType": 1,
        "isUnion": detect_union_flag_by_company_name(context["relation_company_name"]),
        "contactName": context["contact_name"],
        "contactTelephone": context["contact_telephone"],
        "parentType": get_parent_type(task["module_name"]),
    }


def build_candidate_record(context: dict[str, Any]) -> dict[str, Any]:
    # 候选人公告模板：uploadFileUrl 保持为 list，元素是文件对象。
    task = context["task"]
    return {
        "tenderTitle": context["tender_title"],
        "renderDate": context["render_date"],
        "renderType": "中标候选人",
        "procurementUnit": context["procurement_unit"],
        "relationCompanyName": context["relation_company_name"],
        "uploadFileUrl": context["file_info"],
        "provinceCode": SITE_CONTEXT["province_code"],
        "provinceName": SITE_CONTEXT["province_name"],
        "cityId": SITE_CONTEXT["city_id"],
        "cityName": SITE_CONTEXT["city_name"],
        "announcementType": "候选人公告",
        "originalWebsiteAddress": context["detail_url"],
        "htmlContent": context["html_content"],
        "contentType": 1,
        "parentType": get_parent_type(task["module_name"]),
        "extra": {},
        "webSource": SITE_CONTEXT["web_source"],
    }


def build_procurement_intention_record(context: dict[str, Any]) -> dict[str, Any]:
    # 采购意向模板保留，但当前站点没有稳定可采入口，默认不启用。
    task = context["task"]
    extra = {
        "publicResourceCode": str(context["detail"].get("public_resource_code", "")),
        "tradingPlace": str(context["card"].get("trading_place", "")),
        "moduleName": task["module_name"],
        "noticeTypeName": task["notice_type"],
    }
    extra = {key: value for key, value in extra.items() if value}
    release_content_mix: dict[str, Any] = {
        "text": context["content_text"],
    }
    return {
        "provinceCode": str(SITE_CONTEXT["province_code"]),
        "cityId": str(SITE_CONTEXT["city_id"]),
        "cityName": SITE_CONTEXT["city_name"],
        "procurementTitle": context["tender_title"],
        "releaseSource": context["procurement_unit"],
        "releaseDatetime": context["render_date"],
        "releaseContentMix": release_content_mix,
        "fileInfo": context["file_info"],
        "originalWebsiteAddress": context["detail_url"],
        "extra": extra,
        "parentType": get_parent_type(task["module_name"]),
        "bidType": task["notice_type"],
        "webSource": SITE_CONTEXT["web_source"],
    }


def update_additional_info(record: dict[str, Any], **kwargs: Any) -> None:
    # 兼容扩展用：把额外字段追加回 tenderAdditionalInfoStr。
    raw_value = str(record.get("tenderAdditionalInfoStr", "") or "")
    extra_info: dict[str, Any] = {}
    if raw_value:
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, dict):
                extra_info = parsed
        except Exception:
            extra_info = {}
    for key, value in kwargs.items():
        if value in ("", [], {}, None):
            continue
        extra_info[key] = value
    record["tenderAdditionalInfoStr"] = json.dumps(extra_info, ensure_ascii=False) if extra_info else ""


def build_standard_record(
    card: dict[str, Any],
    detail: dict[str, Any],
    detail_html: str,
    task: dict[str, str],
    crawl_time: str,
) -> dict[str, Any]:
    # 先按 notice_board 分发到四套模板，再返回最终字典。
    context = build_common_context(card, detail, detail_html, task, crawl_time)
    notice_board = str(context["notice_board"])

    if notice_board == "招标公告":
        record = build_bid_record(context)
    elif notice_board == "采购意向":
        record = build_procurement_intention_record(context)
    elif notice_board == "候选人公告":
        record = build_candidate_record(context)
    else:
        record = build_win_record(context)
    return sync_requirement_alias_fields(record)


def apply_model_enrichment(
    record: dict[str, Any],
    detail: dict[str, Any],
    detail_html: str,
    *,
    enable_model_enrichment: bool,
    notice_board: str,
    model_clients: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # 模型是可选增强：开启后优先覆盖对应字段，出错则回退规则提取结果。
    if not enable_model_enrichment:
        return record
    if not notice_board:
        return record
    client = (model_clients or {}).get(notice_board)
    if client is None:
        return record
    model_input = pick_first_non_empty(
        [
            str(detail.get("plain_text", "")),
            str(detail.get("content_text", "")),
            strip_html_tags(detail_html),
        ]
    )
    if not model_input:
        return record
    try:
        model_result = client.get_result(model_input)
    except Exception:
        return record
    if not isinstance(model_result, dict) or not model_result:
        return record

    if notice_board == "招标公告":
        reset_fields(
            record,
            [
                "projectName",
                "projectNum",
                "announcementTitle",
                "budgetAmount",
                "procurementMethod",
                "releaseSource",
            ],
        )
        set_if_present(record, "projectName", model_result.get("projectName"))
        set_if_present(record, "projectNum", model_result.get("projectNum"))
        set_if_present(record, "announcementTitle", model_result.get("projectName"))
        set_if_present(record, "budgetAmount", model_result.get("budgetAmount"))
        set_if_present(record, "procurementMethod", model_result.get("procurementMethod"))
        set_if_present(record, "releaseSource", model_result.get("releaseSource"))
        consultation_info = model_result.get("consultationInfo", {})
        if isinstance(consultation_info, dict):
            record["consultationInfo"] = {
                "purchasingInfor": consultation_info.get("purchasingInfor", []) if isinstance(consultation_info.get("purchasingInfor", []), list) else [],
                "projectInfo": consultation_info.get("projectInfor", []) if isinstance(consultation_info.get("projectInfor", []), list) else [],
            }

    if notice_board == "中标公告":
        reset_fields(
            record,
            [
                "tenderTitle",
                "tenderNumber",
                "procurementUnit",
                "relationCompanyName",
                "contactName",
                "contactTelephone",
                "renderMoney",
            ],
        )
        set_if_present(record, "tenderTitle", model_result.get("tenderTitle"))
        set_if_present(record, "tenderNumber", model_result.get("tenderNumber"))
        set_if_present(record, "procurementUnit", model_result.get("procurementUnit"))
        model_results = model_result.get("result", [])
        if isinstance(model_results, list) and model_results:
            first_item = model_results[0]
            if isinstance(first_item, dict):
                set_if_present(record, "relationCompanyName", first_item.get("relationCompanyName"))
                set_if_present(record, "contactName", first_item.get("contactName"))
                set_if_present(record, "contactTelephone", first_item.get("contactTelephone"))
                set_if_present(record, "renderMoney", first_item.get("renderMoney"))

    if notice_board == "候选人公告":
        reset_fields(
            record,
            [
                "tenderTitle",
                "procurementUnit",
                "relationCompanyName",
            ],
        )
        set_if_present(record, "tenderTitle", model_result.get("tenderTitle"))
        set_if_present(record, "procurementUnit", model_result.get("procurementUnit"))
        model_results = model_result.get("result", [])
        if isinstance(model_results, list) and model_results:
            candidate_names = [
                normalize_text(str(item.get("relationCompanyName", "")))
                for item in model_results
                if isinstance(item, dict) and str(item.get("relationCompanyName", "")).strip()
            ]
            if candidate_names:
                record["relationCompanyName"] = ",".join(candidate_names)
            candidate_sort_values: list[str] = []
            for item in model_results:
                if not isinstance(item, dict):
                    continue
                for sort_item in item.get("candidateSort", []):
                    text = normalize_text(str(sort_item))
                    if text:
                        candidate_sort_values.append(text)
            extra = record.get("extra", {})
            if not isinstance(extra, dict):
                extra = {}
            extra["candidateSort"] = candidate_sort_values
            extra["tenderNumber"] = normalize_text(str(model_result.get("extra", {}).get("tenderNumber", "")))
            record["extra"] = extra

    return sync_requirement_alias_fields(record)


def get_record_display_title(record: dict[str, Any]) -> str:
    # 打印时不同模板标题字段不一样，这里统一做回退。
    return pick_first_non_empty(
        [
            str(record.get("tenderTitle", "")),
            str(record.get("announcementTitle", "")),
            str(record.get("projectName", "")),
            str(record.get("procurementTitle", "")),
        ]
    )


def load_profile(profile_path: Path) -> dict[str, Any]:
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("profile.yml 必须是字典结构")
    return profile


class JnggzySpider:
    def __init__(self, profile: dict[str, Any], session: requests.Session | Any | None = None) -> None:
        self.profile = profile
        self.source = profile["source"]
        self.session = session or requests.Session()
        self.base_url = str(self.source["base_url"]).rstrip("/")
        self.module_name = str(self.source.get("module_name", "建设工程"))
        self.notice_type = str(self.source.get("notice_type", ""))
        self.module_tasks = filter_tasks_by_notice_type(get_module_tasks(self.module_name), self.notice_type)
        self.trade_type = str(self.source.get("type", ""))
        self.area = str(self.source.get("area", ""))
        self.subheading = str(self.source.get("subheading", ""))
        self.start_page = int(self.source["start_page"])
        self.max_pages = int(self.source["max_pages"])
        self.timeout_seconds = int(self.source.get("timeout_seconds", 30))
        self.detail_delay_seconds = float(self.source.get("detail_delay_seconds", 0))
        self.enable_model_enrichment = bool(profile.get("enable_model_enrichment", False))
        self.model_clients = load_model_clients(self.enable_model_enrichment, self.timeout_seconds)
        self.homepage_cache: dict[tuple[str, str], dict[str, Any]] = {}

    def search_url(self) -> str:
        return f"{self.base_url}/search.do"

    def homepage_url(self) -> str:
        return f"{self.base_url}/newChangeHomePageList.do"

    def soa_list_url(self) -> str:
        return f"{self.base_url}/assets/querySoaList.do"

    def agriculture_list_url(self) -> str:
        return f"{self.base_url}/getAgricultureList.do"

    def fetch_list_page(self, page_number: int, trade_type: str, notice_type: str, subheading: str = "") -> dict[str, Any]:
        # 常规 search.do 列表分页。
        response = self.session.post(
            self.search_url(),
            data={
                "area": self.area,
                "type": trade_type,
                "xuanxiang": notice_type,
                "subheading": subheading,
                "pagenum": str(page_number),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def fetch_agriculture_list_page(self, page_number: int, agriculture_type: str) -> dict[str, Any]:
        # 农村产权单独接口分页。
        response = self.session.post(
            self.agriculture_list_url(),
            data={
                "index": str(page_number),
                "pageSize": "15",
                "type": agriculture_type,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def fetch_soa_list_page(self, page_number: int, soa_type: str) -> dict[str, Any]:
        # 国有企业采购单独接口分页。
        response = self.session.post(
            self.soa_list_url(),
            data={
                "index": str(page_number),
                "pageSize": "15",
                "type": soa_type,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def fetch_homepage_module_data(self, trade_type: str, subheading: str) -> dict[str, Any]:
        # 少量栏目从首页接口取列表块。
        cache_key = (trade_type, subheading)
        if cache_key in self.homepage_cache:
            return self.homepage_cache[cache_key]
        response = self.session.post(
            self.homepage_url(),
            data={
                "type": trade_type,
                "subheading": subheading,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        self.homepage_cache[cache_key] = payload
        return payload

    def fetch_notice_detail(
        self,
        notice_id: str,
        is_new: int,
        notice_type: str,
        detail_path: str,
    ) -> tuple[str, str]:
        # 通过站点 show*.do 详情地址拼接拿正文。
        detail_url = build_detail_url(notice_id, notice_type or self.notice_type, is_new, detail_path=detail_path)
        response = self.session.get(detail_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return detail_url, response.text

    def fetch_notice_detail_by_url(self, detail_url: str) -> tuple[str, str]:
        # 少数列表页已经给了完整详情链接，直接请求即可。
        response = self.session.get(detail_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return detail_url, response.text

    def fetch_land_result_notice_payload(self, target_id: str) -> dict[str, Any]:
        response = self.session.post(
            "http://119.164.252.44:8001/data",
            data={
                "module": "portal",
                "service": "Query",
                "method": "queryTarget",
                "targetId": target_id,
            },
            headers={
                "Referer": f"http://119.164.252.44:8001/portal/noticeDetail.html?targetId={target_id}",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def collect_card_record(
        self,
        card: dict[str, Any],
        task: dict[str, str],
        crawl_time: str,
    ) -> dict[str, Any] | None:
        # 列表卡片 -> 详情页 -> 标准字典 -> 模型增强。
        direct_detail_url = str(card.get("detail_url", ""))
        if direct_detail_url:
            detail_url, detail_html = self.fetch_notice_detail_by_url(direct_detail_url)
        else:
            detail_url, detail_html = self.fetch_notice_detail(
                notice_id=str(card.get("notice_id", "")),
                is_new=int(card.get("is_new", 1)),
                notice_type=str(card.get("notice_type", "")) or task["notice_type"],
                detail_path=get_default_detail_path(task),
            )
        if is_land_result_notice_task(task):
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', detail_html, flags=re.I)
            if iframe_match:
                iframe_url = urljoin(detail_url, iframe_match.group(1))
                target_id = parse_qs(urlparse(iframe_url).query).get("targetId", [""])[0]
                if target_id:
                    _, iframe_html = self.fetch_notice_detail_by_url(iframe_url)
                    payload = self.fetch_land_result_notice_payload(target_id)
                    detail, detail_html = build_land_result_notice_detail(payload, detail_url, template_html=iframe_html)
                else:
                    detail = parse_notice_detail(detail_html, detail_url)
            else:
                detail = parse_notice_detail(detail_html, detail_url)
        else:
            detail = parse_notice_detail(detail_html, detail_url)
        if is_blank_notice_detail(task, detail, detail_html):
            return None
        record = build_standard_record(card, detail, detail_html, task, crawl_time)
        return apply_model_enrichment(
            record,
            detail,
            detail_html,
            enable_model_enrichment=self.enable_model_enrichment,
            notice_board=get_notice_board(task["notice_type"]),
            model_clients=self.model_clients,
        )

    def run(self) -> list[dict[str, Any]]:
        # 按一级模块顺序跑，每个二级栏目分页采集并逐条打印。
        all_records: list[dict[str, Any]] = []
        print(f"开始采集 jnggzy，一级模块: {self.module_name}")
        tasks = self.module_tasks or [
            {
                "module_name": self.module_name,
                "type": self.trade_type,
                "xuanxiang": self.notice_type,
                "notice_type": self.notice_type,
                "detail_path": "showNotice.do",
            }
        ]
        current_module_name = ""
        current_module_count = 0
        for task in tasks:
            task_module_name = str(task["module_name"])
            if task_module_name != current_module_name:
                if current_module_name:
                    print(f"一级模块结束: {current_module_name}，本组记录数: {current_module_count}")
                current_module_name = task_module_name
                current_module_count = 0
                print("")
                print(f"========== 一级模块: {current_module_name} ==========")

            print(f"当前二级栏目: {task['notice_type']}")
            task_record_count = 0
            if task.get("list_api") == "search":
                page_number = self.start_page
                max_page_limit = self.max_pages if self.max_pages > 0 else None
                search_type = str(task.get("search_type", task["type"]))
                search_notice_type = str(task.get("search_notice_type", task["notice_type"]))
                search_subheading = str(task.get("subheading", self.subheading))
                while True:
                    payload = self.fetch_list_page(page_number, search_type, search_notice_type, search_subheading)
                    total_pages = parse_search_total_pages(payload)
                    cards = parse_search_response(payload, self.search_url())
                    total_pages_text = total_pages if total_pages is not None else "未知"
                    print(f"[{task['notice_type']}][第 {page_number} 页 / 共 {total_pages_text} 页] 列表条数: {len(cards)}")
                    if not cards:
                        break

                    for index, card in enumerate(cards, start=1):
                        crawl_time = datetime.now().isoformat(timespec="seconds")
                        record = self.collect_card_record(card, task, crawl_time)
                        if record is None:
                            continue
                        all_records.append(record)
                        current_module_count += 1
                        task_record_count += 1
                        print(f"[{task['notice_type']}][第 {page_number} 页][第 {index} 条] 标题: {get_record_display_title(record)}")
                        print(json.dumps(record, ensure_ascii=False, indent=2))

                        if self.detail_delay_seconds > 0:
                            time.sleep(self.detail_delay_seconds)
                    if total_pages is not None and page_number >= total_pages:
                        break
                    if max_page_limit is not None and page_number >= max_page_limit:
                        break
                    page_number += 1
                print(f"二级栏目结束: {task['notice_type']}，本栏记录数: {task_record_count}")
                continue

            if task.get("list_api") == "homepage":
                subheading = str(task.get("subheading", self.subheading))
                payload = self.fetch_homepage_module_data(task["type"], subheading)
                html = str(payload.get("params", {}).get(str(task["list_key"]), ""))
                cards = parse_list_html(html, self.homepage_url())
                print(f"[{task['notice_type']}][首页列表] 条数: {len(cards)}")
                for index, card in enumerate(cards, start=1):
                    crawl_time = datetime.now().isoformat(timespec="seconds")
                    record = self.collect_card_record(card, task, crawl_time)
                    if record is None:
                        continue
                    all_records.append(record)
                    current_module_count += 1
                    task_record_count += 1
                    print(f"[{task['notice_type']}][首页列表][第 {index} 条] 标题: {get_record_display_title(record)}")
                    print(json.dumps(record, ensure_ascii=False, indent=2))
                    if self.detail_delay_seconds > 0:
                        time.sleep(self.detail_delay_seconds)
                print(f"二级栏目结束: {task['notice_type']}，本栏记录数: {task_record_count}")
                continue

            if task.get("list_api") == "soa":
                page_number = self.start_page
                max_page_limit = self.max_pages if self.max_pages > 0 else None
                soa_type = str(task["soa_type"])
                while True:
                    payload = self.fetch_soa_list_page(page_number, soa_type)
                    total_pages = parse_search_total_pages(payload)
                    cards = parse_search_response(payload, self.soa_list_url())
                    total_pages_text = total_pages if total_pages is not None else "未知"
                    print(f"[{task['notice_type']}][第 {page_number} 页 / 共 {total_pages_text} 页] 列表条数: {len(cards)}")
                    if not cards:
                        break

                    for index, card in enumerate(cards, start=1):
                        crawl_time = datetime.now().isoformat(timespec="seconds")
                        record = self.collect_card_record(card, task, crawl_time)
                        if record is None:
                            continue
                        all_records.append(record)
                        current_module_count += 1
                        task_record_count += 1
                        print(f"[{task['notice_type']}][第 {page_number} 页][第 {index} 条] 标题: {get_record_display_title(record)}")
                        print(json.dumps(record, ensure_ascii=False, indent=2))
                        if self.detail_delay_seconds > 0:
                            time.sleep(self.detail_delay_seconds)
                    if total_pages is not None and page_number >= total_pages:
                        break
                    if max_page_limit is not None and page_number >= max_page_limit:
                        break
                    page_number += 1
                print(f"二级栏目结束: {task['notice_type']}，本栏记录数: {task_record_count}")
                continue

            if task.get("list_api") == "agriculture":
                page_number = self.start_page
                max_page_limit = self.max_pages if self.max_pages > 0 else None
                agriculture_type = str(task["agriculture_type"])
                while True:
                    payload = self.fetch_agriculture_list_page(page_number, agriculture_type)
                    total_pages = parse_search_total_pages(payload)
                    cards = parse_search_response(payload, self.agriculture_list_url())
                    total_pages_text = total_pages if total_pages is not None else "未知"
                    print(f"[{task['notice_type']}][第 {page_number} 页 / 共 {total_pages_text} 页] 列表条数: {len(cards)}")
                    if not cards:
                        break

                    for index, card in enumerate(cards, start=1):
                        crawl_time = datetime.now().isoformat(timespec="seconds")
                        record = self.collect_card_record(card, task, crawl_time)
                        if record is None:
                            continue
                        all_records.append(record)
                        current_module_count += 1
                        task_record_count += 1
                        print(f"[{task['notice_type']}][第 {page_number} 页][第 {index} 条] 标题: {get_record_display_title(record)}")
                        print(json.dumps(record, ensure_ascii=False, indent=2))
                        if self.detail_delay_seconds > 0:
                            time.sleep(self.detail_delay_seconds)
                    if total_pages is not None and page_number >= total_pages:
                        break
                    if max_page_limit is not None and page_number >= max_page_limit:
                        break
                    page_number += 1
                print(f"二级栏目结束: {task['notice_type']}，本栏记录数: {task_record_count}")

        if current_module_name:
            print(f"一级模块结束: {current_module_name}，本组记录数: {current_module_count}")
        print(f"采集结束，总记录数: {len(all_records)}")
        return all_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="jnggzy 采集脚本，只负责构造并打印字典")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("profile.yml"),
        help="配置文件路径，默认读取当前目录下的 profile.yml",
    )
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    spider = JnggzySpider(profile)
    spider.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
