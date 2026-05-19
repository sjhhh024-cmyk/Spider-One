"""公开接口请求构造。"""

from __future__ import annotations

import json

BASE_WEB_URL = "https://patient.allinmd.cn"
BASE_EDU_WEB_URL = "https://www.allinmd.cn/edu"
BASE_GATEWAY_URL = "https://api-gateway.allinmd.cn"

API_ENDPOINTS = {
    "getHospitalPage": f"{BASE_GATEWAY_URL}/landing-resource/appd/dept/hospital/getHospitalPage",
    "getHospitalDetail": f"{BASE_GATEWAY_URL}/landing-resource/h5d/dept/hospital/getHospitalDetail",
    "getHospitalDeptGroupList": f"{BASE_GATEWAY_URL}/landing-resource/mpd/dept/hospital/getDeptGroupList",
    "getHospitalDoctorPage": f"{BASE_GATEWAY_URL}/landing-resource/mpd/dept/hospital/getDeptDoctorPage",
    "getDeptList": f"{BASE_GATEWAY_URL}/tocure-api-platform/services/tocure/dept/getDeptList",
    "getFrontDoctorList": f"{BASE_GATEWAY_URL}/tocure-api-platform/services/tocure/dept/getFrontDoctorList",
    "getCustomerAuth": f"{BASE_GATEWAY_URL}/base-customer-platform/customer/auth/v1/getCustomerAuth",
    "getDoctorProfileCards": f"{BASE_GATEWAY_URL}/allin-api-platform/services/customer/patent/v3/getMapList",
    "getDoctorBigEvent": f"{BASE_GATEWAY_URL}/base-customer-platform/customer/event/v4/getMapList",
    "getMapById": (
        f"{BASE_GATEWAY_URL}/tocure-api-platform/services/tocure/customer/auth/"
        "chongqing/procedure/getMapById"
    ),
    "getDoctorArticle": (
        f"{BASE_GATEWAY_URL}/base_patienteducation_platform/cms/patient/education/api/getDoctorArticle"
    ),
    "searchCustomer": f"{BASE_GATEWAY_URL}/base-search-service/search/tocure/customer/searchCustomer",
    "getDoctorHomeInfo": f"{BASE_GATEWAY_URL}/landing-resource/mpd/doctor/mainpage/getDoctorInfo",
    "getDoctorHomeFans": (
        f"{BASE_GATEWAY_URL}/allin-api-platform/services/customer/follow/fans/v2/getMapList"
    ),
    "getLiveActivityHistory": f"{BASE_GATEWAY_URL}/live-service/pcd/live/activity/getAllActivityPageInfo",
    "getLiveActivityDetail": f"{BASE_GATEWAY_URL}/live-service/meeting/activity/getActivityDetail",
    "getCourseNavigationList": f"{BASE_GATEWAY_URL}/ccos-training/mpd/credit/project/course/getNavigationList",
    "getCourseProjectList": f"{BASE_GATEWAY_URL}/ccos-training/mpd/credit/project/course/getProjectList",
    "getCourseProjectDetail": f"{BASE_GATEWAY_URL}/ccos-training/mpd/credit/project/getProductDetail",
    "getCourseTimetable": f"{BASE_GATEWAY_URL}/ccos-training/mpd/credit/project/course/getSystemCourseTimetable",
    "getSurgeryFeedVideoList": f"{BASE_GATEWAY_URL}/base-video-platform/cms/video/getFeedVideoList",
    "getOrganizationResourceColumnList": (
        f"{BASE_GATEWAY_URL}/base-resource-platform/organization/resource/getResourceColumnList"
    ),
    "getOrganizationHomepageColumnList": (
        f"{BASE_GATEWAY_URL}/ccos-training/pcd/organization/homepage/getOrganizationColumnList"
    ),
}

DEFAULT_API_PARAMS = {
    "visitSiteId": 27,
    "hospitalId": 1,
}

DEFAULT_APP_API_PARAMS = {
    "visitSiteId": 5,
}

DEFAULT_EDU_API_PARAMS = {
    "visitSiteId": 1,
}


def build_hospital_list_request(
    *,
    page_num: int = 1,
    page_size: int = 20,
    visit_site_id: int | None = None,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getHospitalPage"],
        "params": {
            "visitSiteId": visit_site_id or DEFAULT_APP_API_PARAMS["visitSiteId"],
            "pageNum": page_num,
            "pageSize": page_size,
        },
    }


def build_hospital_department_groups_request(*, hospital_id: int | str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getHospitalDeptGroupList"],
        "params": {
            "hospitalId": int(hospital_id) if str(hospital_id).isdigit() else str(hospital_id),
        },
    }


def build_hospital_detail_request(*, hospital_id: int | str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getHospitalDetail"],
        "params": {
            "hospitalId": int(hospital_id) if str(hospital_id).isdigit() else str(hospital_id),
        },
    }


def build_hospital_doctor_page_request(
    *,
    hospital_id: int | str,
    group_id: int | str,
    page_num: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    params: dict[str, object] = {
        "hospitalId": int(hospital_id) if str(hospital_id).isdigit() else str(hospital_id),
        "pageNum": page_num,
        "pageSize": page_size,
    }
    normalized_group_id = str(group_id).strip()
    if normalized_group_id:
        params["groupId"] = int(normalized_group_id) if normalized_group_id.isdigit() else normalized_group_id
    return {
        "url": API_ENDPOINTS["getHospitalDoctorPage"],
        "params": params,
    }


def build_department_request(
    hospital_id: int | str | None = None,
    *,
    visit_site_id: int | None = None,
    first_result: int = 0,
    max_result: int = 100,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getDeptList"],
        "params": {
            "visitSiteId": visit_site_id or DEFAULT_API_PARAMS["visitSiteId"],
            "hospitalId": hospital_id or DEFAULT_API_PARAMS["hospitalId"],
            "firstResult": first_result,
            "maxResult": max_result,
        },
    }


def build_doctor_list_request(
    *,
    dept_id: str,
    dept_name: str,
    visit_site_id: int | None = None,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getFrontDoctorList"],
        "params": {
            "visitSiteId": visit_site_id or DEFAULT_API_PARAMS["visitSiteId"],
            "deptId": str(dept_id),
            "deptName": dept_name,
        },
    }


def build_doctor_detail_request(
    doctor_id: str,
    *,
    visit_site_id: int | None = None,
) -> dict[str, object]:
    return build_doctor_auth_request(doctor_id)


def build_doctor_auth_request(doctor_id: str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getCustomerAuth"],
        "params": {
            "queryJson": f'{{"customerId":"{str(doctor_id).strip()}"}}',
        },
    }


def build_doctor_profile_cards_request(doctor_id: str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getDoctorProfileCards"],
        "params": {
            "queryJson": f'{{"customerId":"{str(doctor_id).strip()}"}}',
        },
    }


def build_doctor_big_event_request(doctor_id: str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getDoctorBigEvent"],
        "params": {
            "queryJson": f'{{"customerId":"{str(doctor_id).strip()}"}}',
        },
    }


def build_doctor_legacy_detail_request(
    doctor_id: str,
    *,
    visit_site_id: int | None = None,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getMapById"],
        "params": {
            "doctorId": str(doctor_id),
            "visitSiteId": visit_site_id or DEFAULT_API_PARAMS["visitSiteId"],
        },
    }


def build_doctor_article_request(
    doctor_id: str,
    *,
    first_result: int = 0,
    max_result: int = 3,
    visit_site_id: int | None = None,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getDoctorArticle"],
        "params": {
            "refCustomerIdSetIn": str(doctor_id),
            "sortType": 8,
            "firstResult": first_result,
            "maxResult": max_result,
            "isValid": 1,
            "educationContentTypeNotIn": 5,
            "status": 1,
            "attUseFlag": 15,
            "visitSiteId": visit_site_id or DEFAULT_API_PARAMS["visitSiteId"],
        },
    }


def build_doctor_detail_page_url(doctor_id: str) -> str:
    normalized_doctor_id = str(doctor_id).strip()
    return f"{BASE_EDU_WEB_URL}/personalInfo?doctorId={normalized_doctor_id}"


def build_doctor_home_info_request(doctor_id: str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getDoctorHomeInfo"],
        "params": {
            "customerId": str(doctor_id).strip(),
        },
    }


def build_doctor_home_fans_request(
    doctor_id: str,
    *,
    first_result: int = 0,
    max_result: int = 20,
) -> dict[str, object]:
    query_json = json.dumps(
        {
            "sortType": 2,
            "followTypeFlag": 31,
            "followType": 1,
            "logoUseFlag": 4,
            "customerId": str(doctor_id).strip(),
            "firstResult": first_result,
            "maxResult": max_result,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return {
        "url": API_ENDPOINTS["getDoctorHomeFans"],
        "params": {
            "queryJson": query_json,
        },
    }


def build_doctor_home_page_url(doctor_id: str) -> str:
    return f"{BASE_EDU_WEB_URL}/doctorHome?doctorId={str(doctor_id).strip()}"


def build_live_history_request(
    *,
    page_num: int = 1,
    page_size: int = 10,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getLiveActivityHistory"],
        "params": {
            "opUsr": "",
            "customerId": "",
            "visitSiteId": DEFAULT_EDU_API_PARAMS["visitSiteId"],
            "pageNum": page_num,
            "pageSize": page_size,
        },
    }


def build_live_activity_detail_request(activity_id: str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getLiveActivityDetail"],
        "params": {
            "activityId": str(activity_id),
            "bizType": 2,
            "pageSize": 5,
            "userId": "",
            "userType": "",
        },
    }


def build_live_detail_page_url(activity_id: str) -> str:
    return f"{BASE_EDU_WEB_URL}/liveDetail?activityId={str(activity_id).strip()}"


def build_course_navigation_request() -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getCourseNavigationList"],
        "params": {
            "customerId": "",
            "visitSiteId": DEFAULT_EDU_API_PARAMS["visitSiteId"],
        },
    }


def build_course_project_list_request(
    *,
    channel_id: int | str,
    page_num: int = 1,
    page_size: int = 20,
    distinct_id: str = "doctor_wygk",
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getCourseProjectList"],
        "body": {
            "channelId": int(channel_id),
            "propertyOneList": [],
            "propertySecList": [],
            "courseTagList": [],
            "sortType": 1,
            "pageNum": page_num,
            "pageSize": page_size,
            "customerId": "",
            "distinctId": distinct_id,
        },
    }


def build_course_project_detail_request(project_id: str) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getCourseProjectDetail"],
        "params": {
            "projectId": str(project_id),
            "customerId": "",
            "visitSiteId": DEFAULT_EDU_API_PARAMS["visitSiteId"],
        },
    }


def build_course_timetable_request(
    *,
    project_id: str,
    channel_id: str,
    sort_type_id: int = 1,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getCourseTimetable"],
        "body": {
            "projectId": str(project_id),
            "customerId": "",
            "channelId": str(channel_id),
            "sortTypeId": sort_type_id,
        },
    }


def build_course_project_page_url(project_id: str) -> str:
    return f"{BASE_EDU_WEB_URL}/courseTerminal?projectId={str(project_id).strip()}"


def build_surgery_list_request(
    *,
    page_num: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getSurgeryFeedVideoList"],
        "params": {
            "professionId": "",
            "propertyId": "",
            "queryType": 1,
            "pageSize": page_size,
            "pageNum": page_num,
            "includeInternation": 0,
            "visitSiteId": DEFAULT_EDU_API_PARAMS["visitSiteId"],
        },
    }


def build_video_terminal_page_url(resource_id: str) -> str:
    return f"{BASE_EDU_WEB_URL}/videoTerminal?resourceId={str(resource_id).strip()}"


def build_organization_resource_request(*, max_result: int = 4) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getOrganizationResourceColumnList"],
        "params": {
            "maxResult": max_result,
            "opUsr": "",
        },
    }


def build_organization_homepage_request(organization_id: int | str = 14) -> dict[str, object]:
    return {
        "url": API_ENDPOINTS["getOrganizationHomepageColumnList"],
        "params": {
            "organizationId": str(organization_id),
            "opUsr": "",
        },
    }


def build_organization_page_url(organization_id: int | str) -> str:
    return f"{BASE_EDU_WEB_URL}/organization?organizationId={str(organization_id).strip()}"
