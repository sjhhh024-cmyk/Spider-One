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
