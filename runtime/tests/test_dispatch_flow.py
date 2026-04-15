from pathlib import Path

from runtime.app.dispatcher.dispatch_service import DispatchRequest, DispatchService
from runtime.app.scheduler.scheduler_service import SchedulerService
from runtime.app.shared.profile_config import load_profile_config
from runtime.app.shared.redis_queue import InMemoryQueueSink, RedisQueueAdapter
from runtime.app.shared.sqlite_ledger import SQLiteTaskLedger
from runtime.app.shared.task_status import TaskStatus
from runtime.app.shared.task_types import TaskType


def write_profile(profile_path: Path) -> None:
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

mongodb:
  host: 127.0.0.1
  port: 27017
  database: crawler_platform
  collection: doctor_profiles

runtime:
  concurrency: 10
  timeout_seconds: 20
  max_retries: 3

workers:
  http: true
  browser: true
  scrapy: false
  reverse: false
""".strip(),
        encoding="utf-8",
    )


def test_dispatch_service_persists_and_queues_tasks(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yml"
    write_profile(profile_path)
    profile = load_profile_config(profile_path)

    ledger = SQLiteTaskLedger(tmp_path / "state" / "jobs.sqlite")
    ledger.initialize()

    queue_sink = InMemoryQueueSink()
    queue_adapter = RedisQueueAdapter(profile, queue_sink=queue_sink)
    dispatch_service = DispatchService(profile, ledger, queue_adapter)

    request = DispatchRequest(
        request_text="collect doctor detail pages",
        task_type=TaskType.DETAIL_FETCH,
        task_payloads=[
            {"url": "https://example.com/doctor/1"},
            {"url": "https://example.com/doctor/2"},
        ],
    )

    dispatch_result = dispatch_service.dispatch(request)
    unfinished_tasks = ledger.get_unfinished_tasks()

    assert dispatch_result.job_id.startswith("job-")
    assert len(dispatch_result.tasks) == 2
    assert [task.status for task in unfinished_tasks] == [TaskStatus.QUEUED, TaskStatus.QUEUED]
    assert len(queue_sink.messages) == 2
    assert queue_sink.messages[0].body["task_id"] == dispatch_result.tasks[0].task_id


def test_scheduler_requeues_recoverable_tasks(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yml"
    write_profile(profile_path)
    profile = load_profile_config(profile_path)

    ledger = SQLiteTaskLedger(tmp_path / "state" / "jobs.sqlite")
    ledger.initialize()

    queue_sink = InMemoryQueueSink()
    queue_adapter = RedisQueueAdapter(profile, queue_sink=queue_sink)
    dispatch_service = DispatchService(profile, ledger, queue_adapter)
    scheduler = SchedulerService(ledger, queue_adapter)

    dispatch_result = dispatch_service.dispatch(
        DispatchRequest(
            request_text="collect doctor detail pages",
            task_type=TaskType.DETAIL_FETCH,
            task_payloads=[{"url": "https://example.com/doctor/1"}],
        )
    )

    task = dispatch_result.tasks[0]
    ledger.update_task_status(task.task_id, TaskStatus.RUNNING)

    queue_sink.messages.clear()
    requeued_task_ids = scheduler.requeue_recoverable_tasks()
    unfinished_tasks = ledger.get_unfinished_tasks()

    assert requeued_task_ids == [task.task_id]
    assert unfinished_tasks[0].status is TaskStatus.QUEUED
    assert queue_sink.messages[0].body["task_id"] == task.task_id
