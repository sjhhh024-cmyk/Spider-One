from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_wygk.middlewares import ProxyMiddleware, UserAgentMiddleware  # noqa: E402
from doctor_wygk.tools import get_proxy, get_proxy_auth_header  # noqa: E402


class DummyRequest:
    def __init__(self) -> None:
        self.meta: dict[str, str] = {}
        self.headers: dict[str, str] = {}


def test_get_proxy_returns_same_abuyun_endpoint_as_doctor_ywbd() -> None:
    assert get_proxy() == "http://http-dyn.abuyun.com:9020"


def test_get_proxy_auth_header_returns_basic_auth_value() -> None:
    assert get_proxy_auth_header().startswith("Basic ")


def test_proxy_middleware_sets_proxy_on_every_request() -> None:
    request = DummyRequest()

    ProxyMiddleware().process_request(request, spider=None)

    assert request.meta["proxy"] == "http://http-dyn.abuyun.com:9020"
    assert request.meta["_auth_proxy"] == "http://http-dyn.abuyun.com:9020"
    assert request.headers["Proxy-Authorization"].startswith("Basic ")


def test_user_agent_middleware_keeps_existing_user_agent_behavior() -> None:
    request = DummyRequest()

    UserAgentMiddleware().process_request(request, spider=None)

    assert "Chrome/" in request.headers["User-Agent"]
