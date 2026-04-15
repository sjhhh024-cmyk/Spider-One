from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_wygk.request_builders import (  # noqa: E402
    build_course_project_list_request,
    build_doctor_auth_request,
    build_doctor_big_event_request,
    build_doctor_detail_page_url,
    build_doctor_home_fans_request,
    build_doctor_home_info_request,
    build_doctor_home_page_url,
    build_doctor_legacy_detail_request,
    build_doctor_profile_cards_request,
    build_live_history_request,
    build_organization_resource_request,
    build_department_request,
    build_doctor_list_request,
    build_surgery_list_request,
)


def test_build_department_request_uses_verified_visit_site_and_hospital_scope() -> None:
    request_data = build_department_request()

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getDeptList",
        "params": {
            "visitSiteId": 27,
            "hospitalId": 1,
            "firstResult": 0,
            "maxResult": 100,
        },
    }


def test_build_doctor_list_request_keeps_department_identity_in_query() -> None:
    request_data = build_doctor_list_request(dept_id="42", dept_name="创伤骨科")

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getFrontDoctorList",
        "params": {
            "visitSiteId": 27,
            "deptId": "42",
            "deptName": "创伤骨科",
        },
    }


def test_build_doctor_auth_request_targets_personal_info_base_api() -> None:
    request_data = build_doctor_auth_request("1450269515500")

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/base-customer-platform/customer/auth/v1/getCustomerAuth",
        "params": {
            "queryJson": '{"customerId":"1450269515500"}',
        },
    }


def test_build_doctor_profile_cards_request_targets_personal_info_card_api() -> None:
    request_data = build_doctor_profile_cards_request("1450269515500")

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/allin-api-platform/services/customer/patent/v3/getMapList",
        "params": {
            "queryJson": '{"customerId":"1450269515500"}',
        },
    }


def test_build_doctor_big_event_request_targets_personal_info_event_api() -> None:
    request_data = build_doctor_big_event_request("1450269515500")

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/base-customer-platform/customer/event/v4/getMapList",
        "params": {
            "queryJson": '{"customerId":"1450269515500"}',
        },
    }


def test_build_doctor_legacy_detail_request_keeps_old_detail_api_as_fallback() -> None:
    request_data = build_doctor_legacy_detail_request("1450269515500")

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/customer/auth/chongqing/procedure/getMapById",
        "params": {
            "doctorId": "1450269515500",
            "visitSiteId": 27,
        },
    }


def test_build_doctor_detail_page_url_uses_personal_info_page() -> None:
    assert build_doctor_detail_page_url("1450269515500") == (
        "https://www.allinmd.cn/edu/personalInfo?doctorId=1450269515500"
    )


def test_build_doctor_home_info_request_targets_mainpage_api() -> None:
    request_data = build_doctor_home_info_request("1424958335567")

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/landing-resource/mpd/doctor/mainpage/getDoctorInfo",
        "params": {
            "customerId": "1424958335567",
        },
    }


def test_build_doctor_home_fans_request_matches_verified_query_json_shape() -> None:
    request_data = build_doctor_home_fans_request("1424958335567", first_result=20, max_result=20)

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/allin-api-platform/services/customer/follow/fans/v2/getMapList",
        "params": {
            "queryJson": (
                '{"sortType":2,"followTypeFlag":31,"followType":1,"logoUseFlag":4,'
                '"customerId":"1424958335567","firstResult":20,"maxResult":20}'
            ),
        },
    }


def test_build_doctor_home_page_url_uses_doctor_home_route() -> None:
    assert build_doctor_home_page_url("1424958335567") == (
        "https://www.allinmd.cn/edu/doctorHome?doctorId=1424958335567"
    )


def test_build_live_history_request_uses_public_visit_site_scope() -> None:
    request_data = build_live_history_request(page_num=3, page_size=20)

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/live-service/pcd/live/activity/getAllActivityPageInfo",
        "params": {
            "opUsr": "",
            "customerId": "",
            "visitSiteId": 1,
            "pageNum": 3,
            "pageSize": 20,
        },
    }


def test_build_course_project_list_request_keeps_body_separate_from_url() -> None:
    request_data = build_course_project_list_request(channel_id=406, page_num=2, page_size=10)

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getProjectList",
        "body": {
            "channelId": 406,
            "propertyOneList": [],
            "propertySecList": [],
            "courseTagList": [],
            "sortType": 1,
            "pageNum": 2,
            "pageSize": 10,
            "customerId": "",
            "distinctId": "doctor_wygk",
        },
    }


def test_build_surgery_list_request_targets_feed_video_list() -> None:
    request_data = build_surgery_list_request(page_num=4, page_size=30)

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/base-video-platform/cms/video/getFeedVideoList",
        "params": {
            "professionId": "",
            "propertyId": "",
            "queryType": 1,
            "pageSize": 30,
            "pageNum": 4,
            "includeInternation": 0,
            "visitSiteId": 1,
        },
    }


def test_build_organization_resource_request_keeps_homepage_pool_shape() -> None:
    request_data = build_organization_resource_request(max_result=4)

    assert request_data == {
        "url": "https://api-gateway.allinmd.cn/base-resource-platform/organization/resource/getResourceColumnList",
        "params": {
            "maxResult": 4,
            "opUsr": "",
        },
    }
