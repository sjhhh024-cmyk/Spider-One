from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_hnyygh import settings  # noqa: E402


def test_default_redis_config_uses_password_protected_remote_instance() -> None:
    assert settings.REDIS_HOST == "117.50.131.232"
    assert settings.REDIS_PORT == 6379
    assert settings.REDIS_DB == 1
    assert settings.REDIS_PASSWORD == "Yb$]Mdh3YU2k}hw"
    assert settings.REDIS_URL == "redis://:Yb%24%5DMdh3YU2k%7Dhw@117.50.131.232:6379/1"


def test_redis_params_match_shared_authenticated_pattern() -> None:
    assert settings.REDIS_PARAMS == {
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
        "decode_responses": False,
    }
