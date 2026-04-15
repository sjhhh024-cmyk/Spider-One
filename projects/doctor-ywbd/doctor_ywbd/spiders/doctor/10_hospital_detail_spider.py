"""医院详情页扩展。"""

from __future__ import annotations

from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.probe_helpers import extract_doctor_info_urls
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    """处理医院详情页，补充页面直出的医生详情链接。"""

    name = "hospital_detail_spider"
    redis_key = build_redis_keys()["hospital_detail_url"]

    def parse(self, response):
        doctor_urls = extract_doctor_info_urls(response.url, response.text)
        doctor_info_key = build_redis_keys()["doctor_info_url"]
        new_doctor_count = 0

        for url in doctor_urls:
            new_doctor_count += push_redis_request(self.server, doctor_info_key, url)

        self.logger.info(
            "医院详情页: %s | 详情入队: %s/%s | 详情队列剩余: %s | 样本详情: %s",
            response.url,
            new_doctor_count,
            len(doctor_urls),
            self.server.scard(doctor_info_key),
            doctor_urls[0] if doctor_urls else "",
        )
