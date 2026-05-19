from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


def build_biz_type(module_name: str, notice_type: str, sub_type: str = "") -> str:
    """
    构造监控 BizType。

    - 如果站点存在真实二级分类（如“房屋建筑”“公开招标”），优先使用：一级类型-二级类型
    - 如果站点没有真实二级分类，则只保留一级类型本身
    """
    module = str(module_name or "").strip()
    secondary = str(sub_type or "").strip()
    if module and secondary:
        return f"{module}-{secondary}"
    return module or secondary


class WebsiteRedisStorage:
    """监控状态调用的方法。"""

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 6379,
        db: int = 11,
        password: str | None = None,
        decode_responses: bool = True,
        socket_connect_timeout: int = 5,
    ) -> None:
        if redis is None:
            raise RuntimeError("redis 模块未安装，无法初始化 WebsiteRedisStorage")

        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
                socket_connect_timeout=socket_connect_timeout,
            )
            self.redis_client.ping()
            logging.info("Redis连接成功")
        except Exception as exc:  # pragma: no cover
            logging.error(f"Redis连接失败: {exc}")
            raise

    def _get_unique_key(self, webname: str, biz_type: str | None = None) -> str:
        if biz_type:
            return f"{webname}:{biz_type}"
        return webname

    def update_website_data(
        self, province: str, city: str, webname: str, updates: dict[str, Any]
    ) -> bool:
        try:
            level3_key = f"website_data_v3:{province}:{city}"
            biz_type = updates.get("BizType", "")
            website_data = {
                "WebName": webname,
                "BizType": biz_type,
                "WasSuccessful": updates.get("WasSuccessful", 0),
                "WebsiteError": updates.get("WebsiteError", 0),
                "HasContent": updates.get("HasContent", 0),
                "HasNewData": updates.get("HasNewData", 0),
                "IsValidData": updates.get("IsValidData", 0),
                **updates,
            }
            website_data["_province"] = province
            website_data["_city"] = city
            website_data["_last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            website_json = json.dumps(website_data, ensure_ascii=False)
            unique_key = self._get_unique_key(webname, biz_type)
            self.redis_client.hset(level3_key, unique_key, website_json)
            logging.info(
                f"成功更新网站: website_data_v3/{province}/{city}/{unique_key}"
            )
            return True
        except Exception as exc:  # pragma: no cover
            logging.error(f"更新/创建网站失败: {province}/{city}/{webname} - {exc}")
            return False


def build_logo_info(webname: str, biz_type: str) -> dict[str, Any]:
    return {
        "WasSuccessful": 1,
        "WebsiteError": 1,
        "HasContent": 0,
        "HasNewData": 0,
        "IsValidData": 1,
        "WebName": webname,
        "BizType": biz_type,
    }


class SpiderMonitor:
    def __init__(
        self,
        *,
        province: str,
        city: str,
        webname: str,
        biz_type: str,
        storage: WebsiteRedisStorage | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.province = province
        self.city = city
        self.webname = webname
        self.biz_type = biz_type
        self.logger = logger or logging.getLogger(__name__)
        self.logo_info = build_logo_info(webname, biz_type)
        self.storage = storage if storage is not None else self._create_storage()

    def _create_storage(self) -> WebsiteRedisStorage | None:
        try:
            return WebsiteRedisStorage()
        except Exception as exc:  # pragma: no cover
            self.logger.warning(f"监控存储初始化失败，跳过监控上报: {exc}")
            return None

    def mark_run_failed(self) -> None:
        self.logo_info["WasSuccessful"] = 0

    def mark_website_error(self) -> None:
        self.logo_info["WebsiteError"] = 0

    def mark_has_content(self) -> None:
        self.logo_info["HasContent"] = 1

    def mark_has_new_data(self) -> None:
        self.logo_info["HasNewData"] = 1

    def mark_invalid_data(self) -> None:
        self.logo_info["IsValidData"] = 0

    def flush(self) -> bool:
        if self.storage is None:
            self.logger.info(f"监控存储不可用，跳过状态上报: {self.logo_info}")
            return False
        return self.storage.update_website_data(
            province=self.province,
            city=self.city,
            webname=self.webname,
            updates=self.logo_info,
        )
