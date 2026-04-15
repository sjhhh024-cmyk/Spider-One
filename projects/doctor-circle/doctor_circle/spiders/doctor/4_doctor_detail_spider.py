"""第 4 步：采医生详情。"""

import json
from time import gmtime, strftime
from urllib.parse import parse_qs, urlparse

from scrapy_redis.spiders import RedisSpider

from doctor_circle.items import DoctorItem


class Spider(RedisSpider):
    """读取医生详情接口结果，并整理成医生记录。"""

    name = "doctor_detail_spider"
    redis_key = "doctor_circle:doctor_url"

    def parse(self, response):
        """解析医生详情字段。"""

        item = DoctorItem()
        url = response.url
        doctor_id = parse_qs(urlparse(url).query).get("userId", [""])[0]
        json_data = json.loads(response.body)
        data = json_data["data"]

        item["_id"] = doctor_id if doctor_id else url
        item["source_url"] = url
        item["website"] = "医生圈APP"
        item["grab_date"] = strftime("%Y-%m-%d", gmtime())
        item["extracted"] = "N"
        item["doctor_id"] = doctor_id
        item["doctor_name"] = data.get("name", "")
        item["hospital"] = data.get("hospital", "")
        item["departments"] = data.get("departments", "")
        item["fans"] = data.get("fans", "")
        item["followers"] = data.get("followers", "")
        item["is_3a"] = data.get("is3A", "")
        item["logo_url"] = data.get("logoUrl", "")
        item["real_status"] = data.get("realStatus", "")
        item["skill"] = data.get("skill", "")

        star_friend = data.get("starFriend", "")
        if star_friend is False:
            item["star_friend"] = "false"
        else:
            item["star_friend"] = "True" if star_friend else ""

        item["status"] = data.get("status", "")
        item["telephone"] = data.get("telephone", "")
        item["title"] = data.get("title", "")
        item["user_level"] = data.get("userLevel", "")
        item["user_type"] = data.get("userType", "")

        if len(data) == 17:
            setting = data.get("setting", "")
            if setting:
                item["patient_verify"] = setting.get("patientVerify", "")
                item["need_assistant"] = setting.get("needAssistant", "")
                item["is_push_flag"] = setting.get("ispushflag", "")
                item["friends_verify"] = setting.get("friendsVerify", "")
                item["doctor_verify"] = setting.get("doctorVerify", "")
                item["disp_msg_detail"] = setting.get("dispMsgDetail", "")
                item["allow_greet"] = setting.get("allowGreet", "")
                item["allow_att"] = setting.get("allowAtt", "")
            else:
                item["patient_verify"] = ""
                item["need_assistant"] = ""
                item["is_push_flag"] = ""
                item["friends_verify"] = ""
                item["doctor_verify"] = ""
                item["disp_msg_detail"] = ""
                item["allow_greet"] = ""
                item["allow_att"] = ""
        else:
            item["patient_verify"] = ""
            item["need_assistant"] = ""
            item["is_push_flag"] = ""
            item["friends_verify"] = ""
            item["doctor_verify"] = ""
            item["disp_msg_detail"] = ""
            item["allow_greet"] = ""
            item["allow_att"] = ""

        yield item
