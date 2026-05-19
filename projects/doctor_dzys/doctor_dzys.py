from __future__ import annotations

import argparse
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus, urljoin
from threading import Lock

import requests
from bs4 import BeautifulSoup

try:
    import pymongo
except ImportError:  # pragma: no cover - 本地 dry-run 不依赖数据库
    pymongo = None

try:
    import redis
except ImportError:  # pragma: no cover - 本地 dry-run 不依赖数据库
    redis = None


SOURCE_SITE = "大众网-妙正云康"
DEFAULT_SITEMAP_URL = "https://www.dazhong.com/hospital/sitemap_doctor"
DEFAULT_HOSPITAL_DB = "Doctor_Database"
DEFAULT_DOCTOR_COLLECTION = "doctor_dzys"
REDIS_HOST = os.getenv("SPIDER_ONE_REDIS_HOST", "117.50.131.232")
REDIS_PORT = int(os.getenv("SPIDER_ONE_REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("SPIDER_ONE_REDIS_DB", "1"))
REDIS_PASSWORD = os.getenv("SPIDER_ONE_REDIS_PASSWORD", "Yb$]Mdh3YU2k}hw")
if REDIS_PASSWORD:
    DEFAULT_REDIS_URL = (
        f"redis://:{quote_plus(REDIS_PASSWORD)}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    )
else:
    DEFAULT_REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
REDIS_KEY_DOCTOR_INFO_URL = "doctor_dzys:doctor_info_url"
REDIS_KEY_DOCTOR_INFO_DONE = "doctor_dzys:doctor_info_done"
DEFAULT_PROFILE: dict[str, Any] = {
    "project": {
        "site": SOURCE_SITE,
    },
    "source": {
        "sitemap_url": DEFAULT_SITEMAP_URL,
        "detail_max_workers": 20,
        "timeout_seconds": 30,
        "max_retries": 3,
        "fetch_detail": True,
        "max_records": 0,
        "skip_placeholder_doctors": True,
        "skip_suspicious_hospitals": True,
    },
    "redis": {
        "url": DEFAULT_REDIS_URL,
        "doctor_info_url": REDIS_KEY_DOCTOR_INFO_URL,
        "doctor_info_done": REDIS_KEY_DOCTOR_INFO_DONE,
    },
    "mongodb": {
        "host": "101.200.125.240",
        "port": 27017,
        "username": "admin",
        "password": "a@Mfv8k!r@8r@8&R",
        "auth_source": "admin",
        "database": DEFAULT_HOSPITAL_DB,
        "doctor_collection": DEFAULT_DOCTOR_COLLECTION,
    },
}

logger = logging.getLogger("doctor-dzys-spider")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

EDGE_NOISE_CHARS = "'\"`,，。.;；:：、/\\|+-_!！?？*"
DECORATIVE_CHARS = "✔️✓✘✖★☆"
HOSPITAL_KEYWORDS = (
    "医院",
    "中医院",
    "人民医院",
    "妇幼保健院",
    "儿童医院",
    "总医院",
    "附属医院",
    "康复医院",
    "疗养院",
    "卫生院",
    "卫生所",
    "卫生服务中心",
    "卫生服务站",
    "社区卫生服务中心",
    "社区卫生服务站",
    "医疗中心",
    "分院",
    "院区",
)
SUSPICIOUS_HOSPITAL_KEYWORDS = (
    "割包皮",
    "阳痿早泄",
    "阳痿",
    "早泄",
    "包茎",
    "生殖器疱疹",
    "宫颈糜烂",
    "不孕症",
    "不育症",
    "附件炎",
    "乳腺炎",
    "痤疮",
    "痔疮",
    "hpv",
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_multiline_text(value: str) -> str:
    text = re.sub(r"\r\n?", "\n", value or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def normalize_doctor_name(name: str) -> str:
    return normalize_text(name)


def normalize_hospital_name(name: str) -> str:
    normalized = normalize_text(name)
    previous = None
    while normalized != previous:
        previous = normalized
        normalized = normalized.strip(EDGE_NOISE_CHARS).strip()
        normalized = normalized.strip(DECORATIVE_CHARS).strip()
    return normalized


def is_placeholder_doctor_name(name: str) -> bool:
    normalized = normalize_doctor_name(name)
    if not normalized:
        return True
    if "医生" in normalized:
        return True
    if normalized.isdigit():
        return True
    return len(normalized) < 2


def is_viable_hospital_name(name: str) -> bool:
    normalized = normalize_hospital_name(name)
    if not normalized:
        return False
    if len(normalized) < 2:
        return False
    if normalized.isdigit():
        return False
    if any(keyword.lower() in normalized.lower() for keyword in SUSPICIOUS_HOSPITAL_KEYWORDS):
        return False
    return any(keyword in normalized for keyword in HOSPITAL_KEYWORDS)


def build_mongo_client(mongodb_config: dict[str, Any]):
    if pymongo is None:
        raise RuntimeError("未安装 pymongo，无法写入 MongoDB")

    uri = str(mongodb_config.get("uri", "")).strip()
    if uri:
        return pymongo.MongoClient(uri)

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


def dump_task(task: dict[str, object]) -> str:
    return json.dumps(task, ensure_ascii=False, separators=(",", ":"))


def load_task(task_data: bytes | str) -> dict[str, object]:
    if isinstance(task_data, bytes):
        task_data = task_data.decode("utf-8")
    return json.loads(task_data)


class InMemoryRedisClient:
    def __init__(self) -> None:
        self._sets: dict[str, set[str]] = {}
        self._lock = Lock()

    def ping(self) -> bool:
        return True

    def delete(self, *keys: str) -> int:
        with self._lock:
            removed = 0
            for key in keys:
                if key in self._sets:
                    removed += 1
                    del self._sets[key]
            return removed

    def sadd(self, key: str, *values: str) -> int:
        with self._lock:
            members = self._sets.setdefault(key, set())
            added = 0
            for value in values:
                if value not in members:
                    members.add(value)
                    added += 1
            return added

    def smembers(self, key: str) -> set[str]:
        with self._lock:
            return set(self._sets.get(key, set()))

    def srem(self, key: str, *values: str) -> int:
        with self._lock:
            members = self._sets.get(key)
            if not members:
                return 0
            removed = 0
            for value in values:
                if value in members:
                    members.remove(value)
                    removed += 1
            if not members:
                self._sets.pop(key, None)
            return removed

    def scard(self, key: str) -> int:
        with self._lock:
            return len(self._sets.get(key, set()))

    def sismember(self, key: str, value: str) -> bool:
        with self._lock:
            return value in self._sets.get(key, set())


def build_redis_client(redis_config: dict[str, Any]):
    redis_url = str(redis_config.get("url") or DEFAULT_REDIS_URL).strip()
    if redis is None:
        logger.warning("未安装 redis 包，使用内存队列代替 Redis")
        return InMemoryRedisClient()

    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:  # pragma: no cover - 依赖现场 Redis
        logger.warning("Redis 连接失败，回退到内存队列: %s", exc)
        return InMemoryRedisClient()


def get_doctor_collection_name(mongodb_config: dict[str, Any]) -> str:
    return str(
        mongodb_config.get("doctor_collection")
        or mongodb_config.get("collection")
        or DEFAULT_DOCTOR_COLLECTION
    )


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
) -> dict[str, str]:
    return {
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


def extract_detail_urls_from_sitemap(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    urls: list[str] = []
    for anchor in soup.select('a[href*="/hospital/doctor_home/"]'):
        href = anchor.get("href", "")
        if not href:
            continue
        detail_url = urljoin(page_url, href)
        if detail_url in seen:
            continue
        seen.add(detail_url)
        urls.append(detail_url)
    return urls


def _extract_doctor_id(detail_url: str) -> str:
    match = re.search(r"/hospital/doctor_home/(\d+)\.html$", detail_url)
    if not match:
        raise ValueError(f"无法从详情链接提取 doctor_id: {detail_url}")
    return match.group(1)


def _clean_title_text(raw_title: str, hospital_name: str) -> str:
    title = normalize_text(raw_title)
    if hospital_name and title.startswith(hospital_name):
        title = title[len(hospital_name) :].strip()
    title = re.sub(r"^[\s|/·、,-]+", "", title)
    return title


def _extract_doctor_avatar_url(
    soup: BeautifulSoup,
    doctor_id: str,
    doctor_name: str,
    detail_url: str,
) -> str:
    normalized_doctor_name = normalize_doctor_name(doctor_name)
    avatar_marker = f"/doctor_img/doctor-{doctor_id}.".lower() if doctor_id else ""
    search_roots = [
        soup.select_one("div.docad_doctor"),
        soup.select_one("main"),
        soup,
    ]

    for scope in search_roots:
        if scope is None:
            continue

        if normalized_doctor_name:
            avatar_node = scope.find("img", alt=normalized_doctor_name)
            if avatar_node and avatar_node.get("src"):
                avatar_src = normalize_text(avatar_node.get("src", ""))
                if "/doctor_img/doctor-0." not in avatar_src.lower():
                    return urljoin(detail_url, avatar_src)

        for img in scope.find_all("img"):
            src = normalize_text(img.get("src", ""))
            if not src:
                continue
            lower_src = src.lower()
            if "logo" in lower_src:
                continue
            if "/doctor_img/doctor-0." in lower_src:
                continue
            if avatar_marker and avatar_marker in lower_src:
                return urljoin(detail_url, src)

    return ""


def parse_doctor_detail_page(detail_url: str, html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    doctor_id = _extract_doctor_id(detail_url)

    detail_root = soup.select_one("div.det_doctor")
    if detail_root is None:
        raise ValueError(f"详情页缺少主内容区: {detail_url}")

    name_node = detail_root.select_one("h1.name")
    department_node = detail_root.select_one("span.depart")
    level_node = detail_root.select_one("p.level")

    hospital_link = level_node.find("a") if level_node else None
    hospital_name = normalize_hospital_name(
        hospital_link.get_text(" ", strip=True) if hospital_link else ""
    )
    level_text = normalize_text(level_node.get_text(" ", strip=True) if level_node else "")
    doctor_title = _clean_title_text(level_text, hospital_name)

    specialties = ""
    intro = ""
    for intro_node in detail_root.select("p.intro"):
        label_node = intro_node.find("strong")
        value_node = intro_node.find("span")
        label = normalize_text(label_node.get_text(" ", strip=True) if label_node else "")
        value = normalize_multiline_text(value_node.get_text(" ", strip=True) if value_node else "")
        if "擅长" in label:
            specialties = value
        elif "简介" in label:
            intro = value

    return build_doctor_record(
        doctor_id=doctor_id,
        doctor_name=normalize_doctor_name(name_node.get_text(" ", strip=True)) if name_node else "",
        doctor_hospital=hospital_name,
        doctor_department=normalize_doctor_name(
            department_node.get_text(" ", strip=True) if department_node else ""
        ),
        doctor_title=doctor_title,
        doctor_avatar_url=_extract_doctor_avatar_url(
            soup,
            doctor_id,
            name_node.get_text(" ", strip=True) if name_node else "",
            detail_url,
        ),
        doctor_specialties=specialties,
        intro=intro,
        source_site=SOURCE_SITE,
        source_url=detail_url,
        crawl_time="",
    )


def should_keep_doctor(
    record: dict[str, str],
    *,
    skip_placeholder_doctors: bool,
    skip_suspicious_hospitals: bool,
) -> tuple[bool, str]:
    if skip_placeholder_doctors and is_placeholder_doctor_name(record.get("doctor_name", "")):
        return False, "placeholder_doctor_name"
    if not record.get("doctor_hospital", ""):
        return False, "missing_hospital_name"
    if skip_suspicious_hospitals and not is_viable_hospital_name(record.get("doctor_hospital", "")):
        return False, "suspicious_hospital_name"
    return True, ""


class DoctorDzysSpider:
    def __init__(self, profile: dict[str, Any], *, dry_run: bool = False) -> None:
        self.profile = profile
        self.project = profile["project"]
        self.source = profile["source"]
        self.mongodb = profile["mongodb"]
        self.dry_run = dry_run

        self.sitemap_url = str(self.source.get("sitemap_url", DEFAULT_SITEMAP_URL))
        self.detail_max_workers = max(1, int(self.source.get("detail_max_workers", 8)))
        self.timeout_seconds = int(self.source.get("timeout_seconds", 30))
        self.max_retries = int(self.source.get("max_retries", 3))
        self.fetch_detail = bool(self.source.get("fetch_detail", True))
        self.max_records = int(self.source.get("max_records", 0))
        self.skip_placeholder_doctors = bool(self.source.get("skip_placeholder_doctors", True))
        self.skip_suspicious_hospitals = bool(self.source.get("skip_suspicious_hospitals", True))
        self.crawl_time = datetime.now().strftime("%Y-%m-%d")
        self.redis_config = profile.get("redis", {})
        self.redis_pending_key = str(
            self.redis_config.get("doctor_info_url", REDIS_KEY_DOCTOR_INFO_URL)
        )
        self.redis_done_key = str(
            self.redis_config.get("doctor_info_done", REDIS_KEY_DOCTOR_INFO_DONE)
        )
        self.redis_client = build_redis_client(self.redis_config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36"
                ),
                "Referer": self.sitemap_url,
            }
        )
        self.collection = None
        if not self.dry_run:
            mongo_client = build_mongo_client(self.mongodb)
            database = mongo_client[self.mongodb["database"]]
            self.collection = database[get_doctor_collection_name(self.mongodb)]

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

    def save_doctor(self, data: dict[str, str]) -> None:
        if self.collection is None:
            return
        self.collection.replace_one({"_id": data["_id"]}, data, upsert=True)

    def seed_detail_tasks(self, detail_urls: list[str]) -> int:
        inserted = 0
        for detail_url in detail_urls:
            detail_task = {
                "doctor_id": _extract_doctor_id(detail_url),
                "detail_url": detail_url,
                "source_url": detail_url,
            }
            inserted += int(self.redis_client.sadd(self.redis_pending_key, dump_task(detail_task)))
        return inserted

    def load_pending_detail_tasks(self) -> list[tuple[str, dict[str, object]]]:
        raw_tasks = sorted(self.redis_client.smembers(self.redis_pending_key))
        return [(raw_task, load_task(raw_task)) for raw_task in raw_tasks]

    def fetch_detail_record(self, detail_url: str) -> dict[str, str]:
        detail_html = self.request_html(detail_url)
        record = parse_doctor_detail_page(detail_url, detail_html)
        record["crawl_time"] = self.crawl_time
        return record

    def run(self) -> dict[str, Any]:
        logger.info("开始执行大众网医生采集")
        logger.info("站点: %s", self.project.get("site", SOURCE_SITE))
        logger.info("种子页: %s", self.sitemap_url)
        logger.info("详情并发数: %s", self.detail_max_workers)
        logger.info("详情抓取: %s", self.fetch_detail)
        logger.info("最大入库条数: %s", self.max_records or "不限")
        logger.info("过滤占位姓名: %s", self.skip_placeholder_doctors)
        logger.info("过滤可疑医院: %s", self.skip_suspicious_hospitals)
        logger.info("MongoDB: %s", "dry-run" if self.collection is None else get_doctor_collection_name(self.mongodb))
        logger.info("Redis 队列: %s", self.redis_pending_key)
        logger.info("-" * 60)

        if not self.fetch_detail:
            logger.warning("doctor_dzys 需要详情页补全字段，已自动启用详情抓取")
            self.fetch_detail = True

        sitemap_html = self.request_html(self.sitemap_url)
        detail_urls = extract_detail_urls_from_sitemap(self.sitemap_url, sitemap_html)
        logger.info("种子页原始医生链接数: %s", len(detail_urls))
        if self.max_records:
            detail_urls = detail_urls[: self.max_records]
        logger.info("本次处理医生链接数: %s", len(detail_urls))

        self.redis_client.delete(self.redis_pending_key, self.redis_done_key)
        queued_count = self.seed_detail_tasks(detail_urls)
        logger.info("Redis 中间详情入队数: %s", queued_count)
        logger.info("Redis 当前待处理数: %s", self.redis_client.scard(self.redis_pending_key))

        records: list[dict[str, str]] = []
        kept_count = 0
        skipped_count = 0
        skipped_reason_counts: dict[str, int] = {}
        pending_tasks = self.load_pending_detail_tasks()
        logger.info("Redis 取出待处理详情数: %s", len(pending_tasks))

        if self.fetch_detail:
            detail_results: dict[int, dict[str, str]] = {}
            with ThreadPoolExecutor(max_workers=self.detail_max_workers) as executor:
                future_to_index = {
                    executor.submit(self.fetch_detail_record, task[1]["detail_url"]): index
                    for index, task in enumerate(pending_tasks)
                }
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    raw_task, task = pending_tasks[index]
                    detail_url = str(task["detail_url"])
                    try:
                        detail_results[index] = future.result()
                        self.redis_client.srem(self.redis_pending_key, raw_task)
                        self.redis_client.sadd(self.redis_done_key, str(task["doctor_id"]))
                    except Exception as exc:  # pragma: no cover - 依赖现场网络
                        skipped_count += 1
                        skipped_reason_counts["detail_request_failed"] = (
                            skipped_reason_counts.get("detail_request_failed", 0) + 1
                        )
                        logger.error("详情页失败: %s | 原因: %s", detail_url, exc)
            ordered_records = [detail_results[index] for index in sorted(detail_results)]

        for record in ordered_records:
            keep, reason = should_keep_doctor(
                record,
                skip_placeholder_doctors=self.skip_placeholder_doctors,
                skip_suspicious_hospitals=self.skip_suspicious_hospitals,
            )
            if not keep:
                skipped_count += 1
                skipped_reason_counts[reason] = skipped_reason_counts.get(reason, 0) + 1
                continue

            self.save_doctor(record)
            records.append(record)
            kept_count += 1

        logger.info("Redis 剩余待处理数: %s", self.redis_client.scard(self.redis_pending_key))
        logger.info("Redis 已完成数: %s", self.redis_client.scard(self.redis_done_key))

        if records:
            sample = records[0]
            logger.info("样本记录:")
            for field_name, field_value in sample.items():
                logger.info("  %s: %s", field_name, field_value)
        else:
            logger.info("没有保留下任何记录")

        logger.info("原始链接数: %s", len(detail_urls))
        logger.info("保留条数: %s", kept_count)
        logger.info("跳过条数: %s", skipped_count)
        logger.info("跳过原因: %s", skipped_reason_counts)
        logger.info("采集完成")

        return {
            "source_url": self.sitemap_url,
            "raw_link_count": len(detail_urls),
            "kept_count": kept_count,
            "skipped_count": skipped_count,
            "skipped_reason_counts": skipped_reason_counts,
            "dry_run": self.dry_run,
        }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="大众网医生采集")
    parser.add_argument("--dry-run", action="store_true", help="只抓取并打印，不写入 MongoDB")
    parser.add_argument("--limit", type=int, default=0, help="最多保留多少条记录，0 表示不限")
    parser.add_argument("--sitemap-url", default=DEFAULT_SITEMAP_URL, help="医生 sitemap 入口")
    parser.add_argument("--detail-workers", type=int, default=20, help="详情页并发数")
    return parser


def build_profile(args: argparse.Namespace) -> dict[str, Any]:
    profile = json.loads(json.dumps(DEFAULT_PROFILE))
    profile["source"]["sitemap_url"] = args.sitemap_url
    profile["source"]["detail_max_workers"] = max(1, int(args.detail_workers))
    profile["source"]["max_records"] = max(0, int(args.limit))
    return profile


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    profile = build_profile(args)
    spider = DoctorDzysSpider(profile, dry_run=bool(args.dry_run))
    result = spider.run()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
