"""医生圈项目配置。

这个文件是整个项目最先要看的地方：
1. 这里改 MongoDB
2. 这里改 Redis
3. 这里改接口 token
4. 这里改并发、重试、下载间隔
"""

import os
from urllib.parse import quote_plus


BOT_NAME = "doctor_circle"

SPIDER_MODULES = ["doctor_circle.spiders"]
NEWSPIDER_MODULE = "doctor_circle.spiders"
COMMANDS_MODULE = "doctor_circle.commands"

ROBOTSTXT_OBEY = False

# MongoDB 配置
# 用户名和密码里有特殊字符时，必须先做 URL 编码，再拼连接串。
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
MONGO_CIRCLE_COLLECTION = "doctor_circle_list"
MONGO_DOCTOR_COLLECTION = "doctor_circle"
MONGO_HOSPITAL_COLLECTION = "hospital_circle"

# Redis 配置
# 这里默认连本地 127.0.0.1:6379，适合先打 SSH 隧道再运行 Scrapy。
REDIS_HOST = os.getenv("SPIDER_ONE_REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("SPIDER_ONE_REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("SPIDER_ONE_REDIS_DB", "1"))
REDIS_PASSWORD = os.getenv("SPIDER_ONE_REDIS_PASSWORD", "ToSP3mvF13zuiT8w")
REDIS_START_URLS_AS_SET = True

if REDIS_PASSWORD:
    password = quote_plus(REDIS_PASSWORD)
    REDIS_URL = f"redis://:{password}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Redis key 配置
REDIS_KEY_CIRCLE_URL = "doctor_circle:circle_url"
REDIS_KEY_DOCTOR_LIST_URL = "doctor_circle:doctor_list_url"
REDIS_KEY_DOCTOR_URL = "doctor_circle:doctor_url"

# 医生圈接口 token
CIRCLE_LIST_TOKEN = os.getenv(
    "DOCTOR_CIRCLE_LIST_TOKEN",
    "86799363272b41aea54224825fe2a275",
)

HOSPITAL_BASE_SEARCH_URL = os.getenv(
    "DOCTOR_CIRCLE_HOSPITAL_BASE_SEARCH_URL",
    "https://api.mediportal.com.cn/health/base/findHospitalByCondition",
)

# 国家医保服务平台医院检索配置
# 当前 hospital_detail_spider.py 实际走的是这组配置：
# 1. NHSA_HOSPITAL_SEARCH_URL 是医院检索接口
# 2. NHSA_APP_CODE / NHSA_APP_SECRET / NHSA_PUBLIC_KEY / NHSA_PRIVATE_KEY
#    用来构造请求头签名和请求体加密数据
# 医生圈的 HOSPITAL_BASE_SEARCH_URL 先保留，方便后面继续对照或回退调试。
NHSA_HOSPITAL_SEARCH_URL = os.getenv(
    "DOCTOR_CIRCLE_NHSA_HOSPITAL_SEARCH_URL",
    "https://fuwu.nhsa.gov.cn/ebus/fuwu/api/nthl/api/CommQuery/queryFixedHospital",
)
NHSA_APP_CODE = os.getenv(
    "DOCTOR_CIRCLE_NHSA_APP_CODE",
    "T98HPCGN5ZVVQBS8LZQNOAEXVI9GYHKQ",
)
NHSA_APP_SECRET = os.getenv(
    "DOCTOR_CIRCLE_NHSA_APP_SECRET",
    "NMVFVILMKT13GEMD3BKPKCTBOQBPZR2P",
)
NHSA_PUBLIC_KEY = os.getenv(
    "DOCTOR_CIRCLE_NHSA_PUBLIC_KEY",
    "BEKaw3Qtc31LG/hTPHFPlriKuAn/nzTWl8LiRxLw4iQiSUIyuglptFxNkdCiNXcXvkqTH79Rh/A2sEFU6hjeK3k=",
)
NHSA_PRIVATE_KEY = os.getenv(
    "DOCTOR_CIRCLE_NHSA_PRIVATE_KEY",
    "AJxKNdmspMaPGj+onJNoQ0cgWk2E3CYFWKBJhpcJrAtC",
)
# CIRCLE_DETAIL_TOKEN = os.getenv(
#     "DOCTOR_CIRCLE_DETAIL_TOKEN",
#     "7994365551674a5eab042bcff198f0f7",
# )


# 采集节奏
RETRY_TIMES = 5
DOWNLOAD_DELAY = 0.2
CONCURRENT_REQUESTS = 30
HOSPITAL_DETAIL_SLEEP_EVERY = int(os.getenv("DOCTOR_CIRCLE_HOSPITAL_SLEEP_EVERY", "300"))
HOSPITAL_DETAIL_SLEEP_SECONDS = int(os.getenv("DOCTOR_CIRCLE_HOSPITAL_SLEEP_SECONDS", "30"))

# 分布式配置
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = True
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderPriorityQueue"
SCHEDULER_IDLE_BEFORE_CLOSE = 5
MAX_IDLE_TIME_BEFORE_CLOSE = 10

ITEM_PIPELINES = {
    "doctor_circle.pipelines.MongoPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
    "doctor_circle.middlewares.RetryMiddleware": 502,
    "doctor_circle.middlewares.UserAgentMiddleware": 503,
}

LOG_LEVEL = "INFO"
