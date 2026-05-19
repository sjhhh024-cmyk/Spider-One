from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.items import HospitalYlysItem, YwbdItem  # noqa: E402
from doctor_ywbd.pipelines import MongoPipeline  # noqa: E402


class DummyCollection:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, dict, bool]] = []

    def replace_one(self, query: dict, document: dict, upsert: bool) -> None:
        self.calls.append((query, document, upsert))


def test_process_item_routes_doctor_and_hospital_to_different_collections() -> None:
    pipeline = MongoPipeline(
        mongo_uri="mongodb://example",
        mongo_database="Doctor_Database",
        doctor_collection_name="doctor_ywbd",
        hospital_collection_name="hospital_ywbd",
    )
    pipeline.doctor_collection = DummyCollection()
    pipeline.hospital_collection = DummyCollection()

    doctor_item = YwbdItem(_id="doctor-1", doctor_name="张三")
    hospital_item = HospitalYlysItem(_id="hospital-1", hospital_name="某医院")

    pipeline.process_item(doctor_item, spider=None)
    pipeline.process_item(hospital_item, spider=None)

    assert pipeline.doctor_collection.calls == [
        ({"_id": "doctor-1"}, {"_id": "doctor-1", "doctor_name": "张三"}, True)
    ]
    assert pipeline.hospital_collection.calls == [
        ({"_id": "hospital-1"}, {"_id": "hospital-1", "hospital_name": "某医院"}, True)
    ]
