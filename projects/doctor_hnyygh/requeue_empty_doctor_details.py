from __future__ import annotations

import json
import sys
from pathlib import Path

import redis
from pymongo import MongoClient


PROJECT_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = PROJECT_ROOT / "doctor_hnyygh"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


from doctor_hnyygh.probe_helpers import build_doctor_info_api_url
from doctor_hnyygh.route_hypotheses import build_redis_keys
from doctor_hnyygh.settings import (
    MONGO_DATABASE,
    MONGO_DOCTOR_COLLECTION,
    MONGO_URI,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
)
from doctor_hnyygh.redis_requests import build_redis_request_data


def build_empty_detail_query() -> dict:
    return {
        "$and": [
            {"$or": [{"doctor_title": ""}, {"doctor_title": {"$exists": False}}]},
            {"$or": [{"doctor_avatar_url": ""}, {"doctor_avatar_url": {"$exists": False}}]},
            {"$or": [{"doctor_specialties": ""}, {"doctor_specialties": {"$exists": False}}]},
            {"$or": [{"intro": ""}, {"intro": {"$exists": False}}]},
        ]
    }


def build_requeue_payload(record: dict) -> dict:
    doctor_id = str(record.get("doctor_id") or record.get("_id") or "").strip()
    return {
        "url": build_doctor_info_api_url(doctor_id),
        "meta": {
            "doctor_id": doctor_id,
            "doctor_name": str(record.get("doctor_name", "")).strip(),
            "hospital_id": str(record.get("hospital_id", "")).strip(),
            "hospital_name": str(record.get("doctor_hospital", "")).strip(),
            "department_name": str(record.get("doctor_department", "")).strip(),
            "city_id": str(record.get("hospital_city_id", "")).strip(),
            "city_name": str(record.get("hospital_city_name", "")).strip(),
        },
    }


def main() -> None:
    mongo_client = MongoClient(MONGO_URI)
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )
    redis_key = build_redis_keys()["doctor_info_url"]

    try:
        collection = mongo_client[MONGO_DATABASE][MONGO_DOCTOR_COLLECTION]
        query = build_empty_detail_query()
        projection = {
            "_id": 1,
            "doctor_id": 1,
            "doctor_name": 1,
            "doctor_hospital": 1,
            "doctor_department": 1,
            "hospital_id": 1,
            "hospital_city_id": 1,
            "hospital_city_name": 1,
        }
        cursor = collection.find(query, projection)

        scanned = 0
        queued = 0
        samples: list[str] = []
        for record in cursor:
            scanned += 1
            payload = build_requeue_payload(record)
            if not payload["meta"]["doctor_id"]:
                continue
            added = redis_client.sadd(redis_key, build_redis_request_data(payload["url"], meta=payload["meta"]))
            queued += int(added)
            if len(samples) < 10:
                samples.append(json.dumps(payload, ensure_ascii=False))

        print(f"Mongo 命中记录数: {scanned}")
        print(f"Redis 新增入队数: {queued}")
        if samples:
            print("样本任务:")
            for sample in samples:
                print(sample)
    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()
