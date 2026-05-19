from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

import requests

from gsxt_probe import classify_gsxt_response, extract_waf_event_id


GOPROXY_API = "http://117.50.131.232:7778/api/proxies"
GSXT_URL = "https://js.gsxt.gov.cn/index.html"
DEFAULT_COUNTRY_KEYWORDS = ("HK", "SG", "JP", "KR", "TW")


@dataclass(frozen=True)
class ProxyCandidate:
    address: str
    protocol: str
    exit_ip: str
    exit_location: str
    latency: int
    quality_grade: str


@dataclass(frozen=True)
class ProbeResult:
    proxy_address: str
    protocol: str
    exit_ip: str
    exit_location: str
    latency: int
    quality_grade: str
    status_code: int
    classification: str
    waf_event_id: str | None


def parse_proxy_candidates(
    payload: list[dict[str, Any]],
    protocol: str = "http",
    country_keywords: tuple[str, ...] = DEFAULT_COUNTRY_KEYWORDS,
    limit: int = 10,
) -> list[ProxyCandidate]:
    normalized_keywords = tuple(keyword.upper() for keyword in country_keywords)
    candidates: list[ProxyCandidate] = []

    for item in payload:
        if item.get("status") != "active":
            continue
        if str(item.get("protocol", "")).lower() != protocol.lower():
            continue

        exit_location = str(item.get("exit_location", ""))
        if normalized_keywords and not any(keyword in exit_location.upper() for keyword in normalized_keywords):
            continue

        candidates.append(
            ProxyCandidate(
                address=str(item.get("address", "")),
                protocol=str(item.get("protocol", "")),
                exit_ip=str(item.get("exit_ip", "")),
                exit_location=exit_location,
                latency=int(item.get("latency", 0) or 0),
                quality_grade=str(item.get("quality_grade", "")),
            )
        )

    candidates.sort(key=lambda item: (item.latency, item.exit_location, item.address))
    return candidates[:limit]


def build_probe_result(proxy: ProxyCandidate, status_code: int, html: str) -> ProbeResult:
    classification = classify_gsxt_response(status_code=status_code, html=html)
    return ProbeResult(
        proxy_address=proxy.address,
        protocol=proxy.protocol,
        exit_ip=proxy.exit_ip,
        exit_location=proxy.exit_location,
        latency=proxy.latency,
        quality_grade=proxy.quality_grade,
        status_code=status_code,
        classification=classification,
        waf_event_id=extract_waf_event_id(html),
    )


def fetch_proxy_payload(timeout: float = 20.0) -> list[dict[str, Any]]:
    response = requests.get(GOPROXY_API, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("GoProxy /api/proxies 返回的不是列表")
    return payload


def probe_gsxt(proxy: ProxyCandidate, timeout: float = 20.0, verify: bool = True) -> ProbeResult:
    proxies = {
        "http": f"http://{proxy.address}",
        "https": f"http://{proxy.address}",
    }
    response = requests.get(
        GSXT_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        proxies=proxies,
        timeout=timeout,
        verify=verify,
    )
    return build_probe_result(proxy=proxy, status_code=response.status_code, html=response.text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用 GoProxy 出口直接探测江苏 GSXT")
    parser.add_argument("--protocol", default="http", choices=("http", "socks5"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--country-keywords", nargs="*", default=list(DEFAULT_COUNTRY_KEYWORDS))
    parser.add_argument("--insecure", action="store_true", help="跳过 TLS 证书校验")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = fetch_proxy_payload(timeout=args.timeout)
    candidates = parse_proxy_candidates(
        payload,
        protocol=args.protocol,
        country_keywords=tuple(args.country_keywords),
        limit=args.limit,
    )

    if not candidates:
        raise SystemExit("没有筛到可用代理候选")

    results: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            result = probe_gsxt(candidate, timeout=args.timeout, verify=not args.insecure)
            results.append(asdict(result))
        except requests.RequestException as exc:
            results.append(
                {
                    "proxy_address": candidate.address,
                    "protocol": candidate.protocol,
                    "exit_ip": candidate.exit_ip,
                    "exit_location": candidate.exit_location,
                    "latency": candidate.latency,
                    "quality_grade": candidate.quality_grade,
                    "status_code": None,
                    "classification": "request_error",
                    "waf_event_id": None,
                    "error": str(exc),
                }
            )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
