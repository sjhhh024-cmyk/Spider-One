"""医院详情页扩展。"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

from scrapy import Request
from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.items import HospitalYlysItem
from doctor_ywbd.probe_helpers import extract_doctor_info_urls
from doctor_ywbd.redis_requests import push_redis_request
from doctor_ywbd.route_hypotheses import BASE_URL
from doctor_ywbd.route_hypotheses import build_redis_keys


TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
BASIC_BLOCK_PATTERN = re.compile(
    r"""<div[^>]+class=["'][^"']*basic[^"']*["'][^>]*>[\s\S]*?<p>([\s\S]*?)</p>""",
    re.IGNORECASE,
)
DETAIL_BLOCK_PATTERN = re.compile(
    r"""<div[^>]+class=["'][^"']*detail[^"']*["'][^>]*>([\s\S]*?)</div>""",
    re.IGNORECASE,
)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _strip_tags(value: str) -> str:
    return _normalize_whitespace(re.sub(r"<[^>]+>", " ", value or ""))


def _extract_labeled_text(html: str, label: str) -> str:
    pattern = re.compile(
        rf"""{re.escape(label)}(?:\s|&nbsp;|<[^>]+>)*([^<\r\n]+)""",
        re.IGNORECASE,
    )
    match = pattern.search(html or "")
    return _normalize_whitespace(match.group(1)) if match else ""


def extract_hospital_detail_fields(url: str, html: str) -> dict[str, str]:
    """从医院介绍页抽取医院基础字段。"""

    path = urlparse(url).path
    hospital_id = path.rsplit("/", 1)[-1].replace(".html", "")

    title_match = TITLE_PATTERN.search(html or "")
    page_title = _strip_tags(title_match.group(1)) if title_match else ""
    hospital_name = _normalize_whitespace(page_title.split("介绍", 1)[0]) if "介绍" in page_title else ""

    basic_match = BASIC_BLOCK_PATTERN.search(html or "")
    basic_html = basic_match.group(1) if basic_match else ""
    detail_match = DETAIL_BLOCK_PATTERN.search(html or "")
    detail_html = detail_match.group(1) if detail_match else ""

    hospital_intro = _strip_tags(re.sub(r"<b[^>]*>.*?</b>", " ", detail_html, flags=re.IGNORECASE | re.DOTALL))

    return {
        "_id": hospital_id,
        "hospital_name": hospital_name,
        "hospital_url": f"{BASE_URL}/yiyuan/{hospital_id}.html",
        "hospital_address": _extract_labeled_text(basic_html, "医院地址："),
        "hospital_phone": _extract_labeled_text(basic_html, "医院电话："),
        "hospital_intro": hospital_intro,
        "website": "有问必答",
    }


class Spider(RedisSpider):
    """处理医院详情页，补充页面直出的医生详情链接。"""

    name = "hospital_detail_spider"
    redis_key = build_redis_keys()["hospital_detail_url"]

    def parse(self, response):
        doctor_urls = extract_doctor_info_urls(response.url, response.text)
        doctor_info_key = build_redis_keys()["doctor_info_url"]
        new_doctor_count = 0
        hospital_id = urlparse(response.url).path.rsplit("/", 1)[-1].replace(".html", "")

        for url in doctor_urls:
            new_doctor_count += push_redis_request(self.server, doctor_info_key, url)

        yield Request(
            url=f"{BASE_URL}/yiyuan/jieshao/{hospital_id}.html",
            callback=self.parse_hospital_intro,
            dont_filter=True,
            cb_kwargs={"hospital_url": response.url},
        )

        self.logger.info(
            "医院详情页: %s | 详情入队: %s/%s | 详情队列剩余: %s | 样本详情: %s",
            response.url,
            new_doctor_count,
            len(doctor_urls),
            self.server.scard(doctor_info_key),
            doctor_urls[0] if doctor_urls else "",
        )

    def parse_hospital_intro(self, response, hospital_url: str):
        hospital_fields = extract_hospital_detail_fields(response.url, response.text)
        hospital_fields["hospital_url"] = hospital_url
        self.logger.info(
            "医院入库: %s | 地址: %s | 电话: %s",
            hospital_fields.get("hospital_name", ""),
            hospital_fields.get("hospital_address", ""),
            hospital_fields.get("hospital_phone", ""),
        )
        item = HospitalYlysItem()
        for field_name, field_value in hospital_fields.items():
            item[field_name] = field_value
        yield item
