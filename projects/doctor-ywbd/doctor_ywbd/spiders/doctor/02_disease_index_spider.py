"""疾病索引页链路扩展。"""

from __future__ import annotations

from urllib.parse import urlparse

from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.probe_helpers import extract_list_urls, is_first_disease_index_page
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    """处理疾病入口页和疾病索引翻页，只向疾病列表队列投放具体疾病页。"""

    name = "disease_index_spider"
    redis_key = build_redis_keys()["disease_index_url"]

    def parse(self, response):
        route_urls = [url for url in extract_list_urls("disease", response.url, response.text) if url != response.url]
        redis_keys = build_redis_keys()
        new_index_count = 0
        new_list_count = 0
        expand_index_pages = is_first_disease_index_page(response.url)

        for url in route_urls:
            if urlparse(url).path.startswith("/yisheng/jibing"):
                if expand_index_pages:
                    new_index_count += push_redis_request(self.server, self.redis_key, url)
            else:
                new_list_count += push_redis_request(self.server, redis_keys["disease_list_url"], url)

        self.logger.info(
            "疾病索引页: %s | 索引入队: %s | 列表入队: %s | 索引队列剩余: %s | 列表队列剩余: %s",
            response.url,
            new_index_count,
            new_list_count,
            self.server.scard(self.redis_key),
            self.server.scard(redis_keys["disease_list_url"]),
        )
