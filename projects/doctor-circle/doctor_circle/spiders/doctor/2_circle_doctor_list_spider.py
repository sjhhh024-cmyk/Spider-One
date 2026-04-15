"""第 2 步：生成圈子里的医生列表地址。"""

import json

from scrapy_redis.spiders import RedisSpider


class Spider(RedisSpider):
    """从圈子详情地址里提取圈子 ID，再生成医生列表接口地址。"""

    name = "circle_doctor_list_spider"
    redis_key = "doctor_circle:circle_url"

    def parse(self, response):
        """把圈子详情地址转换成医生列表地址。"""

        url = response.url
        circle_id = url.split("&id=")[1].split("&")[0]
        access_token = self.settings.get("CIRCLE_LIST_TOKEN")
        redis_key = self.settings.get("REDIS_KEY_DOCTOR_LIST_URL")
        doctor_list_url = (
            "https://api.mediportal.com.cn/circle/user/getRolePage"
            f"?access_token={access_token}&pageIndex=1&pageSize=16232"
            f"&access-token={access_token}&circleId={circle_id}&type=0&device=android"
        )

        self.server.sadd(redis_key, json.dumps({"url": doctor_list_url}, ensure_ascii=False))
