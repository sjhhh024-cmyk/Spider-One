"""科室医生列表链路扩展。"""

from __future__ import annotations

from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.probe_helpers import extract_doctor_info_urls, extract_list_urls, is_first_list_page
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    """处理具体科室医生列表页。"""

    name = "department_list_spider"
    redis_key = build_redis_keys()["department_list_url"]

    def parse(self, response):
        html = response.text
        list_urls = []
        if is_first_list_page("department", response.url):
            list_urls = [url for url in extract_list_urls("department", response.url, html) if url != response.url]
        doctor_urls = extract_doctor_info_urls(response.url, html)
        doctor_info_key = build_redis_keys()["doctor_info_url"]
        new_list_count = 0
        new_doctor_count = 0

        for url in list_urls:
            new_list_count += push_redis_request(self.server, self.redis_key, url)
        for url in doctor_urls:
            new_doctor_count += push_redis_request(self.server, doctor_info_key, url)

        self.logger.info(
            "科室列表页: %s | 列表入队: %s/%s | 详情入队: %s/%s | 列表队列剩余: %s | 样本详情: %s",
            response.url,
            new_list_count,
            len(list_urls),
            new_doctor_count,
            len(doctor_urls),
            self.server.scard(self.redis_key),
            doctor_urls[0] if doctor_urls else "",
        )
