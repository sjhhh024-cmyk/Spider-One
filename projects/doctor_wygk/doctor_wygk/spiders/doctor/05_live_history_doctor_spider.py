"""第 5 步：直播历史活动 -> 医生候选任务。"""

from __future__ import annotations

import json

from scrapy import Request, Spider
from scrapy_redis.connection import get_redis_from_settings

from doctor_wygk.parse_helpers import parse_live_activity_records, parse_live_doctor_records, parse_page_info
from doctor_wygk.request_builders import build_live_activity_detail_request, build_live_history_request
from doctor_wygk.tools import build_get_url, push_doctor_task


class Spider(Spider):
    """按历史直播全量页拉 activityId，再用详情接口补 doctorId。"""

    name = "live_history_doctor_spider"
    page_size = 20

    def start_requests(self):
        request_data = build_live_history_request(page_num=1, page_size=self.page_size)
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_history_page,
            cb_kwargs={"page_num": 1},
            dont_filter=True,
        )

    def parse_history_page(self, response, page_num):
        payload = json.loads(response.text)
        page_info = parse_page_info(payload)
        activities = parse_live_activity_records(payload)

        for activity in activities:
            request_data = build_live_activity_detail_request(activity["activity_id"])
            yield Request(
                build_get_url(request_data["url"], request_data["params"]),
                callback=self.parse_activity_detail,
                cb_kwargs={"activity": activity},
                dont_filter=True,
            )

        if page_info["total_page_count"] > page_num:
            next_page_num = page_num + 1
            request_data = build_live_history_request(page_num=next_page_num, page_size=self.page_size)
            yield Request(
                build_get_url(request_data["url"], request_data["params"]),
                callback=self.parse_history_page,
                cb_kwargs={"page_num": next_page_num},
                dont_filter=True,
            )

        self.logger.info(
            "直播历史页: page=%s/%s | activity=%s",
            page_num,
            page_info["total_page_count"],
            len(activities),
        )

    def parse_activity_detail(self, response, activity):
        payload = json.loads(response.text)
        doctors = parse_live_doctor_records(
            payload,
            activity_id=activity["activity_id"],
            activity_title=activity["activity_title"],
        )
        redis_client = get_redis_from_settings(self.settings)
        detail_push_count = 0
        home_push_count = 0

        for doctor in doctors:
            push_result = push_doctor_task(redis_client, doctor)
            detail_push_count += push_result["doctor_info_url"]
            home_push_count += push_result["doctor_home_task"]

        self.logger.info(
            "直播讲者回流: activity_id=%s | 标题=%s | doctor=%s | 详情入队=%s | 主页入队=%s",
            activity["activity_id"],
            activity["activity_title"],
            len(doctors),
            detail_push_count,
            home_push_count,
        )
