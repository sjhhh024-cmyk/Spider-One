"""doctor_info_url 标准化迁移脚本。"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from scrapy.utils.project import get_project_settings
from scrapy_redis.connection import get_redis_from_settings

from doctor_ywbd.redis_requests import build_redis_request_data
from doctor_ywbd.route_hypotheses import build_redis_keys


DEFAULT_PREFIX = "doctor_ywbd"


@dataclass(frozen=True)
class MigrationPlan:
    total_members: int
    unique_urls: list[str]
    normalized_members: list[str]
    legacy_member_count: int
    json_member_count: int
    invalid_member_count: int

    @property
    def unique_member_count(self) -> int:
        return len(self.normalized_members)

    @property
    def duplicate_member_count(self) -> int:
        return self.total_members - self.unique_member_count - self.invalid_member_count


@dataclass(frozen=True)
class MigrationResult:
    source_key: str
    temp_key: str
    backup_key: str | None
    source_count: int
    temp_count: int
    written_count: int
    swapped: bool
    plan: MigrationPlan


def _decode_member(raw_member: str | bytes) -> str:
    if isinstance(raw_member, bytes):
        return raw_member.decode("utf-8", errors="ignore")
    return str(raw_member)


def normalize_doctor_info_member(raw_member: str | bytes) -> tuple[str | None, str]:
    """把历史 member 解析成标准 URL，并返回来源类型。"""

    text = _decode_member(raw_member).strip()
    if not text:
        return None, "invalid"

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text, "legacy"

    if isinstance(payload, dict):
        url = str(payload.get("url", "")).strip()
        if url:
            return url, "json"
        return None, "invalid"

    if isinstance(payload, str):
        normalized = payload.strip()
        return (normalized, "json") if normalized else (None, "invalid")

    return None, "invalid"


def build_migration_plan(raw_members: Iterable[str | bytes]) -> MigrationPlan:
    """把 doctor_info_url 当前成员构造成标准化迁移计划。"""

    total_members = 0
    invalid_member_count = 0
    legacy_member_count = 0
    json_member_count = 0
    seen_urls: set[str] = set()
    unique_urls: list[str] = []

    for raw_member in raw_members:
        total_members += 1
        url, source_type = normalize_doctor_info_member(raw_member)
        if source_type == "legacy":
            legacy_member_count += 1
        elif source_type == "json":
            json_member_count += 1
        else:
            invalid_member_count += 1

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        unique_urls.append(url)

    unique_urls.sort()
    normalized_members = [build_redis_request_data(url) for url in unique_urls]
    return MigrationPlan(
        total_members=total_members,
        unique_urls=unique_urls,
        normalized_members=normalized_members,
        legacy_member_count=legacy_member_count,
        json_member_count=json_member_count,
        invalid_member_count=invalid_member_count,
    )


def _chunk_members(members: list[str], batch_size: int) -> list[list[str]]:
    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")
    return [members[index:index + batch_size] for index in range(0, len(members), batch_size)]


def write_members_concurrently(
    redis_client,
    redis_key: str,
    members: Iterable[str],
    *,
    workers: int = 8,
    batch_size: int = 1000,
) -> int:
    """按批次并发写入标准 JSON member。"""

    if workers <= 0:
        raise ValueError("workers 必须大于 0")

    member_list = list(members)
    if not member_list:
        return 0

    chunks = _chunk_members(member_list, batch_size)

    def write_chunk(chunk: list[str]) -> int:
        return int(redis_client.sadd(redis_key, *chunk))

    with ThreadPoolExecutor(max_workers=min(workers, len(chunks))) as executor:
        return sum(executor.map(write_chunk, chunks))


def build_default_temp_key(redis_key: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{redis_key}:json_dedup:{timestamp}"


def build_default_backup_key(redis_key: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{redis_key}:backup:{timestamp}"


def resolve_execution_mode(*, apply: bool, swap: bool) -> tuple[bool, bool]:
    """解析执行模式。

    默认直接运行脚本时执行正式替换；显式传 --apply 时只写临时 key。
    """

    if swap:
        return True, True
    if apply:
        return True, False
    return True, True


def execute_migration(
    redis_client,
    *,
    source_key: str,
    temp_key: str,
    workers: int,
    batch_size: int,
    swap: bool = False,
    backup_key: str | None = None,
    overwrite_temp: bool = False,
) -> MigrationResult:
    """执行 doctor_info_url 的规范化写入，可选替换正式 key。"""

    raw_members = redis_client.smembers(source_key)
    plan = build_migration_plan(raw_members)

    if redis_client.exists(temp_key):
        if not overwrite_temp:
            raise RuntimeError(f"临时 key 已存在，请更换 temp_key 或显式开启覆盖: {temp_key}")
        redis_client.delete(temp_key)

    written_count = write_members_concurrently(
        redis_client,
        temp_key,
        plan.normalized_members,
        workers=workers,
        batch_size=batch_size,
    )
    temp_count = int(redis_client.scard(temp_key))

    if temp_count != plan.unique_member_count:
        raise RuntimeError(
            f"临时 key 数量校验失败: 期望 {plan.unique_member_count}，实际 {temp_count}"
        )

    resolved_backup_key = None
    if swap:
        resolved_backup_key = backup_key or build_default_backup_key(source_key)
        if not redis_client.exists(source_key):
            raise RuntimeError(f"源 key 不存在，无法替换: {source_key}")
        if redis_client.exists(resolved_backup_key):
            raise RuntimeError(f"备份 key 已存在，请更换 backup_key: {resolved_backup_key}")
        pipeline = redis_client.pipeline()
        pipeline.rename(source_key, resolved_backup_key)
        pipeline.rename(temp_key, source_key)
        pipeline.execute()
        temp_count = int(redis_client.scard(source_key))

    return MigrationResult(
        source_key=source_key,
        temp_key=temp_key,
        backup_key=resolved_backup_key,
        source_count=len(raw_members),
        temp_count=temp_count,
        written_count=written_count,
        swapped=swap,
        plan=plan,
    )


def get_redis_client():
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "doctor_ywbd.settings")
    settings = get_project_settings()
    return get_redis_from_settings(settings)


def _print_plan(plan: MigrationPlan, *, source_key: str, temp_key: str, apply_mode: bool, swap: bool) -> None:
    print(f"源 key: {source_key}")
    print(f"临时 key: {temp_key}")
    print(f"当前模式: {'执行写入' if apply_mode else '仅分析(dry-run)'}")
    print(f"最终替换正式 key: {'是' if swap else '否'}")
    print(f"总成员数: {plan.total_members}")
    print(f"标准化后唯一 URL 数: {plan.unique_member_count}")
    print(f"历史裸字符串数: {plan.legacy_member_count}")
    print(f"JSON 成员数: {plan.json_member_count}")
    print(f"无效成员数: {plan.invalid_member_count}")
    print(f"重复成员数: {plan.duplicate_member_count}")
    sample_url = plan.unique_urls[0] if plan.unique_urls else ""
    print(f"样本 URL: {sample_url}")


def _print_result(result: MigrationResult) -> None:
    print(f"临时 key 写入完成: {result.temp_key}")
    print(f"源 key 原始成员数: {result.source_count}")
    print(f"临时 key 成员数: {result.temp_count}")
    print(f"实际写入计数: {result.written_count}")
    if result.swapped:
        print(f"正式 key 已替换: {result.source_key}")
        print(f"原 key 备份到: {result.backup_key}")
    else:
        print("本次未替换正式 key，可先核对临时 key 再决定是否执行 --swap。")


def main() -> None:
    parser = argparse.ArgumentParser(description="把 doctor_info_url 的裸字符串成员规范化为 JSON，并按 URL 去重。默认直接替换正式 key。")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="Redis key 前缀，默认 doctor_ywbd。")
    parser.add_argument("--redis-key", help="显式指定要处理的 Redis key，优先级高于 --prefix。")
    parser.add_argument("--temp-key", help="临时 key，默认自动生成。")
    parser.add_argument("--backup-key", help="替换正式 key 时的备份 key，默认自动生成。")
    parser.add_argument("--workers", type=int, default=8, help="并发写入线程数，默认 8。")
    parser.add_argument("--batch-size", type=int, default=1000, help="每批次写入 member 数，默认 1000。")
    parser.add_argument("--apply", action="store_true", help="只把标准化结果写入临时 key，不替换正式 key。")
    parser.add_argument("--swap", action="store_true", help="显式指定替换正式 key；不传参数时默认也是这个行为。")
    parser.add_argument("--overwrite-temp", action="store_true", help="若临时 key 已存在，允许先删除再重写。")
    args = parser.parse_args()

    source_key = args.redis_key or build_redis_keys(args.prefix)["doctor_info_url"]
    temp_key = args.temp_key or build_default_temp_key(source_key)
    apply_mode, swap_mode = resolve_execution_mode(apply=args.apply, swap=args.swap)

    redis_client = get_redis_client()
    plan = build_migration_plan(redis_client.smembers(source_key))
    _print_plan(plan, source_key=source_key, temp_key=temp_key, apply_mode=apply_mode, swap=swap_mode)

    if not apply_mode:
        return

    result = execute_migration(
        redis_client,
        source_key=source_key,
        temp_key=temp_key,
        workers=args.workers,
        batch_size=args.batch_size,
        swap=swap_mode,
        backup_key=args.backup_key,
        overwrite_temp=args.overwrite_temp,
    )
    _print_result(result)


if __name__ == "__main__":
    main()
