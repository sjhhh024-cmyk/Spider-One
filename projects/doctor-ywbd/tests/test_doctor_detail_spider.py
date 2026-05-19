from __future__ import annotations

import importlib
import sys
from pathlib import Path

from scrapy import Request
from scrapy.http import Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.python.failure import Failure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


doctor_detail_module = importlib.import_module("doctor_ywbd.spiders.doctor.12_doctor_detail_spider")


class DummyRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, int]] = {}
        self.sets: dict[str, set[str]] = {}

    def hincrby(self, key: str, field: str, amount: int) -> int:
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = int(bucket.get(field, 0)) + amount
        return bucket[field]

    def hdel(self, key: str, field: str) -> int:
        bucket = self.hashes.setdefault(key, {})
        return int(bucket.pop(field, None) is not None)

    def hget(self, key: str, field: str):
        return self.hashes.get(key, {}).get(field)

    def sadd(self, key: str, value: str) -> int:
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        bucket.add(value)
        return len(bucket) - before


def build_test_spider(max_requeue_attempts: int = 2):
    spider = doctor_detail_module.Spider()
    spider.server = DummyRedis()
    spider.redis_key = "doctor_ywbd:doctor_info_url"
    spider.retry_count_key = "doctor_ywbd:doctor_info_url:failures"
    spider.always_requeue_statuses = {403, 521}
    spider.max_requeue_attempts = max_requeue_attempts
    spider.redis_encoding = "utf-8"
    return spider


def test_extract_doctor_detail_fields_from_detail_html() -> None:
    html = """
    <html>
      <head>
        <title>【王小渝】四川省第三人民医院血液内科王小渝介绍_王小渝出诊时间_王小渝怎么样-快速问医生</title>
      </head>
      <body>
        <div class="dor-msg">
          <dl class="clears">
            <dt><img src="//cdn.120askimages.com/ask/newdata/images/ys/f06faia2nlwg3h0f.jpg"></dt>
            <dd class="name"><b><strong>王小渝</strong>  其他</b></dd>
            <dd class="msg">
              <p><span>所在医院：</span><var><a href="/yiyuan/0nwfblgaszpknec8.html">四川省第三人民医院</a></var></p>
              <p><span>所在科室：</span><var><a href="/keshi/l26iblgaszpknec8.html">血液内科</a></var></p>
              <p><span>擅　　长：</span><var>擅长治疗各种贫血、白血病、淋巴瘤、多发性骨髓瘤。</var></p>
              <p><span>简　　介：</span><var>王小渝，血液科一级，主任医师。从医四十余年。</var></p>
            </dd>
          </dl>
          <div class="experience"><b class="title">医生介绍</b>王小渝，血液科一级，主任医师。从医四十余年，曾任中华医学会四川省分会血液专委会常委。</div>
        </div>
      </body>
    </html>
    """
    assert doctor_detail_module.extract_doctor_detail_fields(
        "https://data.120ask.com/yisheng/f06faia2nlwg3h0f.html",
        html,
    ) == {
        "_id": "f06faia2nlwg3h0f",
        "url": "https://data.120ask.com/yisheng/f06faia2nlwg3h0f.html",
        "website": "有问必答",
        "doctor_name": "王小渝",
        "title": "主任医师",
        "gender": "",
        "hospital_name": "四川省第三人民医院",
        "department_name": "血液内科",
        "good_at": "擅长治疗各种贫血、白血病、淋巴瘤、多发性骨髓瘤。",
        "intro": "王小渝，血液科一级，主任医师。从医四十余年，曾任中华医学会四川省分会血液专委会常委。",
        "avatar_url": "https://cdn.120askimages.com/ask/newdata/images/ys/f06faia2nlwg3h0f.jpg",
    }


def test_extract_doctor_detail_fields_parse_gender_and_title_when_present() -> None:
    html = """
    <html>
      <body>
        <div class="dor-msg">
          <dl class="clears">
            <dt><img src="//cdn.120askimages.com/ask/newdata/images/ys_default.jpg"></dt>
            <dd class="name"><b><strong>马烈</strong> 主任医师</b></dd>
            <dd class="msg">
              <p><span>所在医院：</span><var><a href="/yiyuan/abc.html">北京地坛医院</a></var></p>
              <p><span>所在科室：</span><var><a href="/keshi/abc.html">肝病中心</a></var></p>
              <p><span>擅　　长：</span><var>乙型及丙型病毒性肝炎的抗病毒治疗。</var></p>
              <p><span>简　　介：</span><var>马烈，女，肝病中心主任医师。</var></p>
            </dd>
          </dl>
          <div class="experience"><b class="title">医生介绍</b>马烈，女，肝病中心主任医师，1984年毕业于北京医科大学。</div>
        </div>
      </body>
    </html>
    """
    assert doctor_detail_module.extract_doctor_detail_fields(
        "https://data.120ask.com/yisheng/f0f5aeb62vc9f5a6.html",
        html,
    ) == {
        "_id": "f0f5aeb62vc9f5a6",
        "url": "https://data.120ask.com/yisheng/f0f5aeb62vc9f5a6.html",
        "website": "有问必答",
        "doctor_name": "马烈",
        "title": "主任医师",
        "gender": "女",
        "hospital_name": "北京地坛医院",
        "department_name": "肝病中心",
        "good_at": "乙型及丙型病毒性肝炎的抗病毒治疗。",
        "intro": "马烈，女，肝病中心主任医师，1984年毕业于北京医科大学。",
        "avatar_url": "https://cdn.120askimages.com/ask/newdata/images/ys_default.jpg",
    }


def test_make_request_from_data_attaches_errback() -> None:
    spider = build_test_spider()

    request = spider.make_request_from_data(b'{"url":"https://data.120ask.com/yisheng/test.html"}')

    assert request.errback == spider.handle_request_error


def test_handle_request_error_requeues_url_before_limit() -> None:
    spider = build_test_spider(max_requeue_attempts=2)
    request = Request("https://data.120ask.com/yisheng/test.html")
    failure = Failure(RuntimeError("boom"))
    failure.request = request

    result = spider.handle_request_error(failure)

    assert result == []
    assert spider.server.hget(spider.retry_count_key, request.url) == 1
    assert spider.server.sets[spider.redis_key] == {
        '{"url":"https://data.120ask.com/yisheng/test.html"}'
    }


def test_handle_request_error_stops_requeue_after_limit() -> None:
    spider = build_test_spider(max_requeue_attempts=1)
    request = Request("https://data.120ask.com/yisheng/test.html")
    failure = Failure(RuntimeError("boom"))
    failure.request = request

    spider.handle_request_error(failure)
    spider.handle_request_error(failure)

    assert spider.server.hget(spider.retry_count_key, request.url) == 2
    assert spider.server.sets[spider.redis_key] == {
        '{"url":"https://data.120ask.com/yisheng/test.html"}'
    }


def test_handle_item_error_requeues_item_url() -> None:
    spider = build_test_spider(max_requeue_attempts=2)
    response = type("Response", (), {"url": "https://data.120ask.com/yisheng/from-response.html"})()
    failure = Failure(RuntimeError("mongo failed"))
    item = {"url": "https://data.120ask.com/yisheng/from-item.html"}

    spider.handle_item_error(item=item, response=response, spider=spider, failure=failure)

    assert spider.server.hget(spider.retry_count_key, item["url"]) == 1
    assert spider.server.sets[spider.redis_key] == {
        '{"url":"https://data.120ask.com/yisheng/from-item.html"}'
    }


def test_handle_item_scraped_clears_retry_counter() -> None:
    spider = build_test_spider(max_requeue_attempts=2)
    url = "https://data.120ask.com/yisheng/test.html"
    spider.server.hincrby(spider.retry_count_key, url, 2)

    spider.handle_item_scraped(item={"url": url}, response=None, spider=spider)

    assert spider.server.hget(spider.retry_count_key, url) is None


def test_handle_spider_error_requeues_403_without_retry_limit() -> None:
    spider = build_test_spider(max_requeue_attempts=1)
    request = Request("https://data.120ask.com/yisheng/test.html")
    response = Response(url=request.url, status=403, request=request)
    failure = Failure(HttpError(response, "ignored"))

    spider.handle_spider_error(failure=failure, response=response, spider=spider)
    spider.handle_spider_error(failure=failure, response=response, spider=spider)

    assert spider.server.sets[spider.redis_key] == {
        '{"url":"https://data.120ask.com/yisheng/test.html"}'
    }
    assert spider.server.hget(spider.retry_count_key, request.url) is None
