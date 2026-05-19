"""从医生集合补全医院基础信息。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from pymongo import MongoClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_circle import settings
from doctor_circle.spiders.hospital.hospital_base_helpers import (
    build_nhsa_hospital_search_payload,
    build_nhsa_signed_request,
    build_hospital_base_item,
    choose_best_hospital_match,
    decrypt_nhsa_response_data,
    prepare_hospital_name_candidates,
)


REQUEST_TIMEOUT = 20
SLEEP_EVERY = settings.HOSPITAL_DETAIL_SLEEP_EVERY
SLEEP_SECONDS = settings.HOSPITAL_DETAIL_SLEEP_SECONDS


def build_mongodb_client() -> MongoClient:
    """按项目配置创建 MongoDB 客户端。"""

    return MongoClient(settings.MONGO_URI)


def load_distinct_hospital_names() -> tuple[list[str], dict[str, object]]:
    """从医生集合中读取医院名，并清洗成可查询候选。"""

    mongo_client = build_mongodb_client()
    database = mongo_client[settings.MONGO_DATABASE]
    collection = database[settings.MONGO_DOCTOR_COLLECTION]

    hospital_names = collection.distinct("hospital", {"hospital": {"$exists": True, "$ne": ""}})
    mongo_client.close()
    return prepare_hospital_name_candidates(hospital_names)


def load_processed_hospital_names() -> tuple[set[str], dict[str, object]]:
    """从医院集合中读取已写入的医院查询名，用于断点续跑。"""

    mongo_client = build_mongodb_client()
    database = mongo_client[settings.MONGO_DATABASE]
    collection = database[settings.MONGO_HOSPITAL_COLLECTION]

    processed_query_names = {
        str(name).strip()
        for name in collection.distinct(
            "query_hospital_name",
            {"query_hospital_name": {"$exists": True, "$ne": ""}},
        )
        if str(name).strip()
    }
    processed_hospital_names = {
        str(name).strip()
        for name in collection.distinct(
            "hospital_name",
            {"hospital_name": {"$exists": True, "$ne": ""}},
        )
        if str(name).strip()
    }
    mongo_client.close()

    processed_names = processed_query_names | processed_hospital_names
    summary = {
        "processed_query_name_count": len(processed_query_names),
        "processed_hospital_name_count": len(processed_hospital_names),
        "processed_total_count": len(processed_names),
    }
    return processed_names, summary


def split_pending_hospital_names(
    hospital_names: list[str],
    processed_hospital_names: set[str],
) -> tuple[list[str], dict[str, object]]:
    """剔除已写入医院，返回待处理医院名和断点续跑统计。"""

    pending_hospital_names = [
        hospital_name
        for hospital_name in hospital_names
        if hospital_name not in processed_hospital_names
    ]
    summary = {
        "candidate_count": len(hospital_names),
        "processed_count": len(hospital_names) - len(pending_hospital_names),
        "pending_count": len(pending_hospital_names),
    }
    return pending_hospital_names, summary


def fetch_hospital_base_record(session: requests.Session, hospital_name: str) -> dict[str, object] | None:
    """调用国家医保服务平台查询医院基础信息，并做保守匹配。"""

    payload = build_nhsa_hospital_search_payload(hospital_name)
    headers, body = build_nhsa_signed_request(
        app_code=settings.NHSA_APP_CODE,
        app_secret=settings.NHSA_APP_SECRET,
        public_key_base64=settings.NHSA_PUBLIC_KEY,
        private_key_base64=settings.NHSA_PRIVATE_KEY,
        payload=payload,
    )
    response = session.post(
        settings.NHSA_HOSPITAL_SEARCH_URL,
        headers=headers,
        json=body,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    decrypted_data = decrypt_nhsa_response_data(
        settings.NHSA_APP_CODE,
        settings.NHSA_APP_SECRET,
        response.json(),
    )
    page_data = decrypted_data.get("list", [])
    if not isinstance(page_data, list):
        return None

    return choose_best_hospital_match(hospital_name, page_data)


def write_hospital_items(hospital_names: list[str]) -> tuple[int, int]:
    """逐个医院查询并实时写入独立集合。"""

    mongo_client = build_mongodb_client()
    database = mongo_client[settings.MONGO_DATABASE]
    collection = database[settings.MONGO_HOSPITAL_COLLECTION]
    session = requests.Session()

    resolved_count = 0
    unresolved_count = 0

    for index, hospital_name in enumerate(hospital_names, start=1):
        print(f"[{index}/{len(hospital_names)}] 查询医院: {hospital_name}")
        try:
            matched_record = fetch_hospital_base_record(session, hospital_name)
        except requests.RequestException as error:
            print(f"请求失败，按未命中写入: {hospital_name} | {error}")
            matched_record = None

        item = build_hospital_base_item(hospital_name, matched_record)
        collection.replace_one({"_id": item["_id"]}, item, upsert=True)

        print(
            "结果:",
            {
                "hospital_name": item["hospital_name"],
                "hospital_id": item["hospital_id"],
                "hospital_level": item["hospital_level"],
                "resolved": item["resolved"],
            },
        )

        if item.get("resolved") == "Y":
            resolved_count += 1
        else:
            unresolved_count += 1

        if index % 100 == 0:
            print(
                "已实时写入 MongoDB:",
                {
                    "collection": settings.MONGO_HOSPITAL_COLLECTION,
                    "processed_count": index,
                    "resolved_count": resolved_count,
                    "unresolved_count": unresolved_count,
                },
            )

        if SLEEP_EVERY > 0 and index % SLEEP_EVERY == 0 and index < len(hospital_names):
            print(
                "触发节流休眠:",
                {
                    "processed_count": index,
                    "sleep_seconds": SLEEP_SECONDS,
                },
            )
            time.sleep(SLEEP_SECONDS)

    mongo_client.close()
    return resolved_count, unresolved_count


def main() -> None:
    """执行医院基础信息补全流程。"""

    hospital_names, summary = load_distinct_hospital_names()
    print("MongoDB 医院名清洗结果:", summary)

    if not hospital_names:
        print("没有读到任何医院名，脚本结束。")
        return

    processed_hospital_names, processed_summary = load_processed_hospital_names()
    print("MongoDB 已处理医院统计:", processed_summary)

    pending_hospital_names, resume_summary = split_pending_hospital_names(
        hospital_names,
        processed_hospital_names,
    )
    print("断点续跑过滤结果:", resume_summary)

    if not pending_hospital_names:
        print("所有候选医院都已写入，脚本结束。")
        return

    resolved_count, unresolved_count = write_hospital_items(pending_hospital_names)
    print(
        "写入 MongoDB 完成:",
        {
            "collection": settings.MONGO_HOSPITAL_COLLECTION,
            "resolved_count": resolved_count,
            "unresolved_count": unresolved_count,
            "total_count": len(pending_hospital_names),
        },
    )


if __name__ == "__main__":
    main()
