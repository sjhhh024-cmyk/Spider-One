# Web Crawling Employee Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a skill that lets Codex behave like a task-oriented crawling employee: accept a natural-language website data collection assignment, discover the right extraction route, handle pagination/search/sequential collection, triage JS reverse work, and verify outputs before delivery.

**Architecture:** Keep the skill compact and workflow-first. Put the operating workflow in `SKILL.md`, keep reusable detailed guidance in three references, and include one generic validator script that works with dynamic record schemas. Doctor-information sites are the primary example domain, but the core workflow remains entity-agnostic.

**Tech Stack:** Markdown skill docs, Python 3.12 CLI helper, existing browser/network/JS-reverse tools available in the runtime.

---

### Task 1: Define the skill boundary

**Files:**
- Create: `docs/plans/2026-04-02-web-crawling-employee-design.md`
- Modify: `web-crawling-employee/SKILL.md`

**Step 1: Write the boundary in plain language**

Define the skill as a worker that accepts natural-language crawl tasks. Avoid freezing the schema around one doctor-site workflow.

**Step 2: Verify the boundary is operational**

Check that the design covers: recon, route selection, pagination, search, sequential collection, JS reverse triage, and verification.

### Task 2: Write the reusable guidance

**Files:**
- Create: `web-crawling-employee/references/task-playbook.md`
- Create: `web-crawling-employee/references/field-strategy.md`
- Create: `web-crawling-employee/references/test-checklist.md`

**Step 1: Capture the technical tree**

Document the crawl brief, route selection order, doctor-site patterns, and scaling rules.

**Step 2: Capture schema strategy**

Define stable provenance fields plus dynamic task-driven payload fields.

**Step 3: Capture verification rules**

Define smoke, pagination, search, sequential, data-quality, and delivery checks.

### Task 3: Add one deterministic helper

**Files:**
- Create: `web-crawling-employee/scripts/validate_records.py`

**Step 1: Support common crawl outputs**

Handle JSON arrays, JSONL, and JSON objects with `records`, `items`, or `data`.

**Step 2: Support task-driven validation**

Implement required field checks, non-empty checks, uniqueness checks, minimum count checks, and optional `entity_type` checks.

**Step 3: Run script-level verification**

Run `py web-crawling-employee/scripts/validate_records.py --help`, then run it on a tiny sample file to confirm pass/fail behavior.

### Task 4: Validate the skill package

**Files:**
- Modify: `web-crawling-employee/agents/openai.yaml` if needed

**Step 1: Run structural validation**

Run `py C:/Users/lenovo/.codex/skills/.system/skill-creator/scripts/quick_validate.py web-crawling-employee`

**Step 2: Note forward-test gap**

If subagent-based forward testing is unavailable in the current session, record that limitation rather than pretending the skill has been fully pressure-tested.
