from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import monitoring


class _FakeStorage:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def update_website_data(
        self, province: str, city: str, webname: str, updates: dict[str, object]
    ) -> bool:
        self.calls.append(
            {
                "province": province,
                "city": city,
                "webname": webname,
                "updates": updates,
            }
        )
        return True


def test_build_biz_type_prefers_real_second_level_type_when_available() -> None:
    assert (
        monitoring.build_biz_type("建设工程", "招标公告", "房屋建筑")
        == "建设工程-房屋建筑"
    )


def test_build_biz_type_falls_back_to_first_level_type_when_no_real_second_level_type() -> (
    None
):
    assert monitoring.build_biz_type("建设工程", "招标公告") == "建设工程"
    assert monitoring.build_biz_type("政府采购", "中标（成交）公告") == "政府采购"


def test_build_logo_info_matches_monitoring_document_fields() -> None:
    logo_info = monitoring.build_logo_info("淄博市公共资源交易网", "建设工程-招标公告")

    assert logo_info == {
        "WasSuccessful": 1,
        "WebsiteError": 1,
        "HasContent": 0,
        "HasNewData": 0,
        "IsValidData": 1,
        "WebName": "淄博市公共资源交易网",
        "BizType": "建设工程-招标公告",
    }


def test_spider_monitor_flush_uses_document_storage_shape() -> None:
    storage = _FakeStorage()
    spider_monitor = monitoring.SpiderMonitor(
        province="山东省",
        city="淄博市",
        webname="淄博市公共资源交易网",
        biz_type="建设工程-招标公告",
        storage=storage,
    )

    spider_monitor.mark_has_content()
    spider_monitor.mark_has_new_data()
    spider_monitor.flush()

    assert len(storage.calls) == 1
    call = storage.calls[0]
    assert call["province"] == "山东省"
    assert call["city"] == "淄博市"
    assert call["webname"] == "淄博市公共资源交易网"
    assert call["updates"] == {
        "WasSuccessful": 1,
        "WebsiteError": 1,
        "HasContent": 1,
        "HasNewData": 1,
        "IsValidData": 1,
        "WebName": "淄博市公共资源交易网",
        "BizType": "建设工程-招标公告",
    }


def test_spider_monitor_can_mark_failure_and_invalid_data() -> None:
    storage = _FakeStorage()
    spider_monitor = monitoring.SpiderMonitor(
        province="山东省",
        city="淄博市",
        webname="淄博市公共资源交易网",
        biz_type="政府采购-中标（成交）公告",
        storage=storage,
    )

    spider_monitor.mark_run_failed()
    spider_monitor.mark_website_error()
    spider_monitor.mark_invalid_data()
    spider_monitor.flush()

    assert storage.calls[0]["updates"] == {
        "WasSuccessful": 0,
        "WebsiteError": 0,
        "HasContent": 0,
        "HasNewData": 0,
        "IsValidData": 0,
        "WebName": "淄博市公共资源交易网",
        "BizType": "政府采购-中标（成交）公告",
    }


def test_monitoring_module_is_local_to_zbggzy_project() -> None:
    assert Path(monitoring.__file__).resolve() == PROJECT_ROOT / "monitoring.py"


def test_website_redis_storage_uses_default_connection_settings(monkeypatch) -> None:
    if str(PROJECT_ROOT) in sys.path:
        sys.path.remove(str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT))

    reloaded = importlib.reload(monitoring)
    redis_kwargs: dict[str, object] = {}

    class _FakeRedisClient:
        def __init__(self, **kwargs: object) -> None:
            redis_kwargs.update(kwargs)

        def ping(self) -> bool:
            return True

    monkeypatch.setattr(reloaded, "redis", SimpleNamespace(Redis=_FakeRedisClient))

    reloaded.WebsiteRedisStorage()

    assert Path(reloaded.__file__).resolve() == PROJECT_ROOT / "monitoring.py"
    assert redis_kwargs == {
        "host": "localhost",
        "port": 6379,
        "db": 11,
        "password": None,
        "decode_responses": True,
        "socket_connect_timeout": 5,
    }
