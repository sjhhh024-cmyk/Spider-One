from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import re
import time
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import quote_plus, urljoin

import pymongo
import requests
import redis
from bs4 import BeautifulSoup


SOURCE_SITE = "中国医药信息查询平台"
BASE_URL = "https://www.dayi.org.cn"
DOCTOR_LIST_PREFIX = "/list/3"
HOSPITAL_LIST_PREFIX = "/list/2"
DOCTOR_DETAIL_PREFIX = "/doctor"
HOSPITAL_DETAIL_PREFIX = "/hospital"
REDIS_HOST = os.getenv("SPIDER_ONE_REDIS_HOST", "117.50.131.232")
REDIS_PORT = int(os.getenv("SPIDER_ONE_REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("SPIDER_ONE_REDIS_DB", "1"))
REDIS_PASSWORD = os.getenv("SPIDER_ONE_REDIS_PASSWORD", "Yb$]Mdh3YU2k}hw")
DEFAULT_COOKIE = (
    "BAIDU_SSP_lcr=https://icnxm2gtfq9p.feishu.cn/; "
    "sl-session=ipkEA0eDBmqtWeh3eC1fZg==; "
    "Hm_lvt_b1ccef85a3456b5f14347f4d25b82c86=1777364615,1778056351,1778725324; "
    "HMACCOUNT=BF60C57DDB4B8BA6; "
    "Hm_lpvt_b1ccef85a3456b5f14347f4d25b82c86=1778741092; "
    "sl-waiting-state=queue; "
    "sl-waiting-session=ab156430ef074e8413c1a93c5e8cfef3"
)
if REDIS_PASSWORD:
    DEFAULT_REDIS_URL = f"redis://:{quote_plus(REDIS_PASSWORD)}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    DEFAULT_REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

DEFAULT_PROFILE: dict[str, Any] = {
    "project": {
        "site": SOURCE_SITE,
    },
    "source": {
        "base_url": BASE_URL,
        "start_page": 0,
        "timeout_seconds": 30,
        "max_retries": 3,
        "waiting_poll_interval_seconds": 1,
        "waiting_timeout_seconds": 90,
        "cookie": os.getenv("SPIDER_ONE_DAYI_COOKIE", DEFAULT_COOKIE),
    },
    "redis": {
        "url": DEFAULT_REDIS_URL,
        "doctor_list_task": "doctor_zgyyxx:doctor_list_task",
        "doctor_detail_task": "doctor_zgyyxx:doctor_detail_task",
        "hospital_detail_task": "doctor_zgyyxx:hospital_detail_task",
    },
    "mongodb": {
        "host": "101.200.125.240",
        "port": 27017,
        "username": "admin",
        "password": "a@Mfv8k!r@8r@8&R",
        "auth_source": "admin",
        "database": "Doctor_Database",
        "doctor_collection": "doctor_zgyyxx",
        "hospital_collection": "hospital_zgyyxx",
    },
}


logger = logging.getLogger("doctor-zgyyxx-spider")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_multiline_text(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.IGNORECASE)
    text = re.sub(r"</p>\s*\n\s*<p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>\s*<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = text.replace("\r", "")
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    normalized_lines: list[str] = []
    previous_blank = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            normalized_lines.append(stripped)
            previous_blank = False
            continue
        if normalized_lines and not previous_blank:
            normalized_lines.append("")
            previous_blank = True
    return "\n".join(normalized_lines).strip()


def remove_unwanted_lines(value: str, unwanted_lines: set[str]) -> str:
    if not value:
        return ""
    kept_lines = [line.strip() for line in value.split("\n") if line.strip() and line.strip() not in unwanted_lines]
    return "\n".join(kept_lines).strip()


def strip_html_to_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    return normalize_text(unescape(text))


def decode_js_string(value: str) -> str:
    if value == "":
        return ""
    sanitized = re.sub(
        r"[\x00-\x1f]",
        lambda match: {
            "\b": r"\b",
            "\f": r"\f",
            "\n": r"\n",
            "\r": r"\r",
            "\t": r"\t",
        }.get(match.group(0), f"\\u{ord(match.group(0)):04x}"),
        value,
    )
    return json.loads(f'"{sanitized}"')


def normalize_mongodb_uri(uri: str) -> str:
    prefixes = ("mongodb://", "mongodb+srv://")
    if not uri.startswith(prefixes):
        return uri
    scheme, remainder = uri.split("://", 1)
    if "@" not in remainder:
        return uri
    userinfo, rest = remainder.rsplit("@", 1)
    if ":" not in userinfo:
        return uri
    username, password = userinfo.split(":", 1)
    return f"{scheme}://{quote_plus(username)}:{quote_plus(password)}@{rest}"


def build_mongo_client(mongodb_config: dict[str, Any]):
    uri = str(mongodb_config.get("uri", "")).strip()
    if uri:
        return pymongo.MongoClient(normalize_mongodb_uri(uri))
    client_kwargs: dict[str, Any] = {
        "host": mongodb_config.get("host", "127.0.0.1"),
        "port": int(mongodb_config.get("port", 27017)),
    }
    username = mongodb_config.get("username")
    password = mongodb_config.get("password")
    auth_source = mongodb_config.get("auth_source") or mongodb_config.get("database")
    if username:
        client_kwargs["username"] = username
    if password:
        client_kwargs["password"] = password
    if username or password:
        client_kwargs["authSource"] = auth_source
    return pymongo.MongoClient(**client_kwargs)


class InMemoryRedisClient:
    def __init__(self) -> None:
        self.storage: dict[str, set[str]] = {}

    def sadd(self, key: str, *values: str) -> int:
        members = self.storage.setdefault(key, set())
        before = len(members)
        members.update(values)
        return len(members) - before

    def smembers(self, key: str) -> set[str]:
        return set(self.storage.get(key, set()))

    def srem(self, key: str, *values: str) -> int:
        members = self.storage.get(key, set())
        removed = 0
        for value in values:
            if value in members:
                members.remove(value)
                removed += 1
        return removed

    def scard(self, key: str) -> int:
        return len(self.storage.get(key, set()))

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.storage:
                del self.storage[key]
                deleted += 1
        return deleted


def build_redis_client(redis_config: dict[str, Any]):
    redis_url = str(redis_config.get("url") or DEFAULT_REDIS_URL).strip()
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    client.ping()
    return client


def parse_cookie_string(cookie_text: str) -> dict[str, str]:
    cookie_map: dict[str, str] = {}
    for item in (cookie_text or "").split(";"):
        part = item.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        cookie_map[key.strip()] = value.strip()
    return cookie_map


def dump_task(task: dict[str, object]) -> str:
    return json.dumps(task, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def load_task(task_data: str | bytes) -> dict[str, object]:
    if isinstance(task_data, bytes):
        task_data = task_data.decode("utf-8")
    return json.loads(task_data)


def push_task(redis_client, task_key: str, task: dict[str, object]) -> int:
    return int(redis_client.sadd(task_key, dump_task(task)))


def pop_tasks(redis_client, task_key: str) -> list[tuple[str, dict[str, object]]]:
    raw_tasks = sorted(redis_client.smembers(task_key))
    return [(raw_task, load_task(raw_task)) for raw_task in raw_tasks]


def remove_task(redis_client, task_key: str, raw_task: str) -> int:
    return int(redis_client.srem(task_key, raw_task))


def build_doctor_list_page_url(base_url: str, page_number: int) -> str:
    normalized = base_url.rstrip("/")
    if page_number <= 1:
        return f"{normalized}{DOCTOR_LIST_PREFIX}"
    return f"{normalized}{DOCTOR_LIST_PREFIX}/{page_number}"


def build_hospital_list_page_url(base_url: str, page_number: int) -> str:
    normalized = base_url.rstrip("/")
    if page_number <= 1:
        return f"{normalized}{HOSPITAL_LIST_PREFIX}"
    return f"{normalized}{HOSPITAL_LIST_PREFIX}/{page_number}"


def build_doctor_detail_url(base_url: str, doctor_id: str) -> str:
    return f"{base_url.rstrip('/')}{DOCTOR_DETAIL_PREFIX}/{doctor_id}.html"


def build_hospital_detail_url(base_url: str, hospital_id: str) -> str:
    return f"{base_url.rstrip('/')}{HOSPITAL_DETAIL_PREFIX}/{hospital_id}.html"


def build_doctor_record(
    *,
    doctor_id: str,
    doctor_name: str = "",
    doctor_hospital: str = "",
    doctor_department: str = "",
    doctor_title: str = "",
    doctor_avatar_url: str = "",
    doctor_specialties: str = "",
    intro: str = "",
    source_site: str = SOURCE_SITE,
    source_url: str = "",
    crawl_time: str = "",
    extra_fields: dict[str, str] | None = None,
) -> dict[str, str]:
    record = {
        "_id": doctor_id,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "doctor_hospital": doctor_hospital,
        "doctor_department": doctor_department,
        "doctor_title": doctor_title,
        "doctor_avatar_url": doctor_avatar_url,
        "doctor_specialties": doctor_specialties,
        "intro": intro,
        "source_site": source_site,
        "source_url": source_url,
        "crawl_time": crawl_time,
    }
    if extra_fields:
        for key, value in extra_fields.items():
            if value != "":
                record[key] = value
    return record


def build_hospital_record(
    *,
    hospital_id: str,
    hospital_name: str = "",
    hospital_address: str = "",
    hospital_phone: str = "",
    hospital_intro: str = "",
    hospital_level: str = "",
    hospital_nature: str = "",
    hospital_type: str = "",
    hospital_property: str = "",
    hospital_website: str = "",
    hospital_insurance: str = "",
    hospital_offices: str = "",
    hospital_special: str = "",
    hospital_advantage: str = "",
    source_site: str = SOURCE_SITE,
    source_url: str = "",
    crawl_time: str = "",
    include_id: bool = True,
) -> dict[str, str]:
    record = {
        "hospital_id": hospital_id,
        "hospital_name": hospital_name,
        "hospital_address": hospital_address,
        "hospital_phone": hospital_phone,
        "hospital_intro": hospital_intro,
        "hospital_level": hospital_level,
        "hospital_nature": hospital_nature,
        "hospital_type": hospital_type,
        "hospital_property": hospital_property,
        "hospital_website": hospital_website,
        "hospital_insurance": hospital_insurance,
        "hospital_offices": hospital_offices,
        "hospital_special": hospital_special,
        "hospital_advantage": hospital_advantage,
        "source_site": source_site,
        "source_url": source_url,
        "crawl_time": crawl_time,
    }
    if include_id:
        record["_id"] = hospital_id
    return record


def extract_doctor_title_from_job_text(job_text: str) -> str:
    normalized = normalize_text(job_text)
    title_patterns = [
        "副主任医师",
        "主任医师",
        "主治医师",
        "住院医师",
        "医师",
    ]
    for title in title_patterns:
        if title in normalized:
            return title
    return ""


def build_hospital_expert_doctor_id(hospital_id: str, doctor_name: str) -> str:
    safe_name = re.sub(r"[^\w\u4e00-\u9fff]+", "", doctor_name)
    safe_name = safe_name or "unknown"
    return f"hospital_{hospital_id}_{safe_name}"


def _extract_hospital_name_from_intro(intro: str, department_name: str, fallback: str) -> str:
    intro = normalize_text(intro)
    department_name = normalize_text(department_name)
    patterns = []
    if department_name:
        patterns.extend(
            [
                rf"现就职于(.+?){re.escape(department_name)}",
                rf"现任(.+?){re.escape(department_name)}",
                rf"就职于(.+?){re.escape(department_name)}",
            ]
        )
    for pattern in patterns:
        match = re.search(pattern, intro)
        if match:
            return normalize_text(match.group(1))
    return fallback


def _extract_total_pages_from_pagination(html: str, route_prefix: str) -> int:
    matches = re.findall(rf'href="{re.escape(route_prefix)}(?:/(\\d+))?"', html)
    page_numbers = [1]
    for page in matches:
        if page:
            page_numbers.append(int(page))
    return max(page_numbers)


def _split_top_level_js_objects(text: str) -> list[str]:
    items: list[str] = []
    start_index = -1
    quote_char = ""
    escape = False
    depth_bracket = 0
    depth_brace = 0
    depth_paren = 0
    for index, char in enumerate(text):
        if quote_char:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                quote_char = ""
            continue
        if char in {'"', "'"}:
            quote_char = char
            continue
        if char == "(":
            depth_paren += 1
            continue
        if char == ")":
            depth_paren -= 1
            continue
        if char == "[":
            depth_bracket += 1
            continue
        if char == "]":
            depth_bracket -= 1
            continue
        if char == "{":
            if depth_brace == 0 and depth_bracket == 0 and depth_paren == 0:
                start_index = index
            depth_brace += 1
            continue
        if char == "}":
            depth_brace -= 1
            if depth_brace == 0 and start_index != -1 and depth_bracket == 0 and depth_paren == 0:
                items.append(text[start_index : index + 1].strip())
                start_index = -1
    return items


def _split_js_arguments(text: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    quote_char = ""
    escape = False
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    for char in text:
        if quote_char:
            current.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                quote_char = ""
            continue

        if char in {'"', "'"}:
            quote_char = char
            current.append(char)
            continue
        if char == "(":
            depth_paren += 1
        elif char == ")":
            depth_paren -= 1
        elif char == "[":
            depth_bracket += 1
        elif char == "]":
            depth_bracket -= 1
        elif char == "{":
            depth_brace += 1
        elif char == "}":
            depth_brace -= 1
        elif char == "," and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
            items.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if current:
        items.append("".join(current).strip())
    return items


def _parse_js_literal(token: str) -> Any:
    token = token.strip()
    if token == "true":
        return True
    if token == "false":
        return False
    if token == "null":
        return None
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        if token.startswith("'"):
            token = json.dumps(token[1:-1], ensure_ascii=False)
        return json.loads(token)
    return token


def _split_js_key_value(item: str) -> tuple[str, str]:
    quote_char = ""
    escape = False
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    for index, char in enumerate(item):
        if quote_char:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                quote_char = ""
            continue
        if char in {'"', "'"}:
            quote_char = char
            continue
        if char == "(":
            depth_paren += 1
            continue
        if char == ")":
            depth_paren -= 1
            continue
        if char == "[":
            depth_bracket += 1
            continue
        if char == "]":
            depth_bracket -= 1
            continue
        if char == "{":
            depth_brace += 1
            continue
        if char == "}":
            depth_brace -= 1
            continue
        if char == ":" and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
            return item[:index].strip(), item[index + 1 :].strip()
    return item.strip(), ""


def _extract_nuxt_aliases(html: str) -> dict[str, Any]:
    match = re.search(r"window\.__NUXT__=\(function\((.*?)\)\{.*?\}\((.*)\)\);</script>", html, re.DOTALL)
    if not match:
        return {}
    params = [item.strip() for item in match.group(1).split(",") if item.strip()]
    arguments = _split_js_arguments(match.group(2))
    aliases: dict[str, Any] = {}
    for name, raw_value in zip(params, arguments):
        aliases[name] = _parse_js_literal(raw_value)
    return aliases


def _resolve_js_value(raw_value: str, aliases: dict[str, Any]) -> Any:
    raw_value = raw_value.strip()
    if raw_value in aliases:
        return aliases[raw_value]
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return decode_js_string(raw_value[1:-1])
    return _parse_js_literal(raw_value)


def _extract_js_object_data(html: str, object_name: str) -> dict[str, Any]:
    aliases = _extract_nuxt_aliases(html)
    result: dict[str, Any] = {}
    marker = f"{object_name}."
    position = 0
    html_length = len(html)
    while True:
        start = html.find(marker, position)
        if start == -1:
            break
        key_start = start + len(marker)
        equal_index = html.find("=", key_start)
        if equal_index == -1:
            break
        key = html[key_start:equal_index].strip()
        if not re.fullmatch(r"[a-zA-Z0-9_]+", key):
            position = key_start
            continue

        value_start = equal_index + 1
        cursor = value_start
        quote_char = ""
        escape = False
        depth_paren = 0
        depth_bracket = 0
        depth_brace = 0
        while cursor < html_length:
            char = html[cursor]
            if quote_char:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote_char:
                    quote_char = ""
                cursor += 1
                continue
            if char in {'"', "'"}:
                quote_char = char
            elif char == "(":
                depth_paren += 1
            elif char == ")":
                depth_paren -= 1
            elif char == "[":
                depth_bracket += 1
            elif char == "]":
                depth_bracket -= 1
            elif char == "{":
                depth_brace += 1
            elif char == "}":
                depth_brace -= 1
            elif char == ";" and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
                break
            cursor += 1
        raw_value = html[value_start:cursor].strip()
        result[key] = _resolve_js_value(raw_value, aliases)
        position = cursor + 1
    return result


def _detect_detail_object_name(html: str, marker_keys: list[str]) -> str:
    patterns = [
        r"detail:([a-zA-Z_$][\w$]*)",
        r"response:\{.*?data:([a-zA-Z_$][\w$]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            continue
        object_name = match.group(1)
        if all(f"{object_name}.{key}=" in html for key in marker_keys):
            return object_name

    candidates: dict[str, set[str]] = {}
    for object_name, key in re.findall(r"([a-zA-Z_$][\w$]*)\.([a-zA-Z0-9_]+)=", html):
        candidates.setdefault(object_name, set()).add(key)
    for object_name, keys in candidates.items():
        if all(marker_key in keys for marker_key in marker_keys):
            return object_name
    return ""


def _extract_js_assignment_block(html: str, object_name: str, field_name: str) -> str:
    marker = f"{object_name}.{field_name}="
    start = html.find(marker)
    if start == -1:
        return ""
    value_start = start + len(marker)
    cursor = value_start
    html_length = len(html)
    quote_char = ""
    escape = False
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    while cursor < html_length:
        char = html[cursor]
        if quote_char:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                quote_char = ""
            cursor += 1
            continue
        if char in {'"', "'"}:
            quote_char = char
        elif char == "(":
            depth_paren += 1
        elif char == ")":
            depth_paren -= 1
        elif char == "[":
            depth_bracket += 1
        elif char == "]":
            depth_bracket -= 1
        elif char == "{":
            depth_brace += 1
        elif char == "}":
            depth_brace -= 1
        elif char == ";" and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
            return html[value_start:cursor].strip()
        cursor += 1
    return html[value_start:cursor].strip()


def _stringify_js_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _normalize_hospital_website(value: str) -> str:
    url = normalize_text(value)
    if not url:
        return ""
    url = re.sub(r"^https://", "http://", url, flags=re.IGNORECASE)
    if not url.endswith("/"):
        url = f"{url}/"
    return url


def compact_hospital_record(record: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in record.items() if not (key in {"hospital_address", "hospital_phone"} and value == "")}


def parse_doctor_list_page(page_url: str, html: str) -> dict[str, Any]:
    aliases = _extract_nuxt_aliases(html)
    page_no_match = re.search(r"pageNo:([^,}]+)", html)
    page_size_match = re.search(r"pageSize:([^,}]+)", html)
    total_match = re.search(r"totalCount:(\d+)", html)
    page_no = int(_stringify_js_value(_resolve_js_value(page_no_match.group(1), aliases))) if page_no_match else 1
    page_size = int(_stringify_js_value(_resolve_js_value(page_size_match.group(1), aliases))) if page_size_match else 0
    total = int(total_match.group(1)) if total_match else 0
    total_pages = _extract_total_pages_from_pagination(html, "/list/3")
    if total and page_size:
        total_pages = (total + page_size - 1) // page_size

    list_block_match = re.search(r'list:\[(.*?)\],\s*efficientQaConfigCount', html, re.DOTALL)
    if not list_block_match:
        raise ValueError("医生列表页缺少 list 数据")
    list_block = list_block_match.group(1)

    doctors: list[dict[str, str]] = []
    for raw_item in _split_top_level_js_objects(list_block):
        item_body = raw_item.strip()
        if item_body.startswith("{") and item_body.endswith("}"):
            item_body = item_body[1:-1]
        field_map: dict[str, Any] = {}
        for pair in _split_js_arguments(item_body):
            key, raw_value = _split_js_key_value(pair)
            if not key or raw_value == "":
                continue
            field_map[key] = _resolve_js_value(raw_value, aliases)

        doctor_id = _stringify_js_value(field_map.get("id", "")).strip()
        if not doctor_id:
            continue
        title = _stringify_js_value(field_map.get("title", ""))
        thumbnail = _stringify_js_value(field_map.get("thumbnail", ""))
        introduction_text = strip_html_to_text(_stringify_js_value(field_map.get("introduction", "")))
        clinic_professional = _stringify_js_value(field_map.get("clinicProfessional", ""))
        department_name = _stringify_js_value(field_map.get("departmentName", ""))
        institution_name = _stringify_js_value(field_map.get("institutionName", ""))
        doctors.append(
            build_doctor_record(
                doctor_id=doctor_id,
                doctor_name=title,
                doctor_hospital=institution_name,
                doctor_department=department_name,
                doctor_title=clinic_professional,
                doctor_avatar_url=thumbnail.replace("\\u002F", "/"),
                doctor_specialties="",
                intro=introduction_text,
                source_url=build_doctor_detail_url(BASE_URL, doctor_id),
                crawl_time="",
            )
        )

    return {
        "total": total,
        "page_size": page_size or len(doctors),
        "page_num": page_no,
        "total_pages": total_pages,
        "doctors": doctors,
    }

def parse_doctor_detail_page(detail_url: str, html: str) -> dict[str, str]:
    object_name = _detect_detail_object_name(html, ["id", "mapping", "name"])
    if not object_name:
        raise ValueError("医生详情页缺少详情对象名")

    detail_data = _extract_js_object_data(html, object_name)
    if not detail_data:
        raise ValueError(f"医生详情页缺少 {object_name} 对象数据")

    mapping_match = re.search(
        rf"{re.escape(object_name)}\.mapping=\[\{{institutionId:(\d+),institutionName:([^,]+),departmentName:([^}}]+)\}}\]",
        html,
    )
    aliases = _extract_nuxt_aliases(html)

    hospital_name = ""
    department_name = ""
    hospital_id = ""
    if mapping_match:
        hospital_id = mapping_match.group(1)
        hospital_expr = mapping_match.group(2).strip()
        department_expr = mapping_match.group(3).strip()
        hospital_name = _stringify_js_value(_resolve_js_value(hospital_expr, aliases))
        department_name = _stringify_js_value(_resolve_js_value(department_expr, aliases))

    if not hospital_name:
        hospital_name = _stringify_js_value(detail_data.get("mapHospital", ""))
    if not department_name:
        department_name = _stringify_js_value(detail_data.get("mapDepartment", ""))
    intro_text = normalize_multiline_text(_stringify_js_value(detail_data.get("intro", "")))
    doctor_hospital = hospital_name or _extract_hospital_name_from_intro(intro_text, department_name, hospital_name)

    social_job_text = remove_unwanted_lines(
        normalize_multiline_text(_stringify_js_value(detail_data.get("science", ""))),
        {
            "国家中医药管理局名词术语成果转化与规范推广项目评审专家",
            "国家中医药管理局名词术语成果转化与规范推广项目编审专家",
        },
    )
    extra_fields: dict[str, str] = {
        "doctor_prof_title": _stringify_js_value(detail_data.get("eduProfessional", "")),
        "doctor_graduated": _stringify_js_value(detail_data.get("graduate", "")),
        "doctor_edu_process": normalize_multiline_text(_stringify_js_value(detail_data.get("education", ""))),
        "doctor_work_process": normalize_multiline_text(_stringify_js_value(detail_data.get("workExperience", ""))),
        "doctor_summary": normalize_multiline_text(_stringify_js_value(detail_data.get("treatArea", ""))),
        "doctor_expertise": normalize_multiline_text(_stringify_js_value(detail_data.get("treatArea", ""))),
        "doctor_social_job": social_job_text,
        "doctor_social_activity": normalize_multiline_text(_stringify_js_value(detail_data.get("socialization", ""))),
        "doctor_research_direction": normalize_multiline_text(_stringify_js_value(detail_data.get("researchArea", ""))),
        "doctor_published_works": normalize_multiline_text(_stringify_js_value(detail_data.get("bookmaking", ""))),
        "doctor_achievements": normalize_multiline_text(_stringify_js_value(detail_data.get("production", ""))),
        "doctor_person_honor": normalize_multiline_text(
            _stringify_js_value(detail_data.get("honorary", "")) or _stringify_js_value(detail_data.get("awards", ""))
        ),
    }
    record = build_doctor_record(
        doctor_id=_stringify_js_value(detail_data.get("id", "")).strip(),
        doctor_name=_stringify_js_value(detail_data.get("name", "")),
        doctor_hospital=doctor_hospital,
        doctor_department=department_name,
        doctor_title=_stringify_js_value(detail_data.get("clinicProfessional", "")),
        doctor_avatar_url=_stringify_js_value(detail_data.get("thumbnail", "")).replace("\\u002F", "/"),
        doctor_specialties=normalize_multiline_text(_stringify_js_value(detail_data.get("treatArea", ""))),
        intro=intro_text,
        source_url=detail_url,
        crawl_time="",
        extra_fields=extra_fields,
    )
    return record


def parse_hospital_list_page(page_url: str, html: str) -> dict[str, Any]:
    aliases = _extract_nuxt_aliases(html)
    page_no_match = re.search(r"pageNo:([^,}]+)", html)
    page_size_match = re.search(r"pageSize:([^,}]+)", html)
    total_match = re.search(r"totalCount:(\d+)", html)
    page_no = int(_stringify_js_value(_resolve_js_value(page_no_match.group(1), aliases))) if page_no_match else 1
    page_size = int(_stringify_js_value(_resolve_js_value(page_size_match.group(1), aliases))) if page_size_match else 0
    total = int(total_match.group(1)) if total_match else 0
    total_pages = _extract_total_pages_from_pagination(html, "/list/2")
    if total and page_size:
        total_pages = (total + page_size - 1) // page_size
    list_block_match = re.search(r'list:\[(.*?)\],\s*efficientQaConfigCount', html, re.DOTALL)
    if not list_block_match:
        raise ValueError("医院列表页缺少 list 数据")
    list_block = list_block_match.group(1)
    item_pattern = re.compile(
        r'id:(\d+),title:"([^"]+)",thumbnail:"([^"]+)",introduction:"(.*?)",secondType:[^,]*,secondTitle:[^,]*,classType:',
        re.DOTALL,
    )

    hospitals: list[dict[str, str]] = []
    for match in item_pattern.finditer(list_block):
        hospital_id, title, thumbnail, introduction = match.groups()
        hospitals.append(
            compact_hospital_record(
                build_hospital_record(
                    hospital_id=hospital_id,
                    hospital_name=title,
                    hospital_intro=strip_html_to_text(introduction),
                    hospital_level="",
                    hospital_nature="",
                    hospital_type="",
                    hospital_property="",
                    hospital_website="",
                    hospital_insurance="",
                    hospital_offices="",
                    hospital_special="",
                    hospital_advantage="",
                    source_url=build_hospital_detail_url(BASE_URL, hospital_id),
                    crawl_time="",
                    include_id=True,
                )
            )
        )

    return {
        "total": total,
        "page_size": page_size or len(hospitals),
        "page_num": page_no,
        "total_pages": total_pages,
        "hospitals": hospitals,
    }


def parse_hospital_detail_page(detail_url: str, html: str) -> dict[str, str]:
    object_name = _detect_detail_object_name(html, ["id", "name", "intro"])
    if not object_name:
        raise ValueError("医院详情页缺少详情对象名")

    detail_data = _extract_js_object_data(html, object_name)
    if not detail_data:
        raise ValueError(f"医院详情页缺少 {object_name} 对象数据")

    hospital_id_match = re.search(rf"{re.escape(object_name)}\.id=(\d+)", html)
    hospital_id = hospital_id_match.group(1) if hospital_id_match else ""
    hospital_type = _stringify_js_value(detail_data.get("category", "") or detail_data.get("institutionType", ""))
    if hospital_type == "综合":
        hospital_type = "综合医院"

    return build_hospital_record(
        hospital_id=hospital_id,
        hospital_name=_stringify_js_value(detail_data.get("name", "")),
        hospital_address=_stringify_js_value(detail_data.get("address", "")),
        hospital_phone=_stringify_js_value(detail_data.get("telephone", "")),
        hospital_intro=normalize_multiline_text(_stringify_js_value(detail_data.get("intro", ""))),
        hospital_level=_stringify_js_value(detail_data.get("level", "")),
        hospital_nature=_stringify_js_value(detail_data.get("nature", "")),
        hospital_type=hospital_type,
        hospital_property="",
        hospital_website=_normalize_hospital_website(_stringify_js_value(detail_data.get("website", ""))),
        hospital_insurance=_stringify_js_value(detail_data.get("insurance", "")),
        hospital_offices=normalize_multiline_text(_stringify_js_value(detail_data.get("offices", ""))),
        hospital_special=normalize_multiline_text(_stringify_js_value(detail_data.get("special", ""))),
        hospital_advantage=normalize_multiline_text(_stringify_js_value(detail_data.get("advantage", ""))),
        source_url=detail_url,
        crawl_time="",
        include_id=True,
    )


def parse_hospital_expert_doctors(detail_url: str, html: str) -> list[dict[str, str]]:
    object_name = _detect_detail_object_name(html, ["id", "name", "intro"])
    if not object_name:
        return []

    detail_data = _extract_js_object_data(html, object_name)
    if not detail_data:
        return []

    hospital_id = _stringify_js_value(detail_data.get("id", "")).strip()
    hospital_name = _stringify_js_value(detail_data.get("name", ""))
    doctors_block = _extract_js_assignment_block(html, object_name, "doctors")
    if not doctors_block:
        return []

    records: list[dict[str, str]] = []
    aliases = _extract_nuxt_aliases(html)
    doctor_pattern = re.compile(
        r'\{url:(?P<url>"(?:\\.|[^"])*"|[^,]+),name:(?P<name>"(?:\\.|[^"])*"|[^,]+),job:(?P<job>"(?:\\.|[^"])*"|[^,]+),zl:(?P<zl>"(?:\\.|[^"])*"|[^}]+)\}',
        re.DOTALL,
    )
    for match in doctor_pattern.finditer(doctors_block):
        doctor_name = normalize_text(_stringify_js_value(_resolve_js_value(match.group("name"), aliases)))
        if not doctor_name:
            continue
        job_text = normalize_text(_stringify_js_value(_resolve_js_value(match.group("job"), aliases)))
        summary_text = normalize_text(_stringify_js_value(_resolve_js_value(match.group("zl"), aliases)))
        avatar_url = _stringify_js_value(_resolve_js_value(match.group("url"), aliases)).replace("\\u002F", "/")
        synthetic_doctor_id = build_hospital_expert_doctor_id(hospital_id, doctor_name)
        extra_fields = {
            "doctor_summary": summary_text,
            "doctor_expertise": summary_text,
        }
        records.append(
            build_doctor_record(
                doctor_id=synthetic_doctor_id,
                doctor_name=doctor_name,
                doctor_hospital=hospital_name,
                doctor_department="",
                doctor_title=extract_doctor_title_from_job_text(job_text),
                doctor_avatar_url=avatar_url,
                doctor_specialties=summary_text,
                intro=job_text,
                source_url=detail_url,
                crawl_time="",
                extra_fields=extra_fields,
            )
        )
    return records


def merge_hospital_data(list_record: dict[str, str], detail_record: dict[str, str]) -> dict[str, str]:
    merged = copy.deepcopy(list_record)
    for key, value in detail_record.items():
        if value != "":
            merged[key] = value
    return merged


class DoctorZgyyxxSpider:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile
        self.project = profile["project"]
        self.source = profile["source"]
        self.redis_config = profile["redis"]
        self.mongodb = profile["mongodb"]
        self.base_url = str(self.source.get("base_url", BASE_URL)).rstrip("/")
        self.timeout_seconds = int(self.source.get("timeout_seconds", 30))
        self.max_retries = int(self.source.get("max_retries", 3))
        self.waiting_poll_interval_seconds = max(1, int(self.source.get("waiting_poll_interval_seconds", 1)))
        self.waiting_timeout_seconds = max(5, int(self.source.get("waiting_timeout_seconds", 90)))
        self.cookie_text = str(self.source.get("cookie", "")).strip()
        self.reset_tasks_before_run = bool(self.source.get("reset_tasks_before_run", False))
        configured_start_page = int(self.source.get("start_page", 0))
        self.start_page = 1 if configured_start_page <= 0 else configured_start_page
        self.crawl_time = datetime.now().strftime("%Y-%m-%d")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36"
                )
            }
        )
        self.load_seed_cookies()
        self.redis_client = build_redis_client(self.redis_config)
        self.mongo_client = build_mongo_client(self.mongodb)
        self.database = self.mongo_client[self.mongodb["database"]]
        self.doctor_collection = self.database[self.mongodb["doctor_collection"]]
        self.hospital_collection = self.database[self.mongodb["hospital_collection"]]

    def load_seed_cookies(self) -> None:
        if not self.cookie_text:
            return
        cookie_map = parse_cookie_string(self.cookie_text)
        for key, value in cookie_map.items():
            self.session.cookies.set(key, value, domain="www.dayi.org.cn")
        logger.info("已注入初始 Cookie: %s 个", len(cookie_map))

    def wait_for_safeline_pass(self, response: requests.Response) -> bool:
        waiting_session = self.session.cookies.get("sl-waiting-session")
        waiting_state = self.session.cookies.get("sl-waiting-state")
        if response.status_code != 465 or not waiting_session or waiting_state != "queue":
            return False

        query_url = urljoin(self.base_url, "/.safeline/api/waiting/query")
        deadline = time.time() + self.waiting_timeout_seconds
        logger.info("触发 Safeline 排队，开始等待放行: session=%s", waiting_session)

        while time.time() < deadline:
            query_response = self.session.get(query_url, timeout=self.timeout_seconds)
            query_response.raise_for_status()
            payload = query_response.json()
            data = payload.get("data") or {}
            pos = int(data.get("pos", -1))
            total = int(data.get("total", -1))
            logger.info("Safeline 排队中: pos=%s total=%s", pos, total)
            if pos == 0:
                logger.info("Safeline 排队完成，重试原页面")
                return True
            time.sleep(self.waiting_poll_interval_seconds)

        raise TimeoutError(f"Safeline 排队超时: {response.url}")

    def request_html(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            logger.info("请求第 %s 次: %s", attempt, url)
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                if response.status_code == 465 and self.wait_for_safeline_pass(response):
                    response = self.session.get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or response.encoding or "utf-8"
                return response.text
            except Exception as exc:  # pragma: no cover
                last_error = exc
                logger.error("请求失败: %s", exc)
                if attempt == self.max_retries:
                    raise
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"请求失败: {url}")

    def save_doctor(self, record: dict[str, str]) -> None:
        self.doctor_collection.replace_one({"_id": record["_id"]}, record, upsert=True)

    def save_hospital(self, record: dict[str, str]) -> None:
        self.hospital_collection.replace_one({"_id": record["_id"]}, record, upsert=True)

    def reset_task_queues(self) -> None:
        keys = [
            self.redis_config["doctor_list_task"],
            self.redis_config["doctor_detail_task"],
            self.redis_config["hospital_detail_task"],
        ]
        self.redis_client.delete(*keys)
        logger.info("已清空任务队列: %s", ", ".join(keys))

    def crawl_hospital_lists(self, hospital_detail_key: str) -> dict[str, dict[str, str]]:
        hospital_list_map: dict[str, dict[str, str]] = {}
        page_no = 1
        total_pages = 1
        while page_no <= total_pages:
            hospital_list_url = build_hospital_list_page_url(self.base_url, page_no)
            hospital_list_html = self.request_html(hospital_list_url)
            hospital_list_data = parse_hospital_list_page(hospital_list_url, hospital_list_html)
            total_pages = max(total_pages, int(hospital_list_data["total_pages"]))
            for hospital in hospital_list_data["hospitals"]:
                hospital_list_map[hospital["hospital_id"]] = hospital
                push_task(
                    self.redis_client,
                    hospital_detail_key,
                    {
                        "url": build_hospital_detail_url(self.base_url, hospital["hospital_id"]),
                        "hospital_id": hospital["hospital_id"],
                    },
                )
            page_no += 1
        return hospital_list_map

    def run(self) -> dict[str, int]:
        doctor_list_key = self.redis_config["doctor_list_task"]
        doctor_detail_key = self.redis_config["doctor_detail_task"]
        hospital_detail_key = self.redis_config["hospital_detail_task"]

        if self.reset_tasks_before_run:
            self.reset_task_queues()

        doctor_detail_has_tasks = self.redis_client.scard(doctor_detail_key) > 0
        hospital_detail_has_tasks = self.redis_client.scard(hospital_detail_key) > 0

        if self.redis_client.scard(doctor_list_key) == 0 and not doctor_detail_has_tasks:
            push_task(
                self.redis_client,
                doctor_list_key,
                {"url": build_doctor_list_page_url(self.base_url, self.start_page), "page_no": self.start_page},
            )

        doctor_upsert_count = 0
        hospital_upsert_count = 0

        while self.redis_client.scard(doctor_list_key) > 0:
            for raw_task, task in pop_tasks(self.redis_client, doctor_list_key):
                page_url = str(task["url"])
                page_no = int(task.get("page_no", 1))
                html = self.request_html(page_url)
                parsed = parse_doctor_list_page(page_url, html)
                if page_no < int(parsed["total_pages"]):
                    next_page_no = page_no + 1
                    push_task(
                        self.redis_client,
                        doctor_list_key,
                        {"url": build_doctor_list_page_url(self.base_url, next_page_no), "page_no": next_page_no},
                    )
                for doctor in parsed["doctors"]:
                    push_task(
                        self.redis_client,
                        doctor_detail_key,
                        {"url": doctor["source_url"], "doctor_id": doctor["doctor_id"]},
                    )
                remove_task(self.redis_client, doctor_list_key, raw_task)

        for raw_task, task in pop_tasks(self.redis_client, doctor_detail_key):
            detail_url = str(task["url"])
            record = parse_doctor_detail_page(detail_url, self.request_html(detail_url))
            record["crawl_time"] = self.crawl_time
            self.save_doctor(record)
            doctor_upsert_count += 1
            remove_task(self.redis_client, doctor_detail_key, raw_task)

        hospital_list_map: dict[str, dict[str, str]] = {}
        if not hospital_detail_has_tasks:
            hospital_list_map = self.crawl_hospital_lists(hospital_detail_key)

        for raw_task, task in pop_tasks(self.redis_client, hospital_detail_key):
            detail_url = str(task["url"])
            hospital_id = str(task["hospital_id"])
            html = self.request_html(detail_url)
            detail_record = parse_hospital_detail_page(detail_url, html)
            list_record = hospital_list_map.get(hospital_id)
            merged = merge_hospital_data(list_record, detail_record) if list_record else detail_record
            merged["crawl_time"] = self.crawl_time
            self.save_hospital(merged)
            hospital_upsert_count += 1
            for doctor_record in parse_hospital_expert_doctors(detail_url, html):
                doctor_record["crawl_time"] = self.crawl_time
                self.save_doctor(doctor_record)
                doctor_upsert_count += 1
            remove_task(self.redis_client, hospital_detail_key, raw_task)

        return {
            "doctor_upsert_count": doctor_upsert_count,
            "hospital_upsert_count": hospital_upsert_count,
        }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="中国医药信息查询平台医生采集")
    parser.add_argument("--start-page", type=int, default=1, help="医生列表起始页码")
    parser.add_argument("--base-url", default=BASE_URL, help="站点根地址")
    parser.add_argument("--cookie", default="", help="浏览器复制出的 Cookie，优先覆盖默认配置")
    parser.add_argument("--reset-tasks", action="store_true", help="清空 Redis 任务队列后从头开始")
    return parser


def build_profile(args: argparse.Namespace) -> dict[str, Any]:
    profile = json.loads(json.dumps(DEFAULT_PROFILE))
    profile["source"]["base_url"] = str(args.base_url).strip() or BASE_URL
    profile["source"]["start_page"] = max(1, int(args.start_page))
    profile["source"]["reset_tasks_before_run"] = bool(args.reset_tasks)
    if str(args.cookie).strip():
        profile["source"]["cookie"] = str(args.cookie).strip()
    return profile


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    profile = build_profile(args)
    spider = DoctorZgyyxxSpider(profile)
    result = spider.run()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
