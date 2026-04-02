# Task Playbook

## Purpose

Use this reference when the user gives a natural-language crawl assignment and the execution path is not yet clear. The aim is to turn vague goals into a bounded crawl brief, then choose the cheapest stable route.

## Internal Crawl Brief

Capture these items before scaling:

- `target_site`: domain or site group
- `entity_type`: doctor, hospital, department, institution, article, product, or other
- `requested_fields`: fields named by the user
- `scope`: city, department, keyword, page count, or other boundaries
- `expansion_mode`: list only, detail only, or list-to-detail fanout
- `delivery_format`: sample, JSON, JSONL, CSV-ready records, or code
- `stopping_rule`: page limit, no-next-page, empty results, or explicit cap
- `risk_notes`: login, anti-bot, signed params, captchas, or manual blockers

## Crawl Technical Tree

| Layer | Ask | Action | Output |
|---|---|---|---|
| Recon | What page types exist? | Map list, detail, search, filter, and profile pages | Page map |
| Data Source | Where does the real data come from? | Check network, HTML, script tags, hydration state, JSON-LD | Route candidate |
| Pagination | How does the next page work? | Capture page number, cursor, offset, or token behavior | Pagination rule |
| Search | Which parameters change the result set? | Compare request payloads across keywords and filters | Search mapping |
| Expansion | Is detail crawling required? | Trace list item to detail URL or entity ID | Fanout rule |
| Reverse Triage | Are key params generated? | Locate timestamp, nonce, sign, token, or encrypted payload logic | Reverse scope |
| Verification | How will failure be detected? | Define required fields, uniqueness key, and sample checks | Test brief |
| Delivery | What must the user receive? | Choose output file, coverage notes, and replay steps | Final package |

## Route Selection Order

1. Observed JSON or GraphQL response
2. Inline JSON in HTML or script tags
3. Stable DOM parsing
4. Browser-assisted discovery plus request replay
5. Browser-driven extraction
6. JS reverse engineering for the minimum necessary parameter generation

Move down this list only when the simpler route is insufficient.

## Common Route Playbooks

### 1. List Page to Detail Page

- Extract entity URL, entity ID, and any visible summary fields from the list page.
- Confirm whether the detail page adds unique information before crawling all details.
- Preserve both `listing_page` and `detail_page` provenance when flattening records.

### 2. Request Replay

- Capture the exact request URL, method, headers, cookies, and payload that matter.
- Diff two successful requests to identify page number, cursor, keyword, city, department, or doctor ID parameters.
- Replay one request outside the browser before building the full collector.

### 3. Search or Filter Endpoint

- Trigger one search change at a time.
- Record which request parameter maps to keyword, location, department, hospital, title, or sort order.
- Test at least one empty-result case so the stopping rule is not confused with a blocked response.

### 4. JS Reverse Triage

- Look for `sign`, `token`, `nonce`, `timestamp`, `cipher`, `encrypt`, or similar fields.
- First check whether the browser already exposes the final request body or headers.
- Reverse only the minimal algorithm needed to reproduce the request. Do not deobfuscate the whole app unless required.
- Keep the boundary clear: recon first, replay second, reverse last.

## Doctor-Information Site Patterns

Doctor information platforms often have these structures:

- City, department, or hospital portals that lead to doctor listing pages
- Doctor profile pages with hospital, department, title, specialty, profile, schedules, or booking links
- Search suggestion APIs keyed by keyword, city, hospital, or specialty
- SSR hydration blobs such as `__INITIAL_STATE__`, `__NEXT_DATA__`, JSON-LD, or embedded API payloads
- Separate appointment or schedule interfaces that should be treated as a secondary entity, not blindly merged

Useful doctor-site relationship hints:

- A doctor may appear on multiple list pages; dedupe by canonical profile URL or stable doctor ID.
- Hospital and department names can vary between list and detail pages; preserve raw text before normalizing.
- If a task asks only for doctor info, keep schedule or consultation slots in extension fields unless explicitly requested.

## Scaling Rules

- Prove the route with a small sample before bulk expansion.
- Keep a checkpoint or last-success cursor when the crawl is long.
- Retry transient failures, but do not silently swallow empty payloads that may indicate blocking.
- When page 2 equals page 1, stop and fix pagination logic before continuing.
- When detail requests fail often, store failed URLs or IDs for targeted replay instead of restarting the whole crawl.
