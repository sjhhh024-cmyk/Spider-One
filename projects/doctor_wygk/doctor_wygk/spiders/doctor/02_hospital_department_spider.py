"""第 2 步：医院 -> 科室任务扩展。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.connection import get_redis_from_settings
from scrapy_redis.spiders import RedisSpider

from doctor_wygk.parse_helpers import parse_department_records
from doctor_wygk.request_builders import build_department_request
from doctor_wygk.tools import REDIS_KEYS, build_get_url, load_task, push_task


class Spider(RedisSpider):
    """读取医院维度任务，拆成科室医生列表任务。"""

    name = "hospital_department_spider"
    redis_key = REDIS_KEYS["dept_task"]

    def make_request_from_data(self, data):
        task = load_task(data)
        request_data = build_department_request(
            hospital_id=task["hospital_id"],
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
        departments = parse_department_records(payload, hospital_id=task["hospital_id"])
        redis_client = get_redis_from_settings(self.settings)
        doctor_list_key = REDIS_KEYS["doctor_list_task"]
        push_count = 0

        for department in departments:
            doctor_list_task = {
                **department,
                "visit_site_id": task.get("visit_site_id"),
            }
            push_count += push_task(redis_client, doctor_list_key, doctor_list_task)

        self.logger.info(
            "科室任务扩展: hospital_id=%s | 科室数=%s | 入队=%s | doctor_list_task 剩余=%s",
            task["hospital_id"],
            len(departments),
            push_count,
            redis_client.scard(doctor_list_key),
        )
