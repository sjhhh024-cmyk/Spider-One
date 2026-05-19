"""第 4 步：科室到医生详情任务扩展。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_hnyygh.probe_helpers import build_doctor_detail_task, parse_doctor_items
from doctor_hnyygh.redis_requests import push_redis_request
from doctor_hnyygh.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    name = "doctor_list_spider"
    redis_key = build_redis_keys()["doctor_list_url"]

    def make_request_from_data(self, data):
        request = super().make_request_from_data(data)
        if isinstance(request, Request):
            request.dont_filter = True
        return request

    def parse(self, response):
        redis_keys = build_redis_keys()
        payload = json.loads(response.text)
        doctor_items = parse_doctor_items(payload)
        self.logger.info("医生数量: %s | 来源: %s", len(doctor_items), response.url)

        for doctor in doctor_items:
            detail_task = build_doctor_detail_task(
                doctor_id=doctor["doctor_id"],
                doctor_name=doctor["doctor_name"],
                hospital_id=response.meta.get("hospital_id", ""),
                hospital_name=response.meta.get("hospital_name", ""),
                department_id=response.meta.get("department_id", ""),
                department_name=response.meta.get("department_name", ""),
                city_id=response.meta.get("city_id", ""),
                city_name=response.meta.get("city_name", ""),
            )
            push_redis_request(
                self.server,
                redis_keys["doctor_info_url"],
                detail_task["url"],
                meta=detail_task["meta"],
            )
        return []
