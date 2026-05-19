"""项目启动入口。"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REDIS_HOST = os.getenv("SPIDER_ONE_REDIS_HOST", "117.50.131.232")
REDIS_PORT = int(os.getenv("SPIDER_ONE_REDIS_PORT", "6379"))
SPIDER_NAMES = [
    # "entry_seed_spider",
    # "hospital_department_spider",
    # "department_doctor_list_spider",
    # "live_history_doctor_spider",
    # "course_doctor_spider",
    # "surgery_doctor_spider",
    # "organization_doctor_spider",
    # "doctor_home_fans_spider",
    "doctor_detail_spider",
]
DETAIL_ONLY_SPIDER_NAMES = [
    "doctor_detail_spider",
]


def check_redis_connection():
    try:
        with socket.create_connection((REDIS_HOST, REDIS_PORT), timeout=5):
            print(f"Redis 连接成功：{REDIS_HOST}:{REDIS_PORT}")
            return
    except OSError as error:
        message = [
            f"Redis 连接失败：{REDIS_HOST}:{REDIS_PORT}",
            "推荐直接运行项目根目录下的 start.ps1。",
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
