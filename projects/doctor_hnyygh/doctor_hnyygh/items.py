"""doctor_hnyygh 项目数据结构。

字段对比说明：
1. 未单独说明的基础字段，是之前删减版里已经保留的字段。
2. 标注为“新站详情补回”的字段，是这次接入 169000 新站详情接口后补回、并确认需要入库的扩展字段。
"""

from scrapy import Field, Item


class DoctorHnyyghItem(Item):
    # 基础主键与医生基础信息：之前删减版已保留。
    _id = Field()
    doctor_id = Field()
    doctor_name = Field()
    doctor_hospital = Field()
    doctor_department = Field()
    doctor_title = Field()
    doctor_avatar_url = Field()

    # 新站详情补回字段：之前删减版没有，这次从新站医生详情接口补齐。
    doctor_education = Field()

    # 医生简介与来源信息：之前删减版已保留。
    doctor_specialties = Field()
    intro = Field()
    source_site = Field()
    source_url = Field()
    crawl_time = Field()


class HospitalHnyyghItem(Item):
    # 基础主键与医院基础信息：之前删减版已保留。
    _id = Field()
    hospital_id = Field()
    hospital_name = Field()
    hospital_city_id = Field()
    hospital_city_name = Field()
    hospital_address = Field()
    hospital_phone = Field()
    hospital_intro = Field()
    hospital_website = Field()

    # 新站详情补回字段：之前删减版没有，这次从新站医院详情接口补齐。
    hospital_level = Field()
    hospital_type = Field()
    hospital_logo = Field()
    hospital_code = Field()
    hospital_area = Field()
    hospital_geo = Field()
    hospital_dept_count = Field()
    hospital_doctor_count = Field()

    # 来源信息：之前删减版已保留。
    source_site = Field()
    source_url = Field()
    crawl_time = Field()
