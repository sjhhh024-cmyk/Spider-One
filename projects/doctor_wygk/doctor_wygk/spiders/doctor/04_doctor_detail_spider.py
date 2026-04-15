"""第 4 步：统一详情合流入库。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_wygk.parse_helpers import merge_doctor_task, parse_personal_info_doctor_item
from doctor_wygk.request_builders import (
    build_doctor_auth_request,
    build_doctor_big_event_request,
    build_doctor_legacy_detail_request,
    build_doctor_profile_cards_request,
)
from doctor_wygk.tools import REDIS_KEYS, build_get_url, load_task


class Spider(RedisSpider):
    """读取统一详情任务，并落最终医生文档。"""

    name = "doctor_detail_spider"
    redis_key = REDIS_KEYS["doctor_info_url"]

    def make_request_from_data(self, data):
        task = load_task(data)
        doctor_id = str(task.get("doctor_id") or task.get("customer_id") or "").strip()
        if not doctor_id:
            return Request(
                "data:text/plain,doctor_wygk_merge",
                callback=self.parse_merge_task,
                cb_kwargs={"task": task},
                dont_filter=True,
            )
        request_data = build_doctor_auth_request(doctor_id)
        return Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_auth_payload,
            cb_kwargs={"task": {**task, "doctor_id": doctor_id}},
            dont_filter=True,
        )

    def parse_merge_task(self, response, task):
        detail_item = merge_doctor_task(task)
        self.log_detail_item(detail_item)
        yield detail_item

    def parse_auth_payload(self, response, task):
        auth_payload = self.load_json_payload(response)
        request_data = build_doctor_profile_cards_request(task["doctor_id"])
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_cards_payload,
            cb_kwargs={"task": task, "auth_payload": auth_payload},
            dont_filter=True,
        )

    def parse_cards_payload(self, response, task, auth_payload):
        cards_payload = self.load_json_payload(response)
        request_data = build_doctor_legacy_detail_request(
            task["doctor_id"],
            visit_site_id=task.get("visit_site_id"),
        )
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_legacy_payload,
            cb_kwargs={
                "task": task,
                "auth_payload": auth_payload,
                "cards_payload": cards_payload,
            },
            dont_filter=True,
        )

    def parse_legacy_payload(self, response, task, auth_payload, cards_payload):
        legacy_payload = self.load_json_payload(response)
        request_data = build_doctor_big_event_request(task["doctor_id"])
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_big_event_payload,
            cb_kwargs={
                "task": task,
                "auth_payload": auth_payload,
                "cards_payload": cards_payload,
                "legacy_payload": legacy_payload,
            },
            dont_filter=True,
        )

    def parse_big_event_payload(self, response, task, auth_payload, cards_payload, legacy_payload):
        big_event_payload = self.load_json_payload(response)
        detail_item = parse_personal_info_doctor_item(
            auth_payload=auth_payload,
            cards_payload=cards_payload,
            legacy_payload=legacy_payload,
            big_event_payload=big_event_payload,
            source_context=task,
        )
        self.log_detail_item(detail_item)
        yield detail_item

    @staticmethod
    def load_json_payload(response):
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {}

    def log_detail_item(self, detail_item):
        self.logger.info(
            "医生详情: %s | 姓名: %s | 医院: %s | 科室: %s",
            detail_item.get("doctor_id", ""),
            detail_item.get("doctor_name", ""),
            detail_item.get("hospital_name", ""),
            detail_item.get("department_name", ""),
        )
