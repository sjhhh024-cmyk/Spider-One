"""科室入口页扩展。"""

from __future__ import annotations

from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.probe_helpers import extract_department_seed_urls
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import build_redis_keys


class Spider(RedisSpider):
    """处理科室入口页，只投放叶子科室列表页。"""

    name = "department_index_spider"
    redis_key = build_redis_keys()["department_index_url"]

    def parse(self, response):
        list_urls = extract_department_seed_urls(response.url, response.text)
        list_key = build_redis_keys()["department_list_url"]
        new_list_count = 0

        for url in list_urls:
            new_list_count += push_redis_request(self.server, list_key, url)

        self.logger.info(
            "科室入口页: %s | 列表入队: %s/%s | 列表队列剩余: %s",
            response.url,
            new_list_count,
            len(list_urls),
            self.server.scard(list_key),
        )
