"""第 1 步：写四类入口种子。"""

from __future__ import annotations

from scrapy import Spider
from scrapy_redis.connection import get_redis_from_settings

from doctor_ywbd.probe_helpers import build_entry_seed_records
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import REDIS_KEY_BY_CATEGORY, build_redis_keys


class Spider(Spider):
    """把四条确认过的入口写入各自的 Redis 队列。"""

    name = "entry_seed_spider"

    def start_requests(self):
        redis_client = get_redis_from_settings(self.settings)
        redis_keys = build_redis_keys()
        write_count = 0

        for record in build_entry_seed_records():
            redis_key = redis_keys[REDIS_KEY_BY_CATEGORY[record["category"]]]
            push_redis_request(redis_client, redis_key, record["url"])
            self.logger.info("入口已写入 Redis: %s -> %s", redis_key, record["url"])
            write_count += 1

        self.logger.info("入口种子写入完成，总数: %s", write_count)

        return []
