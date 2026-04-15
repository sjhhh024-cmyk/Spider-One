"""第 7 步：手术视频列表 -> 医生候选任务。"""

from __future__ import annotations

import json

from scrapy import Request, Spider
from scrapy_redis.connection import get_redis_from_settings

from doctor_wygk.parse_helpers import parse_page_info, parse_resource_doctor_records
from doctor_wygk.request_builders import build_surgery_list_request
from doctor_wygk.tools import build_get_url, push_doctor_task


class Spider(Spider):
    """手术模块直接从资源列表拿 resCustomerList。"""

    name = "surgery_doctor_spider"
    page_size = 20

    def start_requests(self):
        request_data = build_surgery_list_request(page_num=1, page_size=self.page_size)
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_page,
            cb_kwargs={"page_num": 1},
            dont_filter=True,
        )

    def parse_page(self, response, page_num):
        payload = json.loads(response.text)
        page_info = parse_page_info(payload)
        doctors = parse_resource_doctor_records(payload, source_channel="surgery_feed")
        redis_client = get_redis_from_settings(self.settings)
        detail_push_count = 0
        home_push_count = 0

        for doctor in doctors:
            push_result = push_doctor_task(redis_client, doctor)
            detail_push_count += push_result["doctor_info_url"]
            home_push_count += push_result["doctor_home_task"]

        if page_info["total_page_count"] > page_num:
            next_page_num = page_num + 1
            request_data = build_surgery_list_request(page_num=next_page_num, page_size=self.page_size)
            yield Request(
                build_get_url(request_data["url"], request_data["params"]),
                callback=self.parse_page,
                cb_kwargs={"page_num": next_page_num},
                dont_filter=True,
            )

        self.logger.info(
            "手术资源页: page=%s/%s | doctor=%s | 详情入队=%s | 主页入队=%s",
            page_num,
            page_info["total_page_count"],
            len(doctors),
            detail_push_count,
            home_push_count,
        )
