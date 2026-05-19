from __future__ import annotations

from datetime import datetime

import redis

from doctor_wygk.settings import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_KEY_DOCTOR_INFO_URL,
    REDIS_PASSWORD,
    REDIS_PORT,
)
from doctor_wygk.tools import dedupe_detail_tasks, dump_task, load_task


def chunked(items: list[bytes | str], size: int = 500) -> list[list[bytes | str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def main() -> None:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    source_key = REDIS_KEY_DOCTOR_INFO_URL
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_key = f"{source_key}:backup:{timestamp}"
    temp_key = f"{source_key}:rewrite:{timestamp}"

    raw_members = list(redis_client.sscan_iter(source_key, count=1000))
    tasks = [load_task(member) for member in raw_members]
    deduped_tasks = dedupe_detail_tasks(tasks)

    print(f"源 key: {source_key}")
    print(f"原始任务数: {len(tasks)}")
    print(f"去重后任务数: {len(deduped_tasks)}")
    print(f"备份 key: {backup_key}")

    if not raw_members:
        print("doctor_info_url 为空，无需处理。")
        return

    pipeline = redis_client.pipeline()
    for batch in chunked(raw_members):
        pipeline.sadd(backup_key, *batch)
    pipeline.execute()

    deduped_members = [dump_task(task) for task in deduped_tasks]
    pipeline = redis_client.pipeline()
    if deduped_members:
        pipeline.delete(temp_key)
        for batch in chunked(deduped_members):
            pipeline.sadd(temp_key, *batch)
        pipeline.delete(source_key)
        pipeline.rename(temp_key, source_key)
    else:
        pipeline.delete(source_key)
    pipeline.execute()

    print("doctor_info_url 去重完成。")


if __name__ == "__main__":
    main()
