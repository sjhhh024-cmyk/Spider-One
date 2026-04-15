from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.tools import (  # noqa: E402
    CookieManager,
    build_cookie_header_from_cookies,
    build_cookie_cache_path,
    build_cookie_header_from_mapping,
    parse_cookie_header_to_mapping,
    resolve_clearance_cookie_value,
)
from doctor_ywbd.js_bak import solve_cookie_assignment_script, solve_go_challenge  # noqa: E402


def test_build_cookie_header_from_cookies_keep_only_named_values() -> None:
    cookie_header = build_cookie_header_from_cookies(
        [
            {"name": "isYY", "value": "yisheng"},
            {"name": "__jsl_clearance_s", "value": "abc"},
            {"name": "", "value": "ignored"},
        ]
    )

    assert cookie_header == "isYY=yisheng; __jsl_clearance_s=abc"


def test_build_cookie_header_from_mapping_ignores_host_and_empty_values() -> None:
    cookie_header = build_cookie_header_from_mapping(
        {
            "isYY": "yisheng",
            "host": "data.120ask.com",
            "__jsl_clearance_s": "abc",
            "empty": "",
        }
    )

    assert cookie_header == "isYY=yisheng; __jsl_clearance_s=abc"


def test_parse_cookie_header_to_mapping_keeps_pairs() -> None:
    cookie_mapping = parse_cookie_header_to_mapping(
        "isYY=yisheng; __jsluid_s=abc; __jsl_clearance_s=clearance"
    )

    assert cookie_mapping == {
        "isYY": "yisheng",
        "__jsluid_s": "abc",
        "__jsl_clearance_s": "clearance",
    }


def test_cookie_manager_returns_existing_cookie_without_refresh() -> None:
    manager = CookieManager(initial_cookie_header="isYY=yisheng")

    assert manager.get_cookie_header() == "isYY=yisheng"


def test_cookie_manager_prefers_initial_cookie_over_cache_file(tmp_path: Path) -> None:
    cache_file = tmp_path / "ywbd_cookie.txt"
    cache_file.write_text("isYY=yisheng; __jsl_clearance_s=cached", encoding="utf-8")

    manager = CookieManager(
        initial_cookie_header="isYY=yisheng; __jsl_clearance_s=manual",
        cookie_cache_path=str(cache_file),
    )

    assert manager.get_cookie_header() == "isYY=yisheng; __jsl_clearance_s=manual"


def test_cookie_manager_reads_cookie_from_cache_file(tmp_path: Path) -> None:
    cache_file = tmp_path / "ywbd_cookie.txt"
    cache_file.write_text("isYY=yisheng; __jsl_clearance_s=cached", encoding="utf-8")

    manager = CookieManager(cookie_cache_path=str(cache_file))

    assert manager.get_cookie_header() == "isYY=yisheng; __jsl_clearance_s=cached"


def test_cookie_manager_updates_clearance_and_all_hm_lpvt_values() -> None:
    manager = CookieManager(
        initial_cookie_header=(
            "isYY=yisheng; __jsluid_s=abc; __jsl_clearance_s=old; "
            "Hm_lpvt_d7682ab43891c68a00de46e9ce5b76aa=1; "
            "Hm_lpvt_7c2c4ab8a1436c0f67383fe9417819b7=2; HMACCOUNT=1"
        )
    )

    updated_cookie_header = manager.set_clearance_cookie_value("new", current_timestamp=1776145525)

    assert updated_cookie_header == (
        "isYY=yisheng; __jsluid_s=abc; __jsl_clearance_s=new; "
        "Hm_lpvt_d7682ab43891c68a00de46e9ce5b76aa=1776145525; "
        "Hm_lpvt_7c2c4ab8a1436c0f67383fe9417819b7=1776145525; HMACCOUNT=1"
    )


def test_resolve_clearance_cookie_value_extracts_cookie_value_from_go_challenge() -> None:
    html = (
        '<script>go({"bts":["foo","bar"],"chars":"abc","ct":"'
        'e4b46d95deb7d3ccf14e984add43a4b2","ha":"md5","is":true,'
        '"tn":"__jsl_clearance_s","vt":"3600","wt":"1500"})</script>'
    )

    clearance_value = resolve_clearance_cookie_value(
        html,
        location_path="/yisheng/list_j4928p106.html",
    )

    assert clearance_value == "foocabar"


def test_build_cookie_cache_path_uses_ywbd_cookie_filename() -> None:
    path = build_cookie_cache_path(r"C:\demo\doctor_ywbd\settings.py")

    assert path.endswith(r"doctor_ywbd\ywbd_cookie.txt")


def test_solve_cookie_assignment_script_evaluates_knownsec_cookie() -> None:
    html = (
        "<script>document.cookie=('__jsl_clearance_s=')+(1+1+'')+('abc')+('; Max-age=3600; Path=/');"
        "location.href=location.pathname+location.search</script>"
    )

    cookie_string, wait_ms = solve_cookie_assignment_script(
        html,
        location_path="/yisheng/list_j4928p106.html",
    )

    assert cookie_string == "__jsl_clearance_s=2abc; Max-age=3600; Path=/"
    assert wait_ms == 0


def test_solve_go_challenge_builds_cookie_and_wait_time() -> None:
    html = (
        '<script>go({"bts":["foo","bar"],"chars":"abc","ct":"'
        'e4b46d95deb7d3ccf14e984add43a4b2","ha":"md5","is":true,'
        '"tn":"__jsl_clearance_s","vt":"3600","wt":"1500"})</script>'
    )

    cookie_string, wait_ms = solve_go_challenge(html)

    assert cookie_string == "__jsl_clearance_s=foocabar; Max-age=3600; Path=/; SameSite=None; Secure"
    assert wait_ms == 1500


def test_solve_go_challenge_supports_sha256() -> None:
    html = (
        '<script>go({"bts":["foo","bar"],"chars":"abc","ct":"'
        '86cb6b19c4ff5e70c0e868bd2f2311df945ff83e2ba5748f1ba48f33baf117e0","ha":"sha256","is":true,'
        '"tn":"__jsl_clearance_s","vt":"3600","wt":"1500"})</script>'
    )

    cookie_string, wait_ms = solve_go_challenge(html)

    assert cookie_string == "__jsl_clearance_s=foocabar; Max-age=3600; Path=/; SameSite=None; Secure"
    assert wait_ms == 1500
