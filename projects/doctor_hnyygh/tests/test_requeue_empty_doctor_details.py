from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_module(filename: str):
    module_path = PROJECT_ROOT / filename
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_empty_detail_query_requires_all_detail_fields_blank() -> None:
    module = load_module("requeue_empty_doctor_details.py")

    assert module.build_empty_detail_query() == {
        "$and": [
            {"$or": [{"doctor_title": ""}, {"doctor_title": {"$exists": False}}]},
            {"$or": [{"doctor_avatar_url": ""}, {"doctor_avatar_url": {"$exists": False}}]},
            {"$or": [{"doctor_specialties": ""}, {"doctor_specialties": {"$exists": False}}]},
            {"$or": [{"intro": ""}, {"intro": {"$exists": False}}]},
        ]
    }


def test_build_requeue_payload_uses_doctor_info_queue_shape() -> None:
    module = load_module("requeue_empty_doctor_details.py")

    payload = module.build_requeue_payload(
        {
            "doctor_id": "1674329307792805888",
            "doctor_name": "金学民",
            "doctor_hospital": "河南省人民医院",
            "doctor_department": "眼科",
            "hospital_id": "1597528443577438208",
            "hospital_city_id": "410100",
            "hospital_city_name": "郑州市",
        }
    )

    assert payload == {
        "url": "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1674329307792805888",
        "meta": {
            "doctor_id": "1674329307792805888",
            "doctor_name": "金学民",
            "hospital_id": "1597528443577438208",
            "hospital_name": "河南省人民医院",
            "department_name": "眼科",
            "city_id": "410100",
            "city_name": "郑州市",
        },
    }
