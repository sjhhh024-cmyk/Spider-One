from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import TextResponse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_hnyygh.items import DoctorHnyyghItem, HospitalHnyyghItem  # noqa: E402
from doctor_hnyygh.route_hypotheses import build_redis_keys  # noqa: E402
from doctor_hnyygh.start import DEFAULT_SPIDER_NAMES  # noqa: E402


SPIDER_DIR = PROJECT_ROOT / "doctor_hnyygh" / "spiders" / "doctor"


def load_spider_module(filename: str):
    module_path = SPIDER_DIR / filename
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_json_response(url: str, payload: dict, meta: dict | None = None) -> TextResponse:
    request = Request(url=url, meta=meta or {})
    return TextResponse(
        url=url,
        request=request,
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        encoding="utf-8",
    )


def test_start_pipeline_keeps_doctor_detail_spider_available() -> None:
    assert "doctor_detail_spider" in DEFAULT_SPIDER_NAMES


def test_hospital_spider_file_exists() -> None:
    assert (SPIDER_DIR / "03_hospital_spider.py").exists()


def test_doctor_detail_spider_rewrites_legacy_doctor_page_queue_to_api_request() -> None:
    module = load_spider_module("05_doctor_detail_spider.py")
    spider = module.Spider()

    request = spider.make_request_from_data(
        json.dumps(
            {
                "url": "https://www.169000.net/ghplat/doctor/show/1860575587849211904.html",
                "meta": {
                    "doctor_id": "1860575587849211904",
                    "doctor_name": "测试医生",
                    "hospital_id": "1597528443577438208",
                    "hospital_name": "河南省人民医院",
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")
    )

    assert isinstance(request, Request)
    assert request.url == "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1860575587849211904"
    assert request.headers.get("channelId") == b"FTSK20240718MP0bN1gI1KvYZb8dM8V5"
    assert request.meta["doctor_id"] == "1860575587849211904"


def test_area_spider_only_expands_city_to_hospital_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_spider_module("02_area_hospital_spider.py")
    pushed: list[dict[str, object]] = []

    def fake_push(redis_client, redis_key, url, *, method=None, meta=None, formdata=None):
        pushed.append(
            {
                "redis_key": redis_key,
                "url": url,
                "method": method,
                "meta": meta,
                "formdata": formdata,
            }
        )
        return 1

    monkeypatch.setattr(module, "push_redis_request", fake_push)

    spider = module.Spider()
    spider.server = object()
    response = build_json_response(
        "https://www.169000.net/fastGh/1",
        {
            "code": 4000,
            "data": [
                {"id": "410100", "name": "郑州市"},
                {"id": "410300", "name": "洛阳市"},
            ],
        },
    )

    results = list(spider.parse(response))

    assert results == []
    assert pushed == [
        {
            "redis_key": build_redis_keys()["hospital_list_url"],
            "url": "https://www.169000.net/fastGh/2-410100",
            "method": None,
            "meta": {"city_id": "410100", "city_name": "郑州市"},
            "formdata": None,
        },
        {
            "redis_key": build_redis_keys()["hospital_list_url"],
            "url": "https://www.169000.net/fastGh/2-410300",
            "method": None,
            "meta": {"city_id": "410300", "city_name": "洛阳市"},
            "formdata": None,
        },
    ]


def test_hospital_spider_only_expands_hospital_to_department_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_spider_module("03_hospital_spider.py")
    pushed: list[dict[str, object]] = []

    def fake_push(redis_client, redis_key, url, *, method=None, meta=None, formdata=None):
        pushed.append(
            {
                "redis_key": redis_key,
                "url": url,
                "method": method,
                "meta": meta,
                "formdata": formdata,
            }
        )
        return 1

    monkeypatch.setattr(module, "push_redis_request", fake_push)

    spider = module.Spider()
    spider.server = object()
    response = build_json_response(
        "https://www.169000.net/fastGh/2-410100",
        {
            "code": 4000,
            "data": [
                {"id": "1597528472392306688", "name": "郑州大学第一附属医院河医院区"},
            ],
        },
        meta={"city_id": "410100", "city_name": "郑州市"},
    )

    results = list(spider.parse(response))

    assert results == []
    assert pushed == [
        {
            "redis_key": build_redis_keys()["department_list_url"],
            "url": "https://www.169000.net/fastGh/3-1597528472392306688",
            "method": None,
            "meta": {
                "hospital_id": "1597528472392306688",
                "hospital_name": "郑州大学第一附属医院河医院区",
                "city_id": "410100",
                "city_name": "郑州市",
            },
            "formdata": None,
        }
    ]


def test_department_spider_keeps_hospital_and_city_meta_when_queueing_doctors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_spider_module("03_department_spider.py")
    pushed: list[dict[str, object]] = []

    def fake_push(redis_client, redis_key, url, *, method=None, meta=None, formdata=None):
        pushed.append(
            {
                "redis_key": redis_key,
                "url": url,
                "method": method,
                "meta": meta,
                "formdata": formdata,
            }
        )
        return 1

    monkeypatch.setattr(module, "push_redis_request", fake_push)

    spider = module.Spider()
    spider.server = object()
    response = build_json_response(
        "https://www.169000.net/fastGh/3-1597528472392306688",
        {
            "code": 4000,
            "data": [
                {"id": "1773286494975561728", "name": "妇科"},
            ],
        },
        meta={
            "hospital_id": "1597528472392306688",
            "hospital_name": "郑州大学第一附属医院河医院区",
            "city_id": "410100",
            "city_name": "郑州市",
        },
    )

    results = list(spider.parse(response))

    assert results == []
    assert pushed == [
        {
            "redis_key": build_redis_keys()["doctor_list_url"],
            "url": "https://www.169000.net/fastGh/4-1773286494975561728",
            "method": None,
            "meta": {
                "hospital_id": "1597528472392306688",
                "hospital_name": "郑州大学第一附属医院河医院区",
                "city_id": "410100",
                "city_name": "郑州市",
                "department_id": "1773286494975561728",
                "department_name": "妇科",
            },
            "formdata": None,
        }
    ]


def test_doctor_list_spider_merges_all_upstream_meta_into_detail_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_spider_module("04_doctor_list_spider.py")
    pushed: list[dict[str, object]] = []

    def fake_push(redis_client, redis_key, url, *, method=None, meta=None, formdata=None):
        pushed.append(
            {
                "redis_key": redis_key,
                "url": url,
                "method": method,
                "meta": meta,
                "formdata": formdata,
            }
        )
        return 1

    monkeypatch.setattr(module, "push_redis_request", fake_push)

    spider = module.Spider()
    spider.server = object()
    response = build_json_response(
        "https://www.169000.net/fastGh/4-1773286494975561728",
        {
            "code": 4000,
            "data": [
                {"id": "1763127300037283840", "name": "张冬雅"},
            ],
        },
        meta={
            "hospital_id": "1597528472392306688",
            "hospital_name": "郑州大学第一附属医院河医院区",
            "department_id": "1773286494975561728",
            "department_name": "妇科",
            "city_id": "410100",
            "city_name": "郑州市",
        },
    )

    results = list(spider.parse(response))

    assert results == []
    assert pushed == [
        {
            "redis_key": build_redis_keys()["doctor_info_url"],
            "url": "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1763127300037283840",
            "method": None,
            "meta": {
                "doctor_id": "1763127300037283840",
                "doctor_name": "张冬雅",
                "hospital_id": "1597528472392306688",
                "hospital_name": "郑州大学第一附属医院河医院区",
                "department_id": "1773286494975561728",
                "department_name": "妇科",
                "city_id": "410100",
                "city_name": "郑州市",
            },
            "formdata": None,
        }
    ]


def test_doctor_detail_spider_yields_doctor_and_hospital_items_from_api_subchain() -> None:
    module = load_spider_module("05_doctor_detail_spider.py")

    spider = module.Spider()
    doctor_response = build_json_response(
        "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1674329307792805888",
        {
            "code": 4000,
            "data": {
                "doctor_name": "金学民",
                "doctor_title": "主任医师",
                "avatar": "https://ossapi.169000.net/doctorimg/1763850958628196352.jpg",
                "good_at": "原河南医学院本科、硕士毕业，主攻眼底病。",
                "detail": "金学民，医学博士、教授、主任医师。",
                "xueli": "其他",
                "office_location_hospital": "郑州大学第一附属医院",
                "hospitalId": "1597528443577438208",
            },
        },
        meta={
            "doctor_id": "1674329307792805888",
            "doctor_name": "金学民",
            "hospital_id": "1597528443577438208",
            "hospital_name": "河南省人民医院",
            "department_id": "1773286494975561728",
            "department_name": "眼科",
            "city_id": "410100",
            "city_name": "郑州市",
        },
    )

    first_results = list(spider.parse(doctor_response))

    assert len(first_results) == 2
    assert isinstance(first_results[0], DoctorHnyyghItem)
    assert dict(first_results[0]) == {
        "_id": "1674329307792805888",
        "doctor_id": "1674329307792805888",
        "doctor_name": "金学民",
        "doctor_hospital": "河南省人民医院",
        "doctor_department": "眼科",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://ossapi.169000.net/doctorimg/1763850958628196352.jpg",
        "doctor_education": "其他",
        "doctor_specialties": "原河南医学院本科、硕士毕业，主攻眼底病。",
        "intro": "金学民，医学博士、教授、主任医师。",
        "source_site": "河南省预约挂号服务平台",
        "source_url": "https://www.169000.net/guahao/index.html#/doctor?docid=1674329307792805888",
        "crawl_time": first_results[0]["crawl_time"],
    }
    assert isinstance(first_results[1], Request)
    assert first_results[1].url == (
        "https://www.169000.net/api/hos/getHospitalInfo?hospitalId=1597528443577438208&location="
    )
    assert first_results[1].headers.get("channelId") == b"FTSK20240718MP0bN1gI1KvYZb8dM8V5"

    hospital_info_response = build_json_response(
        first_results[1].url,
        {
            "code": 4000,
            "data": {
                "plat_hospital_name": "河南省人民医院",
                "hospital_name": "河南省人民医院",
                "hospital_level": "三甲",
                "address": "郑州市纬五路7号",
                "hospital_code": "41010501A1000005",
                "area": "金水区",
                "hospital_logo": "https://ossapi.169000.net/hospitalimg/logo.png",
                "detail": "&nbsp;&nbsp;医院介绍A",
                "url": "http://www.hnsrmyy.net",
                "hospital_type": "综合医院",
                "geo": "113.693823,34.772189",
                "consult_phone": "0371-65580070",
            },
        },
        meta=first_results[1].meta,
    )
    second_results = list(spider.parse_hospital_info(hospital_info_response))

    assert len(second_results) == 1
    assert isinstance(second_results[0], Request)
    assert second_results[0].url == (
        "https://www.169000.net/api/hos/getHospitalOverview?hospitalId=1597528443577438208"
    )

    hospital_overview_response = build_json_response(
        second_results[0].url,
        {
            "code": 4000,
            "data": {
                "detail": "&nbsp;&nbsp;医院介绍B",
                "deptCount": "552",
                "doctorCount": "3452",
            },
        },
        meta=second_results[0].meta,
    )
    final_results = list(spider.parse_hospital_overview(hospital_overview_response))

    assert len(final_results) == 1
    assert isinstance(final_results[0], HospitalHnyyghItem)
    assert dict(final_results[0]) == {
        "_id": "1597528443577438208",
        "hospital_id": "1597528443577438208",
        "hospital_name": "河南省人民医院",
        "hospital_city_id": "410100",
        "hospital_city_name": "郑州市",
        "hospital_address": "郑州市纬五路7号",
        "hospital_phone": "0371-65580070",
        "hospital_intro": "医院介绍B",
        "hospital_website": "http://www.hnsrmyy.net",
        "hospital_level": "三甲",
        "hospital_type": "综合医院",
        "hospital_logo": "https://ossapi.169000.net/hospitalimg/logo.png",
        "hospital_code": "41010501A1000005",
        "hospital_area": "金水区",
        "hospital_geo": "113.693823,34.772189",
        "hospital_dept_count": "552",
        "hospital_doctor_count": "3452",
        "source_site": "河南省预约挂号服务平台",
        "source_url": "https://www.169000.net/guahao/index.html#/home?hosid=1597528443577438208",
        "crawl_time": final_results[0]["crawl_time"],
    }


def test_doctor_detail_spider_missing_hospital_id_only_yields_doctor() -> None:
    module = load_spider_module("05_doctor_detail_spider.py")

    spider = module.Spider()
    response = build_json_response(
        "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1674340106653405184",
        {
            "code": 4000,
            "data": {
                "doctor_name": "张洪田",
                "doctor_title": "主任医师",
                "avatar": "",
                "good_at": "脑血管病诊治",
                "detail": "医生简介",
                "xueli": "本科",
                "office_location_hospital": "柘城县人民医院",
                "hospitalId": "",
            },
        },
        meta={
            "doctor_id": "1674340106653405184",
            "doctor_name": "张洪田",
            "hospital_id": "",
            "hospital_name": "",
            "department_id": "1674640143526662144",
            "department_name": "神经内科二病区",
            "city_id": "411424",
            "city_name": "商丘市",
        },
    )

    results = list(spider.parse(response))

    assert len(results) == 1
    assert isinstance(results[0], DoctorHnyyghItem)
    assert dict(results[0]) == {
        "_id": "1674340106653405184",
        "doctor_id": "1674340106653405184",
        "doctor_name": "张洪田",
        "doctor_hospital": "柘城县人民医院",
        "doctor_department": "神经内科二病区",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "",
        "doctor_education": "本科",
        "doctor_specialties": "脑血管病诊治",
        "intro": "医生简介",
        "source_site": "河南省预约挂号服务平台",
        "source_url": "https://www.169000.net/guahao/index.html#/doctor?docid=1674340106653405184",
        "crawl_time": results[0]["crawl_time"],
    }


def test_doctor_detail_spider_html_shell_response_falls_back_to_api_request() -> None:
    module = load_spider_module("05_doctor_detail_spider.py")
    spider = module.Spider()
    response = TextResponse(
        url="https://www.169000.net/guahao/index.html",
        request=Request(
            url="https://www.169000.net/ghplat/doctor/show/1674329307792805888.html",
            meta={
                "doctor_id": "1674329307792805888",
                "doctor_name": "金学民",
                "hospital_id": "1597528443577438208",
                "hospital_name": "河南省人民医院",
                "department_name": "眼科",
            },
        ),
        body=b"<!doctype html><html><body><div id='app'></div></body></html>",
        encoding="utf-8",
    )

    results = list(spider.parse(response))

    assert len(results) == 1
    assert isinstance(results[0], Request)
    assert results[0].url == (
        "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1674329307792805888"
    )
    assert results[0].headers.get("channelId") == b"FTSK20240718MP0bN1gI1KvYZb8dM8V5"
