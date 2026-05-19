"""Scrapy 与 curl_cffi 的桥接下载中间件。"""

from __future__ import annotations

import base64
from urllib.parse import quote, urlsplit, urlunsplit

from curl_cffi import requests as curl_requests
from scrapy.http import Headers, HtmlResponse
from twisted.internet import threads


def _to_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("latin1")
    return str(value)


def scrapy_headers_to_dict(headers) -> dict[str, str]:
    """把 Scrapy Headers 转成普通字典。"""

    if hasattr(headers, "to_unicode_dict"):
        return {str(key): str(value) for key, value in headers.to_unicode_dict().items()}
    return {_to_text(key): _to_text(value) for key, value in dict(headers or {}).items()}


def _pop_header_case_insensitive(headers: dict[str, str], header_name: str) -> str:
    normalized_target = str(header_name or "").strip().lower()
    for key in list(headers):
        if str(key).strip().lower() == normalized_target:
            return headers.pop(key)
    return ""


def build_scrapy_response_headers(response_headers) -> Headers:
    """把 curl_cffi 响应头转换成 Scrapy Headers，并去掉已失效的压缩长度信息。"""

    normalized_headers = {str(key): str(value) for key, value in dict(response_headers or {}).items()}
    _pop_header_case_insensitive(normalized_headers, "Content-Encoding")
    _pop_header_case_insensitive(normalized_headers, "Content-Length")
    return Headers(normalized_headers)


def attach_proxy_credentials(proxy_url: str, proxy_auth_header: str) -> str:
    """把 Proxy-Authorization 头里的 Basic 认证拼回代理 URL。"""

    normalized_proxy_url = str(proxy_url or "").strip()
    normalized_proxy_auth = str(proxy_auth_header or "").strip()
    if not normalized_proxy_url or not normalized_proxy_auth.lower().startswith("basic "):
        return normalized_proxy_url

    parsed_proxy = urlsplit(normalized_proxy_url)
    if parsed_proxy.username:
        return normalized_proxy_url

    encoded_credentials = normalized_proxy_auth.split(" ", 1)[1].strip()
    try:
        credentials = base64.b64decode(encoded_credentials).decode("utf-8")
    except Exception:
        return normalized_proxy_url
    if ":" not in credentials:
        return normalized_proxy_url

    username, password = credentials.split(":", 1)
    host = parsed_proxy.hostname or ""
    port = f":{parsed_proxy.port}" if parsed_proxy.port else ""
    auth_netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{host}{port}"
    return urlunsplit(
        (
            parsed_proxy.scheme,
            auth_netloc,
            parsed_proxy.path,
            parsed_proxy.query,
            parsed_proxy.fragment,
        )
    )


def build_curl_cffi_request_kwargs(request, *, impersonate: str, timeout: int) -> dict[str, object]:
    """从 Scrapy Request 生成 curl_cffi 请求参数。"""

    headers = scrapy_headers_to_dict(request.headers)
    proxy_auth_header = _pop_header_case_insensitive(headers, "Proxy-Authorization")
    proxy_url = attach_proxy_credentials(request.meta.get("proxy", ""), proxy_auth_header)

    kwargs: dict[str, object] = {
        "headers": headers,
        "timeout": timeout,
        "impersonate": impersonate,
        "verify": False,
    }
    if proxy_url:
        kwargs["proxies"] = {
            "http": proxy_url,
            "https": proxy_url,
        }
    if request.method.upper() != "GET" and request.body:
        kwargs["data"] = request.body
    return kwargs


def should_use_curl_cffi(request, *, spider_name: str, enabled_spiders: set[str]) -> bool:
    """判断当前请求是否使用 curl_cffi。"""

    if "use_curl_cffi" in request.meta:
        return bool(request.meta.get("use_curl_cffi"))
    return spider_name in enabled_spiders


class CurlCffiMiddleware:
    """对指定 spider 的请求使用 curl_cffi 下载。"""

    def __init__(self, *, enabled: bool, enabled_spiders: set[str], impersonate: str, timeout: int) -> None:
        self.enabled = bool(enabled)
        self.enabled_spiders = set(enabled_spiders)
        self.impersonate = str(impersonate or "chrome").strip() or "chrome"
        self.timeout = int(timeout)

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(
            enabled=settings.getbool("YWBD_CURL_CFFI_ENABLED", False),
            enabled_spiders=set(settings.getlist("YWBD_CURL_CFFI_ENABLED_SPIDERS", [])),
            impersonate=settings.get("YWBD_CURL_CFFI_IMPERSONATE", "chrome"),
            timeout=settings.getint("YWBD_CURL_CFFI_TIMEOUT", 40),
        )

    def process_request(self, request, spider):
        if not self.enabled:
            return None
        if not should_use_curl_cffi(request, spider_name=spider.name, enabled_spiders=self.enabled_spiders):
            return None
        return threads.deferToThread(self._download_request, request)

    def _download_request(self, request):
        kwargs = build_curl_cffi_request_kwargs(
            request,
            impersonate=str(request.meta.get("curl_cffi_impersonate", self.impersonate)),
            timeout=int(request.meta.get("download_timeout", self.timeout)),
        )
        response = curl_requests.request(request.method, request.url, **kwargs)
        response_headers = build_scrapy_response_headers(response.headers)
        body = response.content if response.content is not None else response.text.encode(response.charset or "utf-8")
        return HtmlResponse(
            url=str(response.url),
            status=response.status_code,
            headers=response_headers,
            body=body,
            encoding=response.charset or "utf-8",
            request=request,
        )
