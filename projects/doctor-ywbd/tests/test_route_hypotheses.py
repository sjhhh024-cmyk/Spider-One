from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.route_hypotheses import (  # noqa: E402
    DOCTOR_COLLECTION_NAME,
    HOSPITAL_COLLECTION_NAME,
    ENTRY_POINTS,
    REDIS_KEY_BY_CATEGORY,
    build_redis_keys,
)


def test_entry_points_match_confirmed_real_pages() -> None:
    assert ENTRY_POINTS == {
        "disease": "https://data.120ask.com/yisheng/jibing.html",
        "department": "https://data.120ask.com/yisheng/keshi.html",
        "area": "https://data.120ask.com/yisheng/area.html",
        "hospital": "https://data.120ask.com/yiyuan/area.html",
    }


def test_redis_keys_split_upstream_routes_and_merge_doctor_detail() -> None:
    assert build_redis_keys() == {
        "disease_index_url": "doctor_ywbd:disease_index_url",
        "disease_list_url": "doctor_ywbd:disease_list_url",
        "department_index_url": "doctor_ywbd:department_index_url",
        "department_list_url": "doctor_ywbd:department_list_url",
        "area_index_url": "doctor_ywbd:area_index_url",
        "area_list_url": "doctor_ywbd:area_list_url",
        "hospital_area_index_url": "doctor_ywbd:hospital_area_index_url",
        "hospital_list_url": "doctor_ywbd:hospital_list_url",
        "hospital_detail_url": "doctor_ywbd:hospital_detail_url",
        "hospital_expert_url": "doctor_ywbd:hospital_expert_url",
        "doctor_info_url": "doctor_ywbd:doctor_info_url",
    }


def test_entry_categories_write_into_stage_one_index_keys() -> None:
    assert REDIS_KEY_BY_CATEGORY == {
        "disease": "disease_index_url",
        "department": "department_index_url",
        "area": "area_index_url",
        "hospital": "hospital_area_index_url",
    }


def test_mongo_collection_name_uses_ywbd_namespace() -> None:
    assert DOCTOR_COLLECTION_NAME == "doctor_ywbd"
    assert HOSPITAL_COLLECTION_NAME == "hospital_ywbd"
