from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_circle.spiders.hospital.hospital_detail_spider import (  # noqa: E402
    split_pending_hospital_names,
)


def test_split_pending_hospital_names_skips_already_written_queries() -> None:
    pending_names, summary = split_pending_hospital_names(
        hospital_names=[
            "北京积水潭医院",
            "上海市第一人民医院",
            "乌鲁木齐市友谊医院",
            "山东大学齐鲁医院",
        ],
        processed_hospital_names={
            "上海市第一人民医院",
            "乌鲁木齐市友谊医院",
        },
    )

    assert pending_names == [
        "北京积水潭医院",
        "山东大学齐鲁医院",
    ]
    assert summary == {
        "candidate_count": 4,
        "processed_count": 2,
        "pending_count": 2,
    }
