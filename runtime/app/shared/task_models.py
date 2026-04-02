from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.app.shared.task_status import TaskStatus
from runtime.app.shared.task_types import TaskType


@dataclass(slots=True)
class CrawlTask:
    task_id: str
    job_id: str
    project_code: str
    site_code: str
    task_type: TaskType
    status: TaskStatus
    payload: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None
