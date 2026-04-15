from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class ProjectProfile:
    name: str
    site: str
    entity_type: str


@dataclass(frozen=True, slots=True)
class RedisProfile:
    host: str
    port: int
    db: int
    password: str | None = None


@dataclass(frozen=True, slots=True)
class MongoDBProfile:
    host: str
    port: int
    database: str
    collection: str
    username: str | None = None
    password: str | None = None


@dataclass(frozen=True, slots=True)
class ProxyProfile:
    enabled: bool = False
    provider: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeProfile:
    concurrency: int
    timeout_seconds: int
    max_retries: int


@dataclass(frozen=True, slots=True)
class WorkerProfile:
    http: bool
    browser: bool
    scrapy: bool
    reverse: bool


@dataclass(frozen=True, slots=True)
class CrawlerProfile:
    project: ProjectProfile
    redis: RedisProfile
    mongodb: MongoDBProfile
    proxy: ProxyProfile
    runtime: RuntimeProfile
    workers: WorkerProfile


REQUIRED_SECTIONS = {"project", "redis", "mongodb", "runtime", "workers"}


def load_profile_config(profile_path: Path) -> CrawlerProfile:
    profile_path = Path(profile_path)
    if not profile_path.is_file():
        raise FileNotFoundError(f"profile file not found: {profile_path}")

    raw_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise ValueError("profile.yml must contain a top-level mapping")

    missing_sections = sorted(REQUIRED_SECTIONS - raw_data.keys())
    if missing_sections:
        joined_sections = ", ".join(missing_sections)
        raise ValueError(f"missing required profile sections: {joined_sections}")

    return CrawlerProfile(
        project=_parse_project_section(raw_data["project"]),
        redis=_parse_redis_section(raw_data["redis"]),
        mongodb=_parse_mongodb_section(raw_data["mongodb"]),
        proxy=_parse_proxy_section(raw_data.get("proxy", {})),
        runtime=_parse_runtime_section(raw_data["runtime"]),
        workers=_parse_workers_section(raw_data["workers"]),
    )


def _parse_project_section(section: Any) -> ProjectProfile:
    mapping = _expect_mapping(section, "project")
    return ProjectProfile(
        name=_require_str(mapping, "name", "project"),
        site=_require_str(mapping, "site", "project"),
        entity_type=_require_str(mapping, "entity_type", "project"),
    )


def _parse_redis_section(section: Any) -> RedisProfile:
    mapping = _expect_mapping(section, "redis")
    return RedisProfile(
        host=_require_str(mapping, "host", "redis"),
        port=_require_int(mapping, "port", "redis"),
        db=_require_int(mapping, "db", "redis"),
        password=_optional_str(mapping, "password"),
    )


def _parse_mongodb_section(section: Any) -> MongoDBProfile:
    mapping = _expect_mapping(section, "mongodb")
    return MongoDBProfile(
        host=_require_str(mapping, "host", "mongodb"),
        port=_require_int(mapping, "port", "mongodb"),
        database=_require_str(mapping, "database", "mongodb"),
        collection=_require_str(mapping, "collection", "mongodb"),
        username=_optional_str(mapping, "username"),
        password=_optional_str(mapping, "password"),
    )


def _parse_proxy_section(section: Any) -> ProxyProfile:
    mapping = _expect_mapping(section, "proxy")
    return ProxyProfile(
        enabled=bool(mapping.get("enabled", False)),
        provider=_optional_str(mapping, "provider"),
        host=_optional_str(mapping, "host"),
        port=_optional_int(mapping, "port"),
        username=_optional_str(mapping, "username"),
        password=_optional_str(mapping, "password"),
    )


def _parse_runtime_section(section: Any) -> RuntimeProfile:
    mapping = _expect_mapping(section, "runtime")
    return RuntimeProfile(
        concurrency=_require_int(mapping, "concurrency", "runtime"),
        timeout_seconds=_require_int(mapping, "timeout_seconds", "runtime"),
        max_retries=_require_int(mapping, "max_retries", "runtime"),
    )


def _parse_workers_section(section: Any) -> WorkerProfile:
    mapping = _expect_mapping(section, "workers")
    return WorkerProfile(
        http=_require_bool(mapping, "http", "workers"),
        browser=_require_bool(mapping, "browser", "workers"),
        scrapy=_require_bool(mapping, "scrapy", "workers"),
        reverse=_require_bool(mapping, "reverse", "workers"),
    )


def _expect_mapping(value: Any, section_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"section '{section_name}' must be a mapping")
    return value


def _require_str(mapping: dict[str, Any], key: str, section_name: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"section '{section_name}' requires a non-empty string for '{key}'")
    return value


def _require_int(mapping: dict[str, Any], key: str, section_name: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int):
        raise ValueError(f"section '{section_name}' requires an integer for '{key}'")
    return value


def _require_bool(mapping: dict[str, Any], key: str, section_name: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"section '{section_name}' requires a boolean for '{key}'")
    return value


def _optional_str(mapping: dict[str, Any], key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"optional field '{key}' must be a non-empty string when provided")
    return value


def _optional_int(mapping: dict[str, Any], key: str) -> int | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"optional field '{key}' must be an integer when provided")
    return value
