"""doctor_wygk Scrapy items."""

from __future__ import annotations

import scrapy


class DoctorWygkItem(scrapy.Item):
    """统一医生详情 item。"""

    _id = scrapy.Field()
    doctor_id = scrapy.Field()
    doctor_name = scrapy.Field()
    doctor_title = scrapy.Field()
    hospital_name = scrapy.Field()
    department_name = scrapy.Field()
    doctor_expertise = scrapy.Field()
    doctor_introduction = scrapy.Field()
    doctor_avatar_url = scrapy.Field()
    doctor_illnesses = scrapy.Field()
    doctor_social_titles = scrapy.Field()
    doctor_honors = scrapy.Field()
    doctor_academic_achievements = scrapy.Field()
    doctor_practice_achievements = scrapy.Field()
    doctor_work_experiences = scrapy.Field()
    doctor_educations = scrapy.Field()
    doctor_continuing_educations = scrapy.Field()
    doctor_funds = scrapy.Field()
    doctor_opuses = scrapy.Field()
    doctor_patents = scrapy.Field()
    doctor_big_events = scrapy.Field()
    website = scrapy.Field()
    source_url = scrapy.Field()
    crawl_time = scrapy.Field()
