from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_wygk.request_builders import API_ENDPOINTS, DEFAULT_API_PARAMS, DEFAULT_EDU_API_PARAMS  # noqa: E402


def test_api_endpoints_cover_confirmed_main_chain_and_probe_chain() -> None:
    assert API_ENDPOINTS == {
        "getDeptList": "https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getDeptList",
        "getFrontDoctorList": "https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getFrontDoctorList",
        "getCustomerAuth": "https://api-gateway.allinmd.cn/base-customer-platform/customer/auth/v1/getCustomerAuth",
        "getDoctorProfileCards": "https://api-gateway.allinmd.cn/allin-api-platform/services/customer/patent/v3/getMapList",
        "getDoctorBigEvent": "https://api-gateway.allinmd.cn/base-customer-platform/customer/event/v4/getMapList",
        "getMapById": "https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/customer/auth/chongqing/procedure/getMapById",
        "getDoctorArticle": "https://api-gateway.allinmd.cn/base_patienteducation_platform/cms/patient/education/api/getDoctorArticle",
        "searchCustomer": "https://api-gateway.allinmd.cn/base-search-service/search/tocure/customer/searchCustomer",
        "getDoctorHomeInfo": "https://api-gateway.allinmd.cn/landing-resource/mpd/doctor/mainpage/getDoctorInfo",
        "getDoctorHomeFans": "https://api-gateway.allinmd.cn/allin-api-platform/services/customer/follow/fans/v2/getMapList",
        "getLiveActivityHistory": "https://api-gateway.allinmd.cn/live-service/pcd/live/activity/getAllActivityPageInfo",
        "getLiveActivityDetail": "https://api-gateway.allinmd.cn/live-service/meeting/activity/getActivityDetail",
        "getCourseNavigationList": "https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getNavigationList",
        "getCourseProjectList": "https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getProjectList",
        "getCourseProjectDetail": "https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/getProductDetail",
        "getCourseTimetable": "https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getSystemCourseTimetable",
        "getSurgeryFeedVideoList": "https://api-gateway.allinmd.cn/base-video-platform/cms/video/getFeedVideoList",
        "getOrganizationResourceColumnList": "https://api-gateway.allinmd.cn/base-resource-platform/organization/resource/getResourceColumnList",
        "getOrganizationHomepageColumnList": "https://api-gateway.allinmd.cn/ccos-training/pcd/organization/homepage/getOrganizationColumnList",
    }


def test_default_api_params_pin_current_verified_visit_and_hospital_scope() -> None:
    assert DEFAULT_API_PARAMS == {
        "visitSiteId": 27,
        "hospitalId": 1,
    }


def test_default_edu_api_params_pin_public_education_scope() -> None:
    assert DEFAULT_EDU_API_PARAMS == {
        "visitSiteId": 1,
    }
