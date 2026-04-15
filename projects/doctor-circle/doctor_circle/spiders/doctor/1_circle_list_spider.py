"""第 1 步：采圈子列表。"""

import json
from time import gmtime, strftime

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_circle.items import CircleItem


class Spider(RedisSpider):
    """拉圈子列表，并把圈子详情地址放入 Redis。"""

    name = "circle_list_spider"

    def start_requests(self):
        """请求圈子列表接口。"""

        access_token = self.settings.get("CIRCLE_LIST_TOKEN")
        circle_list_url = (
            "https://api.mediportal.com.cn/circle/findMoreCirclePage"
            f"?access_token={access_token}&pageIndex=1&pageSize=12069&access-token={access_token}"
        )
        yield Request(url=circle_list_url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        """解析圈子列表，并把圈子详情地址写入 Redis。"""

        json_data = json.loads(response.body)
        data = json_data["data"]
        page_data = data["pageData"]
        redis_key = self.settings.get("REDIS_KEY_CIRCLE_URL")
        access_token = self.settings.get("CIRCLE_LIST_TOKEN")

        print("页数", data["pageCount"])
        print(len(page_data))

        for circle in page_data:
            item = CircleItem()

            circle_name = circle.get("name", "")
            circle_id = circle.get("id", "")
            circle_url = (
                "https://api.mediportal.com.cn/faq/question/circleIndex/"
                f"{circle_id}?access-token={access_token}&pageIndex=0&columnId=&pageSize=16232"
                f"&id={circle_id}&access-token={access_token}"
            )

            item["_id"] = circle_id
            item["source_url"] = circle_url
            item["website"] = "医生圈APP"
            item["grab_date"] = strftime("%Y-%m-%d", gmtime())
            item["extracted"] = "N"
            item["circle_id"] = circle_id
            item["circle_name"] = circle_name if circle_name else ""
            item["logo"] = circle.get("logo", "")
            item["member_total"] = circle.get("memberTotal", "")
            item["master_name"] = circle.get("masterName", "")

            self.server.sadd(redis_key, json.dumps({"url": circle_url}, ensure_ascii=False))
            yield item
