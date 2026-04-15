from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from runtime.app.shared.profile_config import CrawlerProfile
from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_types import TaskType


@dataclass(frozen=True, slots=True)
class QueueMessage:
    queue_name: str
    body: dict[str, Any]


class QueueSink(Protocol):
    def push(self, message: QueueMessage) -> None:
        """Persist a queue message."""


class InMemoryQueueSink:
    def __init__(self) -> None:
        self.messages: list[QueueMessage] = []

    def push(self, message: QueueMessage) -> None:
        self.messages.append(message)


class RedisQueueAdapter:
    def __init__(self, profile: CrawlerProfile, queue_sink: QueueSink | None = None) -> None:
        self._profile = profile
        self._queue_sink = queue_sink

    @property
    def redis_url(self) -> str:
        redis_profile = self._profile.redis
        if redis_profile.password:
            return (
                f"redis://:{redis_profile.password}@"
                f"{redis_profile.host}:{redis_profile.port}/{redis_profile.db}"
            )
        return f"redis://{redis_profile.host}:{redis_profile.port}/{redis_profile.db}"

    def build_queue_name(self, task_type: TaskType) -> str:
        return f"{self._profile.project.name}:{task_type.value}"

    def build_retry_queue_name(self, task_type: TaskType) -> str:
        return f"{self._profile.project.name}:{task_type.value}:retry"

    def build_task_message(self, task: CrawlTask) -> QueueMessage:
        return QueueMessage(
            queue_name=self.build_queue_name(task.task_type),
            body={
                "task_id": task.task_id,
                "job_id": task.job_id,
                "project_code": task.project_code,
                "site_code": task.site_code,
                "task_type": task.task_type.value,
            },
        )

    def enqueue_task(self, task: CrawlTask) -> QueueMessage:
        message = self.build_task_message(task)
        if self._queue_sink is not None:
            self._queue_sink.push(message)
        return message
