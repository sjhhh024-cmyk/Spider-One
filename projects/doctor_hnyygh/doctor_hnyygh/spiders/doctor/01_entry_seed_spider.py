"""第 1 步：写区域入口种子。"""

from __future__ import annotations

from scrapy import Spider
from scrapy_redis.connection import get_redis_from_settings

from doctor_hnyygh.redis_requests import push_redis_request
from doctor_hnyygh.route_hypotheses import build_entry_seed_records, build_redis_keys


class Spider(Spider):
    name = "entry_seed_spider"

    def start_requests(self):
        redis_client = get_redis_from_settings(self.settings)
        redis_keys = build_redis_keys()
        write_count = 0

        for record in build_entry_seed_records():
            push_redis_request(redis_client, redis_keys["area_index_url"], record["url"])
            self.logger.info("入口已写入 Redis: %s -> %s", redis_keys["area_index_url"], record["url"])
            write_count += 1

        self.logger.info("入口种子写入完成，总数: %s", write_count)
        return []
