from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

try:
    import pymongo
except ImportError:  # pragma: no cover - 测试里会替换掉 build_mongo_client
    pymongo = None


logger = logging.getLogger("doctor-qyzx-spider")
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


SOURCE_SITE = "七元网"
DEFAULT_PROFILE: dict[str, Any] = {
    "project": {
        "site": SOURCE_SITE,
    },
    "source": {
        "list_url": "https://www.qypxw.net/zxxmjg/",
        "start_page": 44,
        "detail_max_workers": 20,
        "timeout_seconds": 120,
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
        "doctor_collection": "doctor_qyzx",
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


def build_mongo_client(mongodb_config: dict[str, Any]):
    if pymongo is None:
        raise RuntimeError("未安装 pymongo，无法创建 MongoDB 连接")

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
        or "doctor_qyzx"
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def clean_special_chars(value: str) -> str:
    cleaned = normalize_text(value)
    for char in ("丨", "｜", "∣", "·", "•", "／", "（", "）", "(", ")", "【", "】", "[", "]", "「", "」", "『", "』", "“", "”", '"', "'"):
        cleaned = cleaned.replace(char, "")
    return cleaned


def normalize_multiline_text(value: str) -> str:
    text = re.sub(r"\r\n?", "\n", value or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_doctor_id_from_url(url: str) -> str:
    match = re.search(r"/zxxmjg/([a-z]+_\d+)/?$", url)
    if not match:
        raise ValueError(f"无法从链接提取 doctor_id: {url}")
    return match.group(1)


def extract_department_from_doctor_id(doctor_id: str) -> str:
    prefix = doctor_id.split("_", 1)[0]
    if prefix == "yk":
        return "眼科"
    if prefix == "kq":
        return "口腔"
    if prefix == "ym":
        return "医美"
    return ""


def build_list_page_url(list_url: str, page_number: int) -> str:
    normalized = list_url.rstrip("/") + "/"
    if page_number <= 1:
        return normalized
    return f"{normalized}page{page_number}/"


def build_doctor_record(
    *,
    doctor_id: str,
    doctor_name: str = "",
    doctor_department: str = "",
    doctor_hospital: str = "",
    doctor_title: str = "",
    doctor_specialties: str = "",
    intro: str = "",
    doctor_avatar_url: str = "",
    source_site: str = SOURCE_SITE,
    source_url: str = "",
    crawl_time: str = "",
) -> dict[str, str]:
    return {
        "_id": doctor_id,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "doctor_department": doctor_department,
        "doctor_hospital": doctor_hospital,
        "doctor_title": doctor_title,
        "doctor_specialties": doctor_specialties,
        "intro": intro,
        "doctor_avatar_url": doctor_avatar_url,
        "source_site": source_site,
        "source_url": source_url,
        "crawl_time": crawl_time,
    }


def _extract_page_num_from_url(page_url: str) -> int:
    match = re.search(r"/page(\d+)/?$", page_url)
    return int(match.group(1)) if match else 1


def _extract_total_pages(soup: BeautifulSoup) -> int:
    page_numbers = [1]
    for link in soup.find_all("a", href=True):
        match = re.search(r"/page(\d+)/?$", link["href"])
        if match:
            page_numbers.append(int(match.group(1)))
    return max(page_numbers)


def _extract_card_nodes(soup: BeautifulSoup) -> list[Any]:
    cards: list[Any] = []
    for li in soup.find_all("li"):
        if li.find("a", href=re.compile(r"^/zxxmjg/[a-z]+_\d+/$")):
            cards.append(li)
    return cards


def parse_list_page(page_url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    doctors: list[dict[str, str | int]] = []

    for card in _extract_card_nodes(soup):
        detail_link = card.find("a", href=re.compile(r"^/zxxmjg/[a-z]+_\d+/$"))
        if detail_link is None:
            continue

        detail_url = urljoin(page_url, detail_link["href"])
        doctor_id = extract_doctor_id_from_url(detail_url)
        name_node = card.select_one(".doctorName")
        hospital_node = None
        intro_node = None
        for paragraph in card.find_all("p"):
            text = normalize_text(paragraph.get_text(" ", strip=True))
            if text.startswith("坐诊医院："):
                hospital_node = paragraph
            elif text.startswith("医生简介："):
                intro_node = paragraph

        time_node = card.find("time", class_="doctorTime")
        image_node = card.find("img")

        doctors.append(
            build_doctor_record(
                doctor_id=doctor_id,
                doctor_name=normalize_text(name_node.get_text(" ", strip=True)) if name_node else "",
                doctor_department=extract_department_from_doctor_id(doctor_id),
                doctor_hospital=normalize_text(hospital_node.get_text(" ", strip=True)).replace(
                    "坐诊医院：", "", 1
                ).strip()
                if hospital_node
                else "",
                intro=normalize_text(intro_node.get_text(" ", strip=True)).replace(
                    "医生简介：", "", 1
                ).strip()
                if intro_node
                else "",
                doctor_avatar_url=urljoin(page_url, image_node["src"])
                if image_node and image_node.has_attr("src")
                else "",
                source_site=SOURCE_SITE,
                source_url=detail_url,
                crawl_time="",
            )
        )

    return {
        "total": None,
        "page_size": len(doctors),
        "total_pages": _extract_total_pages(soup),
        "page_num": _extract_page_num_from_url(page_url),
        "doctors": doctors,
    }


def _extract_intro_meta(soup: BeautifulSoup) -> dict[str, str]:
    meta_map: dict[str, str] = {}
    for item in soup.select(".introduceRight > div"):
        label_node = item.find("span", class_="string")
        label = normalize_text(label_node.get_text(" ", strip=True)) if label_node else ""
        text = normalize_text(item.get_text(" ", strip=True))
        if not label or not text.startswith(label):
            continue
        meta_map[label.rstrip("：")] = text[len(label) :].strip()
    return meta_map


def _extract_breadcrumb_department(soup: BeautifulSoup) -> str:
    crumbs = [normalize_text(node.get_text(" ", strip=True)) for node in soup.select(".position a")]
    if "医生" in crumbs:
        doctor_index = crumbs.index("医生")
        if doctor_index + 1 < len(crumbs):
            return crumbs[doctor_index + 1]
    return ""


def _extract_doctor_intro(soup: BeautifulSoup) -> str:
    for heading in soup.find_all("h3"):
        heading_text = normalize_text(heading.get_text(" ", strip=True))
        if "医生简介" not in heading_text:
            continue

        sibling = heading.find_next_sibling()
        while sibling is not None and getattr(sibling, "name", "") != "p":
            sibling = sibling.find_next_sibling()

        if sibling is None:
            return ""
        return normalize_multiline_text(sibling.get_text("\n", strip=True))
    return ""


def parse_detail_page(detail_url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    doctor_id = extract_doctor_id_from_url(detail_url)
    meta_map = _extract_intro_meta(soup)

    name = normalize_text(soup.select_one(".doctorXiming").get_text(" ", strip=True))
    title = clean_special_chars(meta_map.get("医生职称", ""))
    specialties = normalize_text(meta_map.get("诊疗项目", "")).replace(" ", ",")
    hospital = normalize_text(meta_map.get("所属医院", ""))
    avatar_node = soup.select_one(".introduceBox img")
    department = _extract_breadcrumb_department(soup) or extract_department_from_doctor_id(doctor_id)

    return build_doctor_record(
        doctor_id=doctor_id,
        doctor_name=name,
        doctor_department=department,
        doctor_hospital=hospital,
        doctor_title=title,
        doctor_specialties=specialties,
        intro=_extract_doctor_intro(soup),
        doctor_avatar_url=urljoin(detail_url, avatar_node["src"])
        if avatar_node and avatar_node.has_attr("src")
        else "",
        source_site=SOURCE_SITE,
        source_url=detail_url,
        crawl_time="",
    )


class DoctorQyzxSpider:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile
        self.project = profile["project"]
        self.source = profile["source"]
        self.mongodb = profile["mongodb"]

        self.list_url = str(self.source.get("list_url", "https://www.qypxw.net/zxxmjg/")).rstrip("/") + "/"
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
            "Referer": self.list_url,
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
                response.encoding = response.apparent_encoding or response.encoding or "utf-8"
                return response.text
            except Exception as exc:  # pragma: no cover - 网络失败依赖现场环境
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
        list_data: dict[str, str | int],
        detail_data: dict[str, str | int] | None = None,
    ) -> dict[str, str | int]:
        detail_data = detail_data or {}
        return build_doctor_record(
            doctor_id=str(list_data["doctor_id"]),
            doctor_name=str(detail_data.get("doctor_name") or list_data["doctor_name"]),
            doctor_department=str(
                detail_data.get("doctor_department") or list_data["doctor_department"]
            ),
            doctor_hospital=str(detail_data.get("doctor_hospital") or list_data["doctor_hospital"]),
            doctor_title=str(detail_data.get("doctor_title") or list_data["doctor_title"]),
            doctor_specialties=str(
                detail_data.get("doctor_specialties") or list_data["doctor_specialties"]
            ),
            intro=str(detail_data.get("intro") or list_data["intro"]),
            doctor_avatar_url=str(
                detail_data.get("doctor_avatar_url") or list_data["doctor_avatar_url"]
            ),
            source_site=str(detail_data.get("source_site") or list_data["source_site"]),
            source_url=str(detail_data.get("source_url") or list_data["source_url"]),
            crawl_time=self.crawl_time,
        )

    def fetch_detail_record(self, doctor: dict[str, str | int]) -> dict[str, str | int]:
        detail_url = str(doctor["source_url"])
        detail_html = self.request_html(detail_url)
        detail_data = parse_detail_page(detail_url, detail_html)
        return self.merge_doctor_data(doctor, detail_data)

    def run(self) -> dict[str, Any]:
        logger.info("开始执行七元网医生采集")
        logger.info("列表地址: %s", self.list_url)
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
            page_url = build_list_page_url(self.list_url, page_number)
            html = self.request_html(page_url)
            parsed = parse_list_page(page_url, html)
            doctors = parsed["doctors"]
            total_pages = max(total_pages, int(parsed["total_pages"]))

            logger.info("[第 %s 页] 原始条数: %s", page_number, len(doctors))
            logger.info("[第 %s 页] 总页数: %s", page_number, parsed["total_pages"])
            if not doctors:
                logger.info("[第 %s 页] 当前页为空，停止采集", page_number)
                break

            raw_count += len(doctors)
            last_page = page_number

            if self.fetch_detail:
                final_records_by_id: dict[str, dict[str, str | int]] = {}
                with ThreadPoolExecutor(max_workers=self.detail_max_workers) as executor:
                    future_to_doctor_id = {
                        executor.submit(self.fetch_detail_record, doctor): str(doctor["doctor_id"])
                        for doctor in doctors
                    }
                    for future in as_completed(future_to_doctor_id):
                        doctor_id = future_to_doctor_id[future]
                        final_records_by_id[doctor_id] = future.result()
                final_records = [final_records_by_id[str(doctor["doctor_id"])] for doctor in doctors]
            else:
                final_records = [self.merge_doctor_data(doctor) for doctor in doctors]

            page_saved = 0
            for final_data in final_records:
                self.save_doctor(final_data)
                page_saved += 1

            sample = final_records[0]
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
    spider = DoctorQyzxSpider(DEFAULT_PROFILE)
    result = spider.run()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
