from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import doctor_wygk.settings as settings_module  # noqa: E402


def test_default_redis_connection_uses_shared_remote_instance(monkeypatch) -> None:
    monkeypatch.delenv("SPIDER_ONE_REDIS_HOST", raising=False)
    monkeypatch.delenv("SPIDER_ONE_REDIS_PORT", raising=False)
    monkeypatch.delenv("SPIDER_ONE_REDIS_DB", raising=False)
    monkeypatch.delenv("SPIDER_ONE_REDIS_PASSWORD", raising=False)

    reloaded = importlib.reload(settings_module)

    assert reloaded.REDIS_HOST == "117.50.131.232"
    assert reloaded.REDIS_PORT == 6379
    assert reloaded.REDIS_PASSWORD == "Yb$]Mdh3YU2k}hw"
    assert reloaded.REDIS_DB == 1


def test_default_redis_timeouts_match_runtime_convention(monkeypatch) -> None:
    monkeypatch.delenv("SPIDER_ONE_REDIS_HOST", raising=False)
    monkeypatch.delenv("SPIDER_ONE_REDIS_PORT", raising=False)
    monkeypatch.delenv("SPIDER_ONE_REDIS_DB", raising=False)
    monkeypatch.delenv("SPIDER_ONE_REDIS_PASSWORD", raising=False)

    reloaded = importlib.reload(settings_module)

    assert reloaded.REDIS_PARAMS == {
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
        "decode_responses": False,
    }


def test_proxy_defaults_match_doctor_ywbd_credentials(monkeypatch) -> None:
    monkeypatch.delenv("ABUYUN_PROXY_HOST", raising=False)
    monkeypatch.delenv("ABUYUN_PROXY_PORT", raising=False)
    monkeypatch.delenv("ABUYUN_PROXY_USER", raising=False)
    monkeypatch.delenv("ABUYUN_PROXY_PASS", raising=False)

    reloaded = importlib.reload(settings_module)

    assert reloaded.ABUYUN_PROXY_HOST == "http-dyn.abuyun.com"
    assert reloaded.ABUYUN_PROXY_PORT == "9020"
    assert reloaded.ABUYUN_PROXY_USER == "HCBQVZ922819VL8D"
    assert reloaded.ABUYUN_PROXY_PASS == "6445C2F54F51B019"


def test_downloader_middlewares_enable_proxy_for_all_requests(monkeypatch) -> None:
    monkeypatch.delenv("ABUYUN_PROXY_HOST", raising=False)
    monkeypatch.delenv("ABUYUN_PROXY_PORT", raising=False)
    monkeypatch.delenv("ABUYUN_PROXY_USER", raising=False)
    monkeypatch.delenv("ABUYUN_PROXY_PASS", raising=False)

    reloaded = importlib.reload(settings_module)

    assert reloaded.DOWNLOADER_MIDDLEWARES == {
        "doctor_wygk.middlewares.RetryMiddleware": 502,
        "doctor_wygk.middlewares.UserAgentMiddleware": 503,
        "doctor_wygk.middlewares.ProxyMiddleware": 504,
        "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
    }
