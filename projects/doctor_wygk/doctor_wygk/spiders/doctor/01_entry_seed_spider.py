"""第 1 步：写医院科室主链路种子。"""

from __future__ import annotations

from scrapy import Spider
from scrapy_redis.connection import get_redis_from_settings

from doctor_wygk.request_builders import BASE_WEB_URL, DEFAULT_API_PARAMS
from doctor_wygk.tools import REDIS_KEYS, push_task


class Spider(Spider):
    """把当前已确认的医院主链路种子写入 Redis。"""

    name = "entry_seed_spider"

    def start_requests(self):
        redis_client = get_redis_from_settings(self.settings)

        hospital_seed = {
            "hospital_id": DEFAULT_API_PARAMS["hospitalId"],
            "visit_site_id": DEFAULT_API_PARAMS["visitSiteId"],
            "hospital_home_url": f"{BASE_WEB_URL}/interrogation/hospitalHome",
        }
        dept_seed = {
            "hospital_id": DEFAULT_API_PARAMS["hospitalId"],
            "visit_site_id": DEFAULT_API_PARAMS["visitSiteId"],
        }

        push_task(redis_client, REDIS_KEYS["hospital_home_url"], hospital_seed)
        push_task(redis_client, REDIS_KEYS["dept_task"], dept_seed)

        self.logger.info("医院入口种子已写入: %s", hospital_seed["hospital_home_url"])
        self.logger.info("科室任务种子已写入: hospital_id=%s", dept_seed["hospital_id"])
        return []
