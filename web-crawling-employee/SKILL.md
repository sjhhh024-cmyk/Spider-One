---
name: web-crawling-employee
description: Use when Codex is asked to independently complete a website data collection task from natural-language instructions, especially when it must inspect a new site, discover pages or APIs, handle pagination or search, perform sequential collection, decide between HTML parsing and request replay, triage JavaScript signing or obfuscation, and verify results before delivery.
---

# Web Crawling Employee

## Overview

Treat the request as delegated work, not as a narrow code-generation prompt. Turn a natural-language collection goal into a crawl brief, choose the cheapest reliable extraction route, verify with artifacts, and deliver both data and a reproducible method.

## Operating Rules

- Start from the user's goal, target site, scope, and success condition. Infer a working schema from the request instead of forcing a fixed field list.
- Prefer the least fragile route: observed JSON API > inline JSON data > stable HTML > browser automation > JS reverse engineering.
- Keep source traceability for every record. At minimum preserve `source_site`, `source_url`, and `crawl_time`.
- Expand only after a sample proves the route works. First get one page and one detail sample right, then scale.
- Treat doctor-information sites such as Mingyihui or Haoxinqing as first-class examples, but keep the workflow generic enough for hospitals, clinics, experts, institutions, or other structured entities.
- Do not bypass login, payment, or strong protection without explicit user approval.

## Workflow

1. Translate the natural-language task into an internal crawl brief.
Record the site, target entity, requested data, scope, stopping rule, delivery format, blockers, and any assumptions.

2. Recon the site before coding.
Identify entry pages, list/detail relationships, search surfaces, filters, pagination mechanics, embedded JSON, and network endpoints. Use [task-playbook.md](./references/task-playbook.md) to choose the investigation order.

3. Choose the collection route.
Prefer request replay when the data API is observable and stable. Fall back to DOM parsing when the page already contains the data. Use browser automation for discovery before using it for full extraction whenever possible. Escalate to JS reverse work only when required request parameters cannot be reproduced directly.

4. Implement the smallest reliable slice.
Prove the route with a small sample: one listing request, one pagination step, one search variation if relevant, and one detail expansion if details are required.

5. Verify before scaling.
Use [test-checklist.md](./references/test-checklist.md) and `scripts/validate_records.py`. Do not claim success from visual inspection alone.

6. Deliver the result and the reasoning trail.
Return the collected data, extraction scope, unresolved gaps, reproduction notes, and the exact endpoints or selectors that were used.

## Intake Checklist

Before implementation, answer these from the user's message or from quick recon:

- What site or set of sites is in scope?
- What entity is being collected right now?
- Which fields are explicitly requested, and which can remain optional?
- Is the task list-only, detail-only, or list-to-detail fanout?
- Does the task require pagination, search, filters, or ordering?
- What counts as done: sample output, complete export, or reproducible collector code?

## Route Selection Heuristics

- If network traffic reveals a clean JSON or GraphQL response, replay it first.
- If the HTML or script tags already contain the data, extract that before simulating the whole browser.
- If pagination depends on opaque cursors or tokens, capture them from the next-page request instead of guessing.
- If search results change with keyword, department, city, or hospital filters, document the parameter mapping before bulk collection.
- If request parameters are signed or encrypted, isolate the signing path and use JS reverse tooling only for the minimal required inputs.
- If the site is doctor-oriented, explicitly model doctor, hospital, department, and listing-page provenance as related entities even when the final output is flattened.

## Data Strategy

Use [field-strategy.md](./references/field-strategy.md) for schema decisions. The record shape is task-driven: requested fields come first, common provenance fields are always preserved, and task-specific or site-specific leftovers go into extension fields instead of being discarded.

## Verification Standard

Use [test-checklist.md](./references/test-checklist.md) on every task that involves pagination, search, list-to-detail expansion, or reverse-engineered requests. For machine checks, run:

```powershell
py scripts/validate_records.py --input <path> --min-records 1
```

Add `--require`, `--non-empty`, and `--unique-by` based on the current task brief.

## References

- [task-playbook.md](./references/task-playbook.md): task routing, technical tree, and doctor-site patterns
- [field-strategy.md](./references/field-strategy.md): dynamic schema rules and record-shape guidance
- [test-checklist.md](./references/test-checklist.md): verification checklist and validator usage
- [runtime-architecture.md](./references/runtime-architecture.md): distributed runtime architecture, data-layer boundaries, and project packaging rules

## Example Requests

- "Collect Shanghai psychiatry doctor data from Mingyihui. Start with name, hospital, department, title, specialty, and profile URL. Continue through pagination if available."
- "Use Haoxinqing to find Beijing mental-health related doctors. First determine whether the real data comes from an API, then give me a reproducible collection plan."
- "I only said I want doctor information from this site. You need to recon the pages, find the route, handle pagination, and return both samples and verification results."

Use this skill when the goal is to behave like a capable crawling employee: accept the assignment, discover the route, execute carefully, verify with evidence, and hand back usable results.
