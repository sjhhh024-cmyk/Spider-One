from runtime.app.shared.profile_config import (
    CrawlerProfile,
    MongoDBProfile,
    ProjectProfile,
    ProxyProfile,
    RedisProfile,
    RuntimeProfile,
    WorkerProfile,
)
from runtime.app.shared.redis_lock import RedisLockFactory
from runtime.app.shared.redis_queue import RedisQueueAdapter
from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_status import TaskStatus
from runtime.app.shared.task_types import TaskType


def build_profile() -> CrawlerProfile:
    return CrawlerProfile(
        project=ProjectProfile(
            name="doctor_mingyihui",
            site="mingyihui",
            entity_type="doctor",
        ),
        redis=RedisProfile(host="127.0.0.1", port=6379, db=3, password="redis-secret"),
        mongodb=MongoDBProfile(
            host="127.0.0.1",
            port=27017,
            database="crawler_platform",
            collection="doctor_profiles",
        ),
        proxy=ProxyProfile(enabled=False),
        runtime=RuntimeProfile(concurrency=8, timeout_seconds=15, max_retries=3),
        workers=WorkerProfile(http=True, browser=True, scrapy=False, reverse=False),
    )


def build_task() -> CrawlTask:
    return CrawlTask(
        task_id="task-redis-001",
        job_id="job-redis-001",
        project_code="doctor_mingyihui",
        site_code="mingyihui",
        task_type=TaskType.DETAIL_FETCH,
        status=TaskStatus.QUEUED,
        payload={"url": "https://example.com/doctor/1"},
    )


def test_queue_adapter_builds_lightweight_message_and_queue_name() -> None:
    adapter = RedisQueueAdapter(build_profile())
    message = adapter.build_task_message(build_task())

    assert adapter.build_queue_name(TaskType.DETAIL_FETCH) == "doctor_mingyihui:detail_fetch"
    assert message.queue_name == "doctor_mingyihui:detail_fetch"
    assert message.body["task_id"] == "task-redis-001"
    assert message.body["task_type"] == "detail_fetch"
    assert "payload" not in message.body
    assert adapter.redis_url == "redis://:redis-secret@127.0.0.1:6379/3"


def test_lock_factory_uses_project_and_site_namespaces() -> None:
    lock_factory = RedisLockFactory(build_profile())

    assert (
        lock_factory.task_lock_key("task-redis-001")
        == "lock:doctor_mingyihui:mingyihui:task:task-redis-001"
    )
    assert (
        lock_factory.rate_limit_key("detail_fetch")
        == "rate:doctor_mingyihui:mingyihui:detail_fetch"
    )
