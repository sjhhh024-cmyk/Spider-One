from pathlib import Path

import pytest

from runtime.app.shared.profile_config import load_profile_config


def test_load_profile_config_reads_expected_sections(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yml"
    profile_path.write_text(
        """
project:
  name: doctor_mingyihui
  site: mingyihui
  entity_type: doctor

redis:
  host: 127.0.0.1
  port: 6379
  db: 0
  password: redis-secret

mongodb:
  host: 127.0.0.1
  port: 27017
  database: crawler_platform
  collection: doctor_profiles
  username: mongo-user
  password: mongo-pass

proxy:
  enabled: true
  provider: custom
  host: proxy.example.com
  port: 9000
  username: proxy-user
  password: proxy-pass

runtime:
  concurrency: 12
  timeout_seconds: 30
  max_retries: 4

workers:
  http: true
  browser: true
  scrapy: false
  reverse: false
""".strip(),
        encoding="utf-8",
    )

    profile = load_profile_config(profile_path)

    assert profile.project.name == "doctor_mingyihui"
    assert profile.redis.password == "redis-secret"
    assert profile.mongodb.collection == "doctor_profiles"
    assert profile.proxy.enabled is True
    assert profile.proxy.username == "proxy-user"
    assert profile.runtime.concurrency == 12
    assert profile.workers.browser is True
    assert profile.workers.scrapy is False


def test_load_profile_config_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_profile_config(tmp_path / "missing-profile.yml")


def test_load_profile_config_requires_critical_sections(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yml"
    profile_path.write_text(
        """
project:
  name: doctor_mingyihui

redis:
  host: 127.0.0.1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required profile sections"):
        load_profile_config(profile_path)
