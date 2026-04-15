# Test Checklist

## Goal

Use this checklist before claiming the crawl works. A collector is not done just because it returns data once.

## 1. Smoke Test

- Confirm one sample request or page returns the expected entity type.
- Confirm at least one output record contains the requested core fields.
- Save a raw sample response or page reference for debugging.

## 2. Pagination Test

- Verify page 1 and page 2 are different.
- Confirm the next-page parameter or cursor is documented.
- Check the stopping rule: no next page, empty payload, exhausted cursor, or explicit cap.
- Spot-check duplicates across adjacent pages.

## 3. Search and Filter Test

- Change one keyword or one filter at a time.
- Confirm the response actually changes with that parameter.
- Test at least one empty-result or edge-case query.
- Record parameter meaning for keyword, city, hospital, department, or sort fields.

## 4. Sequential Collection Test

- If using list-to-detail expansion, verify detail URLs or IDs come from the list reliably.
- Confirm failed detail items are logged for replay.
- Check that detail fields are merged into the correct parent record.

## 5. Data Quality Test

- Verify required fields exist.
- Verify fields expected to be non-empty are not blank.
- Verify uniqueness by canonical URL, entity ID, or other stable key.
- Check that the record count is plausible for the sampled scope.

## 6. Anti-Bot and Stability Test

- Distinguish true empty results from blocked or degraded responses.
- Watch for repeated payloads, hidden redirects, missing cookies, or stale tokens.
- If a signed request is involved, confirm the signature remains valid across multiple requests.

## 7. Delivery Test

- Confirm the output format matches the current task brief.
- Include coverage notes: which pages, filters, cities, or departments were included.
- Include known gaps and failed IDs or URLs when coverage is partial.
- Confirm the console logs are readable by a human, not just by the program.
- Confirm the console logs show page progress, request target, raw count, deduped count, and write result.
- Confirm the console logs print the actual write fields for at least one sample record, one field per line.
- If the project has staged spiders or a single start entry, confirm one stage can finish and hand off to the next instead of hanging idle forever.

## 8. Runtime Readiness Test

- If Redis is behind an SSH tunnel, confirm the start script or operator steps make the tunnel explicit.
- Confirm the main entry checks key dependencies early when possible, such as Redis reachability before opening a distributed crawl.
- On Windows, confirm `scrapy.cfg` and other bootstrap config files do not contain encoding pitfalls that stop Scrapy before crawling starts.

## Validator Script

Use the bundled validator for machine checks.

```powershell
py scripts/validate_records.py --input output.jsonl --min-records 10 --require source_url --require task_fields.name --non-empty task_fields.name --unique-by source_url
```

Useful variants:

```powershell
py scripts/validate_records.py --input output.json --min-records 1
py scripts/validate_records.py --input output.jsonl --expect-entity-type doctor --unique-by source_url
py scripts/validate_records.py --input output.jsonl --require task_fields.hospital --non-empty task_fields.hospital
```

Do not stop at the script. Keep at least one manual sample inspection in the loop.
