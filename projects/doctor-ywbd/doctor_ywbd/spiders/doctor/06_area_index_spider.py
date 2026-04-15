"""地区入口页扩展。"""

from __future__ import annotations

from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.probe_helpers import extract_area_seed_urls
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    """处理地区入口页，只投放区县级地区列表页。"""

    name = "area_index_spider"
    redis_key = build_redis_keys()["area_index_url"]

    def parse(self, response):
        list_urls = extract_area_seed_urls(response.url, response.text)
        list_key = build_redis_keys()["area_list_url"]
        new_list_count = 0

        for url in list_urls:
            new_list_count += push_redis_request(self.server, list_key, url)

        self.logger.info(
            "地区入口页: %s | 列表入队: %s/%s | 列表队列剩余: %s",
            response.url,
            new_list_count,
            len(list_urls),
            self.server.scard(list_key),
        )
