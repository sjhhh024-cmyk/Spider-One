"""fastGh 主链路与渲染页 XPath 解析辅助。"""

from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

from parsel import Selector

from doctor_hnyygh.route_hypotheses import MAIN_BASE_URL


SOURCE_SITE = "河南省预约挂号服务平台"


def _extract_data_list(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _clean_text(value: str) -> str:
    text = unescape(str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _clean_text_list(values: list[str]) -> str:
    return _clean_text(" ".join(str(value or "") for value in values))


def _class_xpath(class_name: str) -> str:
    return f'contains(concat(" ", normalize-space(@class), " "), " {class_name} ")'


def _selector_text(selector: Selector, xpath: str) -> str:
    return _clean_text_list(selector.xpath(xpath).getall())


def _selector_attr(selector: Selector, xpath: str) -> str:
    return _clean_text(selector.xpath(xpath).get(default=""))


def _normalize_asset_url(value: str) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    if "hoslogomoren" in raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    return urljoin(f"{MAIN_BASE_URL}/", raw.lstrip("/"))


def _extract_section_text(selector: Selector, title: str) -> str:
    title_xpath = (
        f'//div[{_class_xpath("hosindextitltit")}][normalize-space(.)="{title}"]'
        f'/ancestor::div[{_class_xpath("hosindextit")}][1]'
        f'/following-sibling::div[{_class_xpath("xuzhinei")}][1]//text()'
    )
    return _selector_text(selector, title_xpath)


def _guess_area(*, address: str, hospital_name: str, city_name: str) -> str:
    address_tokens = re.findall(r"[\u4e00-\u9fff]+?(?:省|市|区|县)", address)
    districts = [token for token in address_tokens if token.endswith(("区", "县"))]
    if districts:
        return districts[-1]
    cities = [token for token in address_tokens if token.endswith("市")]
    if cities:
        return cities[-1]

    name_tokens = re.findall(r"[\u4e00-\u9fff]+?(?:区|县)", hospital_name)
    if name_tokens:
        return name_tokens[-1]
    return _clean_text(city_name)


def parse_area_items(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    return [
        {
            "city_id": str(item.get("id", "")).strip(),
            "city_name": str(item.get("name", "")).strip(),
        }
        for item in _extract_data_list(payload)
        if str(item.get("id", "")).strip() and str(item.get("name", "")).strip()
    ]


def parse_hospital_items(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    return [
        {
            "hospital_id": str(item.get("id", "")).strip(),
            "hospital_name": str(item.get("name", "")).strip(),
        }
        for item in _extract_data_list(payload)
        if str(item.get("id", "")).strip() and str(item.get("name", "")).strip()
    ]


def parse_department_items(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    return [
        {
            "department_id": str(item.get("id", "")).strip(),
            "department_name": str(item.get("name", "")).strip(),
        }
        for item in _extract_data_list(payload)
        if str(item.get("id", "")).strip() and str(item.get("name", "")).strip()
    ]


def parse_doctor_items(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    return [
        {
            "doctor_id": str(item.get("id", "")).strip(),
            "doctor_name": str(item.get("name", "")).strip(),
        }
        for item in _extract_data_list(payload)
        if str(item.get("id", "")).strip() and str(item.get("name", "")).strip()
    ]


def build_hospital_home_url(hospital_id: str) -> str:
    return f"{MAIN_BASE_URL}/guahao/index.html#/home?hosid={hospital_id}"


def build_doctor_home_url(doctor_id: str) -> str:
    return f"{MAIN_BASE_URL}/guahao/index.html#/doctor?docid={doctor_id}"


def build_doctor_info_api_url(doctor_id: str) -> str:
    return f"{MAIN_BASE_URL}/api/doctor/getDoctorInfo?doctorId={doctor_id}"


def build_hospital_info_api_url(hospital_id: str) -> str:
    return f"{MAIN_BASE_URL}/api/hos/getHospitalInfo?hospitalId={hospital_id}&location="


def build_hospital_overview_api_url(hospital_id: str) -> str:
    return f"{MAIN_BASE_URL}/api/hos/getHospitalOverview?hospitalId={hospital_id}"


def build_hospital_request_record(city_id: str, city_name: str) -> dict[str, Any]:
    return {
        "url": f"{MAIN_BASE_URL}/fastGh/2-{city_id}",
        "meta": {
            "city_id": city_id,
            "city_name": city_name,
        },
    }


def build_department_request_record(
    *,
    hospital_id: str,
    hospital_name: str,
    city_id: str,
    city_name: str,
) -> dict[str, Any]:
    return {
        "url": f"{MAIN_BASE_URL}/fastGh/3-{hospital_id}",
        "meta": {
            "hospital_id": hospital_id,
            "hospital_name": hospital_name,
            "city_id": city_id,
            "city_name": city_name,
        },
    }


def build_doctor_detail_task(
    *,
    doctor_id: str,
    doctor_name: str,
    hospital_id: str,
    hospital_name: str,
    department_id: str,
    department_name: str,
    city_id: str,
    city_name: str,
) -> dict[str, Any]:
    return {
        "url": build_doctor_info_api_url(doctor_id),
        "meta": {
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "hospital_id": hospital_id,
            "hospital_name": hospital_name,
            "department_id": department_id,
            "department_name": department_name,
            "city_id": city_id,
            "city_name": city_name,
        },
    }


def build_hospital_record(
    *,
    hospital_id: str,
    hospital_name: str,
    city_id: str,
    city_name: str,
    source_url: str,
    crawl_time: str,
) -> dict[str, str]:
    return {
        "_id": hospital_id,
        "hospital_id": hospital_id,
        "hospital_name": hospital_name,
        "hospital_city_id": city_id,
        "hospital_city_name": city_name,
        "source_site": SOURCE_SITE,
        "source_url": source_url,
        "crawl_time": crawl_time,
    }


def _extract_data_object(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return {}


def extract_api_doctor_detail_fields(
    payload: dict[str, Any] | None,
    *,
    doctor_id: str,
    fallback_doctor_name: str,
    fallback_hospital_name: str,
    fallback_department_name: str,
) -> dict[str, str]:
    data = _extract_data_object(payload)

    doctor_name = _clean_text(data.get("doctor_name", "")) or _clean_text(fallback_doctor_name)
    doctor_title = _clean_text(data.get("doctor_title", ""))
    doctor_avatar_url = _normalize_asset_url(str(data.get("avatar", "")))
    doctor_specialties = _clean_text(data.get("good_at", ""))
    intro = _clean_text(data.get("detail", ""))
    doctor_education = _clean_text(data.get("xueli", ""))
    hospital_id = _clean_text(data.get("hospitalId", ""))
    doctor_hospital = _clean_text(fallback_hospital_name) or _clean_text(data.get("office_location_hospital", ""))

    return {
        "doctor_name": doctor_name,
        "doctor_hospital": doctor_hospital,
        "doctor_department": _clean_text(fallback_department_name),
        "doctor_title": doctor_title,
        "doctor_avatar_url": doctor_avatar_url,
        "doctor_education": doctor_education,
        "doctor_specialties": doctor_specialties,
        "intro": intro,
        "hospital_id": hospital_id,
        "source_site": SOURCE_SITE,
        "source_url": build_doctor_home_url(doctor_id),
    }


def extract_api_hospital_detail_fields(
    hospital_info_payload: dict[str, Any] | None,
    hospital_overview_payload: dict[str, Any] | None,
    *,
    hospital_id: str,
    fallback_hospital_name: str,
    fallback_city_name: str,
) -> dict[str, str]:
    info_data = _extract_data_object(hospital_info_payload)
    overview_data = _extract_data_object(hospital_overview_payload)

    hospital_name = (
        _clean_text(info_data.get("plat_hospital_name", ""))
        or _clean_text(info_data.get("hospital_name", ""))
        or _clean_text(fallback_hospital_name)
    )
    hospital_address = _clean_text(info_data.get("address", ""))
    hospital_phone = _clean_text(info_data.get("consult_phone", ""))
    hospital_intro = _clean_text(overview_data.get("detail", "")) or _clean_text(info_data.get("detail", ""))
    hospital_website = _clean_text(info_data.get("url", ""))
    hospital_level = _clean_text(info_data.get("hospital_level", ""))
    hospital_type = _clean_text(info_data.get("hospital_type", ""))
    hospital_logo = _normalize_asset_url(
        str(info_data.get("hospital_logo", "")) or str(info_data.get("logo", ""))
    )
    hospital_code = _clean_text(info_data.get("hospital_code", ""))
    hospital_area = _clean_text(info_data.get("area", "")) or _guess_area(
        address=hospital_address,
        hospital_name=hospital_name,
        city_name=fallback_city_name,
    )
    hospital_geo = _clean_text(info_data.get("geo", ""))
    hospital_dept_count = _clean_text(overview_data.get("deptCount", ""))
    hospital_doctor_count = _clean_text(overview_data.get("doctorCount", ""))

    return {
        "hospital_name": hospital_name,
        "hospital_address": hospital_address,
        "hospital_phone": hospital_phone,
        "hospital_intro": hospital_intro,
        "hospital_website": hospital_website,
        "hospital_level": hospital_level,
        "hospital_type": hospital_type,
        "hospital_logo": hospital_logo,
        "hospital_code": hospital_code,
        "hospital_area": hospital_area,
        "hospital_geo": hospital_geo,
        "hospital_dept_count": hospital_dept_count,
        "hospital_doctor_count": hospital_doctor_count,
        "source_site": SOURCE_SITE,
        "source_url": build_hospital_home_url(hospital_id),
    }


def extract_rendered_doctor_detail_fields(
    html: str,
    *,
    doctor_id: str,
    fallback_doctor_name: str,
    fallback_hospital_name: str,
    fallback_department_name: str,
) -> dict[str, str]:
    selector = Selector(text=html or "")

    top_name_xpath = f'(//div[{_class_xpath("hosinfortoponel")}])[1]/text()'
    top_title_xpath = f'(//div[{_class_xpath("hosinfortoponel")}])[1]//span//text()'
    top_specialties_xpath = (
        f'(//div[{_class_xpath("hosinfortopthreel")}][contains(normalize-space(.), "擅长：")])[1]'
    )
    hospital_titles = selector.xpath(
        f'//div[{_class_xpath("hosinfortopthreel")}][contains(normalize-space(.), "执业地点：")]'
        f'//span[{_class_xpath("zhiname")}]/@title'
    ).getall()
    hospital_names = [_clean_text(value) for value in hospital_titles if _clean_text(value)]

    doctor_name = _selector_text(selector, top_name_xpath) or _clean_text(fallback_doctor_name)
    doctor_title = _selector_text(selector, top_title_xpath)
    doctor_specialties = _extract_section_text(selector, "擅长")
    if not doctor_specialties:
        top_specialties = _selector_attr(selector, f"{top_specialties_xpath}/@title") or _selector_text(
            selector,
            f"{top_specialties_xpath}//text()",
        )
        doctor_specialties = _clean_text(re.sub(r"^擅长：", "", top_specialties))

    doctor_hospital = " 丨 ".join(hospital_names) or _clean_text(fallback_hospital_name)

    return {
        "doctor_name": doctor_name,
        "doctor_hospital": doctor_hospital,
        "doctor_department": _clean_text(fallback_department_name),
        "doctor_title": doctor_title,
        "doctor_avatar_url": _normalize_asset_url(
            _selector_attr(selector, f'(//div[{_class_xpath("hoslogo")}]//img/@src)[1]')
        ),
        "doctor_education": _extract_section_text(selector, "学历"),
        "doctor_specialties": doctor_specialties,
        "intro": _extract_section_text(selector, "简介"),
        "source_site": SOURCE_SITE,
        "source_url": build_doctor_home_url(doctor_id),
    }


def extract_rendered_hospital_detail_fields(
    list_html: str,
    intro_html: str,
    *,
    hospital_id: str,
    fallback_hospital_name: str,
    fallback_city_name: str,
) -> dict[str, str]:
    list_selector = Selector(text=list_html or "")
    intro_selector = Selector(text=intro_html or "")

    hospital_name = _selector_text(list_selector, f'(//div[{_class_xpath("hosinfortoponel")}])[1]//text()')
    hospital_website = _selector_text(
        list_selector,
        f'(//div[{_class_xpath("hosinfortopthree")}][contains(normalize-space(.), "官网：")])[1]//span//text()',
    )
    hospital_level = _selector_text(list_selector, f'(//div[{_class_xpath("hosinfortopfouritem")}])[1]//text()')
    hospital_type = _selector_text(list_selector, f'(//div[{_class_xpath("hosinfortopfouritemm")}])[1]//text()')
    hospital_intro = _extract_section_text(intro_selector, "医院介绍")
    hospital_address = _clean_text(re.sub(r"^地址：", "", _extract_section_text(intro_selector, "医院地址")))

    if not hospital_address:
        meta_description = _selector_attr(list_selector, '//meta[@name="description"]/@content')
        address_match = re.search(r"医院地址[:：]\s*(.+?)(?:医院电话[:：]|$)", meta_description)
        hospital_address = _clean_text(address_match.group(1) if address_match else "")
    else:
        meta_description = _selector_attr(list_selector, '//meta[@name="description"]/@content')

    phone_match = re.search(r"医院电话[:：]\s*([0-9-]+)", meta_description)
    hospital_phone = _clean_text(phone_match.group(1) if phone_match else "")

    qr_src = _selector_attr(
        intro_selector,
        '(//img[contains(@src, "hospitalCode=")]/@src)[1]',
    ) or _selector_attr(list_selector, '(//img[contains(@src, "hospitalCode=")]/@src)[1]')
    code_match = re.search(r"hospitalCode=([^&]+)", qr_src)
    hospital_code = _clean_text(code_match.group(1) if code_match else "")

    dept_count = len(
        list_selector.xpath(f'//div[{_class_xpath("deplistdataitem")}]').getall()
    )

    hospital_name = hospital_name or _clean_text(fallback_hospital_name)
    hospital_area = _guess_area(
        address=hospital_address,
        hospital_name=hospital_name,
        city_name=fallback_city_name,
    )

    return {
        "hospital_name": hospital_name,
        "hospital_address": hospital_address,
        "hospital_phone": hospital_phone,
        "hospital_intro": hospital_intro,
        "hospital_website": hospital_website,
        "hospital_level": hospital_level,
        "hospital_type": hospital_type,
        "hospital_logo": _normalize_asset_url(
            _selector_attr(list_selector, f'(//div[{_class_xpath("hoslogo")}]//img/@src)[1]')
        ),
        "hospital_code": hospital_code,
        "hospital_area": hospital_area,
        "hospital_geo": "",
        "hospital_dept_count": str(dept_count) if dept_count else "",
        "hospital_doctor_count": "",
        "source_site": SOURCE_SITE,
        "source_url": build_hospital_home_url(hospital_id),
    }
