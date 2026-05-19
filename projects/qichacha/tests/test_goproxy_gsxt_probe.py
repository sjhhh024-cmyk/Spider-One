from __future__ import annotations

from goproxy_gsxt_probe import (
    ProxyCandidate,
    build_probe_result,
    parse_proxy_candidates,
)


SAMPLE_PROXY_PAYLOAD = [
    {
        "address": "34.96.238.40:8080",
        "protocol": "http",
        "exit_ip": "34.96.238.40",
        "exit_location": "HK Hong Kong",
        "latency": 125,
        "quality_grade": "S",
        "status": "active",
    },
    {
        "address": "43.207.150.235:1080",
        "protocol": "socks5",
        "exit_ip": "43.207.150.235",
        "exit_location": "JP Tokyo",
        "latency": 254,
        "quality_grade": "S",
        "status": "active",
    },
    {
        "address": "8.219.97.248:80",
        "protocol": "http",
        "exit_ip": "8.219.64.236",
        "exit_location": "SG Singapore",
        "latency": 168,
        "quality_grade": "S",
        "status": "active",
    },
    {
        "address": "1.1.1.1:9999",
        "protocol": "http",
        "exit_ip": "1.1.1.1",
        "exit_location": "US Los Angeles",
        "latency": 90,
        "quality_grade": "A",
        "status": "inactive",
    },
]


def test_parse_proxy_candidates_filters_active_http_and_sorts_by_priority() -> None:
    candidates = parse_proxy_candidates(
        SAMPLE_PROXY_PAYLOAD,
        protocol="http",
        country_keywords=("HK", "SG"),
        limit=5,
    )

    assert candidates == [
        ProxyCandidate(
            address="34.96.238.40:8080",
            protocol="http",
            exit_ip="34.96.238.40",
            exit_location="HK Hong Kong",
            latency=125,
            quality_grade="S",
        ),
        ProxyCandidate(
            address="8.219.97.248:80",
            protocol="http",
            exit_ip="8.219.64.236",
            exit_location="SG Singapore",
            latency=168,
            quality_grade="S",
        ),
    ]


def test_build_probe_result_extracts_waf_event_id() -> None:
    html = """
    <html>
    <head><title>NWAF页面</title></head>
    <body>事件ID :<span id="wafId">1777533880207100000837356733450555</span></body>
    </html>
    """

    result = build_probe_result(
        proxy=ProxyCandidate(
            address="34.96.238.40:8080",
            protocol="http",
            exit_ip="34.96.238.40",
            exit_location="HK Hong Kong",
            latency=125,
            quality_grade="S",
        ),
        status_code=405,
        html=html,
    )

    assert result.classification == "waf_block"
    assert result.waf_event_id == "1777533880207100000837356733450555"
    assert result.proxy_address == "34.96.238.40:8080"
