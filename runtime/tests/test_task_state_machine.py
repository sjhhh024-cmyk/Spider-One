import pytest

from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_status import TaskStatus, ensure_transition
from runtime.app.shared.task_types import TaskType


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        (TaskStatus.PENDING, TaskStatus.QUEUED),
        (TaskStatus.PENDING, TaskStatus.CANCELLED),
        (TaskStatus.QUEUED, TaskStatus.RUNNING),
        (TaskStatus.QUEUED, TaskStatus.WAITING_RETRY),
        (TaskStatus.RUNNING, TaskStatus.DONE),
        (TaskStatus.RUNNING, TaskStatus.WAITING_RETRY),
        (TaskStatus.RUNNING, TaskStatus.BLOCKED),
        (TaskStatus.RUNNING, TaskStatus.FAILED),
        (TaskStatus.WAITING_RETRY, TaskStatus.QUEUED),
        (TaskStatus.WAITING_RETRY, TaskStatus.FAILED),
        (TaskStatus.BLOCKED, TaskStatus.QUEUED),
        (TaskStatus.BLOCKED, TaskStatus.CANCELLED),
    ],
)
def test_allowed_status_transitions(
    current_status: TaskStatus,
    next_status: TaskStatus,
) -> None:
    ensure_transition(current_status, next_status)


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        (TaskStatus.DONE, TaskStatus.RUNNING),
        (TaskStatus.FAILED, TaskStatus.QUEUED),
        (TaskStatus.CANCELLED, TaskStatus.PENDING),
        (TaskStatus.PENDING, TaskStatus.DONE),
        (TaskStatus.QUEUED, TaskStatus.DONE),
        (TaskStatus.BLOCKED, TaskStatus.DONE),
    ],
)
def test_invalid_status_transitions_raise_value_error(
    current_status: TaskStatus,
    next_status: TaskStatus,
) -> None:
    with pytest.raises(ValueError):
        ensure_transition(current_status, next_status)


def test_crawl_task_uses_typed_domain_fields() -> None:
    task = CrawlTask(
        task_id="task-001",
        job_id="job-001",
        project_code="example-project",
        site_code="mingyihui",
        task_type=TaskType.DETAIL_FETCH,
        status=TaskStatus.PENDING,
        payload={"page": 1, "city": "shanghai"},
    )

    assert task.task_type is TaskType.DETAIL_FETCH
    assert task.status is TaskStatus.PENDING
    assert task.payload["page"] == 1
