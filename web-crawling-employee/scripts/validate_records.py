#!/usr/bin/env python3
"""Validate JSON or JSONL crawl outputs with lightweight schema checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate crawl result files.")
    parser.add_argument("--input", required=True, help="Path to a JSON or JSONL file.")
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        help="Field path that must exist. Repeatable, e.g. task_fields.name",
    )
    parser.add_argument(
        "--non-empty",
        action="append",
        default=[],
        help="Field path that must exist and not be empty. Repeatable.",
    )
    parser.add_argument(
        "--unique-by",
        action="append",
        default=[],
        help="Field path used for dedupe checks. Repeatable; multiple values form a composite key.",
    )
    parser.add_argument(
        "--min-records",
        type=int,
        default=1,
        help="Minimum number of records expected in the file.",
    )
    parser.add_argument(
        "--expect-entity-type",
        help="Optional expected entity_type value for all records.",
    )
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("input file is empty")

    if path.suffix.lower() == ".jsonl":
        records = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} is not a JSON object")
            records.append(value)
        return records

    value = json.loads(text)
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ValueError("JSON array must contain only objects")
        return value

    if isinstance(value, dict):
        for key in ("records", "items", "data"):
            candidate = value.get(key)
            if isinstance(candidate, list) and all(isinstance(item, dict) for item in candidate):
                return candidate
        raise ValueError("JSON object must contain a list under records, items, or data")

    raise ValueError("unsupported JSON shape")


def get_value(record: Any, field_path: str) -> Any:
    current = record
    for segment in field_path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return None
            current = current[segment]
            continue
        if isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, freeze(val)) for key, val in value.items()))
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    return value


def main() -> int:
    args = parse_args()
    path = Path(args.input)

    if not path.is_file():
        print(f"[FAIL] input file not found: {path}")
        return 1

    try:
        records = load_records(path)
    except Exception as exc:
        print(f"[FAIL] could not load records: {exc}")
        return 1

    errors: list[str] = []

    if len(records) < args.min_records:
        errors.append(
            f"record count {len(records)} is smaller than required minimum {args.min_records}"
        )

    seen_keys: set[Any] = set()

    for index, record in enumerate(records, start=1):
        if args.expect_entity_type:
            entity_type = get_value(record, "entity_type")
            if entity_type != args.expect_entity_type:
                errors.append(
                    f"record {index}: entity_type={entity_type!r} does not match "
                    f"{args.expect_entity_type!r}"
                )

        for field_path in args.require:
            if get_value(record, field_path) is None:
                errors.append(f"record {index}: missing required field {field_path}")

        for field_path in args.non_empty:
            value = get_value(record, field_path)
            if value is None:
                errors.append(f"record {index}: missing non-empty field {field_path}")
            elif is_empty(value):
                errors.append(f"record {index}: empty value for {field_path}")

        if args.unique_by:
            key_parts = [freeze(get_value(record, field_path)) for field_path in args.unique_by]
            if any(part is None for part in key_parts):
                errors.append(
                    f"record {index}: unique key incomplete for fields {', '.join(args.unique_by)}"
                )
            else:
                composite_key = tuple(key_parts)
                if composite_key in seen_keys:
                    errors.append(
                        f"record {index}: duplicate composite key for {', '.join(args.unique_by)}"
                    )
                else:
                    seen_keys.add(composite_key)

    if errors:
        print(f"[FAIL] {len(errors)} validation issue(s) found in {path}")
        for issue in errors[:50]:
            print(f" - {issue}")
        if len(errors) > 50:
            print(f" - ... {len(errors) - 50} more issue(s)")
        return 1

    print(f"[OK] validated {len(records)} record(s) from {path}")
    if args.require:
        print(f" - required fields: {', '.join(args.require)}")
    if args.non_empty:
        print(f" - non-empty fields: {', '.join(args.non_empty)}")
    if args.unique_by:
        print(f" - uniqueness key: {', '.join(args.unique_by)}")
    if args.expect_entity_type:
        print(f" - expected entity_type: {args.expect_entity_type}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
