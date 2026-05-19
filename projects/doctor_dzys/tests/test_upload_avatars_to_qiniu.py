from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from upload_avatars_to_qiniu import (  # noqa: E402
    DEFAULT_QINIU_KEY_PREFIX,
    ScriptConfig,
    SyncResult,
    build_avatar_fetch_headers,
    build_candidate_query,
    build_qiniu_key,
    migrate_legacy_qiniu_fields,
    resolve_config_value,
    resolve_script_config,
    sync_doctor_avatar,
)


class FakeResponse:
    def __init__(
        self,
        *,
        content: bytes = b"",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http error: {self.status_code}")


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response


class FakeUploader:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def upload_bytes(self, *, key: str, data: bytes) -> str:
        self.calls.append({"key": key, "data": data})
        return f"https://cdn.example.com/{key}"


class FakeCollection:
    def __init__(self, records: list[dict[str, object]] | None = None) -> None:
        self.updates: list[tuple[dict[str, object], dict[str, object]]] = []
        self.records = records or []

    def update_one(
        self,
        query: dict[str, object],
        update: dict[str, object],
    ) -> None:
        self.updates.append((query, update))

    def find(
        self,
        query: dict[str, object],
        projection: dict[str, object],
    ) -> list[dict[str, object]]:
        _ = (query, projection)
        return list(self.records)


def test_build_avatar_fetch_headers_prefers_source_url() -> None:
    headers = build_avatar_fetch_headers("https://www.dazhong.com/hospital/doctor_home/366.html")
    assert headers["Referer"] == "https://www.dazhong.com/hospital/doctor_home/366.html"
    assert "Mozilla/5.0" in headers["User-Agent"]


def test_build_candidate_query_skips_already_uploaded_records_by_default() -> None:
    assert build_candidate_query(force=False) == {
        "doctor_avatar_url": {"$nin": ["", None]},
        "$or": [
            {"doctor_avatar_origin_url": {"$exists": False}},
            {"doctor_avatar_origin_url": ""},
            {"doctor_avatar_origin_url": None},
        ],
    }


def test_build_qiniu_key_uses_doctor_id_and_extension() -> None:
    record = {"doctor_id": "366"}
    key = build_qiniu_key(
        record,
        avatar_url="https://static.cndzys.com/doctor_img/doctor-366.jpg?x=1",
        content_type="image/jpeg",
        key_prefix=DEFAULT_QINIU_KEY_PREFIX,
    )
    assert key == "doctor_dzys/avatar/366.jpg"


def test_resolve_config_value_prefers_script_value() -> None:
    assert resolve_config_value("script-ak", "SPIDER_ONE_QINIU_ACCESS_KEY") == "script-ak"


def test_resolve_script_config_uses_env_as_fallback(monkeypatch) -> None:
    monkeypatch.setenv("SPIDER_ONE_QINIU_ACCESS_KEY", "env-ak")
    monkeypatch.setenv("SPIDER_ONE_QINIU_SECRET_KEY", "env-sk")
    monkeypatch.setenv("SPIDER_ONE_QINIU_BUCKET", "env-bucket")
    monkeypatch.setenv("SPIDER_ONE_QINIU_DOMAIN", "https://cdn.example.com")

    config = resolve_script_config(
        ScriptConfig(
            qiniu_access_key="",
            qiniu_secret_key="",
            qiniu_bucket="",
            qiniu_domain="",
        )
    )

    assert config.qiniu_access_key == "env-ak"
    assert config.qiniu_secret_key == "env-sk"
    assert config.qiniu_bucket == "env-bucket"
    assert config.qiniu_domain == "https://cdn.example.com"


def test_sync_doctor_avatar_skips_default_avatar() -> None:
    result = sync_doctor_avatar(
        {
            "_id": "0",
            "doctor_id": "0",
            "doctor_avatar_url": "https://static.cndzys.com/doctor_img/doctor-0.jpg",
            "source_url": "https://www.dazhong.com/hospital/doctor_home/0.html",
        },
        session=FakeSession(FakeResponse()),
        uploader=FakeUploader(),
        collection=FakeCollection(),
        timeout_seconds=10,
        dry_run=False,
    )
    assert result == SyncResult(status="skipped_default_avatar", doctor_id="0", qiniu_url="")


def test_sync_doctor_avatar_downloads_uploads_and_updates_mongo() -> None:
    session = FakeSession(
        FakeResponse(content=b"avatar-bytes", headers={"Content-Type": "image/jpeg"})
    )
    uploader = FakeUploader()
    collection = FakeCollection()

    result = sync_doctor_avatar(
        {
            "_id": "366",
            "doctor_id": "366",
            "doctor_avatar_url": "https://static.cndzys.com/doctor_img/doctor-366.jpg",
            "source_url": "https://www.dazhong.com/hospital/doctor_home/366.html",
        },
        session=session,
        uploader=uploader,
        collection=collection,
        timeout_seconds=10,
        dry_run=False,
    )

    assert result == SyncResult(
        status="uploaded",
        doctor_id="366",
        qiniu_url="https://cdn.example.com/doctor_dzys/avatar/366.jpg",
    )
    assert session.calls == [
        {
            "url": "https://static.cndzys.com/doctor_img/doctor-366.jpg",
            "headers": build_avatar_fetch_headers(
                "https://www.dazhong.com/hospital/doctor_home/366.html"
            ),
            "timeout": 10,
        }
    ]
    assert uploader.calls == [
        {
            "key": "doctor_dzys/avatar/366.jpg",
            "data": b"avatar-bytes",
        }
    ]
    assert collection.updates == [
        (
            {"_id": "366"},
            {
                "$set": {
                    "doctor_avatar_origin_url": "https://static.cndzys.com/doctor_img/doctor-366.jpg",
                    "doctor_avatar_url": "https://cdn.example.com/doctor_dzys/avatar/366.jpg",
                },
                "$unset": {
                    "doctor_avatar_qiniu_key": "",
                    "doctor_avatar_qiniu_url": "",
                },
            },
        )
    ]


def test_sync_doctor_avatar_prefers_origin_url_for_reupload() -> None:
    session = FakeSession(
        FakeResponse(content=b"avatar-bytes", headers={"Content-Type": "image/jpeg"})
    )
    uploader = FakeUploader()
    collection = FakeCollection()

    result = sync_doctor_avatar(
        {
            "_id": "366",
            "doctor_id": "366",
            "doctor_avatar_url": "https://img.infox-med.com/doctor_dzys/avatar/366.jpg",
            "doctor_avatar_origin_url": "https://static.cndzys.com/doctor_img/doctor-366.jpg",
            "source_url": "https://www.dazhong.com/hospital/doctor_home/366.html",
        },
        session=session,
        uploader=uploader,
        collection=collection,
        timeout_seconds=10,
        dry_run=False,
    )

    assert result.status == "uploaded"
    assert session.calls[0]["url"] == "https://static.cndzys.com/doctor_img/doctor-366.jpg"


def test_migrate_legacy_qiniu_fields_overwrites_avatar_and_unsets_legacy_fields() -> None:
    collection = FakeCollection(
        records=[
            {
                "_id": "366",
                "doctor_avatar_url": "https://static.cndzys.com/doctor_img/doctor-366.jpg",
                "doctor_avatar_qiniu_url": "https://cdn.example.com/doctor_dzys/avatar/366.jpg",
            }
        ]
    )

    updated = migrate_legacy_qiniu_fields(collection)

    assert updated == 1
    assert collection.updates == [
        (
            {"_id": "366"},
            {
                "$set": {
                    "doctor_avatar_url": "https://cdn.example.com/doctor_dzys/avatar/366.jpg",
                    "doctor_avatar_origin_url": "https://static.cndzys.com/doctor_img/doctor-366.jpg",
                },
                "$unset": {
                    "doctor_avatar_qiniu_key": "",
                    "doctor_avatar_qiniu_url": "",
                },
            },
        )
    ]
