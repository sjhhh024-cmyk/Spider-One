"""第 6 步：课程导航 -> 项目 -> 课表 -> 医生候选任务。"""

from __future__ import annotations

import json

from scrapy import Request, Spider
from scrapy.http import JsonRequest
from scrapy_redis.connection import get_redis_from_settings

from doctor_wygk.parse_helpers import (
    parse_course_detail_channel_id,
    parse_course_navigation_records,
    parse_course_project_records,
    parse_course_timetable_doctor_records,
    parse_page_info,
)
from doctor_wygk.request_builders import (
    build_course_navigation_request,
    build_course_project_detail_request,
    build_course_project_list_request,
    build_course_timetable_request,
)
from doctor_wygk.tools import build_get_url, push_doctor_task


class Spider(Spider):
    """课程模块走公开导航树和课表，把讲者统一回流到详情队列。"""

    name = "course_doctor_spider"
    page_size = 20

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_project_ids: set[str] = set()

    def start_requests(self):
        request_data = build_course_navigation_request()
        yield Request(
            build_get_url(request_data["url"], request_data["params"]),
            callback=self.parse_navigation,
            dont_filter=True,
        )

    def parse_navigation(self, response):
        payload = json.loads(response.text)
        channel_ids = parse_course_navigation_records(payload)

        for channel_id in channel_ids:
            request_data = build_course_project_list_request(
                channel_id=channel_id,
                page_num=1,
                page_size=self.page_size,
            )
            yield JsonRequest(
                request_data["url"],
                data=request_data["body"],
                callback=self.parse_project_list,
                cb_kwargs={"channel_id": channel_id, "page_num": 1},
                dont_filter=True,
            )

        self.logger.info("课程导航展开完成: channel=%s", len(channel_ids))

    def parse_project_list(self, response, channel_id, page_num):
        payload = json.loads(response.text)
        projects = parse_course_project_records(payload)
        page_info = parse_page_info(payload)

        for project in projects:
            if project["project_id"] in self.seen_project_ids:
                continue
            self.seen_project_ids.add(project["project_id"])
            request_data = build_course_project_detail_request(project["project_id"])
            yield Request(
                build_get_url(request_data["url"], request_data["params"]),
                callback=self.parse_project_detail,
                cb_kwargs={"project": project},
                dont_filter=True,
            )

        if page_info["total_page_count"] > page_num:
            next_page_num = page_num + 1
            request_data = build_course_project_list_request(
                channel_id=channel_id,
                page_num=next_page_num,
                page_size=self.page_size,
            )
            yield JsonRequest(
                request_data["url"],
                data=request_data["body"],
                callback=self.parse_project_list,
                cb_kwargs={"channel_id": channel_id, "page_num": next_page_num},
                dont_filter=True,
            )

        self.logger.info(
            "课程项目页: channel=%s | page=%s/%s | project=%s | 累计去重项目=%s",
            channel_id,
            page_num,
            page_info["total_page_count"],
            len(projects),
            len(self.seen_project_ids),
        )

    def parse_project_detail(self, response, project):
        payload = json.loads(response.text)
        channel_id = parse_course_detail_channel_id(payload)
        if not channel_id:
            self.logger.info("课程项目无课表频道: project_id=%s | title=%s", project["project_id"], project["project_name"])
            return

        request_data = build_course_timetable_request(
            project_id=project["project_id"],
            channel_id=channel_id,
        )
        yield JsonRequest(
            request_data["url"],
            data=request_data["body"],
            callback=self.parse_timetable,
            cb_kwargs={"project": project, "channel_id": channel_id},
            dont_filter=True,
        )

    def parse_timetable(self, response, project, channel_id):
        payload = json.loads(response.text)
        doctors = parse_course_timetable_doctor_records(
            payload,
            project_id=project["project_id"],
            channel_id=channel_id,
        )
        redis_client = get_redis_from_settings(self.settings)
        detail_push_count = 0
        home_push_count = 0

        for doctor in doctors:
            push_result = push_doctor_task(redis_client, doctor)
            detail_push_count += push_result["doctor_info_url"]
            home_push_count += push_result["doctor_home_task"]

        self.logger.info(
            "课程讲者回流: project_id=%s | title=%s | doctor=%s | 详情入队=%s | 主页入队=%s",
            project["project_id"],
            project["project_name"],
            len(doctors),
            detail_push_count,
            home_push_count,
        )
