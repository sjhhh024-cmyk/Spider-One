from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def load_module(module_name: str, filename: str):
    module_path = PROJECT_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doctor_spider_prefers_doctor_collection_name(monkeypatch):
    doctor_module = load_module("doctor_hxq_start", "doctor_hxq_start.py")

    class FakeCollection:
        name = "doctor_hxq"

    class FakeDatabase:
        def __getitem__(self, name: str):
            assert name == "doctor_hxq"
            return FakeCollection()

    class FakeClient:
        def __getitem__(self, name: str):
            assert name == "Doctor_Database"
            return FakeDatabase()

    monkeypatch.setattr(doctor_module, "build_mongo_client", lambda config: FakeClient())

    spider = doctor_module.HaoxinqingDoctorSpider(
        {
            "project": {"site": "好心情"},
            "source": {
                "base_url": "https://example.com/allSearch",
                "page_size": 1000,
                "start_page": 1,
                "max_pages": 100,
                "timeout_seconds": 30,
                "max_retries": 3,
            },
            "mongodb": {
                "database": "Doctor_Database",
                "doctor_collection": "doctor_hxq",
            },
        }
    )

    assert spider.collection.name == "doctor_hxq"


def test_hospital_data_matches_requested_fields():
    hospital_module = load_module("hospital_hxq_start", "hospital_hxq_start.py")

    data = hospital_module.build_hospital_data(
        hospital_payload={
            "id": 15055,
            "name": "遵义医科大学附属医院",
            "alias": "遵义医学院附属医院",
            "address": "贵州省遵义市汇川区大连路149号",
            "hospitalLevel": 1,
            "hospitalEtc": 2,
            "coverImg": "data/hxq/online/temp/20230214/20230214105858005.png",
            "environmentImg": "data/hxq/online/temp/20230214/20230214105902227.png,",
            "intro": "医院简介",
        },
        crawl_time="2026-04-20",
    )

    assert data == {
        "_id": "15055",
        "hospital_id": "15055",
        "name": "遵义医科大学附属医院",
        "alias": "遵义医学院附属医院",
        "address": "贵州省遵义市汇川区大连路149号",
        "hospital_level_text": "三甲",
        "hospital_avatar_url": "https://online-file.haoxinqing.cn/data/hxq/online/temp/20230214/20230214105858005.png",
        "intro": "医院简介",
        "website": "好心情",
        "hospital_url": None,
        "crawl_time": "2026-04-20",
    }


def test_hospital_collection_defaults_to_hospital_hxq(monkeypatch):
    hospital_module = load_module("hospital_hxq_start", "hospital_hxq_start.py")

    class FakeCollection:
        name = "hospital_hxq"

        def find(self, *args, **kwargs):
            return []

    class FakeDatabase:
        def __getitem__(self, name: str):
            if name == "doctor_hxq":
                return FakeCollection()
            assert name == "hospital_hxq"
            return FakeCollection()

    class FakeClient:
        def __getitem__(self, name: str):
            assert name == "Doctor_Database"
            return FakeDatabase()

    monkeypatch.setattr(hospital_module, "build_mongo_client", lambda config: FakeClient())

    spider = hospital_module.HaoxinqingHospitalSpider(
        {
            "project": {"site": "好心情"},
            "hospital_source": {
                "base_url": "https://gw.haoxinqing.cn/papi/hospital/get",
                "timeout_seconds": 30,
                "max_retries": 3,
            },
            "mongodb": {
                "database": "Doctor_Database",
                "doctor_collection": "doctor_hxq",
            },
        }
    )

    assert spider.hospital_collection.name == "hospital_hxq"


def test_hospital_spider_skips_zero_hospital_ids(monkeypatch):
    hospital_module = load_module("hospital_hxq_start", "hospital_hxq_start.py")

    class FakeDoctorCollection:
        def find(self, *args, **kwargs):
            return [
                {"hospital_id_hxq": "3113"},
                {"hospital_id_hxq": 0},
                {"hospital_id_hxq": "0"},
                {"hospital_id_hxq": None},
                {"hospital_id_hxq": ""},
                {"hospital_id_hxq": "3113"},
                {"hospital_id_hxq": "5201"},
            ]

    class FakeHospitalCollection:
        name = "hospital_hxq"

    class FakeDatabase:
        def __getitem__(self, name: str):
            if name == "doctor_hxq":
                return FakeDoctorCollection()
            assert name == "hospital_hxq"
            return FakeHospitalCollection()

    class FakeClient:
        def __getitem__(self, name: str):
            assert name == "Doctor_Database"
            return FakeDatabase()

    monkeypatch.setattr(hospital_module, "build_mongo_client", lambda config: FakeClient())

    spider = hospital_module.HaoxinqingHospitalSpider(
        {
            "project": {"site": "好心情"},
            "hospital_source": {
                "base_url": "https://gw.haoxinqing.cn/papi/hospital/get",
                "timeout_seconds": 30,
                "max_retries": 3,
            },
            "source": {
                "timeout_seconds": 30,
                "max_retries": 3,
            },
            "mongodb": {
                "database": "Doctor_Database",
                "doctor_collection": "doctor_hxq",
            },
        }
    )

    assert list(spider.iter_unique_hospital_ids()) == ["3113", "5201"]
