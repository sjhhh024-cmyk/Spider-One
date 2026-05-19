"""第 1 步：写医院科室主链路种子。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy import Spider
from scrapy_redis.connection import get_redis_from_settings

from doctor_wygk.parse_helpers import parse_hospital_page_records, parse_page_info
from doctor_wygk.request_builders import build_hospital_list_request
from doctor_wygk.tools import REDIS_KEYS, build_get_url, push_task


class Spider(Spider):
    """从医院池分页接口写入医院科室主链路种子。"""

    name = "entry_seed_spider"

    def start_requests(self):
        request_data = build_hospital_list_request(page_num=1)
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse,
            cb_kwargs={"page_num": 1},
            dont_filter=True,
        )

    def parse(self, response, page_num: int):
        payload = json.loads(response.text)
        hospitals = parse_hospital_page_records(payload)
        page_info = parse_page_info(payload)
        redis_client = get_redis_from_settings(self.settings)
        dept_push_count = 0

        for hospital in hospitals:
            dept_push_count += push_task(redis_client, REDIS_KEYS["dept_task"], hospital)

        self.logger.info(
            "医院池分页入队: page=%s/%s | 当前医院=%s | 新增科室任务=%s | dept_task 剩余=%s",
            page_info["current_page_num"],
            page_info["total_page_count"],
            len(hospitals),
            dept_push_count,
            redis_client.scard(REDIS_KEYS["dept_task"]),
        )

        if not page_info["last_page"]:
            next_page_num = int(page_info["current_page_num"]) + 1
            next_request_data = build_hospital_list_request(page_num=next_page_num)
            yield Request(
                build_get_url(next_request_data["url"], next_request_data["params"]),
                callback=self.parse,
                cb_kwargs={"page_num": next_page_num},
                dont_filter=True,
            )
