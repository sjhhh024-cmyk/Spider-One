CREATE TABLE IF NOT EXISTS crawl_job (
    job_id TEXT PRIMARY KEY,
    project_code TEXT NOT NULL,
    site_code TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    request_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_task (
    task_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    parent_task_id TEXT,
    project_code TEXT NOT NULL,
    site_code TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES crawl_job(job_id)
);

CREATE TABLE IF NOT EXISTS crawl_task_attempt (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    worker_type TEXT NOT NULL,
    outcome_status TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES crawl_task(task_id)
);

CREATE TABLE IF NOT EXISTS crawl_task_checkpoint (
    task_id TEXT NOT NULL,
    checkpoint_key TEXT NOT NULL,
    checkpoint_value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(task_id, checkpoint_key),
    FOREIGN KEY(task_id) REFERENCES crawl_task(task_id)
);
