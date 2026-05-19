"""doctor_wygk 的轻量工具。"""

from __future__ import annotations

import base64
import json
import os
from urllib.parse import urlencode


DOCTOR_COLLECTION_NAME = "doctor_wygk"
HOSPITAL_COLLECTION_NAME = "hospital_wygk"
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


def normalize_detail_task_fields(task: dict[str, object]) -> dict[str, object]:
    doctor_id = str(task.get("doctor_id") or task.get("customer_id") or "").strip()
    if not doctor_id:
        return {}

    detail_task: dict[str, object] = {
        "doctor_id": doctor_id,
    }

    doctor_name = str(task.get("doctor_name") or task.get("fullName") or "").strip()
    if doctor_name:
        detail_task["doctor_name"] = doctor_name

    doctor_title = str(
        task.get("doctor_title")
        or task.get("medical_title")
        or task.get("medicalTitle")
        or task.get("customerTitle")
        or ""
    ).strip()
    if doctor_title:
        detail_task["doctor_title"] = doctor_title

    hospital_name = str(task.get("hospital_name") or task.get("company") or "").strip()
    if hospital_name:
        detail_task["hospital_name"] = hospital_name

    dept_name = str(task.get("dept_name") or task.get("department_name") or "").strip()
    if dept_name:
        detail_task["dept_name"] = dept_name

    doctor_avatar_url = str(
        task.get("doctor_avatar_url")
        or task.get("logoUrl")
        or task.get("headUrl")
        or task.get("customerLogo")
        or ""
    ).strip()
    if doctor_avatar_url:
        detail_task["doctor_avatar_url"] = doctor_avatar_url

    visit_site_id = task.get("visit_site_id")
    if str(visit_site_id or "").strip():
        detail_task["visit_site_id"] = visit_site_id

    return detail_task


def build_detail_task(task: dict[str, object]) -> dict[str, object]:
    detail_task = normalize_detail_task_fields(task)
    if not str(detail_task.get("dept_name") or "").strip():
        return {}
    return detail_task


def dedupe_detail_tasks(tasks: list[dict[str, object]]) -> list[dict[str, object]]:
    merged_by_doctor_id: dict[str, dict[str, object]] = {}

    for raw_task in tasks:
        normalized_task = normalize_detail_task_fields(raw_task)
        doctor_id = str(normalized_task.get("doctor_id") or "").strip()
        if not doctor_id:
            continue

        existing_task = merged_by_doctor_id.get(doctor_id)
        if existing_task is None:
            merged_by_doctor_id[doctor_id] = normalized_task
            continue

        for field_name, field_value in normalized_task.items():
            if field_name == "doctor_id":
                continue
            if str(existing_task.get(field_name) or "").strip():
                continue
            if not str(field_value or "").strip():
                continue
            existing_task[field_name] = field_value

    deduped_tasks: list[dict[str, object]] = []
    for merged_task in merged_by_doctor_id.values():
        detail_task = build_detail_task(merged_task)
        if detail_task:
            deduped_tasks.append(detail_task)

    return deduped_tasks


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
    detail_task = build_detail_task(task)
    detail_count = 0
    if detail_task:
        detail_count = push_task(redis_client, REDIS_KEYS["doctor_info_url"], detail_task)
    home_task = build_home_task(task)
    doctor_id = home_task.get("doctor_id", "")
    home_count = 0

    if detail_task and doctor_id and not is_doctor_home_done(redis_client, doctor_id):
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
