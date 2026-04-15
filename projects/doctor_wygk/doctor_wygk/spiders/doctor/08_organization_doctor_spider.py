"""第 8 步：组织资源池 + 协会首页补口 -> 医生候选任务。"""

from __future__ import annotations

import json

from scrapy import Request, Spider
from scrapy_redis.connection import get_redis_from_settings

from doctor_wygk.parse_helpers import parse_organization_homepage_records, parse_organization_resource_records
from doctor_wygk.request_builders import build_organization_homepage_request, build_organization_resource_request
from doctor_wygk.tools import build_get_url, push_doctor_task


class Spider(Spider):
    """组织模块当前没有稳定分页口，先收组织资源池和 CAOS 首页专题。"""

    name = "organization_doctor_spider"

    def start_requests(self):
        resource_request = build_organization_resource_request(max_result=4)
        yield Request(
            build_get_url(resource_request["url"], resource_request["params"]),
            callback=self.parse_resource_pool,
            dont_filter=True,
        )

        homepage_request = build_organization_homepage_request(organization_id=14)
        yield Request(
            build_get_url(homepage_request["url"], homepage_request["params"]),
            callback=self.parse_homepage,
            cb_kwargs={"organization_id": "14"},
            dont_filter=True,
        )

    def parse_resource_pool(self, response):
        payload = json.loads(response.text)
        doctors = parse_organization_resource_records(payload)
        detail_push_count, home_push_count = self.push_doctors(doctors)
        self.logger.info(
            "组织资源池回流: doctor=%s | 详情入队=%s | 主页入队=%s",
            len(doctors),
            detail_push_count,
            home_push_count,
        )

    def parse_homepage(self, response, organization_id):
        payload = json.loads(response.text)
        doctors = parse_organization_homepage_records(payload, organization_id=organization_id)
        detail_push_count, home_push_count = self.push_doctors(doctors)
        self.logger.info(
            "组织首页专题回流: organization_id=%s | doctor=%s | 详情入队=%s | 主页入队=%s",
            organization_id,
            len(doctors),
            detail_push_count,
            home_push_count,
        )

    def push_doctors(self, doctors):
        redis_client = get_redis_from_settings(self.settings)
        detail_push_count = 0
        home_push_count = 0
        for doctor in doctors:
            push_result = push_doctor_task(redis_client, doctor)
            detail_push_count += push_result["doctor_info_url"]
            home_push_count += push_result["doctor_home_task"]
        return detail_push_count, home_push_count
