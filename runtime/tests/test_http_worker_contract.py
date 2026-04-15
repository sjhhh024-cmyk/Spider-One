import pytest

from runtime.app.shared.profile_config import (
    CrawlerProfile,
    MongoDBProfile,
    ProjectProfile,
    ProxyProfile,
    RedisProfile,
    RuntimeProfile,
    WorkerProfile,
)
from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_status import TaskStatus
from runtime.app.shared.task_types import TaskType
from runtime.app.workers.base import WorkerExecutionError, WorkerOutcome
from runtime.app.workers.http_worker import HttpWorker


def build_profile() -> CrawlerProfile:
    return CrawlerProfile(
        project=ProjectProfile(
            name="doctor_mingyihui",
            site="mingyihui",
            entity_type="doctor",
        ),
        redis=RedisProfile(host="127.0.0.1", port=6379, db=0),
        mongodb=MongoDBProfile(
            host="127.0.0.1",
            port=27017,
            database="crawler_platform",
            collection="doctor_profiles",
        ),
        proxy=ProxyProfile(enabled=True, host="proxy.example.com", port=8080),
        runtime=RuntimeProfile(concurrency=6, timeout_seconds=25, max_retries=3),
        workers=WorkerProfile(http=True, browser=True, scrapy=False, reverse=False),
    )


def build_task() -> CrawlTask:
    return CrawlTask(
        task_id="task-http-001",
        job_id="job-http-001",
        project_code="doctor_mingyihui",
        site_code="mingyihui",
        task_type=TaskType.DETAIL_FETCH,
        status=TaskStatus.QUEUED,
        payload={"url": "https://example.com/doctor/1", "method": "GET"},
    )


def test_http_worker_returns_normalized_success_result() -> None:
    def fake_fetch(url: str, context: dict[str, object]) -> dict[str, object]:
        assert url == "https://example.com/doctor/1"
        assert context["timeout_seconds"] == 25
        assert context["proxy_enabled"] is True
        return {
            "status_code": 200,
            "url": url,
            "text": "<html>doctor</html>",
            "headers": {"content-type": "text/html"},
        }

    worker = HttpWorker(fetcher=fake_fetch)
    result = worker.run(build_task(), build_profile())

    assert result.worker_name == "http"
    assert result.outcome is WorkerOutcome.SUCCESS
    assert result.payload["status_code"] == 200
    assert result.payload["text"] == "<html>doctor</html>"


def test_http_worker_raises_worker_execution_error_on_fetch_failure() -> None:
    def broken_fetch(url: str, context: dict[str, object]) -> dict[str, object]:
        raise TimeoutError(f"timeout for {url}")

    worker = HttpWorker(fetcher=broken_fetch)

    with pytest.raises(WorkerExecutionError, match="task-http-001"):
        worker.run(build_task(), build_profile())
