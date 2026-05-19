from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_hnyygh.route_hypotheses import (  # noqa: E402
    DOCTOR_COLLECTION_NAME,
    HOSPITAL_COLLECTION_NAME,
    MAIN_BASE_URL,
    build_entry_seed_records,
    build_redis_keys,
)


def test_site_constants_match_confirmed_hnyygh_endpoints() -> None:
    assert MAIN_BASE_URL == "https://www.169000.net"


def test_entry_seed_records_start_from_fastgh_root() -> None:
    assert build_entry_seed_records() == [
        {
            "category": "area",
            "url": "https://www.169000.net/fastGh/1",
        }
    ]


def test_redis_keys_cover_stage_flow_and_detail_merge() -> None:
    assert build_redis_keys() == {
        "area_index_url": "doctor_hnyygh:area_index_url",
        "hospital_list_url": "doctor_hnyygh:hospital_list_url",
        "department_list_url": "doctor_hnyygh:department_list_url",
        "doctor_list_url": "doctor_hnyygh:doctor_list_url",
        "doctor_info_url": "doctor_hnyygh:doctor_info_url",
    }


def test_collection_names_use_hnyygh_namespace() -> None:
    assert DOCTOR_COLLECTION_NAME == "doctor_hnyygh"
    assert HOSPITAL_COLLECTION_NAME == "hospital_hnyygh"
