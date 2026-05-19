"""doctor_hnyygh 项目的站点常量与命名约定。"""

from __future__ import annotations


MAIN_BASE_URL = "https://www.169000.net"

DOCTOR_COLLECTION_NAME = "doctor_hnyygh"
HOSPITAL_COLLECTION_NAME = "hospital_hnyygh"


def build_entry_seed_records() -> list[dict[str, str]]:
    return [
        {
            "category": "area",
            "url": f"{MAIN_BASE_URL}/fastGh/1",
        }
    ]


def build_redis_keys(prefix: str = "doctor_hnyygh") -> dict[str, str]:
    normalized_prefix = str(prefix).strip() or "doctor_hnyygh"
    return {
        "area_index_url": f"{normalized_prefix}:area_index_url",
        "hospital_list_url": f"{normalized_prefix}:hospital_list_url",
        "department_list_url": f"{normalized_prefix}:department_list_url",
        "doctor_list_url": f"{normalized_prefix}:doctor_list_url",
        "doctor_info_url": f"{normalized_prefix}:doctor_info_url",
    }
