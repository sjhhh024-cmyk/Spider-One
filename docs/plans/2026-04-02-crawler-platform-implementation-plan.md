# Crawler Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a runtime platform plus project-package contract for an AI-driven crawling system that uses Redis for runtime scheduling, SQLite for project-level task state, and MySQL for final business data only.

**Architecture:** The runtime provides shared orchestration, queueing, validation, and worker interfaces. Each project package contains site-specific collectors, parsers, validators, exporters, and a local SQLite task ledger so it can run both under the platform and as a standalone package.

**Tech Stack:** Python 3.12, Redis, SQLite, MySQL, httpx, Playwright, optional Scrapy, pytest, ruff.

---

### Task 1: Scaffold the runtime workspace

**Files:**
- Create: `runtime/pyproject.toml`
- Create: `runtime/app/__init__.py`
- Create: `runtime/app/shared/__init__.py`
- Create: `runtime/tests/__init__.py`

**Step 1: Write the failing test**

Create `runtime/tests/test_imports.py` with import checks for `runtime.app`.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_imports.py -q`
Expected: FAIL because the package files do not exist yet.

**Step 3: Write minimal implementation**

Create the package scaffolding and minimal `pyproject.toml` so the imports resolve.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_imports.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime
git commit -m "feat: scaffold crawler runtime workspace"
```

### Task 2: Define the domain models and task state machine

**Files:**
- Create: `runtime/app/shared/task_types.py`
- Create: `runtime/app/shared/task_models.py`
- Create: `runtime/app/shared/task_status.py`
- Test: `runtime/tests/test_task_state_machine.py`

**Step 1: Write the failing test**

Create tests that verify allowed transitions for `pending`, `queued`, `running`, `waiting_retry`, `blocked`, `done`, `failed`, and `cancelled`.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_task_state_machine.py -q`
Expected: FAIL with missing modules or undefined transition logic.

**Step 3: Write minimal implementation**

Add typed enums and dataclasses or typed models for task payloads and transition rules.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_task_state_machine.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/app/shared runtime/tests/test_task_state_machine.py
git commit -m "feat: add task domain models and state machine"
```

### Task 3: Implement the project SQLite ledger

**Files:**
- Create: `runtime/app/shared/sqlite_ledger.py`
- Create: `runtime/app/shared/sqlite_schema.sql`
- Test: `runtime/tests/test_sqlite_ledger.py`

**Step 1: Write the failing test**

Create tests that insert a job, create child tasks, update status, and recover unfinished tasks.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_sqlite_ledger.py -q`
Expected: FAIL because the ledger does not exist.

**Step 3: Write minimal implementation**

Implement schema initialization, task CRUD, checkpoint updates, attempt logging, and unfinished-task recovery.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_sqlite_ledger.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/app/shared/sqlite_ledger.py runtime/app/shared/sqlite_schema.sql runtime/tests/test_sqlite_ledger.py
git commit -m "feat: add sqlite task ledger"
```

### Task 4: Implement Redis queue adapters

**Files:**
- Create: `runtime/app/shared/redis_queue.py`
- Create: `runtime/app/shared/redis_lock.py`
- Test: `runtime/tests/test_queue_message_shape.py`

**Step 1: Write the failing test**

Create tests that validate the queue message envelope and ensure only lightweight task references are enqueued.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_queue_message_shape.py -q`
Expected: FAIL because the adapters do not exist.

**Step 3: Write minimal implementation**

Implement lightweight message serialization, delayed retry payloads, and lock-key helpers.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_queue_message_shape.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/app/shared/redis_queue.py runtime/app/shared/redis_lock.py runtime/tests/test_queue_message_shape.py
git commit -m "feat: add redis queue adapters"
```

### Task 5: Build the dispatcher and scheduler

**Files:**
- Create: `runtime/app/dispatcher/__init__.py`
- Create: `runtime/app/dispatcher/dispatch_service.py`
- Create: `runtime/app/scheduler/__init__.py`
- Create: `runtime/app/scheduler/scheduler_service.py`
- Test: `runtime/tests/test_dispatch_flow.py`

**Step 1: Write the failing test**

Create tests that turn a high-level project request into queued tasks while also persisting them in the SQLite ledger.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_dispatch_flow.py -q`
Expected: FAIL because the dispatch and scheduler services do not exist.

**Step 3: Write minimal implementation**

Implement task creation, batching, queue handoff, and recovery-aware scheduling.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_dispatch_flow.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/app/dispatcher runtime/app/scheduler runtime/tests/test_dispatch_flow.py
git commit -m "feat: add dispatcher and scheduler services"
```

### Task 6: Add worker contracts and the HTTP worker

**Files:**
- Create: `runtime/app/workers/__init__.py`
- Create: `runtime/app/workers/base.py`
- Create: `runtime/app/workers/http_worker.py`
- Test: `runtime/tests/test_http_worker_contract.py`

**Step 1: Write the failing test**

Create tests for worker input/output contracts, explicit result statuses, and error propagation.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_http_worker_contract.py -q`
Expected: FAIL because the worker base and HTTP worker are missing.

**Step 3: Write minimal implementation**

Implement a worker base protocol and a minimal HTTP worker that can return normalized fetch results.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_http_worker_contract.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/app/workers runtime/tests/test_http_worker_contract.py
git commit -m "feat: add worker base and http worker"
```

### Task 7: Add the browser worker

**Files:**
- Create: `runtime/app/workers/browser_worker.py`
- Test: `runtime/tests/test_browser_worker_contract.py`

**Step 1: Write the failing test**

Create tests that validate the browser worker contract for recon results, cookies, and discovered route metadata.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_browser_worker_contract.py -q`
Expected: FAIL because the browser worker is missing.

**Step 3: Write minimal implementation**

Implement a minimal browser worker wrapper with typed recon output and no project-specific parsing.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_browser_worker_contract.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/app/workers/browser_worker.py runtime/tests/test_browser_worker_contract.py
git commit -m "feat: add browser worker"
```

### Task 8: Implement validators and exporters

**Files:**
- Create: `runtime/app/validator/__init__.py`
- Create: `runtime/app/validator/record_validator.py`
- Create: `runtime/app/validator/pagination_validator.py`
- Create: `runtime/app/shared/export_jsonl.py`
- Create: `runtime/app/shared/export_csv.py`
- Test: `runtime/tests/test_record_validator.py`

**Step 1: Write the failing test**

Create tests for required fields, non-empty fields, duplicate detection, and simple pagination anomalies.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_record_validator.py -q`
Expected: FAIL because the validators and exporters do not exist.

**Step 3: Write minimal implementation**

Implement shared validators and exporters that project packages can reuse.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_record_validator.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/app/validator runtime/app/shared/export_jsonl.py runtime/app/shared/export_csv.py runtime/tests/test_record_validator.py
git commit -m "feat: add shared validators and exporters"
```

### Task 9: Scaffold a standalone project package

**Files:**
- Create: `projects/example-doctor-project/pyproject.toml`
- Create: `projects/example-doctor-project/project.yaml`
- Create: `projects/example-doctor-project/src/example_doctor_project/__init__.py`
- Create: `projects/example-doctor-project/src/example_doctor_project/main.py`
- Create: `projects/example-doctor-project/src/example_doctor_project/cli.py`
- Create: `projects/example-doctor-project/src/example_doctor_project/config/settings.py`
- Create: `projects/example-doctor-project/src/example_doctor_project/profiles/site_profile.yaml`
- Create: `projects/example-doctor-project/src/example_doctor_project/collectors/list_collector.py`
- Create: `projects/example-doctor-project/src/example_doctor_project/parsers/list_parser.py`
- Create: `projects/example-doctor-project/src/example_doctor_project/pipelines/write_mysql.py`
- Create: `projects/example-doctor-project/state/.gitkeep`
- Create: `projects/example-doctor-project/artifacts/.gitkeep`
- Create: `projects/example-doctor-project/outputs/.gitkeep`
- Create: `projects/example-doctor-project/exports/.gitkeep`
- Create: `projects/example-doctor-project/logs/.gitkeep`
- Test: `projects/example-doctor-project/tests/test_cli_entry.py`

**Step 1: Write the failing test**

Create a test that checks the project package exposes `run`, `validate`, and `export` entry points.

**Step 2: Run test to verify it fails**

Run: `pytest projects/example-doctor-project/tests/test_cli_entry.py -q`
Expected: FAIL because the project package does not exist.

**Step 3: Write minimal implementation**

Scaffold the project package so it can run standalone while depending only on runtime contracts.

**Step 4: Run test to verify it passes**

Run: `pytest projects/example-doctor-project/tests/test_cli_entry.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add projects/example-doctor-project
git commit -m "feat: scaffold standalone example project package"
```

### Task 10: Add MySQL result writing and integration verification

**Files:**
- Modify: `projects/example-doctor-project/src/example_doctor_project/pipelines/write_mysql.py`
- Create: `runtime/tests/test_mysql_result_writer.py`
- Create: `projects/example-doctor-project/tests/test_project_flow.py`

**Step 1: Write the failing test**

Create tests that validate only final business records are written through the result writer, not task-state records.

**Step 2: Run test to verify it fails**

Run: `pytest runtime/tests/test_mysql_result_writer.py projects/example-doctor-project/tests/test_project_flow.py -q`
Expected: FAIL because MySQL result writing and project flow are not implemented.

**Step 3: Write minimal implementation**

Implement final-result persistence and a narrow end-to-end project flow using the runtime contracts.

**Step 4: Run test to verify it passes**

Run: `pytest runtime/tests/test_mysql_result_writer.py projects/example-doctor-project/tests/test_project_flow.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add runtime/tests/test_mysql_result_writer.py projects/example-doctor-project/tests/test_project_flow.py projects/example-doctor-project/src/example_doctor_project/pipelines/write_mysql.py
git commit -m "feat: add mysql result writer and project flow"
```
