from pathlib import Path

from runtime.app.shared.sqlite_ledger import SQLiteTaskLedger
from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_status import TaskStatus
from runtime.app.shared.task_types import TaskType


def build_task(task_id: str, status: TaskStatus) -> CrawlTask:
    return CrawlTask(
        task_id=task_id,
        job_id="job-001",
        project_code="doctor-collection",
        site_code="mingyihui",
        task_type=TaskType.DETAIL_FETCH,
        status=status,
        payload={"page": 1, "detail_url": f"https://example.com/{task_id}"},
        parent_task_id="parent-001",
    )


def test_sqlite_ledger_tracks_jobs_tasks_and_recovery(tmp_path: Path) -> None:
    ledger = SQLiteTaskLedger(tmp_path / "jobs.sqlite")
    ledger.initialize()

    ledger.create_job(
        job_id="job-001",
        project_code="doctor-collection",
        site_code="mingyihui",
        entity_type="doctor",
        request_text="collect doctor details",
    )

    pending_task = build_task("task-001", TaskStatus.PENDING)
    done_task = build_task("task-002", TaskStatus.QUEUED)

    ledger.create_task(pending_task)
    ledger.create_task(done_task)
    ledger.update_task_status("task-001", TaskStatus.QUEUED)
    ledger.update_task_status("task-002", TaskStatus.RUNNING)
    ledger.update_task_status("task-002", TaskStatus.DONE)
    ledger.upsert_checkpoint("task-001", "page_cursor", "cursor-002")
    ledger.log_attempt(
        task_id="task-001",
        worker_type="http",
        outcome_status="success",
        error_message=None,
    )

    unfinished_tasks = ledger.get_unfinished_tasks()
    checkpoints = ledger.get_task_checkpoints("task-001")
    attempts = ledger.get_attempts("task-001")

    assert [task.task_id for task in unfinished_tasks] == ["task-001"]
    assert unfinished_tasks[0].status is TaskStatus.QUEUED
    assert checkpoints["page_cursor"] == "cursor-002"
    assert attempts[0]["worker_type"] == "http"
    assert attempts[0]["outcome_status"] == "success"
