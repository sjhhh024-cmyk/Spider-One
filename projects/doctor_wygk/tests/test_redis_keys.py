from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_wygk.tools import (  # noqa: E402
    DOCTOR_COLLECTION_NAME,
    REDIS_KEYS,
    build_get_url,
    build_home_task,
    dump_task,
    load_task,
    push_doctor_task,
)


def test_redis_keys_split_main_chain_and_probe_chain() -> None:
    assert REDIS_KEYS == {
        "hospital_home_url": "doctor_wygk:hospital_home_url",
        "dept_task": "doctor_wygk:dept_task",
        "doctor_list_task": "doctor_wygk:doctor_list_task",
        "doctor_info_url": "doctor_wygk:doctor_info_url",
        "doctor_home_task": "doctor_wygk:doctor_home_task",
        "doctor_home_done": "doctor_wygk:doctor_home_done",
    }


def test_mongo_collection_name_uses_wygk_namespace() -> None:
    assert DOCTOR_COLLECTION_NAME == "doctor_wygk"


def test_task_dump_and_load_keep_compact_json_shape() -> None:
    task = {"doctor_id": "1450269515500", "dept_name": "脊柱外科"}

    dumped = dump_task(task)

    assert dumped == '{"doctor_id":"1450269515500","dept_name":"脊柱外科"}'
    assert load_task(dumped) == task


def test_build_get_url_keeps_query_params_in_one_place() -> None:
    assert build_get_url("https://example.com/api", {"doctorId": "1", "visitSiteId": 27}) == (
        "https://example.com/api?doctorId=1&visitSiteId=27"
    )


def test_build_home_task_only_keeps_doctor_id() -> None:
    assert build_home_task({"doctor_id": "1450269515500", "doctor_name": "张三"}) == {
        "doctor_id": "1450269515500"
    }


def test_push_doctor_task_writes_detail_and_home_queue_but_skips_done_home_doctor() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.storage: dict[str, set[str]] = {}

        def sadd(self, key: str, value: str) -> int:
            bucket = self.storage.setdefault(key, set())
            before = len(bucket)
            bucket.add(value)
            return int(len(bucket) > before)

        def sismember(self, key: str, value: str) -> bool:
            return value in self.storage.get(key, set())

    redis_client = FakeRedis()
    task = {"doctor_id": "1450269515500", "doctor_name": "张三", "company": "北京积水潭医院"}

    push_result = push_doctor_task(redis_client, task)
    redis_client.sadd(REDIS_KEYS["doctor_home_done"], "1450269515500")
    push_result_after_done = push_doctor_task(redis_client, task)

    assert push_result == {"doctor_info_url": 1, "doctor_home_task": 1}
    assert push_result_after_done == {"doctor_info_url": 0, "doctor_home_task": 0}
    assert redis_client.storage[REDIS_KEYS["doctor_info_url"]] == {
        '{"doctor_id":"1450269515500","doctor_name":"张三","company":"北京积水潭医院"}'
    }
    assert redis_client.storage[REDIS_KEYS["doctor_home_task"]] == {
        '{"doctor_id":"1450269515500"}'
    }
