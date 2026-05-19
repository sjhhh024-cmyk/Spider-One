from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.doctor_info_url_migration import (  # noqa: E402
    build_migration_plan,
    resolve_execution_mode,
    write_members_concurrently,
)


class DummyRedis:
    def __init__(self) -> None:
        self.storage: dict[str, set[str]] = {}

    def sadd(self, key: str, *values: str) -> int:
        bucket = self.storage.setdefault(key, set())
        before = len(bucket)
        bucket.update(values)
        return len(bucket) - before


def test_build_migration_plan_normalizes_legacy_and_json_members() -> None:
    plan = build_migration_plan(
        {
            "https://data.120ask.com/yisheng/abc.html",
            '{"url":"https://data.120ask.com/yisheng/abc.html"}',
            '{"url":"https://data.120ask.com/yisheng/xyz.html"}',
        }
    )

    assert sorted(plan.unique_urls) == [
        "https://data.120ask.com/yisheng/abc.html",
        "https://data.120ask.com/yisheng/xyz.html",
    ]
    assert sorted(json.loads(payload)["url"] for payload in plan.normalized_members) == plan.unique_urls
    assert plan.total_members == 3
    assert plan.unique_member_count == 2
    assert plan.legacy_member_count == 1
    assert plan.json_member_count == 2
    assert plan.invalid_member_count == 0


def test_build_migration_plan_skips_invalid_members() -> None:
    plan = build_migration_plan(
        {
            "",
            "   ",
            '{"meta":{"foo":"bar"}}',
            '{"url":""}',
            "https://data.120ask.com/yisheng/ok.html",
        }
    )

    assert plan.unique_urls == ["https://data.120ask.com/yisheng/ok.html"]
    assert plan.invalid_member_count == 4
    assert plan.unique_member_count == 1


def test_write_members_concurrently_writes_all_members_in_batches() -> None:
    redis_client = DummyRedis()
    members = [
        '{"url":"https://data.120ask.com/yisheng/a.html"}',
        '{"url":"https://data.120ask.com/yisheng/b.html"}',
        '{"url":"https://data.120ask.com/yisheng/c.html"}',
    ]

    inserted = write_members_concurrently(
        redis_client,
        "doctor_ywbd:doctor_info_url:tmp",
        members,
        workers=3,
        batch_size=1,
    )

    assert inserted == 3
    assert redis_client.storage["doctor_ywbd:doctor_info_url:tmp"] == set(members)


def test_resolve_execution_mode_defaults_to_swap_when_no_flags_are_given() -> None:
    apply_mode, swap_mode = resolve_execution_mode(apply=False, swap=False)

    assert apply_mode is True
    assert swap_mode is True


def test_resolve_execution_mode_keeps_explicit_apply_without_swap() -> None:
    apply_mode, swap_mode = resolve_execution_mode(apply=True, swap=False)

    assert apply_mode is True
    assert swap_mode is False
