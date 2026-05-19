"""第 9 步：医生主页粉丝列表 -> 医生候选任务。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.connection import get_redis_from_settings
from scrapy_redis.spiders import RedisSpider

from doctor_wygk.parse_helpers import parse_doctor_home_fans_records, parse_doctor_home_info
from doctor_wygk.request_builders import build_doctor_home_fans_request, build_doctor_home_info_request
from doctor_wygk.settings import DOCTOR_HOME_FANS_MIN_COUNT
from doctor_wygk.tools import (
    REDIS_KEYS,
    build_get_url,
    is_doctor_home_done,
    load_task,
    mark_doctor_home_done,
    push_doctor_task,
)


class Spider(RedisSpider):
    """展开医生主页粉丝列表，把医院医生继续回流到详情链路。"""

    name = "doctor_home_fans_spider"
    redis_key = REDIS_KEYS["doctor_home_task"]
    page_size = 20
    min_fans_count = DOCTOR_HOME_FANS_MIN_COUNT

    def make_request_from_data(self, data):
        task = load_task(data)
        doctor_id = str(task.get("doctor_id") or "").strip()
        if not doctor_id:
            return Request(
                "data:text/plain,doctor_wygk_home_skip",
                callback=self.skip_task,
                dont_filter=True,
            )

        redis_client = get_redis_from_settings(self.settings)
        if is_doctor_home_done(redis_client, doctor_id):
            return Request(
                "data:text/plain,doctor_wygk_home_done",
                callback=self.skip_task,
                cb_kwargs={"doctor_id": doctor_id, "reason": "already_done"},
                dont_filter=True,
            )

        request_data = build_doctor_home_info_request(doctor_id)
        return Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_home_info,
            cb_kwargs={"doctor_id": doctor_id},
            dont_filter=True,
        )

    def skip_task(self, response, doctor_id="", reason="invalid_task"):
        self.logger.info("主页粉丝任务跳过: doctor_id=%s | reason=%s", doctor_id, reason)
        return []

    def parse_home_info(self, response, doctor_id):
        payload = json.loads(response.text)
        home_info = parse_doctor_home_info(payload)
        fans_count = int(home_info.get("fans_count") or 0)

        if fans_count <= self.min_fans_count:
            redis_client = get_redis_from_settings(self.settings)
            mark_doctor_home_done(redis_client, doctor_id)
            self.logger.info(
                "主页粉丝跳过: doctor_id=%s | fans_count=%s | threshold=%s",
                doctor_id,
                fans_count,
                self.min_fans_count,
            )
            return

        request_data = build_doctor_home_fans_request(
            doctor_id,
            first_result=0,
            max_result=self.page_size,
        )
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_fans_page,
            cb_kwargs={
                "doctor_id": doctor_id,
                "doctor_name": home_info.get("doctor_name", ""),
                "page_num": 1,
            },
            dont_filter=True,
        )

    def parse_fans_page(self, response, doctor_id, doctor_name, page_num):
        payload = json.loads(response.text)
        raw_records = payload.get("responseData", {}).get("data_list")
        raw_count = len(raw_records) if isinstance(raw_records, list) else 0
        doctors = parse_doctor_home_fans_records(payload, source_doctor_id=doctor_id)
        redis_client = get_redis_from_settings(self.settings)
        detail_push_count = 0
        home_push_count = 0

        if page_num == 1:
            mark_doctor_home_done(redis_client, doctor_id)

        for doctor in doctors:
            push_result = push_doctor_task(redis_client, doctor)
            detail_push_count += push_result["doctor_info_url"]
            home_push_count += push_result["doctor_home_task"]

        if raw_count == self.page_size:
            next_first_result = page_num * self.page_size
            request_data = build_doctor_home_fans_request(
                doctor_id,
                first_result=next_first_result,
                max_result=self.page_size,
            )
            yield Request(
                build_get_url(request_data["url"], request_data["params"]),
                callback=self.parse_fans_page,
                cb_kwargs={
                    "doctor_id": doctor_id,
                    "doctor_name": doctor_name,
                    "page_num": page_num + 1,
                },
                dont_filter=True,
            )

        self.logger.info(
            "主页粉丝页: doctor_id=%s | 姓名=%s | page=%s | raw=%s | 医院医生=%s | 详情入队=%s | 主页入队=%s",
            doctor_id,
            doctor_name,
            page_num,
            raw_count,
            len(doctors),
            detail_push_count,
            home_push_count,
        )
