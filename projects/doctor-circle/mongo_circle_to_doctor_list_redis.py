"""从 MongoDB 的圈子集合重建医生列表 Redis 种子。"""

import json

import redis
from pymongo import MongoClient

from doctor_circle import settings


def build_mongodb_client():
    """按项目配置创建 MongoDB 客户端。"""

    return MongoClient(settings.MONGO_URI)


def build_redis_client():
    """按项目配置创建 Redis 客户端。"""

    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )


def load_circle_ids():
    """从圈子集合里读取去重后的 circle_id。"""

    mongo_client = build_mongodb_client()
    database = mongo_client[settings.MONGO_DATABASE]
    collection = database[settings.MONGO_CIRCLE_COLLECTION]

    circle_ids = collection.distinct("circle_id", {"circle_id": {"$exists": True, "$ne": ""}})
    mongo_client.close()
    return [str(circle_id).strip() for circle_id in circle_ids if str(circle_id).strip()]


def build_doctor_list_url(circle_id):
    """按当前规则拼接医生列表接口地址。"""

    access_token = settings.CIRCLE_LIST_TOKEN
    return (
        "https://api.mediportal.com.cn/circle/user/getRolePage"
        f"?access_token={access_token}&pageIndex=1&pageSize=16232"
        f"&access-token={access_token}&circleId={circle_id}&type=1&device=android"
    )


def write_doctor_list_urls(circle_ids):
    """把医生列表接口地址写回 Redis。"""

    redis_client = build_redis_client()
    redis_key = settings.REDIS_KEY_DOCTOR_LIST_URL
    write_count = 0

    for index, circle_id in enumerate(circle_ids, start=1):
        doctor_list_url = build_doctor_list_url(circle_id)
        payload = json.dumps({"url": doctor_list_url}, ensure_ascii=False)
        redis_client.sadd(redis_key, payload)
        write_count += 1
        print(f"[{index}] circle_id={circle_id}")
        print(f"写入 Redis: {doctor_list_url}")

    return write_count


def main():
    """执行重建流程。"""

    circle_ids = load_circle_ids()
    print(f"MongoDB 读取到 circle_id 数量: {len(circle_ids)}")

    if not circle_ids:
        print("没有读到任何 circle_id，脚本结束。")
        return

    write_count = write_doctor_list_urls(circle_ids)
    print(f"写入 Redis 完成，doctor_list_url 数量: {write_count}")


if __name__ == "__main__":
    main()
