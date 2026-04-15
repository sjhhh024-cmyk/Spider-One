from __future__ import annotations

from runtime.app.shared.profile_config import CrawlerProfile


class RedisLockFactory:
    def __init__(self, profile: CrawlerProfile) -> None:
        self._project_name = profile.project.name
        self._site_name = profile.project.site

    def task_lock_key(self, task_id: str) -> str:
        return f"lock:{self._project_name}:{self._site_name}:task:{task_id}"

    def rate_limit_key(self, worker_scope: str) -> str:
        return f"rate:{self._project_name}:{self._site_name}:{worker_scope}"
