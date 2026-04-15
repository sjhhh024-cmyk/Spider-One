from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.middlewares import ProxyMiddleware, RetryMiddleware, get_proxy  # noqa: E402
from doctor_ywbd.tools import get_proxy_auth_header  # noqa: E402


class DummyRequest:
    def __init__(self, url: str = "https://data.120ask.com/yisheng/jibing.html") -> None:
        self.url = url
        self.meta: dict[str, str] = {}
        self.headers: dict[str, str] = {}
        self.dont_filter = False

    def copy(self):
        cloned = DummyRequest(url=self.url)
        cloned.meta = dict(self.meta)
        cloned.headers = dict(self.headers)
        cloned.dont_filter = self.dont_filter
        return cloned


class DummyRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def sadd(self, key: str, value: str) -> int:
        self.calls.append((key, value))
        return 1


class DummySpider:
    def __init__(self) -> None:
        self.redis_key = "doctor_ywbd:disease_list_url"
        self.server = DummyRedis()
        self.logger = type("Logger", (), {"warning": lambda *args, **kwargs: None})()


class DummyResponse:
    def __init__(self, url: str, status: int) -> None:
        self.url = url
        self.status = status


def test_get_proxy_returns_abuyun_proxy_meta() -> None:
    proxy = get_proxy()
    assert proxy.startswith("http://")
    assert proxy == "http://http-dyn.abuyun.com:9020"


def test_get_proxy_auth_header_returns_basic_auth() -> None:
    proxy_auth = get_proxy_auth_header()

    assert proxy_auth.startswith("Basic ")


def test_proxy_middleware_sets_proxy_on_request() -> None:
    request = DummyRequest()
    middleware = ProxyMiddleware()

    middleware.process_request(request, spider=None)

    assert request.meta["proxy"] == "http://http-dyn.abuyun.com:9020"
    assert request.meta["_auth_proxy"] == "http://http-dyn.abuyun.com:9020"
    assert request.headers["Proxy-Authorization"].startswith("Basic ")


def test_user_agent_middleware_sets_browser_like_headers() -> None:
    request = DummyRequest()
    from doctor_ywbd.middlewares import UserAgentMiddleware

    middleware = UserAgentMiddleware()
    middleware.process_request(request, spider=None)

    assert request.headers["Accept"].startswith("text/html,application/xhtml+xml")
    assert request.headers["Accept-Language"] == "zh-CN,zh;q=0.9"
    assert request.headers["Cache-Control"] == "no-cache"
    assert request.headers["Pragma"] == "no-cache"
    assert request.headers["Upgrade-Insecure-Requests"] == "1"
    assert request.headers["Sec-Fetch-Mode"] == "navigate"
    assert request.headers["sec-ch-ua-platform"] == '"Windows"'
    assert "Chrome/" in request.headers["User-Agent"]


def test_user_agent_middleware_sets_cookie_when_configured() -> None:
    request = DummyRequest()
    from doctor_ywbd.middlewares import UserAgentMiddleware

    middleware = UserAgentMiddleware(cookie_header="isYY=yisheng; __jsl_clearance_s=test")
    middleware.process_request(request, spider=None)

    assert request.headers["Cookie"] == "isYY=yisheng; __jsl_clearance_s=test"


def test_retry_middleware_returns_response_on_521_for_manual_cookie_mode() -> None:
    class DummyCookieManager:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []
            self.current_cookie = "isYY=yisheng; __jsluid_s=abc; __jsl_clearance_s=old"

        def set_clearance_cookie_from_html(self, html: str, *, url: str) -> str:
            self.calls.append((html, url))
            self.current_cookie = "isYY=yisheng; __jsluid_s=abc; __jsl_clearance_s=new"
            return self.current_cookie

        def get_cookie_header(self) -> str:
            return self.current_cookie

    middleware = RetryMiddleware(cookie_manager=DummyCookieManager())
    spider = DummySpider()
    request = DummyRequest(url="https://data.120ask.com/yisheng/list_j4928p106.html")
    response = DummyResponse(request.url, 521)
    response.text = '<script>go({"bts":["foo","bar"],"chars":"abc","ct":"e4b46d95deb7d3ccf14e984add43a4b2","ha":"md5","is":true,"tn":"__jsl_clearance_s","vt":"3600","wt":"1500"})</script>'

    result = middleware.process_response(request=request, response=response, spider=spider)

    assert result is not response
    assert result.headers["Cookie"] == "isYY=yisheng; __jsluid_s=abc; __jsl_clearance_s=new"
    assert result.meta["ywbd_cookie_retry"] == 1
    assert result.dont_filter is True
    assert spider.server.calls == []


def test_retry_middleware_leaves_non_521_status_to_default_retry_chain() -> None:
    middleware = RetryMiddleware()
    spider = DummySpider()
    request = DummyRequest(url="https://data.120ask.com/yisheng/jibing.html")
    response = DummyResponse("https://data.120ask.com/yisheng/jibing.html", 500)

    result = middleware.process_response(request=request, response=response, spider=spider)

    assert result is response
    assert spider.server.calls == []
