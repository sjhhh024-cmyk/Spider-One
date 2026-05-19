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
    assert module_path.exists(), f"缺少实现文件: {module_path}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_list_page_url_uses_page_suffix_style() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")

    assert (
        module.build_list_page_url("https://www.qypxw.net/zxxmjg/", 1)
        == "https://www.qypxw.net/zxxmjg/"
    )
    assert (
        module.build_list_page_url("https://www.qypxw.net/zxxmjg/", 2)
        == "https://www.qypxw.net/zxxmjg/page2/"
    )


def test_parse_list_page_extracts_total_pages_and_doctors() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")
    html = (SAMPLES_DIR / "doctor_qyzx_doctorList.html").read_text(encoding="utf-8")

    result = module.parse_list_page("https://www.qypxw.net/zxxmjg/", html)

    assert result["total"] is None
    assert result["page_size"] == 21
    assert result["total_pages"] == 401
    assert result["page_num"] == 1
    assert result["doctors"][0] == {
        "_id": "yk_2566",
        "doctor_id": "yk_2566",
        "doctor_name": "范元平",
        "doctor_department": "眼科",
        "doctor_hospital": "北京华厦民众眼科医院",
        "doctor_title": "",
        "doctor_specialties": "",
        "intro": "一、范元平医生简介范元平医生在眼科领域拥有丰富的专業知识，尤其擅长处理视神经萎缩、葡萄膜炎、角膜炎及视膜动静脉阻塞等复杂的眼底疾病。此外，他在中医科常见病的诊断方面也展现出杰出的能力。经过30余年的神经身体科从业经历，范医生不仅是精神疾病研究的信赖，还深受中医传统文化的熏陶，致力于将中医与现代医学相...",
        "doctor_avatar_url": "https://img.qypxw.net/machine/machine_ys/public/00527-2641491647.png?x-oss-process=style/qypxw",
        "source_site": "七元网",
        "source_url": "https://www.qypxw.net/zxxmjg/yk_2566/",
        "crawl_time": "",
    }


def test_parse_list_page_page2_uses_current_url_for_page_num() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")
    html = (SAMPLES_DIR / "doctor_qyzx_doctorList_page2.html").read_text(encoding="utf-8")

    result = module.parse_list_page("https://www.qypxw.net/zxxmjg/page2/", html)

    assert result["page_num"] == 2
    assert result["page_size"] == 21


def test_parse_detail_page_extracts_doctor_profile_fields() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")
    html = (SAMPLES_DIR / "doctor_qyzx_doctorDetail_yk_2566.html").read_text(encoding="utf-8")

    result = module.parse_detail_page("https://www.qypxw.net/zxxmjg/yk_2566/", html)

    assert result["_id"] == "yk_2566"
    assert result["doctor_id"] == "yk_2566"
    assert result["doctor_name"] == "范元平"
    assert result["doctor_department"] == "眼科"
    assert result["doctor_hospital"] == "北京华厦民众眼科医院"
    assert result["doctor_title"] == "中医科主任"
    assert result["doctor_specialties"] == "近视眼治疗,儿童视力"
    assert result["doctor_avatar_url"] == (
        "https://img.qypxw.net/machine/machine_ys/public/"
        "00527-2641491647.png?x-oss-process=style/qypxw"
    )
    assert result["source_site"] == "七元网"
    assert result["source_url"] == "https://www.qypxw.net/zxxmjg/yk_2566/"
    assert result["crawl_time"] == ""
    assert result["intro"].startswith("范元平医生在眼科领域拥有丰富的专業知识")
    assert "二、" not in result["intro"]


def test_clean_special_chars_removes_common_noise_characters() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")

    assert module.clean_special_chars("中医科主丨任·（副）") == "中医科主任副"


def test_detail_department_falls_back_to_list_department() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")

    class FakeCollection:
        def replace_one(self, _filter, data, upsert=False):  # noqa: ANN001, FBT002
            return data

    class FakeDatabase:
        def __getitem__(self, _name: str) -> FakeCollection:
            return FakeCollection()

    class FakeClient:
        def __getitem__(self, _name: str) -> FakeDatabase:
            return FakeDatabase()

    module.build_mongo_client = lambda _config: FakeClient()

    list_data = module.build_doctor_record(
        doctor_id="yk_1",
        doctor_name="医生1",
        doctor_department="眼科",
        doctor_hospital="医院1",
        source_site="七元网",
        source_url="https://www.qypxw.net/zxxmjg/yk_1/",
        crawl_time="",
    )
    detail_data = module.build_doctor_record(
        doctor_id="yk_1",
        doctor_name="医生1",
        doctor_department="",
        doctor_hospital="医院1",
        doctor_title="主任医师",
        doctor_specialties="项目A",
        intro="详情简介",
        source_site="七元网",
        source_url="https://www.qypxw.net/zxxmjg/yk_1/",
        crawl_time="",
    )

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    spider = module.DoctorQyzxSpider(profile)
    merged = spider.merge_doctor_data(list_data, detail_data)

    assert merged["doctor_department"] == "眼科"


def test_run_fetches_detail_pages_concurrently() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")
    saved_docs: list[dict[str, str | int]] = []

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
            doctor_id=f"yk_{index}",
            doctor_name=f"医生{index}",
            doctor_department="眼科",
            doctor_hospital="测试医院",
            source_site="七元网",
            source_url=f"https://www.qypxw.net/zxxmjg/yk_{index}/",
            crawl_time="",
        )
        for index in range(1, 4)
    ]

    module.parse_list_page = lambda _page_url, _html: {
        "total": None,
        "page_size": len(doctors),
        "total_pages": 1,
        "page_num": 1,
        "doctors": doctors,
    }
    module.parse_detail_page = lambda detail_url, _html: module.build_doctor_record(
        doctor_id=detail_url.rstrip("/").rsplit("/", 1)[-1],
        doctor_name=f"详情{detail_url.rstrip('/').rsplit('/', 1)[-1]}",
        doctor_department="眼科",
        doctor_hospital="详情医院",
        doctor_title="主任医师",
        doctor_specialties="项目A,项目B",
        intro="详情简介",
        doctor_avatar_url="https://example.com/avatar.png",
        source_site="七元网",
        source_url=detail_url,
        crawl_time="",
    )

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    profile["source"]["fetch_detail"] = True
    profile["source"]["detail_max_workers"] = 3
    spider = module.DoctorQyzxSpider(profile)

    active_count = 0
    max_active_count = 0
    active_lock = threading.Lock()

    def fake_request_html(url: str) -> str:
        nonlocal active_count, max_active_count
        if "/zxxmjg/page" in url or url.rstrip("/") == "https://www.qypxw.net/zxxmjg":
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
    assert {doc["_id"] for doc in saved_docs} == {"yk_1", "yk_2", "yk_3"}
    assert all(doc["crawl_time"] == spider.crawl_time for doc in saved_docs)


def test_run_uses_total_pages_for_full_crawl() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")
    saved_docs: list[dict[str, str | int]] = []

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
                doctor_id="yk_1",
                doctor_name="医生1",
                doctor_department="眼科",
                doctor_hospital="医院1",
                source_site="七元网",
                source_url="https://www.qypxw.net/zxxmjg/yk_1/",
                crawl_time="",
            )
        ],
        2: [
            module.build_doctor_record(
                doctor_id="yk_2",
                doctor_name="医生2",
                doctor_department="眼科",
                doctor_hospital="医院2",
                source_site="七元网",
                source_url="https://www.qypxw.net/zxxmjg/yk_2/",
                crawl_time="",
            )
        ],
    }

    def fake_parse_list_page(page_url: str, _html: str) -> dict[str, object]:
        page_number = 2 if page_url.rstrip("/").endswith("page2") else 1
        return {
            "total": None,
            "page_size": 1,
            "total_pages": 2,
            "page_num": page_number,
            "doctors": page_doctors[page_number],
        }

    module.parse_list_page = fake_parse_list_page

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    profile["source"]["start_page"] = 1
    profile["source"]["fetch_detail"] = False
    spider = module.DoctorQyzxSpider(profile)
    spider.request_html = lambda _url: "<html></html>"

    result = spider.run()

    assert result == {
        "last_page": 2,
        "raw_row_count": 2,
        "mongodb_upsert_count": 2,
    }
    assert [doc["_id"] for doc in saved_docs] == ["yk_1", "yk_2"]


def test_zero_start_page_means_full_crawl_from_page_one() -> None:
    module = load_module("doctor_qyzx", "doctor_qyzx.py")
    saved_docs: list[dict[str, str | int]] = []

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
                doctor_id="yk_1",
                doctor_name="医生1",
                doctor_department="眼科",
                doctor_hospital="医院1",
                source_site="七元网",
                source_url="https://www.qypxw.net/zxxmjg/yk_1/",
                crawl_time="",
            )
        ],
        2: [
            module.build_doctor_record(
                doctor_id="yk_2",
                doctor_name="医生2",
                doctor_department="眼科",
                doctor_hospital="医院2",
                source_site="七元网",
                source_url="https://www.qypxw.net/zxxmjg/yk_2/",
                crawl_time="",
            )
        ],
    }

    def fake_parse_list_page(page_url: str, _html: str) -> dict[str, object]:
        page_number = 2 if page_url.rstrip("/").endswith("page2") else 1
        return {
            "total": None,
            "page_size": 1,
            "total_pages": 2,
            "page_num": page_number,
            "doctors": page_doctors[page_number],
        }

    module.parse_list_page = fake_parse_list_page

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    profile["source"]["start_page"] = 0
    profile["source"]["fetch_detail"] = False
    spider = module.DoctorQyzxSpider(profile)

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
        "https://www.qypxw.net/zxxmjg/",
        "https://www.qypxw.net/zxxmjg/page2/",
    ]
    assert [doc["_id"] for doc in saved_docs] == ["yk_1", "yk_2"]
