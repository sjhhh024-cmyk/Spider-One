"""把 txt 里的医生详情地址重新写回 Redis。"""

import redis

from doctor_circle import settings


def build_redis_client():
    """按项目 settings.py 创建 Redis 连接。"""

    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )


def main():
    """把文本文件里的 URL 按行写入医生详情 Redis key。"""

    redis_client = build_redis_client()
    file_path = "doctor_circle_doctor_url_n.txt"
    redis_key = "doctor_circle:doctor_url"

    with open(file_path, encoding="utf-8") as file_object:
        for line in file_object:
            doctor_url = line.strip()
            if not doctor_url:
                continue

            redis_client.sadd(redis_key, doctor_url)
            print(f"写入 Redis: {doctor_url}")


if __name__ == "__main__":
    main()
