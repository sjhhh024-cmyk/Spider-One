"""项目启动入口。

直接运行这个文件，就会按固定顺序依次启动医生圈项目里的 spider。
"""

import os
import socket
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REDIS_HOST = os.getenv("SPIDER_ONE_REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("SPIDER_ONE_REDIS_PORT", "6379"))
SPIDER_NAMES = [
    # "circle_list_spider",
    # "circle_doctor_list_spider",
    "doctor_detail_url_spider",
    "doctor_detail_spider",
]


def check_redis_connection():
    """启动前先检查 Redis 是否可连。"""

    try:
        with socket.create_connection((REDIS_HOST, REDIS_PORT), timeout=3):
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


def run_spider(spider_name):
    """按顺序执行单个 spider。"""

    command = [sys.executable, "-m", "scrapy", "crawl", spider_name]
    print(f"开始运行 spider: {spider_name}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main():
    """顺序跑完整条采集链。"""

    check_redis_connection()

    for spider_name in SPIDER_NAMES:
        run_spider(spider_name)


if __name__ == "__main__":
    main()
