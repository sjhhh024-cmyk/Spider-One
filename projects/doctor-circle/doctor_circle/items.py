"""项目里的数据结构定义。"""

from scrapy import Field, Item


class CircleItem(Item):
    """圈子列表记录。"""

    _id = Field()
    source_url = Field()
    website = Field()
    grab_date = Field()
    extracted = Field()

    circle_id = Field()
    circle_name = Field()
    logo = Field()
    member_total = Field()
    master_name = Field()


class DoctorItem(Item):
    """医生详情记录。"""

    _id = Field()
    source_url = Field()
    website = Field()
    grab_date = Field()
    extracted = Field()

    doctor_id = Field()
    doctor_name = Field()
    hospital = Field()
    departments = Field()
    fans = Field()
    followers = Field()
    is_3a = Field()
    logo_url = Field()
    real_status = Field()
    skill = Field()
    star_friend = Field()
    status = Field()
    telephone = Field()
    title = Field()
    user_level = Field()
    user_type = Field()
    patient_verify = Field()
    need_assistant = Field()
    is_push_flag = Field()
    friends_verify = Field()
    doctor_verify = Field()
    disp_msg_detail = Field()
    allow_greet = Field()
    allow_att = Field()
