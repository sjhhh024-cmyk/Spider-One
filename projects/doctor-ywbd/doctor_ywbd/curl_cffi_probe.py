"""curl_cffi 探针脚本。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable

import requests
from curl_cffi import requests as curl_requests

from doctor_ywbd.settings import YWBD_INITIAL_COOKIE_HEADER
from doctor_ywbd.tools import BROWSER_REQUEST_HEADERS, DEFAULT_BROWSER_USER_AGENT, get_proxy


DEFAULT_PROBE_URLS = [
    "https://data.120ask.com/yisheng/list_a410102.html",
]


@dataclass
class ProbeResult:
    client_name: str
    url: str
    status_code: int | None
    stage: str
    final_url: str
    body_excerpt: str
    error: str = ""


def build_probe_request_headers(*, referer: str, cookie_header: str = "") -> dict[str, str]:
    """构造探针请求头。"""

    headers = dict(BROWSER_REQUEST_HEADERS)
    headers["User-Agent"] = DEFAULT_BROWSER_USER_AGENT
    headers["Referer"] = referer
    if cookie_header:
        headers["Cookie"] = cookie_header
    return headers


def detect_response_stage(status_code: int | None, html: str) -> str:
    """根据响应状态和内容识别当前拦截阶段。"""

    normalized_html = str(html or "")
    if "本站开启了验证码保护" in normalized_html:
        return "captcha"
    if status_code == 521 or "__jsl_clearance_s" in normalized_html or "document.cookie" in normalized_html:
        return "521_js"
    if status_code == 403 and (
        "online-desc-con" in normalized_html or "禁止访问" in normalized_html or "访问过于频繁" in normalized_html
    ):
        return "403_block"
    if status_code == 200:
        return "ok"
    return "other"


def _build_excerpt(text: str, limit: int = 220) -> str:
    return " ".join(str(text or "").split())[:limit]


def _build_proxies(use_proxy: bool) -> dict[str, str] | None:
    if not use_proxy:
        return None
    proxy = get_proxy()
    return {"http": proxy, "https": proxy}


def probe_with_requests(
    url: str,
    *,
    headers: dict[str, str],
    use_proxy: bool = False,
    timeout: int = 40,
) -> ProbeResult:
    """用 requests 发起探针。"""

    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=_build_proxies(use_proxy),
            timeout=timeout,
            verify=False,
        )
        return ProbeResult(
            client_name="requests",
            url=url,
            status_code=response.status_code,
            stage=detect_response_stage(response.status_code, response.text),
            final_url=response.url,
            body_excerpt=_build_excerpt(response.text),
        )
    except Exception as error:  # pragma: no cover - 网络异常按真实结果展示
        return ProbeResult(
            client_name="requests",
            url=url,
            status_code=None,
            stage="error",
            final_url=url,
            body_excerpt="",
            error=str(error),
        )


def probe_with_curl_cffi(
    url: str,
    *,
    headers: dict[str, str],
    use_proxy: bool = False,
    impersonate: str = "chrome",
    timeout: int = 40,
) -> ProbeResult:
    """用 curl_cffi 发起探针。"""

    try:
        response = curl_requests.get(
            url,
            headers=headers,
            proxies=_build_proxies(use_proxy),
            timeout=timeout,
            verify=False,
            impersonate=impersonate,
        )
        return ProbeResult(
            client_name=f"curl_cffi[{impersonate}]",
            url=url,
            status_code=response.status_code,
            stage=detect_response_stage(response.status_code, response.text),
            final_url=str(response.url),
            body_excerpt=_build_excerpt(response.text),
        )
    except Exception as error:  # pragma: no cover - 网络异常按真实结果展示
        return ProbeResult(
            client_name=f"curl_cffi[{impersonate}]",
            url=url,
            status_code=None,
            stage="error",
            final_url=url,
            body_excerpt="",
            error=str(error),
        )


def run_probe(
    urls: Iterable[str],
    *,
    referer: str,
    cookie_header: str = "",
    use_proxy: bool = False,
    impersonate: str = "chrome",
) -> list[ProbeResult]:
    """依次运行 requests / curl_cffi 对照探针。"""

    results: list[ProbeResult] = []
    for url in urls:
        headers = build_probe_request_headers(referer=referer, cookie_header=cookie_header)
        results.append(probe_with_requests(url, headers=headers, use_proxy=use_proxy))
        results.append(
            probe_with_curl_cffi(
                url,
                headers=headers,
                use_proxy=use_proxy,
                impersonate=impersonate,
            )
        )
    return results


def _print_results(results: list[ProbeResult]) -> None:
    for result in results:
        print(f"client: {result.client_name}")
        print(f"url: {result.url}")
        print(f"status: {result.status_code}")
        print(f"stage: {result.stage}")
        print(f"final_url: {result.final_url}")
        if result.error:
            print(f"error: {result.error}")
        else:
            print(f"body: {result.body_excerpt}")
        print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="对比 requests 和 curl_cffi 在 120ask 的返回差异。")
    parser.add_argument("urls", nargs="*", default=DEFAULT_PROBE_URLS)
    parser.add_argument("--referer", default="https://data.120ask.com/yisheng/area.html")
    parser.add_argument("--no-cookie", action="store_true")
    parser.add_argument("--use-proxy", action="store_true")
    parser.add_argument("--impersonate", default="chrome")
    args = parser.parse_args()

    cookie_header = "" if args.no_cookie else YWBD_INITIAL_COOKIE_HEADER
    results = run_probe(
        args.urls,
        referer=args.referer,
        cookie_header=cookie_header,
        use_proxy=args.use_proxy,
        impersonate=args.impersonate,
    )
    _print_results(results)


if __name__ == "__main__":
    main()
