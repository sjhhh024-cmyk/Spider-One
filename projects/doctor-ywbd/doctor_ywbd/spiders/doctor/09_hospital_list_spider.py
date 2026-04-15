"""医院列表链路扩展。"""

from __future__ import annotations

from urllib.parse import urlparse

from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.probe_helpers import extract_hospital_list_urls, is_first_list_page
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    """处理医院地区列表页，只拆分到医院详情页和专家页。"""

    name = "hospital_list_spider"
    redis_key = build_redis_keys()["hospital_list_url"]

    def parse(self, response):
        html = response.text
        route_urls = [url for url in extract_hospital_list_urls(response.url, html) if url != response.url]
        redis_keys = build_redis_keys()
        expand_list_pages = is_first_list_page("hospital", response.url)

        hospital_route_urls: list[str] = []
        hospital_detail_urls: list[str] = []
        hospital_expert_urls: list[str] = []
        new_route_count = 0
        new_detail_count = 0
        new_expert_count = 0
        for url in route_urls:
            path = urlparse(url).path
            if path.startswith("/yiyuan/yisheng/"):
                hospital_expert_urls.append(url)
            elif path.startswith("/yiyuan/list_a"):
                if expand_list_pages:
                    hospital_route_urls.append(url)
            else:
                hospital_detail_urls.append(url)

        for url in hospital_route_urls:
            new_route_count += push_redis_request(self.server, self.redis_key, url)
        for url in hospital_detail_urls:
            new_detail_count += push_redis_request(self.server, redis_keys["hospital_detail_url"], url)
        for url in hospital_expert_urls:
            new_expert_count += push_redis_request(self.server, redis_keys["hospital_expert_url"], url)

        self.logger.info(
            "医院列表页: %s | 列表入队: %s/%s | 医院详情入队: %s/%s | 专家入队: %s/%s | 列表队列剩余: %s | 样本专家页: %s",
            response.url,
            new_route_count,
            len(hospital_route_urls),
            new_detail_count,
            len(hospital_detail_urls),
            new_expert_count,
            len(hospital_expert_urls),
            self.server.scard(self.redis_key),
            hospital_expert_urls[0] if hospital_expert_urls else "",
        )
