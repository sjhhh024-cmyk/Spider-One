"""doctor-ywbd 项目配置。"""

from __future__ import annotations

import os
from urllib.parse import quote_plus

from doctor_ywbd.route_hypotheses import DOCTOR_COLLECTION_NAME, HOSPITAL_COLLECTION_NAME, build_redis_keys
from doctor_ywbd.tools import build_cookie_cache_path, build_cookie_header_from_mapping


BOT_NAME = "doctor_ywbd"

SPIDER_MODULES = ["doctor_ywbd.spiders"]
NEWSPIDER_MODULE = "doctor_ywbd.spiders"
COMMANDS_MODULE = "doctor_ywbd.commands"

ROBOTSTXT_OBEY = False

# MongoDB 配置：复用 doctor-circle 的现有库，只切换集合名。
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
MONGO_HOSPITAL_COLLECTION = HOSPITAL_COLLECTION_NAME

# Redis 配置：复用 doctor-circle 的现有连接。
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

REDIS_KEYS = build_redis_keys()
REDIS_KEY_DISEASE_INDEX_URL = REDIS_KEYS["disease_index_url"]
REDIS_KEY_DISEASE_LIST_URL = REDIS_KEYS["disease_list_url"]
REDIS_KEY_DEPARTMENT_INDEX_URL = REDIS_KEYS["department_index_url"]
REDIS_KEY_DEPARTMENT_LIST_URL = REDIS_KEYS["department_list_url"]
REDIS_KEY_AREA_INDEX_URL = REDIS_KEYS["area_index_url"]
REDIS_KEY_AREA_LIST_URL = REDIS_KEYS["area_list_url"]
REDIS_KEY_HOSPITAL_AREA_INDEX_URL = REDIS_KEYS["hospital_area_index_url"]
REDIS_KEY_HOSPITAL_LIST_URL = REDIS_KEYS["hospital_list_url"]
REDIS_KEY_HOSPITAL_DETAIL_URL = REDIS_KEYS["hospital_detail_url"]
REDIS_KEY_HOSPITAL_EXPERT_URL = REDIS_KEYS["hospital_expert_url"]
REDIS_KEY_DOCTOR_INFO_URL = REDIS_KEYS["doctor_info_url"]

YWBD_INITIAL_COOKIE = {
  "isYY": "yiyuan",
  "__jsluid_s": "c057e52512c25f82cdc56c0ec47c5bfd",
  "ASKBAIDUUID": "ask%3A1775803406573247",
  "Hm_lvt_d7682ab43891c68a00de46e9ce5b76aa": "1776144331,1776215054",
  "Hm_lvt_7c2c4ab8a1436c0f67383fe9417819b7": "1775969081,1776051745,1776214795,1776654523",
  "HMACCOUNT": "BF60C57DDB4B8BA6",
  "comHealthCloudUserProfileUseTag": "d3d841ec20d22dcd32cb9f8b2a88e202",
  "__jsl_clearance_s": "1776654540.731|0|Wr0gDIEupl437VofDqwsAZdm2JQ%3D",
  "_csrf": "d17a3840ec791a9eea87efdf8f81cbfd995a6a4bd9c7c7f460db7cd3c35c8ca7a%3A2%3A%7Bi%3A0%3Bs%3A5%3A%22_csrf%22%3Bi%3A1%3Bs%3A32%3A%22E58HuLi-23LLfBuCeRCk3Urvjt_klkyh%22%3B%7D",
  "Hm_lpvt_7c2c4ab8a1436c0f67383fe9417819b7": "1776655385"
}
YWBD_INITIAL_COOKIE_HEADER = build_cookie_header_from_mapping(YWBD_INITIAL_COOKIE)
YWBD_COOKIE_PROBE_URL = os.getenv("YWBD_COOKIE_PROBE_URL", "https://data.120ask.com/yisheng/jibing.html")
YWBD_COOKIE_CACHE_FILE = os.getenv(
    "YWBD_COOKIE_CACHE_FILE",
    build_cookie_cache_path(__file__),
)

RETRY_TIMES = 5
DOWNLOAD_DELAY = 0.3
CONCURRENT_REQUESTS = 30
COOKIES_ENABLED = False
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
YWBD_CURL_CFFI_ENABLED = True
YWBD_CURL_CFFI_ENABLED_SPIDERS = [
    "area_list_spider",
    "hospital_area_index_spider",
    "hospital_list_spider",
    "hospital_detail_spider",
    "hospital_expert_spider",
]
YWBD_CURL_CFFI_IMPERSONATE = "chrome"
YWBD_CURL_CFFI_TIMEOUT = 40
YWBD_PROXY_ENABLED = False
YWBD_DOCTOR_DETAIL_REQUEUE_MAX_ATTEMPTS = 3
YWBD_DOCTOR_DETAIL_ALWAYS_REQUEUE_STATUSES = [403, 521]

SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = True
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderPriorityQueue"
SCHEDULER_IDLE_BEFORE_CLOSE = 5
MAX_IDLE_TIME_BEFORE_CLOSE = 10

ITEM_PIPELINES = {
    "doctor_ywbd.pipelines.MongoPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
    # 这些默认中间件的职责由项目自定义实现接管，显式关闭以减少日志噪音。
    "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware": None,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "doctor_ywbd.middlewares.ClearanceRetryMiddleware": 502,
    "doctor_ywbd.middlewares.BrowserHeadersMiddleware": 503,
    "doctor_ywbd.middlewares.AbuyunProxyMiddleware": 504,
    "doctor_ywbd.curl_cffi_downloader.CurlCffiMiddleware": 505,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

LOG_LEVEL = "INFO"
