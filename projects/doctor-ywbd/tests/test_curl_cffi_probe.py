from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.curl_cffi_probe import (  # noqa: E402
    build_probe_request_headers,
    detect_response_stage,
)


def test_build_probe_request_headers_includes_referer_and_cookie() -> None:
    headers = build_probe_request_headers(
        referer="https://data.120ask.com/yisheng/area.html",
        cookie_header="isYY=yisheng",
    )

    assert headers["Referer"] == "https://data.120ask.com/yisheng/area.html"
    assert headers["Cookie"] == "isYY=yisheng"
    assert "Chrome/" in headers["User-Agent"]


def test_build_probe_request_headers_skips_empty_cookie() -> None:
    headers = build_probe_request_headers(
        referer="https://data.120ask.com/yisheng/area.html",
        cookie_header="",
    )

    assert "Cookie" not in headers


def test_detect_response_stage_marks_direct_403_block() -> None:
    html = '<div class="online-desc-con">禁止访问</div>'

    assert detect_response_stage(403, html) == "403_block"


def test_detect_response_stage_marks_knownsec_js_challenge() -> None:
    html = "<script>document.cookie='__jsl_clearance_s=test'</script>"

    assert detect_response_stage(521, html) == "521_js"


def test_detect_response_stage_marks_captcha_page() -> None:
    html = "<title>本站开启了验证码保护</title>"

    assert detect_response_stage(521, html) == "captcha"


def test_detect_response_stage_marks_normal_html() -> None:
    html = "<html><title>地区找医生</title></html>"

    assert detect_response_stage(200, html) == "ok"
