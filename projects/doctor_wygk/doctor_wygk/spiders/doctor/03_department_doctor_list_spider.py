"""第 3 步：科室 -> 医生详情任务扩展。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.connection import get_redis_from_settings
from scrapy_redis.spiders import RedisSpider

from doctor_wygk.parse_helpers import parse_doctor_list_records
from doctor_wygk.request_builders import build_doctor_list_request
from doctor_wygk.tools import REDIS_KEYS, build_get_url, load_task, push_doctor_task


class Spider(RedisSpider):
    """读取科室任务，扩展到统一医生详情任务。"""

    name = "department_doctor_list_spider"
    redis_key = REDIS_KEYS["doctor_list_task"]

    def make_request_from_data(self, data):
        task = load_task(data)
        request_data = build_doctor_list_request(
            dept_id=task["dept_id"],
            dept_name=task["dept_name"],
            visit_site_id=task.get("visit_site_id"),
        )
        return Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse,
            cb_kwargs={"task": task},
            dont_filter=True,
        )

    def parse(self, response, task):
        payload = json.loads(response.text)
        doctors = parse_doctor_list_records(
            payload,
            hospital_id=task["hospital_id"],
            dept_id=task["dept_id"],
            dept_name=task["dept_name"],
        )
        redis_client = get_redis_from_settings(self.settings)
        detail_push_count = 0
        home_push_count = 0

        for doctor in doctors:
            detail_task = {
                **doctor,
                "visit_site_id": task.get("visit_site_id"),
            }
            push_result = push_doctor_task(redis_client, detail_task)
            detail_push_count += push_result["doctor_info_url"]
            home_push_count += push_result["doctor_home_task"]

        self.logger.info(
            "医生详情任务扩展: dept=%s | 当前条数=%s | 详情入队=%s | 主页入队=%s",
            task["dept_name"],
            len(doctors),
            detail_push_count,
            home_push_count,
        )
