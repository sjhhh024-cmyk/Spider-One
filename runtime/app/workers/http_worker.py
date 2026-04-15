from __future__ import annotations

from typing import Any, Callable

from runtime.app.shared.profile_config import CrawlerProfile
from runtime.app.shared.task_models import CrawlTask
from runtime.app.workers.base import WorkerExecutionError, WorkerOutcome, WorkerResult


FetchCallable = Callable[[str, dict[str, object]], dict[str, object]]


class HttpWorker:
    def __init__(self, fetcher: FetchCallable) -> None:
        self._fetcher = fetcher

    def run(self, task: CrawlTask, profile: CrawlerProfile) -> WorkerResult:
        url = task.payload.get("url")
        if not isinstance(url, str) or url.strip() == "":
            raise WorkerExecutionError(f"http worker failed for {task.task_id}: missing url")

        request_context = {
            "timeout_seconds": profile.runtime.timeout_seconds,
            "proxy_enabled": profile.proxy.enabled,
            "method": task.payload.get("method", "GET"),
        }

        try:
            fetch_result = self._fetcher(url, request_context)
        except Exception as exc:  # noqa: BLE001
            raise WorkerExecutionError(
                f"http worker failed for {task.task_id}: {exc}"
            ) from exc

        return WorkerResult(
            task_id=task.task_id,
            worker_name="http",
            outcome=WorkerOutcome.SUCCESS,
            payload=dict(fetch_result),
        )
