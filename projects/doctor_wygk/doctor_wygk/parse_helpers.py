"""接口 JSON 解析辅助。"""

from __future__ import annotations

import re
from datetime import datetime

from doctor_wygk.request_builders import (
    build_doctor_detail_page_url,
    build_doctor_home_page_url,
    build_live_detail_page_url,
    build_organization_page_url,
    build_video_terminal_page_url,
)


def _normalize_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _normalize_object_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def merge_doctor_detail(
    detail_fields: dict[str, object],
    *,
    source_url: str,
    source_context: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized_context = dict(source_context or {})
    doctor_id = str(
        detail_fields.get("doctor_id")
        or detail_fields.get("doctorId")
        or normalized_context.get("doctor_id")
        or normalized_context.get("customer_id")
        or ""
    ).strip()
    if not doctor_id:
        raise ValueError("doctor_id 不能为空")

    return {
        "_id": doctor_id,
        "doctor_id": doctor_id,
        "doctor_name": str(
            detail_fields.get("doctor_name")
            or detail_fields.get("fullName")
            or normalized_context.get("doctor_name")
            or ""
        ).strip(),
        "doctor_title": str(
            detail_fields.get("doctor_title")
            or detail_fields.get("medical_title")
            or detail_fields.get("medicalTitle")
            or normalized_context.get("doctor_title")
            or normalized_context.get("medical_title")
            or ""
        ).strip(),
        "hospital_name": str(
            detail_fields.get("hospital_name")
            or detail_fields.get("hospitalName")
            or normalized_context.get("hospital_name")
            or normalized_context.get("company")
            or ""
        ).strip(),
        "department_name": str(
            detail_fields.get("department_name")
            or normalized_context.get("department_name")
            or normalized_context.get("dept_name")
            or ""
        ).strip(),
        "doctor_expertise": str(
            detail_fields.get("doctor_expertise")
            or detail_fields.get("expertise")
            or normalized_context.get("doctor_expertise")
            or normalized_context.get("expertise")
            or ""
        ).strip(),
        "doctor_introduction": str(
            detail_fields.get("doctor_introduction")
            or detail_fields.get("practiceIntroduction")
            or normalized_context.get("doctor_introduction")
            or ""
        ).strip(),
        "doctor_avatar_url": str(
            detail_fields.get("doctor_avatar_url")
            or detail_fields.get("logoUrl")
            or detail_fields.get("headUrl")
            or normalized_context.get("doctor_avatar_url")
            or normalized_context.get("logoUrl")
            or normalized_context.get("headUrl")
            or ""
        ).strip(),
        "doctor_illnesses": _normalize_string_list(
            detail_fields.get("doctor_illnesses") or normalized_context.get("doctor_illnesses")
        ),
        "doctor_social_titles": _normalize_object_list(
            detail_fields.get("doctor_social_titles") or normalized_context.get("doctor_social_titles")
        ),
        "doctor_honors": _normalize_object_list(
            detail_fields.get("doctor_honors") or normalized_context.get("doctor_honors")
        ),
        "doctor_academic_achievements": _normalize_string_list(
            detail_fields.get("doctor_academic_achievements")
            or normalized_context.get("doctor_academic_achievements")
        ),
        "doctor_practice_achievements": _normalize_string_list(
            detail_fields.get("doctor_practice_achievements")
            or normalized_context.get("doctor_practice_achievements")
        ),
        "doctor_work_experiences": _normalize_object_list(
            detail_fields.get("doctor_work_experiences")
            or normalized_context.get("doctor_work_experiences")
        ),
        "doctor_educations": _normalize_object_list(
            detail_fields.get("doctor_educations") or normalized_context.get("doctor_educations")
        ),
        "doctor_continuing_educations": _normalize_object_list(
            detail_fields.get("doctor_continuing_educations")
            or normalized_context.get("doctor_continuing_educations")
        ),
        "doctor_funds": _normalize_object_list(
            detail_fields.get("doctor_funds") or normalized_context.get("doctor_funds")
        ),
        "doctor_opuses": _normalize_object_list(
            detail_fields.get("doctor_opuses") or normalized_context.get("doctor_opuses")
        ),
        "doctor_patents": _normalize_object_list(
            detail_fields.get("doctor_patents") or normalized_context.get("doctor_patents")
        ),
        "doctor_big_events": _normalize_string_list(
            detail_fields.get("doctor_big_events") or normalized_context.get("doctor_big_events")
        ),
        "website": "唯医骨科",
        "source_url": source_url,
        "crawl_time": datetime.now().strftime("%Y-%m-%d"),
    }


def merge_doctor_task(task: dict[str, object]) -> dict[str, object]:
    source_url = str(task.get("source_url") or "").strip()
    return merge_doctor_detail(
        dict(task),
        source_url=source_url,
        source_context=task,
    )


def _extract_response_data(payload: dict[str, object]) -> dict[str, object] | list[object]:
    if not isinstance(payload, dict):
        return {}
    response_object = payload.get("responseObject")
    if isinstance(response_object, dict):
        response_data = response_object.get("responseData")
        if isinstance(response_data, (dict, list)):
            return response_data
    response_data = payload.get("responseData")
    if isinstance(response_data, (dict, list)):
        return response_data
    data = payload.get("data")
    if isinstance(data, (dict, list)):
        return data
    return {}


def _extract_records(payload: dict[str, object]) -> list[dict[str, object]]:
    response_data = _extract_response_data(payload)
    if isinstance(response_data, dict):
        for key in ("pageList", "dataList", "items", "list", "doctorList"):
            value = response_data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        data_list = response_data.get("data_list")
        if isinstance(data_list, list):
            return [item for item in data_list if isinstance(item, dict)]
    if isinstance(response_data, list):
        return [item for item in response_data if isinstance(item, dict)]
    return []


def _extract_page_info(payload: dict[str, object]) -> dict[str, object]:
    response_data = _extract_response_data(payload)
    if isinstance(response_data, dict):
        page_info = response_data.get("pageInfo")
        if isinstance(page_info, dict):
            return page_info
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        page_info = data.get("pageInfo")
        if isinstance(page_info, dict):
            return page_info
    return {}


def _extract_detail_data(payload: dict[str, object]) -> dict[str, object]:
    response_data = _extract_response_data(payload)
    if isinstance(response_data, dict):
        data_list = response_data.get("data_list")
        if isinstance(data_list, dict):
            return data_list
        return response_data
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        return data
    return {}


def _extract_department_name_from_detail(detail_data: dict[str, object]) -> str:
    department_name = str(detail_data.get("department") or "").strip()
    if department_name:
        return department_name

    dept_list = detail_data.get("deptList")
    if not isinstance(dept_list, list):
        return ""

    names: list[str] = []
    for dept in dept_list:
        if isinstance(dept, dict):
            name = str(dept.get("deptName") or dept.get("name") or "").strip()
        else:
            name = str(dept or "").strip()
        if name:
            names.append(name)
    return " / ".join(names)


def _pick_pc_link(record: dict[str, object]) -> str:
    combo_action = record.get("comboActionJump")
    if isinstance(combo_action, dict):
        combo_action_v3 = combo_action.get("comboActionJumpV3")
        if isinstance(combo_action_v3, dict):
            pc_link = combo_action_v3.get("pcLink")
            if isinstance(pc_link, str) and pc_link.strip():
                return pc_link.strip()
        pc_link = combo_action.get("pcLink")
        if isinstance(pc_link, str) and pc_link.strip():
            return pc_link.strip()
    return ""


def _format_month(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"(\d{4})-(\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r"(\d{4})", text)
    if match:
        return match.group(1)
    return text


def _split_names(value: object) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    parts = re.split(r"[，,；;、\n]+", text)
    return [part.strip() for part in parts if part and part.strip()]


def _extract_illness_names(detail_data: dict[str, object]) -> list[str]:
    illness_list = detail_data.get("illnessList")
    if isinstance(illness_list, list):
        names = []
        for illness in illness_list:
            if isinstance(illness, dict):
                name = str(illness.get("illnessName") or "").strip()
                if name:
                    names.append(name)
        if names:
            return names
    return _split_names(detail_data.get("illnessNameList"))


def _extract_description_list(records: object) -> list[str]:
    if not isinstance(records, list):
        return []
    descriptions: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        description = str(record.get("contentDescribe") or record.get("content") or "").strip()
        if description:
            descriptions.append(description)
    return descriptions


def _parse_work_experiences(cards_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("occupationList")
    if not isinstance(records, list):
        return []

    experiences: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        organization = str(record.get("unit") or record.get("occupation") or "").strip()
        department_name = str(record.get("department") or "").strip()
        doctor_title = str(record.get("medicalTitle") or "").strip()
        start_date = _format_month(record.get("startTime"))
        end_date = _format_month(record.get("endTime"))
        if not any((organization, department_name, doctor_title, start_date, end_date)):
            continue
        experiences.append(
            {
                "organization": organization,
                "department_name": department_name,
                "doctor_title": doctor_title,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return experiences


def _parse_educations(cards_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("educationList")
    if not isinstance(records, list):
        return []

    educations: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        school_name = str(record.get("university") or "").strip()
        major_name = str(record.get("major") or "").strip()
        education_name = str(record.get("education") or "").strip()
        start_date = _format_month(record.get("startTime"))
        end_date = _format_month(record.get("endTime"))
        if not any((school_name, major_name, education_name, start_date, end_date)):
            continue
        educations.append(
            {
                "school_name": school_name,
                "major_name": major_name,
                "education_name": education_name,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return educations


def _parse_continuing_educations(cards_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("continuingEducationList")
    if not isinstance(records, list):
        return []

    educations: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        organization = str(record.get("organization") or "").strip()
        certificate_name = str(record.get("certificate") or "").strip()
        address = str(record.get("address") or record.get("adress") or "").strip()
        start_date = _format_month(record.get("startTime"))
        end_date = _format_month(record.get("endTime"))
        if not any((organization, certificate_name, address, start_date, end_date)):
            continue
        educations.append(
            {
                "organization": organization,
                "certificate_name": certificate_name,
                "address": address,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return educations


def _parse_social_titles(cards_data: dict[str, object], legacy_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("socialList")
    if not isinstance(records, list):
        records = legacy_data.get("socialList")
    if not isinstance(records, list):
        return []

    social_titles: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        organization = str(record.get("organization") or "").strip()
        social_title = str(record.get("socialTitle") or "").strip()
        start_date = _format_month(record.get("startTime"))
        end_date = _format_month(record.get("endTime"))
        if not any((organization, social_title, start_date, end_date)):
            continue
        social_titles.append(
            {
                "organization": organization,
                "social_title": social_title,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return social_titles


def _parse_honors(cards_data: dict[str, object], legacy_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("honorList")
    if not isinstance(records, list):
        records = legacy_data.get("honorList")
    if not isinstance(records, list):
        return []

    honors: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        honor_name = str(record.get("honorName") or "").strip()
        award_department = str(record.get("awardDepartment") or "").strip()
        award_date = _format_month(record.get("awardYear"))
        if not any((honor_name, award_department, award_date)):
            continue
        honors.append(
            {
                "honor_name": honor_name,
                "award_department": award_department,
                "award_date": award_date,
            }
        )
    return honors


def _parse_funds(cards_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("fundList")
    if not isinstance(records, list):
        return []

    funds: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        fund_name = str(record.get("fundName") or "").strip()
        fund_code = str(record.get("fundCode") or "").strip()
        approval_date = _format_month(record.get("approvalTime"))
        if not any((fund_name, fund_code, approval_date)):
            continue
        funds.append(
            {
                "fund_name": fund_name,
                "fund_code": fund_code,
                "approval_date": approval_date,
            }
        )
    return funds


def _parse_opuses(cards_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("opusList")
    if not isinstance(records, list):
        return []

    opuses: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        opus_name = str(record.get("opusName") or "").strip()
        publisher = str(record.get("publisher") or "").strip()
        publication_date = _format_month(record.get("publicationTime"))
        author_type = str(record.get("authorType") or "").strip()
        if not any((opus_name, publisher, publication_date, author_type)):
            continue
        opuses.append(
            {
                "opus_name": opus_name,
                "publisher": publisher,
                "publication_date": publication_date,
                "author_type": author_type,
            }
        )
    return opuses


def _parse_patents(cards_data: dict[str, object]) -> list[dict[str, str]]:
    records = cards_data.get("patentList")
    if not isinstance(records, list):
        return []

    patents: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        patent_name = str(record.get("patentName") or "").strip()
        patent_code = str(record.get("patentCode") or "").strip()
        patent_date = _format_month(record.get("patentTime"))
        country = str(record.get("country") or "").strip()
        if not any((patent_name, patent_code, patent_date, country)):
            continue
        patents.append(
            {
                "patent_name": patent_name,
                "patent_code": patent_code,
                "patent_date": patent_date,
                "country": country,
            }
        )
    return patents


def _parse_big_events(big_event_payload: dict[str, object]) -> list[str]:
    response_data = _extract_response_data(big_event_payload)
    if not isinstance(response_data, dict):
        return []
    data_list = response_data.get("dataList")
    if not isinstance(data_list, list):
        return []

    event_names: list[str] = []
    for record in data_list:
        if not isinstance(record, dict):
            continue
        event_name = str(record.get("event_name") or record.get("eventName") or "").strip()
        if event_name:
            event_names.append(event_name)
    return event_names


def _build_resource_doctors(
    resource: dict[str, object],
    *,
    source_channel: str,
    source_url: str | None = None,
    extra_fields: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    resource_id = str(resource.get("resId") or resource.get("resourceId") or "").strip()
    resource_name = str(resource.get("resName") or resource.get("resourceName") or "").strip()
    normalized_source_url = source_url or _pick_pc_link(resource)
    if not normalized_source_url and resource_id:
        normalized_source_url = build_video_terminal_page_url(resource_id)

    doctors = []
    for customer in resource.get("resCustomerList") or []:
        if not isinstance(customer, dict):
            continue
        customer_id = str(customer.get("customerId") or customer.get("doctorId") or "").strip()
        if not customer_id or customer_id == "0":
            continue
        doctors.append(
            {
                **(extra_fields or {}),
                "resource_id": resource_id,
                "resource_name": resource_name,
                "doctor_id": customer_id,
                "doctor_name": str(customer.get("name") or customer.get("doctorName") or "").strip(),
                "doctor_title": str(customer.get("medicalTitle") or "").strip(),
                "company": str(customer.get("company") or "").strip(),
                "doctor_avatar_url": str(customer.get("logoUrl") or customer.get("headUrl") or "").strip(),
                "source_channel": source_channel,
                "source_url": normalized_source_url,
            }
        )
    return doctors


def parse_department_records(
    payload: dict[str, object],
    *,
    hospital_id: int | str,
) -> list[dict[str, str]]:
    departments = []
    for record in _extract_records(payload):
        dept_id = str(record.get("id") or record.get("deptId") or "").strip()
        dept_name = str(record.get("deptName") or record.get("name") or "").strip()
        if not dept_id or not dept_name:
            continue
        departments.append(
            {
                "hospital_id": int(hospital_id) if str(hospital_id).isdigit() else str(hospital_id),
                "dept_id": dept_id,
                "dept_name": dept_name,
            }
        )
    return departments


def parse_doctor_list_records(
    payload: dict[str, object],
    *,
    hospital_id: int | str,
    dept_id: str,
    dept_name: str,
) -> list[dict[str, str]]:
    doctors = []
    for record in _extract_records(payload):
        doctor_id = str(record.get("doctorId") or record.get("id") or "").strip()
        if not doctor_id:
            continue
        doctors.append(
            {
                "hospital_id": int(hospital_id) if str(hospital_id).isdigit() else str(hospital_id),
                "dept_id": str(dept_id),
                "dept_name": dept_name,
                "doctor_id": doctor_id,
                "doctor_name": str(record.get("doctorName") or record.get("fullName") or "").strip(),
                "doctor_title": str(record.get("medicalTitle") or "").strip(),
            }
        )
    return doctors


def parse_doctor_detail_item(
    payload: dict[str, object],
    *,
    source_url: str,
    source_context: dict[str, object] | None = None,
) -> dict[str, object]:
    detail_data = _extract_detail_data(payload)
    raw_detail = {
        "doctor_id": str(
            detail_data.get("doctorId")
            or detail_data.get("customerId")
            or detail_data.get("id")
            or ""
        ).strip(),
        "doctor_name": str(detail_data.get("fullName") or detail_data.get("doctorName") or "").strip(),
        "doctor_title": str(
            detail_data.get("medicalTitleShow") or detail_data.get("medicalTitle") or ""
        ).strip(),
        "hospital_name": str(detail_data.get("hospitalName") or detail_data.get("company") or "").strip(),
        "department_name": _extract_department_name_from_detail(detail_data),
        "doctor_expertise": str(detail_data.get("expertise") or "").strip(),
        "doctor_introduction": str(
            detail_data.get("summary") or detail_data.get("practiceIntroduction") or ""
        ).strip(),
        "doctor_avatar_url": str(detail_data.get("logoUrl") or "").strip(),
        "doctor_illnesses": _extract_illness_names(detail_data),
        "doctor_social_titles": _parse_social_titles({}, detail_data),
        "doctor_honors": _parse_honors({}, detail_data),
        "doctor_academic_achievements": _extract_description_list(detail_data.get("abilityAcademicList")),
        "doctor_practice_achievements": _extract_description_list(detail_data.get("abilityPracticeList")),
    }
    return merge_doctor_detail(
        raw_detail,
        source_url=source_url,
        source_context=source_context,
    )


def parse_personal_info_doctor_item(
    *,
    auth_payload: dict[str, object],
    cards_payload: dict[str, object],
    legacy_payload: dict[str, object],
    big_event_payload: dict[str, object],
    source_context: dict[str, object] | None = None,
) -> dict[str, object]:
    auth_data = _extract_detail_data(auth_payload)
    cards_data = _extract_detail_data(cards_payload)
    legacy_data = _extract_detail_data(legacy_payload)

    doctor_id = str(
        auth_data.get("customerId")
        or auth_data.get("doctorId")
        or legacy_data.get("doctorId")
        or legacy_data.get("customerId")
        or ""
    ).strip()

    raw_detail = {
        "doctor_id": doctor_id,
        "doctor_name": str(auth_data.get("fullName") or legacy_data.get("fullName") or "").strip(),
        "doctor_title": str(
            auth_data.get("medicalTitleShow")
            or auth_data.get("socialTitle")
            or legacy_data.get("medicalTitle")
            or ""
        ).strip(),
        "hospital_name": str(
            auth_data.get("company")
            or auth_data.get("workplace")
            or legacy_data.get("hospitalName")
            or ""
        ).strip(),
        "department_name": _extract_department_name_from_detail(auth_data)
        or _extract_department_name_from_detail(legacy_data),
        "doctor_expertise": str(auth_data.get("expertise") or legacy_data.get("expertise") or "").strip(),
        "doctor_introduction": str(
            auth_data.get("summary") or legacy_data.get("practiceIntroduction") or ""
        ).strip(),
        "doctor_avatar_url": str(
            legacy_data.get("logoUrl") or auth_data.get("logoUrl") or auth_data.get("headUrl") or ""
        ).strip(),
        "doctor_illnesses": _extract_illness_names(auth_data) or _extract_illness_names(legacy_data),
        "doctor_social_titles": _parse_social_titles(cards_data, legacy_data),
        "doctor_honors": _parse_honors(cards_data, legacy_data),
        "doctor_academic_achievements": _extract_description_list(legacy_data.get("abilityAcademicList")),
        "doctor_practice_achievements": _extract_description_list(legacy_data.get("abilityPracticeList")),
        "doctor_work_experiences": _parse_work_experiences(cards_data),
        "doctor_educations": _parse_educations(cards_data),
        "doctor_continuing_educations": _parse_continuing_educations(cards_data),
        "doctor_funds": _parse_funds(cards_data),
        "doctor_opuses": _parse_opuses(cards_data),
        "doctor_patents": _parse_patents(cards_data),
        "doctor_big_events": _parse_big_events(big_event_payload),
    }
    return merge_doctor_detail(
        raw_detail,
        source_url=build_doctor_detail_page_url(doctor_id),
        source_context=source_context,
    )


def parse_page_info(payload: dict[str, object]) -> dict[str, int | bool]:
    page_info = _extract_page_info(payload)
    return {
        "current_page_num": int(page_info.get("currentPageNum") or 1),
        "page_size": int(page_info.get("pageSize") or 0),
        "total_page_count": int(page_info.get("totalPageCount") or 0),
        "total_count": int(page_info.get("totalCount") or 0),
        "last_page": bool(page_info.get("lastPage")),
    }


def parse_doctor_home_info(payload: dict[str, object]) -> dict[str, object]:
    detail_data = _extract_detail_data(payload)
    return {
        "doctor_id": str(detail_data.get("customerId") or detail_data.get("doctorId") or "").strip(),
        "doctor_name": str(detail_data.get("name") or detail_data.get("fullName") or "").strip(),
        "company": str(detail_data.get("company") or "").strip(),
        "doctor_title": str(
            detail_data.get("medicalTitleShow") or detail_data.get("medicalTitle") or ""
        ).strip(),
        "doctor_avatar_url": str(
            detail_data.get("logoUrl") or detail_data.get("customerLogoUrl") or ""
        ).strip(),
        "fans_count": int(detail_data.get("fansCount") or 0),
    }


def parse_doctor_home_fans_records(
    payload: dict[str, object],
    *,
    source_doctor_id: str,
) -> list[dict[str, str]]:
    doctors = []
    source_url = build_doctor_home_page_url(source_doctor_id)

    for record in _extract_records(payload):
        customer_auth = record.get("customer_auth")
        if not isinstance(customer_auth, dict):
            continue
        company = str(customer_auth.get("company") or "").strip()
        if "医院" not in company:
            continue

        doctor_id = str(customer_auth.get("customerId") or "").strip()
        doctor_name = str(customer_auth.get("fullName") or "").strip()
        if not doctor_id or not doctor_name:
            continue

        customer_att = record.get("customer_att")
        doctors.append(
            {
                "doctor_id": doctor_id,
                "doctor_name": doctor_name,
                "doctor_title": str(
                    customer_auth.get("medicalTitleShow") or customer_auth.get("medicalTitle") or ""
                ).strip(),
                "company": company,
                "doctor_avatar_url": str(
                    customer_att.get("logoUrl") if isinstance(customer_att, dict) else ""
                ).strip(),
                "source_url": source_url,
            }
        )

    return doctors


def parse_live_activity_records(payload: dict[str, object]) -> list[dict[str, str]]:
    activities = []
    for record in _extract_records(payload):
        activity_id = str(record.get("activityId") or "").strip()
        if not activity_id:
            continue
        activities.append(
            {
                "activity_id": activity_id,
                "activity_title": str(record.get("activityTitle") or "").strip(),
            }
        )
    return activities


def parse_live_doctor_records(
    payload: dict[str, object],
    *,
    activity_id: str,
    activity_title: str,
) -> list[dict[str, str]]:
    detail_data = _extract_detail_data(payload)
    doctors = []
    for record in detail_data.get("doctorList") or []:
        if not isinstance(record, dict):
            continue
        doctor_id = str(record.get("doctorId") or record.get("customerId") or "").strip()
        if not doctor_id:
            continue
        doctors.append(
            {
                "activity_id": str(activity_id),
                "activity_title": activity_title,
                "doctor_id": doctor_id,
                "doctor_name": str(record.get("doctorName") or record.get("name") or "").strip(),
                "doctor_title": str(record.get("medicalTitle") or "").strip(),
                "company": str(record.get("company") or "").strip(),
                "doctor_avatar_url": str(record.get("headUrl") or record.get("logoUrl") or "").strip(),
                "source_url": build_live_detail_page_url(activity_id),
            }
        )
    return doctors


def parse_course_navigation_records(payload: dict[str, object]) -> list[int]:
    data = _extract_detail_data(payload)
    property_ids: list[int] = []
    seen: set[int] = set()

    def walk(nodes: list[dict[str, object]]) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            property_id = node.get("propertyId")
            if isinstance(property_id, int) and property_id > 0 and property_id not in seen:
                seen.add(property_id)
                property_ids.append(property_id)
            children = node.get("children")
            if isinstance(children, list):
                walk([child for child in children if isinstance(child, dict)])

    data_list = data.get("dataList")
    if isinstance(data_list, list):
        walk([item for item in data_list if isinstance(item, dict)])
    return property_ids


def parse_course_project_records(payload: dict[str, object]) -> list[dict[str, str]]:
    projects = []
    for record in _extract_records(payload):
        project_id = str(record.get("projectId") or "").strip()
        if not project_id:
            continue
        projects.append(
            {
                "project_id": project_id,
                "project_name": str(record.get("projectName") or "").strip(),
            }
        )
    return projects


def parse_course_detail_channel_id(payload: dict[str, object]) -> str:
    detail_data = _extract_detail_data(payload)
    for channel in detail_data.get("channelList") or []:
        if not isinstance(channel, dict):
            continue
        if int(channel.get("channelType") or 0) != 5:
            continue
        channel_id = str(channel.get("id") or "").strip()
        if channel_id:
            return channel_id
    return ""


def parse_course_timetable_doctor_records(
    payload: dict[str, object],
    *,
    project_id: str,
    channel_id: str,
) -> list[dict[str, str]]:
    detail_data = _extract_detail_data(payload)
    doctors = []
    for group in detail_data.get("courseGroupResultList") or []:
        if not isinstance(group, dict):
            continue
        for resource in group.get("courseGroupList") or []:
            if not isinstance(resource, dict):
                continue
            doctors.extend(
                _build_resource_doctors(
                    resource,
                    source_channel="course_timetable",
                    extra_fields={
                        "project_id": str(project_id),
                        "channel_id": str(channel_id),
                    },
                )
            )
    for doctor in doctors:
        doctor.pop("source_channel", None)
    return doctors


def parse_resource_doctor_records(
    payload: dict[str, object],
    *,
    source_channel: str,
) -> list[dict[str, str]]:
    doctors = []
    for resource in _extract_records(payload):
        doctors.extend(_build_resource_doctors(resource, source_channel=source_channel))
    return doctors


def parse_organization_resource_records(payload: dict[str, object]) -> list[dict[str, str]]:
    detail_data = _extract_detail_data(payload)
    doctors = []
    for organization in detail_data.get("organizationList") or []:
        if not isinstance(organization, dict):
            continue
        organization_id = str(organization.get("orgId") or "").strip()
        for resource in organization.get("orgResourceList") or []:
            if not isinstance(resource, dict):
                continue
            doctors.extend(
                _build_resource_doctors(
                    resource,
                    source_channel="organization_resource_pool",
                    source_url=build_organization_page_url(organization_id or 14),
                    extra_fields={"organization_id": organization_id},
                )
            )
    return doctors


def parse_organization_homepage_records(
    payload: dict[str, object],
    *,
    organization_id: str,
) -> list[dict[str, str]]:
    detail_data = _extract_detail_data(payload)
    doctors = []
    for section in detail_data.get("dataList") or []:
        if not isinstance(section, dict):
            continue
        for key in ("videoList", "docList", "liveList", "meetingList", "topicList"):
            for resource in section.get(key) or []:
                if not isinstance(resource, dict):
                    continue
                doctors.extend(
                    _build_resource_doctors(
                        resource,
                        source_channel="organization_homepage",
                        source_url=build_organization_page_url(organization_id),
                        extra_fields={"organization_id": str(organization_id)},
                    )
                )
    return doctors
