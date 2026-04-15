from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from runtime.app.shared.profile_config import CrawlerProfile
from runtime.app.shared.redis_queue import RedisQueueAdapter
from runtime.app.shared.sqlite_ledger import SQLiteTaskLedger
from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_status import TaskStatus
from runtime.app.shared.task_types import TaskType


@dataclass(frozen=True, slots=True)
class DispatchRequest:
    request_text: str
    task_type: TaskType
    task_payloads: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class DispatchResult:
    job_id: str
    tasks: list[CrawlTask]


class DispatchService:
    def __init__(
        self,
        profile: CrawlerProfile,
        ledger: SQLiteTaskLedger,
        queue_adapter: RedisQueueAdapter,
    ) -> None:
        self._profile = profile
        self._ledger = ledger
        self._queue_adapter = queue_adapter

    def dispatch(self, request: DispatchRequest) -> DispatchResult:
        job_id = self._build_job_id()
        self._ledger.create_job(
            job_id=job_id,
            project_code=self._profile.project.name,
            site_code=self._profile.project.site,
            entity_type=self._profile.project.entity_type,
            request_text=request.request_text,
        )

        tasks: list[CrawlTask] = []
        for payload in request.task_payloads:
            task = CrawlTask(
                task_id=self._build_task_id(),
                job_id=job_id,
                project_code=self._profile.project.name,
                site_code=self._profile.project.site,
                task_type=request.task_type,
                status=TaskStatus.PENDING,
                payload=payload,
            )
            self._ledger.create_task(task)
            self._ledger.update_task_status(task.task_id, TaskStatus.QUEUED)
            queued_task = CrawlTask(
                task_id=task.task_id,
                job_id=task.job_id,
                project_code=task.project_code,
                site_code=task.site_code,
                task_type=task.task_type,
                status=TaskStatus.QUEUED,
                payload=task.payload,
                parent_task_id=task.parent_task_id,
            )
            self._queue_adapter.enqueue_task(queued_task)
            tasks.append(queued_task)

        return DispatchResult(job_id=job_id, tasks=tasks)

    def _build_job_id(self) -> str:
        return f"job-{uuid4().hex[:12]}"

    def _build_task_id(self) -> str:
        return f"task-{uuid4().hex[:12]}"
