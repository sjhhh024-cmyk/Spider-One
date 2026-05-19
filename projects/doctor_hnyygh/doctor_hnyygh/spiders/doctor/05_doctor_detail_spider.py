"""第 5 步：医生详情与医院子链路详情入库。"""

from __future__ import annotations

from datetime import datetime
import json
import re
from urllib.parse import parse_qs, urlparse

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_hnyygh.items import DoctorHnyyghItem, HospitalHnyyghItem
from doctor_hnyygh.probe_helpers import (
    build_doctor_info_api_url,
    build_hospital_info_api_url,
    build_hospital_overview_api_url,
    extract_api_doctor_detail_fields,
    extract_api_hospital_detail_fields,
)
from doctor_hnyygh.route_hypotheses import MAIN_BASE_URL, build_redis_keys


class Spider(RedisSpider):
    name = "doctor_detail_spider"
    redis_key = build_redis_keys()["doctor_info_url"]

    channel_id = "FTSK20240718MP0bN1gI1KvYZb8dM8V5"
    default_headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{MAIN_BASE_URL}/guahao/index.html",
        "channelId": channel_id,
    }

    def _extract_doctor_id_from_url(self, url: str) -> str:
        path_match = re.search(r"/ghplat/doctor/show/(\d+)\.html", url or "")
        if path_match:
            return path_match.group(1).strip()
        fragment = urlparse(url).fragment or ""
        if "?" not in fragment:
            return ""
        query = fragment.split("?", 1)[1]
        return parse_qs(query).get("docid", [""])[0].strip()

    def _build_api_request(self, doctor_id: str, meta: dict | None = None) -> Request:
        return Request(
            url=build_doctor_info_api_url(doctor_id),
            headers=self.default_headers,
            dont_filter=True,
            meta=meta or {},
            callback=self.parse,
        )

    def make_request_from_data(self, data):
        if isinstance(data, bytes):
            encoding = getattr(self, "redis_encoding", None) or "utf-8"
            formatted_data = data.decode(encoding)
        else:
            formatted_data = data

        if isinstance(formatted_data, str):
            try:
                parameter = json.loads(formatted_data)
            except ValueError:
                parameter = {}
            if isinstance(parameter, dict):
                url = str(parameter.get("url", "")).strip()
                meta = parameter.get("meta") if isinstance(parameter.get("meta"), dict) else {}
                doctor_id = str(meta.get("doctor_id", "")).strip() or self._extract_doctor_id_from_url(url)
                if doctor_id and (
                    "/guahao/index.html#/doctor?docid=" in url or "/ghplat/doctor/show/" in url
                ):
                    return self._build_api_request(doctor_id, meta)

        request = super().make_request_from_data(data)
        if isinstance(request, Request):
            request.dont_filter = True
            for header_name, header_value in self.default_headers.items():
                request.headers.setdefault(header_name, header_value)
        return request

    def _build_doctor_item(self, response, doctor_fields: dict[str, str], crawl_time: str) -> DoctorHnyyghItem:
        doctor_record = {
            "_id": response.meta.get("doctor_id", ""),
            "doctor_id": response.meta.get("doctor_id", ""),
            "doctor_name": doctor_fields.get("doctor_name") or response.meta.get("doctor_name", ""),
            "doctor_hospital": doctor_fields.get("doctor_hospital") or response.meta.get("hospital_name", ""),
            "doctor_department": doctor_fields.get("doctor_department") or response.meta.get("department_name", ""),
            "doctor_title": doctor_fields.get("doctor_title", ""),
            "doctor_avatar_url": doctor_fields.get("doctor_avatar_url", ""),
            "doctor_education": doctor_fields.get("doctor_education", ""),
            "doctor_specialties": doctor_fields.get("doctor_specialties", ""),
            "intro": doctor_fields.get("intro", ""),
            "source_site": doctor_fields.get("source_site", "河南省预约挂号服务平台"),
            "source_url": doctor_fields.get("source_url", response.url),
            "crawl_time": crawl_time,
        }

        doctor_item = DoctorHnyyghItem()
        for field_name, field_value in doctor_record.items():
            doctor_item[field_name] = field_value
        return doctor_item

    def _build_hospital_item(self, response, hospital_fields: dict[str, str], crawl_time: str) -> HospitalHnyyghItem:
        hospital_record = {
            "_id": response.meta.get("hospital_id", ""),
            "hospital_id": response.meta.get("hospital_id", ""),
            "hospital_name": hospital_fields.get("hospital_name") or response.meta.get("hospital_name", ""),
            "hospital_city_id": response.meta.get("city_id", ""),
            "hospital_city_name": response.meta.get("city_name", ""),
            "hospital_address": hospital_fields.get("hospital_address", ""),
            "hospital_phone": hospital_fields.get("hospital_phone", ""),
            "hospital_intro": hospital_fields.get("hospital_intro", ""),
            "hospital_website": hospital_fields.get("hospital_website", ""),
            "hospital_level": hospital_fields.get("hospital_level", ""),
            "hospital_type": hospital_fields.get("hospital_type", ""),
            "hospital_logo": hospital_fields.get("hospital_logo", ""),
            "hospital_code": hospital_fields.get("hospital_code", ""),
            "hospital_area": hospital_fields.get("hospital_area", ""),
            "hospital_geo": hospital_fields.get("hospital_geo", ""),
            "hospital_dept_count": hospital_fields.get("hospital_dept_count", ""),
            "hospital_doctor_count": hospital_fields.get("hospital_doctor_count", ""),
            "source_site": hospital_fields.get("source_site", "河南省预约挂号服务平台"),
            "source_url": hospital_fields.get("source_url", f"{MAIN_BASE_URL}/fastGh/1"),
            "crawl_time": crawl_time,
        }

        hospital_item = HospitalHnyyghItem()
        for field_name, field_value in hospital_record.items():
            hospital_item[field_name] = field_value
        return hospital_item

    def parse(self, response):
        crawl_time = datetime.now().strftime("%Y-%m-%d")
        try:
            payload = json.loads(response.text)
        except ValueError:
            request_url = response.request.url if response.request else response.url
            doctor_id = str(response.meta.get("doctor_id", "")).strip() or self._extract_doctor_id_from_url(request_url)
            if doctor_id and (
                "/guahao/index.html#/doctor?docid=" in request_url or "/ghplat/doctor/show/" in request_url
            ):
                yield self._build_api_request(doctor_id, response.meta)
                return
            self.logger.warning("医生详情不是 JSON，跳过 | url=%s", response.url)
            return

        doctor_fields = extract_api_doctor_detail_fields(
            payload,
            doctor_id=response.meta.get("doctor_id", ""),
            fallback_doctor_name=response.meta.get("doctor_name", ""),
            fallback_hospital_name=response.meta.get("hospital_name", ""),
            fallback_department_name=response.meta.get("department_name", ""),
        )

        hospital_id = doctor_fields.get("hospital_id") or response.meta.get("hospital_id", "")
        response.meta["hospital_id"] = hospital_id

        yield self._build_doctor_item(response, doctor_fields, crawl_time)

        if not hospital_id:
            return

        yield Request(
            url=build_hospital_info_api_url(hospital_id),
            headers=self.default_headers,
            callback=self.parse_hospital_info,
            dont_filter=True,
            meta={
                **response.meta,
                "doctor_payload": payload,
                "crawl_time": crawl_time,
            },
        )

    def parse_hospital_info(self, response):
        payload = json.loads(response.text)
        hospital_id = response.meta.get("hospital_id", "")
        yield Request(
            url=build_hospital_overview_api_url(hospital_id),
            headers=self.default_headers,
            callback=self.parse_hospital_overview,
            dont_filter=True,
            meta={
                **response.meta,
                "hospital_info_payload": payload,
            },
        )

    def parse_hospital_overview(self, response):
        crawl_time = response.meta.get("crawl_time") or datetime.now().strftime("%Y-%m-%d")
        hospital_fields = extract_api_hospital_detail_fields(
            response.meta.get("hospital_info_payload"),
            json.loads(response.text),
            hospital_id=response.meta.get("hospital_id", ""),
            fallback_hospital_name=response.meta.get("hospital_name", ""),
            fallback_city_name=response.meta.get("city_name", ""),
        )
        yield self._build_hospital_item(response, hospital_fields, crawl_time)
