"""第 2 步：医院 -> 科室任务扩展。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.connection import get_redis_from_settings
from scrapy_redis.spiders import RedisSpider

from doctor_wygk.parse_helpers import parse_hospital_department_group_records
from doctor_wygk.request_builders import build_hospital_department_groups_request
from doctor_wygk.tools import REDIS_KEYS, build_get_url, load_task, push_task


class Spider(RedisSpider):
    """读取医院维度任务，拆成科室医生列表任务。"""

    name = "hospital_department_spider"
    redis_key = REDIS_KEYS["dept_task"]

    def make_request_from_data(self, data):
        task = load_task(data)
        request_data = build_hospital_department_groups_request(hospital_id=task["hospital_id"])
        return Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse,
            cb_kwargs={"task": task},
            dont_filter=True,
        )

    def parse(self, response, task):
        payload = json.loads(response.text)
        departments = parse_hospital_department_group_records(payload, hospital_id=task["hospital_id"])
        redis_client = get_redis_from_settings(self.settings)
        doctor_list_key = REDIS_KEYS["doctor_list_task"]
        push_count = 0

        for department in departments:
            doctor_list_task = {
                **department,
                "hospital_name": task.get("hospital_name", ""),
                "page_num": 1,
                "page_size": 20,
            }
            push_count += push_task(redis_client, doctor_list_key, doctor_list_task)

        self.logger.info(
            "医院科室组扩展: hospital=%s | 科室数=%s | 入队=%s | doctor_list_task 剩余=%s",
            task["hospital_id"],
            len(departments),
            push_count,
            redis_client.scard(doctor_list_key),
        )
