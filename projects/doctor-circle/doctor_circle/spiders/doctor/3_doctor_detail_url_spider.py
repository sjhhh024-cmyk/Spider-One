"""第 3 步：生成医生详情地址。"""

import json

from scrapy_redis.spiders import RedisSpider


class Spider(RedisSpider):
    """读取医生列表接口结果，拆出每个医生的详情地址。"""

    name = "doctor_detail_url_spider"
    redis_key = "doctor_circle:doctor_list_url"

    def parse(self, response):
        """把医生列表里的 userId 转成医生详情地址。"""

        json_data = json.loads(response.body)
        data = json_data["data"]
        page_data = data["pageData"]
        access_token = self.settings.get("CIRCLE_LIST_TOKEN")
        redis_key = self.settings.get("REDIS_KEY_DOCTOR_URL")

        print("num:", len(page_data))

        for doctor in page_data:
            doctor_id = doctor.get("userId", "")
            if doctor_id:
                doctor_url = (
                    "https://api.mediportal.com.cn/health/m/circle/doctor/getDoctorHomePage"
                    f"?access_token={access_token}&access-token={access_token}&device=android&userId={doctor_id}"
                )
                self.server.sadd(redis_key, json.dumps({"url": doctor_url}, ensure_ascii=False))
