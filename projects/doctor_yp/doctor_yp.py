from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import pymongo
import requests


logger = logging.getLogger("doctor-yp-spider")
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)


DOCTOR_SITE = "医谱"
LIST_PATH = "/doctorList"
DETAIL_PATH = "/doctorDetail"
MEDICAL_TITLES = {
    "主任医师",
    "副主任医师",
    "主治医师",
    "住院医师",
    "医师",
    "主任中医师",
    "副主任中医师",
    "主治中医师",
    "中医师",
    "主任药师",
    "副主任药师",
    "主管药师",
    "药师",
    "主任技师",
    "副主任技师",
    "主管技师",
    "技师",
    "主任护师",
    "副主任护师",
    "主管护师",
    "护师",
    "护士",
}
DEFAULT_PROFILE: dict[str, Any] = {
    "project": {
        "site": DOCTOR_SITE,
    },
    "source": {
        "base_url": "https://docbook.com.cn",
        "start_page": 682,
        "detail_max_workers": 20,
        "timeout_seconds": 30,
        "max_retries": 3,
        "fetch_detail": True,
    },
    "mongodb": {
        "host": "101.200.125.240",
        "port": 27017,
        "username": "admin",
        "password": "a@Mfv8k!r@8r@8&R",
        "auth_source": "admin",
        "database": "Doctor_Database",
        "doctor_collection": "doctor_yp",
    },
}


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


def build_mongo_client(mongodb_config: dict[str, Any]) -> pymongo.MongoClient:
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


def get_doctor_collection_name(mongodb_config: dict[str, Any]) -> str:
    return str(
        mongodb_config.get("doctor_collection")
        or mongodb_config.get("collection")
        or "doctor_yp"
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_multiline_text(value: str) -> str:
    lines = [line.strip() for line in (value or "").splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def split_title_fields(raw_title: str, department_name: str = "") -> tuple[str, str]:
    doctor_title = ""
    other_titles: list[str] = []

    candidates: list[str] = []
    if raw_title:
        candidates.extend(re.split(r"[，,/\s]+", raw_title))

    for candidate in candidates:
        value = candidate.strip()
        if not value:
            continue
        if department_name and value == department_name:
            continue
        if value in MEDICAL_TITLES and not doctor_title:
            doctor_title = value
            continue
        if value not in MEDICAL_TITLES and value not in other_titles:
            other_titles.append(value)

    return doctor_title, ",".join(other_titles)


def build_list_page_url(base_url: str, page_number: int) -> str:
    normalized_base = base_url.rstrip("/")
    if page_number <= 1:
        return f"{normalized_base}{LIST_PATH}"
    return f"{normalized_base}{LIST_PATH}/{page_number}"


def build_detail_url(base_url: str, doctor_id: str) -> str:
    return f"{base_url.rstrip('/')}{DETAIL_PATH}/{doctor_id}"


def build_doctor_record(
    *,
    doctor_id: str,
    doctor_name: str = "",
    doctor_hospital: str = "",
    doctor_department: str = "",
    doctor_titile: str = "",
    doctor_other_title: str = "",
    intro: str = "",
    doctor_avatar_url: str = "",
    source_url: str = "",
    crawl_time: str = "",
) -> dict[str, str]:
    return {
        "_id": doctor_id,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "doctor_hospital": doctor_hospital,
        "doctor_department": doctor_department,
        "doctor_titile": doctor_titile,
        "doctor_other_title": doctor_other_title,
        "intro": intro,
        "doctor_avatar_url": doctor_avatar_url,
        "source_url": source_url,
        "crawl_time": crawl_time,
    }


def _extract_nuxt_script(html: str) -> str:
    match = re.search(r"window\.__NUXT__=.*?</script>", html, re.DOTALL)
    if not match:
        raise ValueError("页面里没有找到 __NUXT__ 数据块")
    return match.group(0)


def parse_list_page(page_url: str, html: str) -> dict[str, Any]:
    html_match_total = re.search(r"共\s*(\d+)\s*条", html)
    total = int(html_match_total.group(1)) if html_match_total else 0

    total_pages_match = re.search(r'max="(\d+)"\s+class="el-input__inner"', html)
    total_pages = int(total_pages_match.group(1)) if total_pages_match else 1

    page_num_match = re.search(r"routePath:\"\\u002FdoctorList(?:\\u002F(\d+))?\"", html)
    page_num = int(page_num_match.group(1)) if page_num_match and page_num_match.group(1) else 1

    doctors: list[dict[str, Any]] = []
    item_pattern = re.compile(
        r'<li class="doctor-item".*?<a href="/doctorDetail/(\d+)".*?'
        r'<h3.*?>\s*<a .*?>\s*([^<]+?)\s*</a>\s*</h3>\s*'
        r'<p[^>]*>([^<]*)</p>\s*<p[^>]*>([^<]*)</p>',
        re.DOTALL,
    )
    title_map = {
        match.group(1): match.group(2)
        for match in re.finditer(
            r'doctor_id:(\d+),doctor_name:"[^"]+",doctor_cover:"[^"]+".*?doctor_position:"([^"]*)"',
            _extract_nuxt_script(html),
            re.DOTALL,
        )
    }
    cover_map = {
        match.group(1): match.group(2).replace("\\u002F", "/")
        for match in re.finditer(
            r'doctor_id:(\d+),doctor_name:"[^"]+",doctor_cover:"([^"]+)"',
            _extract_nuxt_script(html),
            re.DOTALL,
        )
    }
    for match in item_pattern.finditer(html):
        doctor_id, doctor_name, department_name, hospital_name = match.groups()
        raw_title = normalize_text(title_map.get(doctor_id, ""))
        doctor_title, doctor_other_title = split_title_fields(
            raw_title,
            department_name=department_name.strip(),
        )
        doctors.append(
            build_doctor_record(
                doctor_id=doctor_id,
                doctor_name=normalize_text(doctor_name),
                doctor_hospital=hospital_name.strip(),
                doctor_department=department_name.strip(),
                doctor_titile=doctor_title,
                doctor_other_title=doctor_other_title,
                intro="",
                doctor_avatar_url=cover_map.get(doctor_id, ""),
                source_url=page_url,
                crawl_time="",
            )
        )

    return {
        "total": total,
        "page_size": 15,
        "total_pages": total_pages,
        "page_num": page_num,
        "doctors": doctors,
    }


def parse_detail_page(detail_url: str, html: str) -> dict[str, Any]:
    doctor_id_match = re.search(r"/doctorDetail/(\d+)", detail_url)
    if not doctor_id_match:
        raise ValueError(f"无法从详情链接提取 doctor_id: {detail_url}")
    doctor_id = doctor_id_match.group(1)

    name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
    title_match = re.search(r"<h4[^>]*>([^<]+)</h4>", html)
    hospital_match = re.search(r'<p class="doctor-hospital"[^>]*>([^<]+)</p>', html)
    department_match = re.search(r'<p class="doctor-dept"[^>]*>([^<]+)</p>', html)
    intro_match = re.search(r"简介：(.*?)</p>", html, re.DOTALL)

    nuxt_script = _extract_nuxt_script(html)
    photo_match = re.search(r'doctor_photo:"([^"]+)"', nuxt_script)

    doctor_title, doctor_other_title = split_title_fields(
        normalize_text(title_match.group(1)) if title_match else "",
        normalize_text(department_match.group(1)) if department_match else "",
    )

    return build_doctor_record(
        doctor_id=doctor_id,
        doctor_name=normalize_text(name_match.group(1)) if name_match else "",
        doctor_hospital=normalize_text(hospital_match.group(1)) if hospital_match else "",
        doctor_department=normalize_text(department_match.group(1)) if department_match else "",
        doctor_titile=doctor_title,
        doctor_other_title=doctor_other_title,
        intro=normalize_multiline_text(intro_match.group(1)) if intro_match else "",
        doctor_avatar_url=photo_match.group(1).replace("\\u002F", "/") if photo_match else "",
        source_url=detail_url,
        crawl_time="",
    )


class DoctorYpSpider:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile
        self.project = profile["project"]
        self.source = profile["source"]
        self.mongodb = profile["mongodb"]

        self.base_url = str(self.source.get("base_url", "https://docbook.com.cn")).rstrip("/")
        configured_start_page = int(self.source.get("start_page", 0))
        self.start_page = 1 if configured_start_page <= 0 else configured_start_page
        self.configured_start_page = configured_start_page
        self.detail_max_workers = max(1, int(self.source.get("detail_max_workers", 5)))
        self.timeout_seconds = int(self.source.get("timeout_seconds", 30))
        self.max_retries = int(self.source.get("max_retries", 3))
        self.fetch_detail = bool(self.source.get("fetch_detail", True))
        self.crawl_time = datetime.now().strftime("%Y-%m-%d")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Referer": f"{self.base_url}{LIST_PATH}",
        }

        self.mongo_client = build_mongo_client(self.mongodb)
        self.collection = self.mongo_client[self.mongodb["database"]][
            get_doctor_collection_name(self.mongodb)
        ]
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def request_html(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            logger.info("请求第 %s 次: %s", attempt, url)
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or response.encoding
                return response.text
            except Exception as exc:
                last_error = exc
                logger.error("请求失败: %s", exc)
                if attempt == self.max_retries:
                    raise
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"请求失败: {url}")

    def save_doctor(self, data: dict[str, Any]) -> None:
        self.collection.replace_one({"_id": data["_id"]}, data, upsert=True)

    def merge_doctor_data(
        self,
        list_data: dict[str, str],
        detail_data: dict[str, str] | None = None,
    ) -> dict[str, str]:
        detail_data = detail_data or {}
        return build_doctor_record(
            doctor_id=list_data["doctor_id"],
            doctor_name=detail_data.get("doctor_name") or list_data["doctor_name"],
            doctor_hospital=detail_data.get("doctor_hospital") or list_data["doctor_hospital"],
            doctor_department=detail_data.get("doctor_department") or list_data["doctor_department"],
            doctor_titile=detail_data.get("doctor_titile") or list_data["doctor_titile"],
            doctor_other_title=detail_data.get("doctor_other_title") or list_data["doctor_other_title"],
            intro=detail_data.get("intro") or list_data["intro"],
            doctor_avatar_url=detail_data.get("doctor_avatar_url") or list_data["doctor_avatar_url"],
            source_url=detail_data.get("source_url") or list_data["source_url"],
            crawl_time=self.crawl_time,
        )

    def fetch_detail_record(self, doctor: dict[str, str]) -> dict[str, str]:
        detail_url = build_detail_url(self.base_url, doctor["doctor_id"])
        detail_html = self.request_html(detail_url)
        detail_data = parse_detail_page(detail_url, detail_html)
        return self.merge_doctor_data(doctor, detail_data)

    def run(self) -> dict[str, Any]:
        logger.info("开始执行医谱医生采集")
        logger.info("站点: %s", self.base_url)
        logger.info("配置页码: %s", self.configured_start_page)
        logger.info("实际起始页: %s", self.start_page)
        logger.info("采集模式: 全量采集")
        logger.info("详情模式: %s", self.fetch_detail)
        logger.info("详情并发数: %s", self.detail_max_workers)
        logger.info("MongoDB 集合: %s", get_doctor_collection_name(self.mongodb))
        logger.info("-" * 60)

        saved_count = 0
        raw_count = 0
        last_page = 0
        total_pages = self.start_page
        page_number = self.start_page

        while page_number <= total_pages:
            page_url = build_list_page_url(self.base_url, page_number)
            html = self.request_html(page_url)
            parsed = parse_list_page(page_url, html)
            doctors = parsed["doctors"]
            total_pages = max(total_pages, int(parsed["total_pages"]))

            logger.info("[第 %s 页] 原始条数: %s", page_number, len(doctors))
            logger.info("[第 %s 页] 总条数: %s | 总页数: %s", page_number, parsed["total"], parsed["total_pages"])
            if not doctors:
                logger.info("[第 %s 页] 当前页为空，停止采集", page_number)
                break

            raw_count += len(doctors)
            last_page = page_number

            page_saved = 0
            if self.fetch_detail:
                final_records_by_id: dict[str, dict[str, str]] = {}
                with ThreadPoolExecutor(max_workers=self.detail_max_workers) as executor:
                    future_to_doctor_id = {
                        executor.submit(self.fetch_detail_record, doctor): doctor["doctor_id"]
                        for doctor in doctors
                    }
                    for future in as_completed(future_to_doctor_id):
                        doctor_id = future_to_doctor_id[future]
                        final_records_by_id[doctor_id] = future.result()
                final_records = [final_records_by_id[doctor["doctor_id"]] for doctor in doctors]
            else:
                final_records = [self.merge_doctor_data(doctor) for doctor in doctors]

            for final_data in final_records:
                self.save_doctor(final_data)
                page_saved += 1

            sample = doctors[0]
            logger.info("[第 %s 页] 样本记录:", page_number)
            for field_name, field_value in sample.items():
                logger.info("  %s: %s", field_name, field_value)
            logger.info("[第 %s 页] 入库成功数: %s", page_number, page_saved)
            logger.info("-" * 60)

            saved_count += page_saved
            if page_number >= total_pages:
                break
            page_number += 1

        result = {
            "last_page": last_page,
            "raw_row_count": raw_count,
            "mongodb_upsert_count": saved_count,
        }
        logger.info("采集完成")
        logger.info("最后成功页: %s", result["last_page"])
        logger.info("原始总条数: %s", result["raw_row_count"])
        logger.info("MongoDB 入库总数: %s", result["mongodb_upsert_count"])
        return result


def main() -> int:
    spider = DoctorYpSpider(DEFAULT_PROFILE)
    result = spider.run()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
