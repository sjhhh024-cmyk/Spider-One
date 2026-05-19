"""Redis 请求入队辅助函数。"""

from __future__ import annotations

import json


def build_redis_request_data(
    url: str,
    *,
    method: str | None = None,
    meta: dict | None = None,
    formdata: dict | None = None,
) -> str:
    payload: dict[str, object] = {"url": url}
    if method:
        payload["method"] = str(method).upper()
    if meta:
        payload["meta"] = meta
    if formdata:
        payload.update(formdata)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def push_redis_request(
    redis_client,
    redis_key: str,
    url: str,
    *,
    method: str | None = None,
    meta: dict | None = None,
    formdata: dict | None = None,
) -> int:
    return int(
        redis_client.sadd(
            redis_key,
            build_redis_request_data(url, method=method, meta=meta, formdata=formdata),
        )
    )
