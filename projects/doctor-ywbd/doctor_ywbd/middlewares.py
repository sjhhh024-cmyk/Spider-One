"""下载中间件。"""

from __future__ import annotations

from doctor_ywbd.tools import (
    BROWSER_REQUEST_HEADERS,
    DEFAULT_BROWSER_USER_AGENT,
    create_cookie_manager_from_settings,
    get_proxy,
    get_proxy_auth_header,
)


class UserAgentMiddleware:
    """给请求补齐浏览器请求头，并可注入过盾 cookie。"""

    DEFAULT_USER_AGENT = DEFAULT_BROWSER_USER_AGENT
    DEFAULT_HEADERS = BROWSER_REQUEST_HEADERS

    def __init__(self, cookie_header: str = "", cookie_manager=None) -> None:
        self.cookie_header = (cookie_header or "").strip()
        self.cookie_manager = cookie_manager

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            cookie_manager=create_cookie_manager_from_settings(crawler.settings),
        )

    def process_request(self, request, spider):
        for header_name, header_value in self.DEFAULT_HEADERS.items():
            request.headers.setdefault(header_name, header_value)
        request.headers["User-Agent"] = self.DEFAULT_USER_AGENT
        cookie_header = self.cookie_header
        if self.cookie_manager is not None:
            cookie_header = self.cookie_manager.get_cookie_header() or cookie_header
        if cookie_header:
            request.headers["Cookie"] = cookie_header
        return None


class RetryMiddleware:
    """手工 cookie 模式下，521 时刷新动态 cookie 字段并重试。"""

    def __init__(self, cookie_manager=None) -> None:
        self.cookie_manager = cookie_manager

    @classmethod
    def from_crawler(cls, crawler):
        return cls(cookie_manager=create_cookie_manager_from_settings(crawler.settings))

    def process_response(self, request, response, spider):
        if response.status == 521:
            retry_count = int(request.meta.get("ywbd_cookie_retry", 0))
            if self.cookie_manager is not None and retry_count < 2:
                try:
                    refreshed_cookie = self.cookie_manager.set_clearance_cookie_from_html(response.text, url=response.url)
                except Exception as error:  # pragma: no cover - 防止 challenge 解析异常打崩 spider
                    spider.logger.warning("521 拦截，更新动态 cookie 字段失败: %s | %s", response.url, error)
                    return response
                if refreshed_cookie:
                    retry_request = request.copy()
                    retry_request.meta["ywbd_cookie_retry"] = retry_count + 1
                    retry_request.headers["Cookie"] = refreshed_cookie
                    retry_request.dont_filter = True
                    spider.logger.warning("521 拦截，已更新动态 cookie 字段并重试: %s", response.url)
                    return retry_request
            spider.logger.warning("521 拦截，请手动更新 YWBD_INITIAL_COOKIE: %s", response.url)
        return response


class ProxyMiddleware:
    """给请求挂 Abuyun 代理。"""

    def process_request(self, request, spider):
        request.meta["proxy"] = get_proxy()
        request.headers["Proxy-Authorization"] = get_proxy_auth_header()
        request.meta["_auth_proxy"] = get_proxy()
        return None
