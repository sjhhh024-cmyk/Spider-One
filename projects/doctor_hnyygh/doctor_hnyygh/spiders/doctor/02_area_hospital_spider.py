"""第 2 步：区域到医院列表扩展。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_hnyygh.probe_helpers import (
    build_hospital_request_record,
    parse_area_items,
)
from doctor_hnyygh.redis_requests import push_redis_request
from doctor_hnyygh.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    name = "area_hospital_spider"
    redis_key = build_redis_keys()["area_index_url"]

    def make_request_from_data(self, data):
        request = super().make_request_from_data(data)
        if isinstance(request, Request):
            request.dont_filter = True
        return request

    def parse(self, response):
        redis_keys = build_redis_keys()
        payload = json.loads(response.text)
        area_items = parse_area_items(payload)
        self.logger.info("区域数量: %s | 来源: %s", len(area_items), response.url)

        for area in area_items:
            record = build_hospital_request_record(area["city_id"], area["city_name"])
            push_redis_request(
                self.server,
                redis_keys["hospital_list_url"],
                record["url"],
                meta=record["meta"],
            )
        return []
