"""运行时公共工具。"""

from __future__ import annotations

import base64
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from doctor_ywbd.js_bak import solve_cookie_assignment_script, solve_go_challenge


DEFAULT_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/139.0.0.0 Safari/537.36"
)

BROWSER_REQUEST_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://data.120ask.com/yisheng/jibing.html",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

ABUYUN_PROXY_HOST = "http-dyn.abuyun.com"
ABUYUN_PROXY_PORT = "9020"
ABUYUN_PROXY_USER = "HCBQVZ922819VL8D"
ABUYUN_PROXY_PASS = "6445C2F54F51B019"


def get_proxy() -> str:
    """返回阿布云代理地址。"""

    return f"http://{ABUYUN_PROXY_HOST}:{ABUYUN_PROXY_PORT}"


def get_proxy_auth_header() -> str:
    """返回阿布云代理认证头。"""

    credentials = f"{ABUYUN_PROXY_USER}:{ABUYUN_PROXY_PASS}".encode("utf-8")
    encoded_credentials = base64.b64encode(credentials).decode("ascii")
    return f"Basic {encoded_credentials}"


def build_cookie_header_from_cookies(cookies: list[dict]) -> str:
    """把 cookie 记录列表转成请求头 Cookie 字符串。"""

    cookie_parts: list[str] = []
    for cookie in cookies or []:
        cookie_name = str(cookie.get("name", "")).strip()
        cookie_value = str(cookie.get("value", "")).strip()
        if not cookie_name:
            continue
        cookie_parts.append(f"{cookie_name}={cookie_value}")
    return "; ".join(cookie_parts)


def build_cookie_header_from_mapping(cookie_mapping: dict[str, str] | None) -> str:
    """把结构化 cookie 字典转成请求头 Cookie 字符串。"""

    cookie_parts: list[str] = []
    for cookie_name, cookie_value in (cookie_mapping or {}).items():
        normalized_name = str(cookie_name or "").strip()
        if not normalized_name or normalized_name.lower() == "host":
            continue
        normalized_value = str(cookie_value or "").strip()
        if not normalized_value:
            continue
        cookie_parts.append(f"{normalized_name}={normalized_value}")
    return "; ".join(cookie_parts)


def parse_cookie_header_to_mapping(cookie_header: str) -> dict[str, str]:
    """把 Cookie 请求头字符串拆回结构化字典。"""

    cookie_mapping: dict[str, str] = {}
    for raw_part in str(cookie_header or "").split(";"):
        part = raw_part.strip()
        if not part or "=" not in part:
            continue
        cookie_name, cookie_value = part.split("=", 1)
        normalized_name = cookie_name.strip()
        if not normalized_name:
            continue
        cookie_mapping[normalized_name] = cookie_value.strip()
    return cookie_mapping


def resolve_clearance_cookie_value(html: str, *, location_path: str) -> str:
    """从 521 页面中提取新的 __jsl_clearance_s 值。"""

    cookie_string, _ = solve_go_challenge(html)
    if not cookie_string:
        cookie_string, _ = solve_cookie_assignment_script(html, location_path=location_path)
    cookie_mapping = parse_cookie_header_to_mapping(cookie_string)
    return cookie_mapping.get("__jsl_clearance_s", "")


def update_dynamic_cookie_fields(
    cookie_mapping: dict[str, str],
    *,
    clearance_cookie_value: str,
    current_timestamp: int | None = None,
) -> dict[str, str]:
    """更新动态 cookie 字段。"""

    updated_cookie_mapping = dict(cookie_mapping or {})
    normalized_clearance_value = str(clearance_cookie_value or "").strip()
    if normalized_clearance_value:
        updated_cookie_mapping["__jsl_clearance_s"] = normalized_clearance_value

    timestamp_value = str(
        int(current_timestamp if current_timestamp is not None else time.time())
    )
    for cookie_name in list(updated_cookie_mapping):
        if str(cookie_name).startswith("Hm_lpvt_"):
            updated_cookie_mapping[cookie_name] = timestamp_value

    return updated_cookie_mapping


def build_cookie_cache_path(base_file: str) -> str:
    """返回默认 cookie 缓存文件路径。"""

    return str(Path(base_file).with_name("ywbd_cookie.txt"))


class CookieManager:
    """手工 cookie 模式下的简单 cookie 容器。"""

    def __init__(
        self,
        *,
        initial_cookie_header: str = "",
        cookie_cache_path: str = "",
    ) -> None:
        self.cookie_cache_path = (cookie_cache_path or "").strip()
        self._cookie_header = (initial_cookie_header or "").strip() or self._read_cookie_cache()
        self._lock = threading.Lock()

    def _read_cookie_cache(self) -> str:
        if not self.cookie_cache_path:
            return ""
        cache_file = Path(self.cookie_cache_path)
        if not cache_file.exists():
            return ""
        return cache_file.read_text(encoding="utf-8").strip()

    def get_cookie_header(self) -> str:
        with self._lock:
            return self._cookie_header

    def set_cookie_header(self, cookie_header: str) -> str:
        with self._lock:
            self._cookie_header = (cookie_header or "").strip()
            return self._cookie_header

    def set_clearance_cookie_value(
        self,
        clearance_cookie_value: str,
        *,
        current_timestamp: int | None = None,
    ) -> str:
        """更新当前 cookie 里的动态字段。"""

        with self._lock:
            cookie_mapping = parse_cookie_header_to_mapping(self._cookie_header)
            cookie_mapping = update_dynamic_cookie_fields(
                cookie_mapping,
                clearance_cookie_value=clearance_cookie_value,
                current_timestamp=current_timestamp,
            )
            self._cookie_header = build_cookie_header_from_mapping(cookie_mapping)
            return self._cookie_header

    def set_clearance_cookie_from_html(self, html: str, *, url: str) -> str:
        """从 521 HTML 中计算新的 __jsl_clearance_s 并写回当前 cookie。"""

        location_path = urlparse(url).path or "/"
        clearance_cookie_value = resolve_clearance_cookie_value(html, location_path=location_path)
        if not clearance_cookie_value:
            return self.get_cookie_header()
        return self.set_clearance_cookie_value(clearance_cookie_value)


_COOKIE_MANAGER: CookieManager | None = None


def get_cookie_manager(
    *,
    initial_cookie_header: str = "",
    cookie_cache_path: str = "",
) -> CookieManager:
    """返回当前进程共享的 cookie 管理器。"""

    global _COOKIE_MANAGER
    if _COOKIE_MANAGER is None:
        _COOKIE_MANAGER = CookieManager(
            initial_cookie_header=initial_cookie_header,
            cookie_cache_path=cookie_cache_path,
        )
    return _COOKIE_MANAGER


def create_cookie_manager_from_settings(settings) -> CookieManager:
    """根据 Scrapy settings 构建 cookie 管理器。"""

    return get_cookie_manager(
        initial_cookie_header=settings.get("YWBD_INITIAL_COOKIE_HEADER", ""),
        cookie_cache_path=settings.get("YWBD_COOKIE_CACHE_FILE", ""),
    )
