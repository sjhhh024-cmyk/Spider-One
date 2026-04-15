"""第 6 步：医院专家页和 ajax 扩展。"""

from __future__ import annotations

import hashlib

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.probe_helpers import (
    build_hospital_expert_ajax_request_specs,
    extract_doctor_info_urls,
    extract_hospital_expert_ajax_context,
    extract_hospital_expert_doctor_urls,
)
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    """处理医院专家首屏 HTML，并继续请求 ajax 分页。"""

    name = "hospital_expert_spider"
    redis_key = build_redis_keys()["hospital_expert_url"]

    def parse(self, response):
        html = response.text
        doctor_urls = extract_doctor_info_urls(response.url, html)
        ajax_context = extract_hospital_expert_ajax_context(response.url, html)
        doctor_info_key = build_redis_keys()["doctor_info_url"]
        cookiejar_id = response.meta.get("cookiejar", f"hospital-expert::{hashlib.md5(response.url.encode('utf-8')).hexdigest()}")

        for url in doctor_urls:
            push_redis_request(self.server, doctor_info_key, url)

        page_count = int(ajax_context["page_count"])
        self.logger.info(
            "医院专家页: %s | 首屏详情: %s | ajax分页: %s | 样本详情: %s",
            response.url,
            len(doctor_urls),
            page_count,
            doctor_urls[0] if doctor_urls else "",
        )
        for request_spec in build_hospital_expert_ajax_request_specs(
            source_url=response.url,
            ajax_context=ajax_context,
            cookiejar_id=cookiejar_id,
        ):
            yield Request(
                url=str(request_spec["url"]),
                callback=self.parse_ajax_page,
                dont_filter=True,
                headers=request_spec["headers"],
                meta=request_spec["meta"],
                cb_kwargs={"source_url": response.url, "page_number": request_spec["page_number"]},
            )

    def parse_ajax_page(self, response, source_url: str, page_number: int):
        doctor_urls = extract_hospital_expert_doctor_urls(response.text)
        doctor_info_key = build_redis_keys()["doctor_info_url"]

        for url in doctor_urls:
            push_redis_request(self.server, doctor_info_key, url)

        self.logger.info(
            "医院专家 ajax: %s | 第%s页 | 医生详情: %s | 样本详情: %s",
            source_url,
            page_number,
            len(doctor_urls),
            doctor_urls[0] if doctor_urls else "",
        )
