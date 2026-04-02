# Field Strategy

## Principle

Do not freeze the schema around one site or one entity type. The user can change the requested fields from task to task, so the record shape must support both stable provenance and dynamic payloads.

## Recommended Record Shape

```json
{
  "entity_type": "doctor",
  "source_site": "example.com",
  "source_url": "https://example.com/profile/123",
  "crawl_time": "2026-04-02T10:00:00+08:00",
  "task_fields": {
    "name": "Example Doctor",
    "hospital": "Example Hospital",
    "department": "Psychiatry"
  },
  "extra_fields": {
    "title": "Chief Physician",
    "booking_url": "https://example.com/order/123"
  },
  "raw_context": {
    "listing_page": "https://example.com/doctors?page=1",
    "entity_id": "123"
  }
}
```

## Field Layers

- `entity_type`: what this record represents right now
- `source_site`: domain or source label
- `source_url`: canonical page or endpoint for this record
- `crawl_time`: acquisition time
- `task_fields`: fields the user explicitly asked for, or fields required to make the record useful
- `extra_fields`: useful but task-specific leftovers, secondary attributes, or low-confidence enrichments
- `raw_context`: IDs, page numbers, list-page URLs, ranking positions, raw labels, and debugging context

## Rules

- Put user-requested fields into `task_fields` first.
- Use `snake_case` for normalized field names.
- Preserve site-native labels in `raw_context` when normalization may lose meaning.
- Keep relationship hints such as `hospital`, `department`, `institution_id`, or `doctor_id` if they help dedupe or join downstream.
- When a field is present but low confidence, keep it in `extra_fields` with enough context to revisit it later.
- Avoid dropping data just because it does not fit the current flat schema.

## Common Optional Fields

Use these as references, not as mandatory schema:

- `name`
- `hospital`
- `department`
- `title`
- `specialty`
- `city`
- `profile`
- `booking_url`
- `listing_page`
- `doctor_id`
- `rank`
- `comment_count`
- `consultation_mode`

## Multi-Entity Tasks

If a task spans different entities, keep them separate by `entity_type` instead of forcing them into one flattened shape. Example: doctor records and schedule records can be exported as separate arrays or separate JSONL files linked by `doctor_id` or `source_url`.

## Doctor-Site Notes

For doctor information tasks, default to preserving these relationships even if the final export is flattened:

- doctor to hospital
- doctor to department
- doctor to city
- doctor to listing source

This makes later dedupe, aggregation, and audit much easier.
