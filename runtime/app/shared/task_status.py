from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_RETRY = "waiting_retry"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_STATUS_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {
        TaskStatus.RUNNING,
        TaskStatus.WAITING_RETRY,
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.RUNNING: {
        TaskStatus.DONE,
        TaskStatus.WAITING_RETRY,
        TaskStatus.BLOCKED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_RETRY: {
        TaskStatus.QUEUED,
        TaskStatus.BLOCKED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.BLOCKED: {
        TaskStatus.QUEUED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


def can_transition(current_status: TaskStatus, next_status: TaskStatus) -> bool:
    return next_status in ALLOWED_STATUS_TRANSITIONS[current_status]


def ensure_transition(current_status: TaskStatus, next_status: TaskStatus) -> None:
    if can_transition(current_status, next_status):
        return

    raise ValueError(
        f"invalid task status transition: {current_status.value} -> {next_status.value}"
    )
