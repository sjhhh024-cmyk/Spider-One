from __future__ import annotations

from runtime.app.shared.redis_queue import RedisQueueAdapter
from runtime.app.shared.sqlite_ledger import SQLiteTaskLedger
from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_status import TaskStatus


RECOVERABLE_STATUSES = {
    TaskStatus.PENDING,
    TaskStatus.QUEUED,
    TaskStatus.RUNNING,
    TaskStatus.WAITING_RETRY,
    TaskStatus.BLOCKED,
}


class SchedulerService:
    def __init__(self, ledger: SQLiteTaskLedger, queue_adapter: RedisQueueAdapter) -> None:
        self._ledger = ledger
        self._queue_adapter = queue_adapter

    def requeue_recoverable_tasks(self) -> list[str]:
        requeued_task_ids: list[str] = []

        for task in self._ledger.get_unfinished_tasks():
            if task.status not in RECOVERABLE_STATUSES:
                continue

            queued_task = self._ensure_task_is_queued(task)
            self._queue_adapter.enqueue_task(queued_task)
            requeued_task_ids.append(queued_task.task_id)

        return requeued_task_ids

    def _ensure_task_is_queued(self, task: CrawlTask) -> CrawlTask:
        if task.status is TaskStatus.RUNNING:
            self._ledger.update_task_status(task.task_id, TaskStatus.WAITING_RETRY)
            self._ledger.update_task_status(task.task_id, TaskStatus.QUEUED)
        elif task.status in {TaskStatus.PENDING, TaskStatus.WAITING_RETRY, TaskStatus.BLOCKED}:
            self._ledger.update_task_status(task.task_id, TaskStatus.QUEUED)

        return CrawlTask(
            task_id=task.task_id,
            job_id=task.job_id,
            project_code=task.project_code,
            site_code=task.site_code,
            task_type=task.task_type,
            status=TaskStatus.QUEUED,
            payload=task.payload,
            parent_task_id=task.parent_task_id,
        )
