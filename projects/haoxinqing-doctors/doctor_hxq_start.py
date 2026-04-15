from __future__ import annotations

import argparse
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pymongo
import requests
import yaml


logger = logging.getLogger("haoxinqing-doctor-spider")
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


def load_profile(profile_path: Path) -> dict[str, Any]:
    """读取 profile.yml，并检查基础配置是否存在。"""
    profile = yaml.safe_load(Path(profile_path).read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("profile.yml 必须是字典结构")

    required_sections = ("project", "source", "mongodb")
    for section_name in required_sections:
        if not isinstance(profile.get(section_name), dict):
            raise ValueError(f"缺少配置段: {section_name}")

    return profile


def normalize_mongodb_uri(uri: str) -> str:
    """把 MongoDB URI 里的账号密码做转义，避免特殊字符报错。"""
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
    """按配置创建 MongoDB 客户端，支持 uri 或账号密码两种写法。"""
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


class HaoxinqingDoctorSpider:
    """好心情医生采集脚本，负责请求接口、整理字段并写入 MongoDB。"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
    ]

    def __init__(self, profile: dict[str, Any]) -> None:
        """读取配置并初始化 MongoDB 集合和请求参数。"""
        self.profile = profile
        self.project = profile["project"]
        self.source = profile["source"]
        self.mongodb = profile["mongodb"]

        self.base_url = self.source["base_url"]
        self.page_size = int(self.source["page_size"])
        self.start_page = int(self.source["start_page"])
        self.max_pages = int(self.source["max_pages"])
        self.timeout_seconds = int(self.source["timeout_seconds"])
        self.max_retries = int(self.source.get("max_retries", 3))
        self.grab_data = datetime.now().strftime("%Y-%m-%d")
        self.headers = {
            "Host": "papi.haoxinqing.cn",
            "Origin": "https://mp.haoxinqing.cn",
            "Referer": "https://mp.haoxinqing.cn/doctor/list",
            "Accept": "application/json, text/plain, */*",
        }

        self.mongo_client = build_mongo_client(self.mongodb)
        self.collection = self.mongo_client[self.mongodb["database"]][self.mongodb["collection"]]
        self.seen_doctor_ids: set[str] = set()

    def build_page_url(self, page_number: int) -> str:
        """拼出某一页的接口地址。"""
        return f"{self.base_url}?pn={page_number}&ps={self.page_size}"

    def request_page(self, page_number: int) -> dict[str, Any]:
        """请求单页接口，并处理系统错误和错页重试。"""
        page_url = self.build_page_url(page_number)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            self.headers["User-Agent"] = random.choice(self.USER_AGENTS)
            logger.info("[第 %s 页] 第 %s 次请求", page_number, attempt)
            logger.info("[第 %s 页] 请求地址: %s", page_number, page_url)

            try:
                response = requests.get(
                    url=page_url,
                    headers=self.headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                last_error = exc
                logger.error("[第 %s 页] 请求失败: %s", page_number, exc)
                if attempt == self.max_retries:
                    raise
                continue

            if payload.get("code") == 4998 or payload.get("msg") == "系统错误":
                logger.warning("[第 %s 页] 返回系统错误，准备重试", page_number)
                if attempt == self.max_retries:
                    raise ValueError(f"第 {page_number} 页连续返回系统错误")
                continue

            response_page_number = self.get_response_page_number(payload)
            if response_page_number is not None and response_page_number != page_number:
                logger.warning(
                    "[第 %s 页] 响应页码异常，实际返回页码是 %s，准备重试",
                    page_number,
                    response_page_number,
                )
                if attempt == self.max_retries:
                    raise ValueError(f"第 {page_number} 页连续返回错页响应")
                continue

            return payload

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"第 {page_number} 页请求失败")

    def get_response_page_number(self, payload: dict[str, Any]) -> int | None:
        """读取响应里的真实页码，用来判断有没有错页。"""
        try:
            response_page_number = payload["result"]["doctor"].get("pn")
        except Exception as exc:
            raise ValueError("响应缺少 result.doctor.pn") from exc

        if isinstance(response_page_number, int):
            return response_page_number
        return None

    def get_doctor_list(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """从响应里取出医生列表。"""
        try:
            doctor_list = payload["result"]["doctor"]["list"]
        except Exception as exc:
            raise ValueError("响应缺少 result.doctor.list") from exc

        if not isinstance(doctor_list, list):
            raise ValueError("result.doctor.list 不是列表")
        return [doctor for doctor in doctor_list if isinstance(doctor, dict)]

    def build_avatar_url(self, head_path: object) -> str | None:
        """把头像相对路径拼成完整地址。"""
        if not isinstance(head_path, str) or not head_path.strip():
            return None
        return f"https://online-file.haoxinqing.cn/{head_path.lstrip('/')}"

    def build_profile_url(self, doctor_id: str) -> str:
        """按前台规则拼出医生主页链接。"""
        return f"https://www.haoxinqing.cn/doctor/{doctor_id}.html"

    def build_doctor_data(self, doctor: dict[str, Any], page_url: str) -> dict[str, Any] | None:
        """把原始医生字段整理成最终入库结构。"""
        doctor_id = str(doctor.get("id", "")).strip()
        if not doctor_id:
            return None

        data = {
            "_id": doctor_id,
            "doctor_id": doctor_id,
            "name": doctor.get("name", ""),
            "hospital_name": doctor.get("hospitalName", ""),
            "department_name": doctor.get("departmentName", ""),
            "title": doctor.get("typeName", ""),
            "avatar_url": self.build_avatar_url(doctor.get("headPath")),
            "profile_url": self.build_profile_url(doctor_id),
            "territory": doctor.get("territory", ""),
            "intro": doctor.get("intro", ""),
            "disease_names": doctor.get("diseaseNames", ""),
            "city_id": doctor.get("cityId", ""),
            "province_id": doctor.get("provinceId", ""),
            "hospital_id_hxq": doctor.get("hospitalId", ""),
            "department_id_hxq": doctor.get("departmentId", ""),
            "evaluation_score": doctor.get("evaluationScore", ""),
            "source_site": self.project["site"],
            "source_url": page_url,
            "grab_data": self.grab_data,
        }
        return data

    def print_sample_data(self, page_number: int, data: dict[str, Any]) -> None:
        """按行打印一条样本记录，方便人工核对字段和值。"""
        logger.info("[第 %s 页] 本次入库字段:", page_number)
        for field_name in data.keys():
            logger.info("  - %s", field_name)

        logger.info("[第 %s 页] 样本记录:", page_number)
        for field_name, field_value in data.items():
            logger.info("  %s: %s", field_name, field_value)

    def save_doctor(self, data: dict[str, Any]) -> None:
        """按 _id 覆盖写入单条医生数据。"""
        self.collection.replace_one({"_id": data["_id"]}, data, upsert=True)

    def run(self) -> dict[str, Any]:
        """按页采集好心情医生，并把结果顺序写入 MongoDB。"""
        raw_row_count = 0
        unique_row_count = 0
        mongodb_upsert_count = 0
        last_page = 0
        empty_page_number: int | None = None

        logger.info("开始执行好心情医生采集")
        logger.info("接口地址: %s", self.base_url)
        logger.info("分页大小: %s", self.page_size)
        logger.info("起始页: %s", self.start_page)
        logger.info("最大页数: %s", self.max_pages)
        logger.info("MongoDB 库: %s", self.mongodb["database"])
        logger.info("MongoDB 集合: %s", self.mongodb["collection"])
        logger.info("-" * 60)

        for page_number in range(self.start_page, self.max_pages + 1):
            page_url = self.build_page_url(page_number)
            payload = self.request_page(page_number)
            doctor_list = self.get_doctor_list(payload)

            if not doctor_list:
                empty_page_number = page_number
                logger.info("[第 %s 页] 当前页为空，停止采集", page_number)
                break

            raw_row_count += len(doctor_list)
            last_page = page_number

            page_data_list: list[dict[str, Any]] = []
            for doctor in doctor_list:
                data = self.build_doctor_data(doctor, page_url)
                if data is None:
                    continue
                if data["doctor_id"] in self.seen_doctor_ids:
                    continue
                self.seen_doctor_ids.add(data["doctor_id"])
                page_data_list.append(data)

            logger.info("[第 %s 页] 原始条数: %s", page_number, len(doctor_list))
            logger.info("[第 %s 页] 去重后条数: %s", page_number, len(page_data_list))
            logger.info("[第 %s 页] 跳过重复条数: %s", page_number, len(doctor_list) - len(page_data_list))

            if page_data_list:
                self.print_sample_data(page_number, page_data_list[0])
            else:
                logger.info("[第 %s 页] 本页没有新的记录需要入库", page_number)

            saved_count = 0
            for data in page_data_list:
                try:
                    self.save_doctor(data)
                    saved_count += 1
                except Exception as exc:
                    logger.error("[第 %s 页] 入库失败，doctor_id=%s，错误=%s", page_number, data["_id"], exc)
                    raise

            unique_row_count += len(page_data_list)
            mongodb_upsert_count += saved_count
            logger.info("[第 %s 页] 入库成功数: %s", page_number, saved_count)
            logger.info("-" * 60)

            if len(doctor_list) < self.page_size:
                empty_page_number = page_number + 1
                logger.info("[第 %s 页] 当前页条数小于 page_size，下一页视为空页并停止", page_number)
                break

        result = {
            "last_page": last_page,
            "empty_page_number": empty_page_number,
            "raw_row_count": raw_row_count,
            "unique_row_count": unique_row_count,
            "duplicate_row_count": raw_row_count - unique_row_count,
            "mongodb_upsert_count": mongodb_upsert_count,
        }

        logger.info("采集完成")
        logger.info("最后成功页: %s", result["last_page"])
        logger.info("空页页码: %s", result["empty_page_number"])
        logger.info("原始总条数: %s", result["raw_row_count"])
        logger.info("去重后总条数: %s", result["unique_row_count"])
        logger.info("重复总条数: %s", result["duplicate_row_count"])
        logger.info("MongoDB 入库总数: %s", result["mongodb_upsert_count"])
        return result


def main(argv: list[str] | None = None) -> int:
    """读取配置并启动采集脚本。"""
    parser = argparse.ArgumentParser(description="好心情医生采集启动脚本")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("profile.yml"),
        help="profile.yml 路径，默认读取当前目录下的 profile.yml",
    )
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    spider = HaoxinqingDoctorSpider(profile)
    result = spider.run()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
