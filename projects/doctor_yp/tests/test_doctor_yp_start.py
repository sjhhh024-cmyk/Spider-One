from __future__ import annotations

import copy
import importlib.util
import threading
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_DIR / "samples"


def load_module(module_name: str, filename: str):
    module_path = PROJECT_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_list_page_url_uses_route_style_pagination() -> None:
    module = load_module("doctor_yp", "doctor_yp.py")

    assert module.build_list_page_url("https://docbook.com.cn", 1) == "https://docbook.com.cn/doctorList"
    assert module.build_list_page_url("https://docbook.com.cn", 2) == "https://docbook.com.cn/doctorList/2"


def test_parse_list_page_extracts_total_page_and_doctors() -> None:
    module = load_module("doctor_yp", "doctor_yp.py")
    html = (SAMPLES_DIR / "doctor_yp_doctorList.html").read_text(encoding="utf-8")

    result = module.parse_list_page("https://docbook.com.cn/doctorList", html)

    assert result["total"] == 27432
    assert result["page_size"] == 15
    assert result["total_pages"] == 1829
    assert result["page_num"] == 1
    assert result["doctors"][0] == {
        "_id": "22794",
        "doctor_id": "22794",
        "doctor_name": "葛均波",
        "doctor_hospital": "复旦大学附属中山医院",
        "doctor_department": "心血管内科",
        "doctor_titile": "",
        "doctor_other_title": "院士",
        "intro": "",
        "doctor_avatar_url": "https://file.docbook.com.cn/upload/experts/2cb35b0ad3a89a1c4e618c03b8e72bd9.png",
        "source_url": "https://docbook.com.cn/doctorList",
        "crawl_time": "",
    }


def test_parse_detail_page_extracts_doctor_profile_fields() -> None:
    module = load_module("doctor_yp", "doctor_yp.py")
    html = (SAMPLES_DIR / "doctor_yp_doctorDetail_86043.html").read_text(encoding="utf-8")

    result = module.parse_detail_page("https://docbook.com.cn/doctorDetail/86043", html)

    assert result == {
        "_id": "86043",
        "doctor_id": "86043",
        "doctor_name": "田晋帆",
        "doctor_hospital": "首都医科大学附属北京安贞医院",
        "doctor_department": "心血管内科",
        "doctor_titile": "主任医师",
        "doctor_other_title": "",
        "intro": "首都医科大学北京安贞医院\n心血管内科，主任医师，副教授，硕士研究生导师\n擅长心血管领域（冠心病、高脂血症、高血压、心衰）药物及介入治疗\n社会任职：\n中国中西医结合老年医学分会委员\n中国中西医结合房颤分会兼副秘书长\n获得“北京市科协青年人才托举工程”，“北京市优秀人才”，“北京市医院管理中心青苗人才”。承担或者作为骨干参与国家自然科学基金，省部级课题，北京市教育委员会科技计划项目，北京安贞医院院级项目。获得专利2项，软著3项。",
        "doctor_avatar_url": "https://file.docbook.com.cn/upload/experts/90cd219a973507438e4b359fc0f3409f.jpeg",
        "source_url": "https://docbook.com.cn/doctorDetail/86043",
        "crawl_time": "",
    }


def test_run_fetches_detail_pages_concurrently() -> None:
    module = load_module("doctor_yp", "doctor_yp.py")
    saved_docs: list[dict[str, str]] = []

    class FakeCollection:
        def replace_one(self, _filter, data, upsert=False):  # noqa: ANN001, FBT002
            saved_docs.append(data)

    class FakeDatabase:
        def __init__(self) -> None:
            self.collection = FakeCollection()

        def __getitem__(self, _name: str) -> FakeCollection:
            return self.collection

    class FakeClient:
        def __init__(self) -> None:
            self.database = FakeDatabase()

        def __getitem__(self, _name: str) -> FakeDatabase:
            return self.database

    module.build_mongo_client = lambda _config: FakeClient()

    doctors = [
        module.build_doctor_record(
            doctor_id=str(index),
            doctor_name=f"医生{index}",
            doctor_hospital="测试医院",
            doctor_department="测试科室",
            source_url="https://docbook.com.cn/doctorList",
            crawl_time="",
        )
        for index in range(1, 4)
    ]

    module.parse_list_page = lambda _page_url, _html: {
        "total": len(doctors),
        "page_size": len(doctors),
        "total_pages": 1,
        "page_num": 1,
        "doctors": doctors,
    }
    module.parse_detail_page = lambda detail_url, _html: module.build_doctor_record(
        doctor_id=detail_url.rsplit("/", 1)[-1],
        doctor_name=f"详情{detail_url.rsplit('/', 1)[-1]}",
        doctor_hospital="详情医院",
        doctor_department="详情科室",
        doctor_titile="主任医师",
        intro="详情简介",
        doctor_avatar_url="https://example.com/avatar.png",
        source_url=detail_url,
        crawl_time="",
    )

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    profile["source"]["max_pages"] = 1
    profile["source"]["fetch_detail"] = True
    profile["source"]["detail_max_workers"] = 3
    spider = module.DoctorYpSpider(profile)

    active_count = 0
    max_active_count = 0
    active_lock = threading.Lock()

    def fake_request_html(url: str) -> str:
        nonlocal active_count, max_active_count
        if "/doctorDetail/" not in url:
            return "<html>list</html>"

        with active_lock:
            active_count += 1
            max_active_count = max(max_active_count, active_count)
        time.sleep(0.05)
        with active_lock:
            active_count -= 1
        return "<html>detail</html>"

    spider.request_html = fake_request_html

    result = spider.run()

    assert result == {
        "last_page": 1,
        "raw_row_count": 3,
        "mongodb_upsert_count": 3,
    }
    assert max_active_count > 1
    assert {doc["_id"] for doc in saved_docs} == {"1", "2", "3"}
    assert all(doc["crawl_time"] == spider.crawl_time for doc in saved_docs)


def test_run_uses_total_pages_for_full_crawl() -> None:
    module = load_module("doctor_yp", "doctor_yp.py")
    saved_docs: list[dict[str, str]] = []

    class FakeCollection:
        def replace_one(self, _filter, data, upsert=False):  # noqa: ANN001, FBT002
            saved_docs.append(data)

    class FakeDatabase:
        def __init__(self) -> None:
            self.collection = FakeCollection()

        def __getitem__(self, _name: str) -> FakeCollection:
            return self.collection

    class FakeClient:
        def __init__(self) -> None:
            self.database = FakeDatabase()

        def __getitem__(self, _name: str) -> FakeDatabase:
            return self.database

    module.build_mongo_client = lambda _config: FakeClient()

    page_doctors = {
        1: [
            module.build_doctor_record(
                doctor_id="1",
                doctor_name="医生1",
                doctor_hospital="医院1",
                doctor_department="科室1",
                source_url="https://docbook.com.cn/doctorList",
                crawl_time="",
            )
        ],
        2: [
            module.build_doctor_record(
                doctor_id="2",
                doctor_name="医生2",
                doctor_hospital="医院2",
                doctor_department="科室2",
                source_url="https://docbook.com.cn/doctorList/2",
                crawl_time="",
            )
        ],
    }

    def fake_parse_list_page(page_url: str, _html: str) -> dict[str, object]:
        page_number = 2 if page_url.endswith("/2") else 1
        return {
            "total": 2,
            "page_size": 1,
            "total_pages": 2,
            "page_num": page_number,
            "doctors": page_doctors[page_number],
        }

    module.parse_list_page = fake_parse_list_page

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    profile["source"]["start_page"] = 1
    profile["source"]["max_pages"] = 1
    profile["source"]["fetch_detail"] = False
    spider = module.DoctorYpSpider(profile)
    spider.request_html = lambda _url: "<html></html>"

    result = spider.run()

    assert result == {
        "last_page": 2,
        "raw_row_count": 2,
        "mongodb_upsert_count": 2,
    }
    assert [doc["_id"] for doc in saved_docs] == ["1", "2"]


def test_zero_start_page_means_full_crawl_from_page_one() -> None:
    module = load_module("doctor_yp", "doctor_yp.py")
    saved_docs: list[dict[str, str]] = []

    class FakeCollection:
        def replace_one(self, _filter, data, upsert=False):  # noqa: ANN001, FBT002
            saved_docs.append(data)

    class FakeDatabase:
        def __init__(self) -> None:
            self.collection = FakeCollection()

        def __getitem__(self, _name: str) -> FakeCollection:
            return self.collection

    class FakeClient:
        def __init__(self) -> None:
            self.database = FakeDatabase()

        def __getitem__(self, _name: str) -> FakeDatabase:
            return self.database

    module.build_mongo_client = lambda _config: FakeClient()

    requested_urls: list[str] = []
    page_doctors = {
        1: [
            module.build_doctor_record(
                doctor_id="1",
                doctor_name="医生1",
                doctor_hospital="医院1",
                doctor_department="科室1",
                source_url="https://docbook.com.cn/doctorList",
                crawl_time="",
            )
        ],
        2: [
            module.build_doctor_record(
                doctor_id="2",
                doctor_name="医生2",
                doctor_hospital="医院2",
                doctor_department="科室2",
                source_url="https://docbook.com.cn/doctorList/2",
                crawl_time="",
            )
        ],
    }

    def fake_parse_list_page(page_url: str, _html: str) -> dict[str, object]:
        page_number = 2 if page_url.endswith("/2") else 1
        return {
            "total": 2,
            "page_size": 1,
            "total_pages": 2,
            "page_num": page_number,
            "doctors": page_doctors[page_number],
        }

    module.parse_list_page = fake_parse_list_page

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    profile["source"]["start_page"] = 0
    profile["source"]["fetch_detail"] = False
    spider = module.DoctorYpSpider(profile)

    def fake_request_html(url: str) -> str:
        requested_urls.append(url)
        return "<html></html>"

    spider.request_html = fake_request_html

    result = spider.run()

    assert result == {
        "last_page": 2,
        "raw_row_count": 2,
        "mongodb_upsert_count": 2,
    }
    assert requested_urls == [
        "https://docbook.com.cn/doctorList",
        "https://docbook.com.cn/doctorList/2",
    ]
    assert [doc["_id"] for doc in saved_docs] == ["1", "2"]
