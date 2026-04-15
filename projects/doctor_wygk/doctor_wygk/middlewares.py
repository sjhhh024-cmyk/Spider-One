"""doctor_wygk 下载中间件。"""

from __future__ import annotations

from doctor_wygk.tools import get_proxy, get_proxy_auth_header


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class UserAgentMiddleware:
    """给请求补一个固定桌面 UA。"""

    def process_request(self, request, spider):
        if "User-Agent" not in request.headers:
            request.headers["User-Agent"] = DEFAULT_USER_AGENT
        return None


class RetryMiddleware:
    """预留自定义重试扩展位。当前保持透传。"""

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None


class ProxyMiddleware:
    """给所有请求挂 Abuyun 代理。"""

    def process_request(self, request, spider):
        proxy = get_proxy()
        request.meta["proxy"] = proxy
        request.meta["_auth_proxy"] = proxy
        request.headers["Proxy-Authorization"] = get_proxy_auth_header()
        return None
