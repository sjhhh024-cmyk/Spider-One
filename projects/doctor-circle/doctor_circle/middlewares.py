"""下载中间件。"""

import random


class UserAgentMiddleware:
    """给请求随机挂一个常用浏览器 UA。"""

    USER_AGENTS = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    ]

    def process_request(self, request, spider):
        """在请求发出前补一个随机 User-Agent。"""

        request.headers["User-Agent"] = random.choice(self.USER_AGENTS)
        return None


class RetryMiddleware:
    """请求失败时，把地址重新塞回 Redis。"""

    ALLOW_STATUS = {200, 404, 503}

    def process_response(self, request, response, spider):
        """遇到异常状态码时把当前地址放回对应 Redis key。"""

        if response.status not in self.ALLOW_STATUS and getattr(spider, "redis_key", ""):
            spider.server.sadd(spider.redis_key, response.url)
            spider.logger.warning("状态码异常，重新放回 Redis: %s", response.url)

        return response
