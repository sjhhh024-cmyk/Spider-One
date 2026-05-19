"""第 3 步：医院列表到科室列表扩展。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_hnyygh.probe_helpers import build_department_request_record, parse_hospital_items
from doctor_hnyygh.redis_requests import push_redis_request
from doctor_hnyygh.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    name = "hospital_spider"
    redis_key = build_redis_keys()["hospital_list_url"]

    def make_request_from_data(self, data):
        request = super().make_request_from_data(data)
        if isinstance(request, Request):
            request.dont_filter = True
        return request

    def parse(self, response):
        redis_keys = build_redis_keys()
        payload = json.loads(response.text)
        hospital_items = parse_hospital_items(payload)
        self.logger.info("医院数量: %s | 来源: %s", len(hospital_items), response.url)
        city_id = response.meta.get("city_id", "")
        city_name = response.meta.get("city_name", "")

        for hospital in hospital_items:
            record = build_department_request_record(
                hospital_id=hospital["hospital_id"],
                hospital_name=hospital["hospital_name"],
                city_id=city_id,
                city_name=city_name,
            )
            push_redis_request(
                self.server,
                redis_keys["department_list_url"],
                record["url"],
                meta=record["meta"],
            )
        return []
