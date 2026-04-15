"""doctor_wygk 项目配置。"""

from __future__ import annotations

import os
from urllib.parse import quote_plus

from doctor_wygk.tools import (
    ABUYUN_PROXY_HOST,
    ABUYUN_PROXY_PASS,
    ABUYUN_PROXY_PORT,
    ABUYUN_PROXY_USER,
    DOCTOR_COLLECTION_NAME,
    REDIS_KEYS,
)


BOT_NAME = "doctor_wygk"

SPIDER_MODULES = ["doctor_wygk.spiders"]
NEWSPIDER_MODULE = "doctor_wygk.spiders"
COMMANDS_MODULE = "doctor_wygk.commands"

ROBOTSTXT_OBEY = False

MONGO_HOST = "101.200.125.240"
MONGO_PORT = 27017
MONGO_USERNAME = "admin"
MONGO_PASSWORD = "a@Mfv8k!r@8r@8&R"
MONGO_AUTH_SOURCE = "admin"
MONGO_DATABASE = "Doctor_Database"

mongo_username = quote_plus(MONGO_USERNAME)
mongo_password = quote_plus(MONGO_PASSWORD)
MONGO_URI = (
    f"mongodb://{mongo_username}:{mongo_password}@{MONGO_HOST}:{MONGO_PORT}/"
    f"?authSource={MONGO_AUTH_SOURCE}"
)
MONGO_DOCTOR_COLLECTION = DOCTOR_COLLECTION_NAME

REDIS_HOST = os.getenv("SPIDER_ONE_REDIS_HOST", "117.50.131.232")
REDIS_PORT = int(os.getenv("SPIDER_ONE_REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("SPIDER_ONE_REDIS_DB", "1"))
REDIS_PASSWORD = os.getenv("SPIDER_ONE_REDIS_PASSWORD", "Yb$]Mdh3YU2k}hw")
REDIS_START_URLS_AS_SET = True
REDIS_PARAMS = {
    "socket_connect_timeout": 5,
    "socket_timeout": 5,
    "decode_responses": False,
}

if REDIS_PASSWORD:
    password = quote_plus(REDIS_PASSWORD)
    REDIS_URL = f"redis://:{password}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

REDIS_KEY_HOSPITAL_HOME_URL = REDIS_KEYS["hospital_home_url"]
REDIS_KEY_DEPT_TASK = REDIS_KEYS["dept_task"]
REDIS_KEY_DOCTOR_LIST_TASK = REDIS_KEYS["doctor_list_task"]
REDIS_KEY_DOCTOR_INFO_URL = REDIS_KEYS["doctor_info_url"]
REDIS_KEY_DOCTOR_HOME_TASK = REDIS_KEYS["doctor_home_task"]
REDIS_KEY_DOCTOR_HOME_DONE = REDIS_KEYS["doctor_home_done"]

RETRY_TIMES = 5
DOWNLOAD_DELAY = 0.2
CONCURRENT_REQUESTS = 16
COOKIES_ENABLED = False
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"

SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = True
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderPriorityQueue"
SCHEDULER_IDLE_BEFORE_CLOSE = 5
MAX_IDLE_TIME_BEFORE_CLOSE = 10

ITEM_PIPELINES = {
    "doctor_wygk.pipelines.MongoPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
    "doctor_wygk.middlewares.RetryMiddleware": 502,
    "doctor_wygk.middlewares.UserAgentMiddleware": 503,
    "doctor_wygk.middlewares.ProxyMiddleware": 504,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

LOG_LEVEL = "INFO"
