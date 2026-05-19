"""项目启动入口。"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REDIS_HOST = os.getenv("SPIDER_ONE_REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("SPIDER_ONE_REDIS_PORT", "6379"))
DEFAULT_SPIDER_NAMES = [
    # "entry_seed_spider",
    # "disease_index_spider",
    # "disease_list_spider",
    # "department_index_spider",
    # "department_list_spider",
    # "area_index_spider",
    # "area_list_spider",
    # "hospital_area_index_spider",
    # "hospital_list_spider",
    # "hospital_detail_spider",
   # "hospital_expert_spider",
    "doctor_detail_spider",
]
DETAIL_ONLY_SPIDER_NAMES = [
    "doctor_detail_spider",
]


def _parse_spider_names_from_env() -> list[str]:
    raw_value = os.getenv("YWBD_START_SPIDERS", "").strip()
    if not raw_value:
        return list(DEFAULT_SPIDER_NAMES)
    return [name.strip() for name in raw_value.split(",") if name.strip()]


SPIDER_NAMES = _parse_spider_names_from_env()


def check_redis_connection():
    try:
        with socket.create_connection((REDIS_HOST, REDIS_PORT), timeout=3):
            print(f"Redis 连接成功：{REDIS_HOST}:{REDIS_PORT}")
            return
    except OSError as error:
        message = [
            f"Redis 连接失败：{REDIS_HOST}:{REDIS_PORT}",
            "请先启动 SSH 隧道，再运行采集。",
            "推荐直接运行项目根目录下的 start.ps1。",
            "也可以先手工执行：ssh -L 6379:localhost:6379 root@8.140.197.200",
            f"原始错误：{error}",
        ]
        raise SystemExit("\n".join(message)) from error


def run_spider(spider_name: str):
    command = [sys.executable, "-m", "scrapy", "crawl", spider_name]
    print(f"开始运行 spider: {spider_name}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    print(f"spider 运行完成: {spider_name}")


def run_pipeline(spider_names: list[str]):
    check_redis_connection()

    for spider_name in spider_names:
        run_spider(spider_name)


def main():
    run_pipeline(SPIDER_NAMES)


if __name__ == "__main__":
    main()
