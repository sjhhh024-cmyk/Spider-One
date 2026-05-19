from __future__ import annotations

import logging
import mimetypes
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

import requests

from doctor_dzys import DEFAULT_PROFILE, build_mongo_client, get_doctor_collection_name

try:
    from qiniu import Auth, put_data
except ImportError:  # pragma: no cover - 本地未安装时运行期报错
    Auth = None
    put_data = None


DEFAULT_REFERER = "https://www.dazhong.com/"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_QINIU_KEY_PREFIX = "doctor_dzys/avatar"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
DEFAULT_QINIU_ACCESS_KEY = os.getenv("SPIDER_ONE_QINIU_ACCESS_KEY", "")
DEFAULT_QINIU_SECRET_KEY = os.getenv("SPIDER_ONE_QINIU_SECRET_KEY", "")
DEFAULT_QINIU_BUCKET = os.getenv("SPIDER_ONE_QINIU_BUCKET", "")
DEFAULT_QINIU_DOMAIN = os.getenv("SPIDER_ONE_QINIU_DOMAIN", "")

# 直接填写这里即可，一键运行时优先使用这里的值；留空则回退到同名环境变量。
QINIU_ACCESS_KEY = "T89tUhVK006ZCfT2b3oCVWOTvsL6eUHs4loc2bZg"
QINIU_SECRET_KEY = "nYgc-NLoWkAZRN_ba1hEN-SVar8WKoqZzhzxXPTS"
QINIU_BUCKET = "infoxmed"
QINIU_DOMAIN = "https://img.infox-med.com"

# 运行开关：保持默认即可；需要时再修改。
RUN_LIMIT = 0
RUN_FORCE = False
RUN_DRY_RUN = False
RUN_DOCTOR_ID = ""
RUN_TIMEOUT_SECONDS = DEFAULT_TIMEOUT_SECONDS
RUN_KEY_PREFIX = DEFAULT_QINIU_KEY_PREFIX

logger = logging.getLogger("doctor-dzys-qiniu-uploader")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class AvatarUploader(Protocol):
    def upload_bytes(self, *, key: str, data: bytes) -> str: ...


@dataclass(frozen=True)
class ScriptConfig:
    qiniu_access_key: str = QINIU_ACCESS_KEY
    qiniu_secret_key: str = QINIU_SECRET_KEY
    qiniu_bucket: str = QINIU_BUCKET
    qiniu_domain: str = QINIU_DOMAIN
    limit: int = RUN_LIMIT
    force: bool = RUN_FORCE
    dry_run: bool = RUN_DRY_RUN
    doctor_id: str = RUN_DOCTOR_ID
    timeout_seconds: int = RUN_TIMEOUT_SECONDS
    key_prefix: str = RUN_KEY_PREFIX


@dataclass(frozen=True)
class SyncResult:
    status: str
    doctor_id: str
    qiniu_url: str = ""


def is_default_avatar_url(avatar_url: str) -> bool:
    return "/doctor_img/doctor-0." in str(avatar_url or "").strip().lower()


def get_origin_avatar_url(record: dict[str, Any]) -> str:
    origin_url = str(record.get("doctor_avatar_origin_url") or "").strip()
    if origin_url:
        return origin_url
    return str(record.get("doctor_avatar_url") or "").strip()


def build_avatar_fetch_headers(source_url: str) -> dict[str, str]:
    referer = str(source_url or "").strip() or DEFAULT_REFERER
    return {
        "Referer": referer,
        "User-Agent": DEFAULT_USER_AGENT,
    }


def build_candidate_query(*, force: bool) -> dict[str, object]:
    query: dict[str, object] = {
        "doctor_avatar_url": {"$nin": ["", None]},
    }
    if not force:
        query["$or"] = [
            {"doctor_avatar_origin_url": {"$exists": False}},
            {"doctor_avatar_origin_url": ""},
            {"doctor_avatar_origin_url": None},
        ]
    return query


def resolve_config_value(script_value: str, env_name: str) -> str:
    explicit = str(script_value or "").strip()
    if explicit:
        return explicit
    return str(os.getenv(env_name, "") or "").strip()


def resolve_script_config(config: ScriptConfig | None = None) -> ScriptConfig:
    base = config or ScriptConfig()
    return ScriptConfig(
        qiniu_access_key=resolve_config_value(
            base.qiniu_access_key, "SPIDER_ONE_QINIU_ACCESS_KEY"
        ),
        qiniu_secret_key=resolve_config_value(
            base.qiniu_secret_key, "SPIDER_ONE_QINIU_SECRET_KEY"
        ),
        qiniu_bucket=resolve_config_value(base.qiniu_bucket, "SPIDER_ONE_QINIU_BUCKET"),
        qiniu_domain=resolve_config_value(base.qiniu_domain, "SPIDER_ONE_QINIU_DOMAIN"),
        limit=max(0, int(base.limit)),
        force=bool(base.force),
        dry_run=bool(base.dry_run),
        doctor_id=str(base.doctor_id or "").strip(),
        timeout_seconds=max(1, int(base.timeout_seconds)),
        key_prefix=str(base.key_prefix or DEFAULT_QINIU_KEY_PREFIX).strip(),
    )


def guess_file_extension(avatar_url: str, content_type: str) -> str:
    path = urlparse(avatar_url).path
    _, ext = os.path.splitext(path)
    normalized_ext = ext.lower().strip()
    if normalized_ext:
        return normalized_ext

    mime_type = str(content_type or "").split(";", 1)[0].strip().lower()
    if mime_type:
        guessed = mimetypes.guess_extension(mime_type)
        if guessed:
            if guessed == ".jpe":
                return ".jpg"
            return guessed.lower()
    return ".jpg"


def build_qiniu_key(
    record: dict[str, Any],
    *,
    avatar_url: str,
    content_type: str,
    key_prefix: str = DEFAULT_QINIU_KEY_PREFIX,
) -> str:
    doctor_id = str(record.get("doctor_id") or record.get("_id") or "").strip()
    if not doctor_id:
        raise ValueError("缺少 doctor_id，无法生成七牛 key")

    clean_prefix = str(key_prefix or "").strip().strip("/")
    extension = guess_file_extension(avatar_url, content_type)
    file_name = f"{doctor_id}{extension}"
    return f"{clean_prefix}/{file_name}" if clean_prefix else file_name


def download_avatar(
    record: dict[str, Any],
    *,
    session: requests.Session,
    timeout_seconds: int,
) -> tuple[bytes, str]:
    avatar_url = get_origin_avatar_url(record)
    if not avatar_url:
        raise ValueError("缺少 doctor_avatar_url")

    response = session.get(
        avatar_url,
        headers=build_avatar_fetch_headers(str(record.get("source_url") or "")),
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    content = response.content
    if not content:
        raise ValueError(f"头像响应为空: {avatar_url}")

    content_type = str(response.headers.get("Content-Type") or "").strip()
    if content_type and not content_type.lower().startswith("image/"):
        raise ValueError(f"头像响应不是图片: {avatar_url} ({content_type})")

    return content, content_type


class QiniuUploader:
    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        bucket: str,
        domain: str,
    ) -> None:
        if Auth is None or put_data is None:
            raise RuntimeError("未安装 qiniu SDK，请先执行: py -3 -m pip install qiniu")

        self.access_key = str(access_key or "").strip()
        self.secret_key = str(secret_key or "").strip()
        self.bucket = str(bucket or "").strip()
        self.domain = str(domain or "").strip().rstrip("/")

        missing = [
            name
            for name, value in (
                ("SPIDER_ONE_QINIU_ACCESS_KEY", self.access_key),
                ("SPIDER_ONE_QINIU_SECRET_KEY", self.secret_key),
                ("SPIDER_ONE_QINIU_BUCKET", self.bucket),
                ("SPIDER_ONE_QINIU_DOMAIN", self.domain),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"缺少七牛配置: {', '.join(missing)}")

        self.auth = Auth(self.access_key, self.secret_key)

    def upload_bytes(self, *, key: str, data: bytes) -> str:
        token = self.auth.upload_token(self.bucket, key)
        result, info = put_data(token, key, data)
        status_code = getattr(info, "status_code", None)
        if status_code != 200:
            raise RuntimeError(f"七牛上传失败: key={key}, status_code={status_code}, result={result}")
        return f"{self.domain}/{key}"


def sync_doctor_avatar(
    record: dict[str, Any],
    *,
    session: requests.Session,
    uploader: AvatarUploader,
    collection,
    timeout_seconds: int,
    dry_run: bool,
    key_prefix: str = DEFAULT_QINIU_KEY_PREFIX,
) -> SyncResult:
    doctor_id = str(record.get("doctor_id") or record.get("_id") or "").strip()
    avatar_url = get_origin_avatar_url(record)

    if not doctor_id:
        return SyncResult(status="skipped_missing_doctor_id", doctor_id="")
    if not avatar_url:
        return SyncResult(status="skipped_missing_avatar_url", doctor_id=doctor_id)
    if is_default_avatar_url(avatar_url):
        return SyncResult(status="skipped_default_avatar", doctor_id=doctor_id)
    if dry_run:
        return SyncResult(status="dry_run", doctor_id=doctor_id)

    content, content_type = download_avatar(
        record,
        session=session,
        timeout_seconds=timeout_seconds,
    )
    key = build_qiniu_key(
        record,
        avatar_url=avatar_url,
        content_type=content_type,
        key_prefix=key_prefix,
    )
    qiniu_url = uploader.upload_bytes(key=key, data=content)

    if collection is not None:
        collection.update_one(
            {"_id": str(record.get("_id") or doctor_id)},
            {
                "$set": {
                    "doctor_avatar_url": qiniu_url,
                },
                "$unset": {
                    "doctor_avatar_qiniu_key": "",
                    "doctor_avatar_qiniu_url": "",
                },
            },
        )

    return SyncResult(status="uploaded", doctor_id=doctor_id, qiniu_url=qiniu_url)


def iter_candidate_records(collection, *, force: bool, limit: int, doctor_id: str):
    query = build_candidate_query(force=force)
    normalized_doctor_id = str(doctor_id or "").strip()
    if normalized_doctor_id:
        query["doctor_id"] = normalized_doctor_id

    cursor = collection.find(
        query,
        {
            "_id": 1,
            "doctor_id": 1,
            "doctor_avatar_url": 1,
            "doctor_avatar_origin_url": 1,
            "source_url": 1,
        },
    ).sort("_id", 1)
    if limit > 0:
        cursor = cursor.limit(limit)
    return cursor


def migrate_legacy_qiniu_fields(collection) -> int:
    updated = 0
    cursor = collection.find(
        {
            "doctor_avatar_qiniu_url": {"$nin": ["", None]},
        },
        {
            "_id": 1,
            "doctor_avatar_url": 1,
            "doctor_avatar_origin_url": 1,
            "doctor_avatar_qiniu_url": 1,
        },
    )
    for record in cursor:
        qiniu_url = str(record.get("doctor_avatar_qiniu_url") or "").strip()
        if not qiniu_url:
            continue
        origin_url = str(record.get("doctor_avatar_origin_url") or "").strip()
        current_avatar_url = str(record.get("doctor_avatar_url") or "").strip()
        update_doc: dict[str, Any] = {
            "$set": {
                "doctor_avatar_url": qiniu_url,
            },
            "$unset": {
                "doctor_avatar_qiniu_key": "",
                "doctor_avatar_qiniu_url": "",
            },
        }
        if not origin_url and current_avatar_url and current_avatar_url != qiniu_url:
            update_doc["$set"]["doctor_avatar_origin_url"] = current_avatar_url
        collection.update_one({"_id": record["_id"]}, update_doc)
        updated += 1
    return updated


def main() -> int:
    config = resolve_script_config()
    profile = DEFAULT_PROFILE
    mongodb_config = profile["mongodb"]

    mongo_client = build_mongo_client(mongodb_config)
    database = mongo_client[mongodb_config["database"]]
    collection = database[get_doctor_collection_name(mongodb_config)]
    migrated_count = migrate_legacy_qiniu_fields(collection)
    if migrated_count:
        logger.info("已清理历史七牛字段 migrated=%s", migrated_count)

    session = requests.Session()
    uploader = QiniuUploader(
        access_key=config.qiniu_access_key,
        secret_key=config.qiniu_secret_key,
        bucket=config.qiniu_bucket,
        domain=config.qiniu_domain,
    )

    total = 0
    uploaded = 0
    skipped = 0
    failed = 0

    for record in iter_candidate_records(
        collection,
        force=config.force,
        limit=config.limit,
        doctor_id=config.doctor_id,
    ):
        total += 1
        try:
            result = sync_doctor_avatar(
                record,
                session=session,
                uploader=uploader,
                collection=collection,
                timeout_seconds=config.timeout_seconds,
                dry_run=config.dry_run,
                key_prefix=config.key_prefix,
            )
            if result.status == "uploaded":
                uploaded += 1
                logger.info("上传完成 doctor_id=%s qiniu_url=%s", result.doctor_id, result.qiniu_url)
            else:
                skipped += 1
                logger.info("跳过 doctor_id=%s status=%s", result.doctor_id, result.status)
        except Exception as exc:
            failed += 1
            logger.error("处理失败 doctor_id=%s error=%s", record.get("doctor_id") or record.get("_id"), exc)

    logger.info(
        "处理结束 total=%s uploaded=%s skipped=%s failed=%s dry_run=%s",
        total,
        uploaded,
        skipped,
        failed,
        config.dry_run,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
