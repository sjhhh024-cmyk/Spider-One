"""第 7 步：医生详情页入库。"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin, urlparse

from scrapy_redis.spiders import RedisSpider

from doctor_ywbd.items import YwbdItem
from doctor_ywbd.route_hypotheses import build_redis_keys


TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
NAME_BLOCK_PATTERN = re.compile(
    r"""<dd[^>]+class=["'][^"']*name[^"']*["'][^>]*>\s*<b>(.*?)</b>\s*</dd>""",
    re.IGNORECASE | re.DOTALL,
)
EXPERIENCE_PATTERN = re.compile(
    r"""<div[^>]+class=["'][^"']*experience[^"']*["'][^>]*>(.*?)</div>""",
    re.IGNORECASE | re.DOTALL,
)
AVATAR_PATTERN = re.compile(
    r"""<div[^>]+class=["'][^"']*dor-msg[^"']*["'][\s\S]*?<img[^>]+src=["']([^"']+)["']""",
    re.IGNORECASE,
)
TITLE_VALUE_PATTERN = re.compile(
    r"(主任医师|副主任医师|主治医师|医师|主任中医师|副主任中医师|主治中医师|中医师|主任药师|副主任药师|主管药师|药师|主任护师|副主任护师|主管护师|护师|护士|技师|主管技师)"
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


def _extract_doctor_name_and_title(html: str, page_title: str) -> tuple[str, str]:
    match = NAME_BLOCK_PATTERN.search(html or "")
    if match:
        name_block = match.group(1)
        strong_match = re.search(r"<strong[^>]*>(.*?)</strong>", name_block, re.IGNORECASE | re.DOTALL)
        doctor_name = _strip_tags(strong_match.group(1)) if strong_match else ""
        name_line_text = _strip_tags(name_block)
        title_text = name_line_text.replace(doctor_name, "", 1).strip() if doctor_name else name_line_text
        return doctor_name, title_text

    title_name_match = re.search(r"【([^】]+)】", page_title)
    if title_name_match:
        return _normalize_whitespace(title_name_match.group(1)), ""
    if page_title:
        return _normalize_whitespace(page_title.split("_", 1)[0]), ""
    return "", ""


def _extract_intro(html: str) -> str:
    experience_match = EXPERIENCE_PATTERN.search(html or "")
    if experience_match:
        intro = _strip_tags(experience_match.group(1))
        return re.sub(r"^医生介绍\s*", "", intro).strip()

    return _extract_labeled_text(html, "简　　介：") or _extract_labeled_text(html, "简介：")


def _extract_gender(intro: str) -> str:
    match = re.search(r"[，,\s](男|女)[，,\s]", f" {intro} ")
    return match.group(1) if match else ""


def _extract_title(name_title: str, intro: str) -> str:
    normalized = _normalize_whitespace(name_title)
    if normalized and normalized != "其他":
        title_match = TITLE_VALUE_PATTERN.search(normalized)
        if title_match:
            return title_match.group(1)
        return normalized

    intro_match = TITLE_VALUE_PATTERN.search(intro)
    return intro_match.group(1) if intro_match else ""


def extract_doctor_detail_fields(url: str, html: str) -> dict[str, str]:
    """从医生详情页抽取最终医生详情字段。"""

    path = urlparse(url).path
    doctor_id = path.rsplit("/", 1)[-1].replace(".html", "")

    title_match = TITLE_PATTERN.search(html or "")
    page_title = _strip_tags(title_match.group(1)) if title_match else ""
    doctor_name, name_title = _extract_doctor_name_and_title(html, page_title)
    intro = _extract_intro(html)
    avatar_match = AVATAR_PATTERN.search(html or "")
    avatar_url = urljoin(url, avatar_match.group(1)) if avatar_match else ""
    good_at = (
        _extract_labeled_text(html, "擅　　长：")
        or _extract_labeled_text(html, "擅长：")
    ).replace("[详细]", "").strip()

    return {
        "_id": doctor_id,
        "url": url,
        "website": "有问必答",
        "doctor_name": doctor_name,
        "title": _extract_title(name_title, intro),
        "gender": _extract_gender(intro),
        "hospital_name": _extract_labeled_text(html, "所在医院："),
        "department_name": _extract_labeled_text(html, "所在科室：") or _extract_labeled_text(html, "科室："),
        "good_at": good_at,
        "intro": intro,
        "avatar_url": avatar_url,
    }


class Spider(RedisSpider):
    """读取统一医生详情队列并落库。"""

    name = "doctor_detail_spider"
    redis_key = build_redis_keys()["doctor_info_url"]

    def parse(self, response):
        detail_fields = extract_doctor_detail_fields(response.url, response.text)
        self.logger.info(
            "医生详情: %s | 姓名: %s | 医院: %s | 科室: %s | 职称: %s",
            detail_fields.get("url", response.url),
            detail_fields.get("doctor_name", ""),
            detail_fields.get("hospital_name", ""),
            detail_fields.get("department_name", ""),
            detail_fields.get("title", ""),
        )
        item = YwbdItem()
        for field_name, field_value in detail_fields.items():
            item[field_name] = field_value
        yield item
