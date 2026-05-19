"""项目里的数据结构定义。"""

from scrapy import Field, Item


class YwbdItem(Item):
    """最终医生详情结构。"""

    _id = Field()
    url = Field()
    website = Field()
    doctor_name = Field()
    title = Field()
    gender = Field()
    hospital_name = Field()
    department_name = Field()
    good_at = Field()
    intro = Field()
    avatar_url = Field()


class HospitalYlysItem(Item):
    """医院基础信息结构。"""

    _id = Field()
    hospital_name = Field()
    hospital_url = Field()
    hospital_address = Field()
    hospital_phone = Field()
    hospital_intro = Field()
    website = Field()
