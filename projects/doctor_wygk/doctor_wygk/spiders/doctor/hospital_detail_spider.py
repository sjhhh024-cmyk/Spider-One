"""医院详情独立采集。"""

from __future__ import annotations

import json

from scrapy import Request
from scrapy import Spider

from doctor_wygk.items import HospitalWygkItem
from doctor_wygk.parse_helpers import merge_hospital_detail, parse_hospital_detail_records, parse_page_info
from doctor_wygk.request_builders import build_hospital_detail_request, build_hospital_list_request
from doctor_wygk.tools import build_get_url


class Spider(Spider):
    """从医院池接口直接落医院详情。"""

    name = "hospital_detail_spider"

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
        hospitals = parse_hospital_detail_records(payload)
        page_info = parse_page_info(payload)

        for hospital in hospitals:
            request_data = build_hospital_detail_request(hospital_id=hospital["hospitalId"])
            yield Request(
                build_get_url(request_data["url"], request_data["params"]),
                callback=self.parse_hospital_detail,
                cb_kwargs={"hospital_seed": hospital},
                dont_filter=True,
            )

        self.logger.info(
            "医院详情分页扩展: page=%s/%s | 当前医院=%s",
            page_info["current_page_num"],
            page_info["total_page_count"],
            len(hospitals),
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

    def parse_hospital_detail(self, response, hospital_seed: dict[str, object]):
        payload = json.loads(response.text)
        detail_data = payload.get("data")
        if not isinstance(detail_data, dict):
            detail_data = {}
        merged_detail = {**hospital_seed, **detail_data}
        yield HospitalWygkItem(**merge_hospital_detail(merged_detail))
