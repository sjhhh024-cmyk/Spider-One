from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.redis_requests import build_redis_request_data, push_redis_request  # noqa: E402


class DummyRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def sadd(self, key: str, value: str) -> int:
        self.calls.append((key, value))
        return 1


def test_build_redis_request_data_wraps_url_as_json_payload() -> None:
    payload = build_redis_request_data("https://data.120ask.com/yisheng/jibing.html")

    assert json.loads(payload) == {
        "url": "https://data.120ask.com/yisheng/jibing.html",
    }


def test_build_redis_request_data_keeps_meta_and_method() -> None:
    payload = build_redis_request_data(
        "https://data.120ask.com/public/ajaxyisheng?hid=1&pid=2",
        method="POST",
        meta={"cookiejar": "expert-1"},
    )

    assert json.loads(payload) == {
        "url": "https://data.120ask.com/public/ajaxyisheng?hid=1&pid=2",
        "method": "POST",
        "meta": {"cookiejar": "expert-1"},
    }


def test_push_redis_request_writes_json_string_to_redis() -> None:
    redis_client = DummyRedis()

    result = push_redis_request(
        redis_client,
        "doctor_ywbd:disease_list_url",
        "https://data.120ask.com/yisheng/jibing.html",
    )

    assert result == 1
    assert len(redis_client.calls) == 1
    redis_key, raw_payload = redis_client.calls[0]
    assert redis_key == "doctor_ywbd:disease_list_url"
    assert json.loads(raw_payload) == {
        "url": "https://data.120ask.com/yisheng/jibing.html",
    }
