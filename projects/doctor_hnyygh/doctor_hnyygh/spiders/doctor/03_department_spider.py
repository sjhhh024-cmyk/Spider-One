"""第 3 步：医院到科室扩展。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_hnyygh.probe_helpers import parse_department_items
from doctor_hnyygh.redis_requests import push_redis_request
from doctor_hnyygh.route_hypotheses import MAIN_BASE_URL, build_redis_keys


class Spider(RedisSpider):
    name = "department_spider"
    redis_key = build_redis_keys()["department_list_url"]

    def make_request_from_data(self, data):
        request = super().make_request_from_data(data)
        if isinstance(request, Request):
            request.dont_filter = True
        return request

    def parse(self, response):
        redis_keys = build_redis_keys()
        payload = json.loads(response.text)
        department_items = parse_department_items(payload)
        self.logger.info("科室数量: %s | 来源: %s", len(department_items), response.url)

        for department in department_items:
            url = f"{MAIN_BASE_URL}/fastGh/4-{department['department_id']}"
            push_redis_request(
                self.server,
                redis_keys["doctor_list_url"],
                url,
                meta={
                    "hospital_id": response.meta.get("hospital_id", ""),
                    "hospital_name": response.meta.get("hospital_name", ""),
                    "city_id": response.meta.get("city_id", ""),
                    "city_name": response.meta.get("city_name", ""),
                    "department_id": department["department_id"],
                    "department_name": department["department_name"],
                },
            )
        return []
