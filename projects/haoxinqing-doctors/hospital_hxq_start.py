from __future__ import annotations

import argparse
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import requests

from doctor_hxq_start import build_mongo_client, get_doctor_collection_name, load_profile


logger = logging.getLogger("haoxinqing-hospital-spider")
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


def get_hospital_collection_name(mongodb_config: dict[str, Any]) -> str:
    """优先读取 hospital_collection，未配置时默认 hospital_hxq。"""
    return str(mongodb_config.get("hospital_collection") or "hospital_hxq")


def build_file_url(path: object) -> str | None:
    """把相对文件路径拼成完整文件地址。"""
    if not isinstance(path, str) or not path.strip():
        return None
    return f"https://online-file.haoxinqing.cn/{path.lstrip('/')}"


def normalize_hospital_id(raw_hospital_id: object) -> str | None:
    """把原始 hospital_id_hxq 规范化；空值和占位值返回 None。"""
    if raw_hospital_id is None:
        return None

    hospital_id = str(raw_hospital_id).strip()
    if hospital_id in {"", "0", "None", "null"}:
        return None
    return hospital_id


def build_hospital_level_text(hospital_level: object, hospital_etc: object) -> str:
    """把医院等级和等次代码拼成常见展示文案。"""
    level_map = {
        1: "三",
        2: "二",
        3: "一",
    }
    etc_map = {
        1: "",
        2: "甲",
        3: "乙",
        4: "丙",
    }

    level_text = level_map.get(hospital_level, "")
    etc_text = etc_map.get(hospital_etc, "")
    return f"{level_text}{etc_text}" if level_text or etc_text else ""


def build_hospital_data(
    hospital_payload: dict[str, Any],
    crawl_time: str,
    website: str = "好心情",
    hospital_url: str | None = None,
) -> dict[str, Any]:
    """把医院接口字段整理成最终落库结构。"""
    hospital_id = str(hospital_payload.get("id", "")).strip()
    if not hospital_id:
        raise ValueError("医院详情缺少 id")

    return {
        "_id": hospital_id,
        "hospital_id": hospital_id,
        "name": hospital_payload.get("name", ""),
        "alias": hospital_payload.get("alias", ""),
        "address": hospital_payload.get("address", ""),
        "hospital_level_text": build_hospital_level_text(
            hospital_payload.get("hospitalLevel"),
            hospital_payload.get("hospitalEtc"),
        ),
        "hospital_avatar_url": build_file_url(hospital_payload.get("coverImg")),
        "intro": hospital_payload.get("intro", ""),
        "website": website,
        "hospital_url": hospital_url,
        "crawl_time": crawl_time,
    }


class HaoxinqingHospitalSpider:
    """从医生集合抽取医院 ID，再抓取好心情医院详情并入库。"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
    ]

    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile
        self.project = profile["project"]
        self.mongodb = profile["mongodb"]
        self.hospital_source = profile.get("hospital_source") or {
            "base_url": "https://gw.haoxinqing.cn/papi/hospital/get",
            "timeout_seconds": profile["source"].get("timeout_seconds", 30),
            "max_retries": profile["source"].get("max_retries", 3),
        }

        self.base_url = self.hospital_source["base_url"]
        self.timeout_seconds = int(self.hospital_source.get("timeout_seconds", 30))
        self.max_retries = int(self.hospital_source.get("max_retries", 3))
        self.crawl_time = datetime.now().strftime("%Y-%m-%d")
        self.headers = {
            "Origin": "https://www.haoxinqing.cn",
            "Referer": "https://www.haoxinqing.cn/",
            "Accept": "application/json, text/plain, */*",
        }

        self.mongo_client = build_mongo_client(self.mongodb)
        database = self.mongo_client[self.mongodb["database"]]
        self.doctor_collection = database[get_doctor_collection_name(self.mongodb)]
        self.hospital_collection = database[get_hospital_collection_name(self.mongodb)]
        self.skipped_invalid_hospital_id_count = 0

    def iter_unique_hospital_ids(self) -> Iterable[str]:
        """从医生集合里抽取去重后的 hospital_id_hxq。"""
        seen_ids: set[str] = set()
        for record in self.doctor_collection.find(
            {"hospital_id_hxq": {"$nin": ["", None]}},
            {"hospital_id_hxq": 1},
        ):
            hospital_id = normalize_hospital_id(record.get("hospital_id_hxq"))
            if hospital_id is None:
                self.skipped_invalid_hospital_id_count += 1
                continue
            if hospital_id in seen_ids:
                continue
            seen_ids.add(hospital_id)
            yield hospital_id

    def request_hospital_payload(self, hospital_id: str) -> dict[str, Any]:
        """请求单个医院详情，接口要求 form data 而不是 JSON。"""
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            self.headers["User-Agent"] = random.choice(self.USER_AGENTS)
            logger.info("[医院 %s] 第 %s 次请求", hospital_id, attempt)
            logger.info("[医院 %s] 请求地址: %s", hospital_id, self.base_url)

            try:
                response = requests.post(
                    self.base_url,
                    data={"hospitalId": hospital_id},
                    headers=self.headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                last_error = exc
                logger.error("[医院 %s] 请求失败: %s", hospital_id, exc)
                if attempt == self.max_retries:
                    raise
                continue

            if payload.get("code") != 1000:
                last_error = ValueError(
                    f"医院 {hospital_id} 返回异常: code={payload.get('code')}, msg={payload.get('msg')}"
                )
                logger.warning("[医院 %s] 返回异常，准备重试: %s", hospital_id, last_error)
                if attempt == self.max_retries:
                    raise last_error
                continue

            result = payload.get("result")
            if not isinstance(result, dict):
                raise ValueError(f"医院 {hospital_id} 的 result 不是字典")
            return result

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"医院 {hospital_id} 请求失败")

    def print_sample_data(self, hospital_id: str, data: dict[str, Any]) -> None:
        """打印单条医院样本，方便人工核对。"""
        logger.info("[医院 %s] 本次入库字段:", hospital_id)
        for field_name in data.keys():
            logger.info("  - %s", field_name)

        logger.info("[医院 %s] 样本记录:", hospital_id)
        for field_name, field_value in data.items():
            logger.info("  %s: %s", field_name, field_value)

    def save_hospital(self, data: dict[str, Any]) -> None:
        """按 _id 覆盖写入医院详情。"""
        self.hospital_collection.replace_one({"_id": data["_id"]}, data, upsert=True)

    def run(self) -> dict[str, Any]:
        """顺序抓取医院详情并写入 MongoDB。"""
        hospital_ids = list(self.iter_unique_hospital_ids())
        raw_hospital_count = len(hospital_ids)
        saved_count = 0

        logger.info("开始执行好心情医院详情采集")
        logger.info("医院详情接口: %s", self.base_url)
        logger.info("医生来源集合: %s", get_doctor_collection_name(self.mongodb))
        logger.info("医院目标集合: %s", get_hospital_collection_name(self.mongodb))
        logger.info("待抓取医院数: %s", raw_hospital_count)
        logger.info("跳过无效医院ID数: %s", self.skipped_invalid_hospital_id_count)
        logger.info("-" * 60)

        for index, hospital_id in enumerate(hospital_ids, start=1):
            logger.info("[医院 %s] 进度: %s/%s", hospital_id, index, raw_hospital_count)
            hospital_payload = self.request_hospital_payload(hospital_id)
            data = build_hospital_data(
                hospital_payload=hospital_payload,
                crawl_time=self.crawl_time,
                website=self.project.get("site", "好心情"),
                hospital_url=None,
            )
            self.print_sample_data(hospital_id, data)
            self.save_hospital(data)
            saved_count += 1
            logger.info("[医院 %s] 入库成功", hospital_id)
            logger.info("-" * 60)

        result = {
            "raw_hospital_count": raw_hospital_count,
            "skipped_invalid_hospital_id_count": self.skipped_invalid_hospital_id_count,
            "mongodb_upsert_count": saved_count,
            "hospital_collection": get_hospital_collection_name(self.mongodb),
        }
        logger.info("医院详情采集完成")
        logger.info("原始医院数: %s", result["raw_hospital_count"])
        logger.info("跳过无效医院ID数: %s", result["skipped_invalid_hospital_id_count"])
        logger.info("MongoDB 入库总数: %s", result["mongodb_upsert_count"])
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="好心情医院详情采集启动脚本")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("profile.yml"),
        help="profile.yml 路径，默认读取当前目录下的 profile.yml",
    )
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    spider = HaoxinqingHospitalSpider(profile)
    result = spider.run()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
