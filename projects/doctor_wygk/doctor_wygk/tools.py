"""doctor_wygk 的轻量工具。"""

from __future__ import annotations

import base64
import json
import os
from urllib.parse import urlencode


DOCTOR_COLLECTION_NAME = "doctor_wygk"
ABUYUN_PROXY_HOST = os.getenv("ABUYUN_PROXY_HOST", "http-dyn.abuyun.com")
ABUYUN_PROXY_PORT = os.getenv("ABUYUN_PROXY_PORT", "9020")
ABUYUN_PROXY_USER = os.getenv("ABUYUN_PROXY_USER", "HCBQVZ922819VL8D")
ABUYUN_PROXY_PASS = os.getenv("ABUYUN_PROXY_PASS", "6445C2F54F51B019")
REDIS_KEYS = {
    "hospital_home_url": "doctor_wygk:hospital_home_url",
    "dept_task": "doctor_wygk:dept_task",
    "doctor_list_task": "doctor_wygk:doctor_list_task",
    "doctor_info_url": "doctor_wygk:doctor_info_url",
    "doctor_home_task": "doctor_wygk:doctor_home_task",
    "doctor_home_done": "doctor_wygk:doctor_home_done",
}


def dump_task(task: dict[str, object]) -> str:
    return json.dumps(task, ensure_ascii=False, separators=(",", ":"))


def load_task(task_data: bytes | str) -> dict[str, object]:
    if isinstance(task_data, bytes):
        task_data = task_data.decode("utf-8")
    return json.loads(task_data)


def push_task(redis_client, redis_key: str, task: dict[str, object]) -> int:
    return int(redis_client.sadd(redis_key, dump_task(task)))


def build_home_task(task: dict[str, object]) -> dict[str, str]:
    doctor_id = str(task.get("doctor_id") or task.get("customer_id") or "").strip()
    if not doctor_id:
        return {}
    return {"doctor_id": doctor_id}


def is_doctor_home_done(redis_client, doctor_id: str) -> bool:
    normalized_doctor_id = str(doctor_id).strip()
    if not normalized_doctor_id:
        return False
    return bool(redis_client.sismember(REDIS_KEYS["doctor_home_done"], normalized_doctor_id))


def mark_doctor_home_done(redis_client, doctor_id: str) -> int:
    normalized_doctor_id = str(doctor_id).strip()
    if not normalized_doctor_id:
        return 0
    return int(redis_client.sadd(REDIS_KEYS["doctor_home_done"], normalized_doctor_id))


def push_doctor_task(redis_client, task: dict[str, object]) -> dict[str, int]:
    detail_count = push_task(redis_client, REDIS_KEYS["doctor_info_url"], task)
    home_task = build_home_task(task)
    doctor_id = home_task.get("doctor_id", "")
    home_count = 0

    if doctor_id and not is_doctor_home_done(redis_client, doctor_id):
        home_count = push_task(redis_client, REDIS_KEYS["doctor_home_task"], home_task)

    return {
        "doctor_info_url": detail_count,
        "doctor_home_task": home_count,
    }


def get_proxy() -> str:
    return f"http://{ABUYUN_PROXY_HOST}:{ABUYUN_PROXY_PORT}"


def get_proxy_auth_header() -> str:
    credentials = f"{ABUYUN_PROXY_USER}:{ABUYUN_PROXY_PASS}".encode("utf-8")
    encoded_credentials = base64.b64encode(credentials).decode("ascii")
    return f"Basic {encoded_credentials}"


def build_get_url(url: str, params: dict[str, object]) -> str:
    return f"{url}?{urlencode(params, doseq=True)}"
