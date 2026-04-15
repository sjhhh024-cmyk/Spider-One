from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from runtime.app.shared.task_models import CrawlTask


class WorkerOutcome(StrEnum):
    SUCCESS = "success"
    RETRY = "retry"
    BLOCKED = "blocked"
    FAILED = "failed"


class WorkerExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class WorkerResult:
    task_id: str
    worker_name: str
    outcome: WorkerOutcome
    payload: dict[str, Any] = field(default_factory=dict)
