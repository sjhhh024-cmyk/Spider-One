from __future__ import annotations

import sys
from pathlib import Path

from scrapy.http import Headers, Request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.curl_cffi_downloader import (  # noqa: E402
    CurlCffiMiddleware,
    attach_proxy_credentials,
    build_curl_cffi_request_kwargs,
    should_use_curl_cffi,
)


def test_attach_proxy_credentials_inlines_basic_auth_into_proxy_url() -> None:
    proxy_url = "http://http-dyn.abuyun.com:9020"
    proxy_auth_header = "Basic SE1URVNUOlBBU1NURVNU"

    result = attach_proxy_credentials(proxy_url, proxy_auth_header)

    assert result == "http://HMTEST:PASSTEST@http-dyn.abuyun.com:9020"


def test_attach_proxy_credentials_keeps_proxy_url_without_auth() -> None:
    proxy_url = "http://http-dyn.abuyun.com:9020"

    result = attach_proxy_credentials(proxy_url, "")

    assert result == proxy_url


def test_build_curl_cffi_request_kwargs_reuses_scrapy_headers_and_proxy() -> None:
    request = Request("https://data.120ask.com/yisheng/list_a410102.html", method="GET")
    request.headers = Headers(
        {
            "Accept": "text/html",
            "Cookie": "isYY=yisheng",
            "Proxy-Authorization": "Basic SE1URVNUOlBBU1NURVNU",
        }
    )
    request.meta["proxy"] = "http://http-dyn.abuyun.com:9020"

    kwargs = build_curl_cffi_request_kwargs(request, impersonate="chrome", timeout=30)

    assert kwargs["impersonate"] == "chrome"
    assert kwargs["timeout"] == 30
    assert kwargs["headers"]["accept"] == "text/html"
    assert kwargs["headers"]["cookie"] == "isYY=yisheng"
    assert "proxy-authorization" not in kwargs["headers"]
    assert kwargs["proxies"] == {
        "http": "http://HMTEST:PASSTEST@http-dyn.abuyun.com:9020",
        "https": "http://HMTEST:PASSTEST@http-dyn.abuyun.com:9020",
    }


def test_should_use_curl_cffi_matches_enabled_spider_name() -> None:
    request = Request("https://data.120ask.com/yisheng/list_a410102.html")

    assert should_use_curl_cffi(request, spider_name="area_list_spider", enabled_spiders={"area_list_spider"}) is True
    assert should_use_curl_cffi(request, spider_name="doctor_detail_spider", enabled_spiders={"area_list_spider"}) is False


def test_should_use_curl_cffi_respects_request_meta_override() -> None:
    request = Request("https://data.120ask.com/yisheng/list_a410102.html", meta={"use_curl_cffi": True})

    assert should_use_curl_cffi(request, spider_name="doctor_detail_spider", enabled_spiders=set()) is True


def test_download_request_drops_compression_headers_for_decoded_body(monkeypatch) -> None:
    class FakeCurlResponse:
        url = "https://data.120ask.com/yisheng/list_a410102.html"
        status_code = 200
        headers = {
            "Content-Encoding": "gzip",
            "Content-Length": "9999",
            "Content-Type": "text/html; charset=utf-8",
        }
        content = b"<!DOCTYPE html><html><body>ok</body></html>"
        text = content.decode("utf-8")
        charset = "utf-8"

    def fake_request(method, url, **kwargs):
        return FakeCurlResponse()

    monkeypatch.setattr("doctor_ywbd.curl_cffi_downloader.curl_requests.request", fake_request)
    middleware = CurlCffiMiddleware(
        enabled=True,
        enabled_spiders={"area_list_spider"},
        impersonate="chrome",
        timeout=40,
    )
    request = Request("https://data.120ask.com/yisheng/list_a410102.html", method="GET")

    response = middleware._download_request(request)

    assert response.body.startswith(b"<!DOCTYPE html>")
    assert b"Content-Encoding" not in response.headers
    assert b"Content-Length" not in response.headers
