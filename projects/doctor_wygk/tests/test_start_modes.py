from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_wygk.commands.crawl_all import Command  # noqa: E402
from doctor_wygk.start import DETAIL_ONLY_SPIDER_NAMES, SPIDER_NAMES  # noqa: E402


def test_start_pipeline_only_keeps_main_chain_spiders() -> None:
    assert SPIDER_NAMES == [
        "entry_seed_spider",
        "hospital_department_spider",
        "department_doctor_list_spider",
        "live_history_doctor_spider",
        "course_doctor_spider",
        "surgery_doctor_spider",
        "organization_doctor_spider",
        "doctor_home_fans_spider",
        "doctor_detail_spider",
    ]


def test_detail_only_mode_targets_single_detail_spider() -> None:
    assert DETAIL_ONLY_SPIDER_NAMES == ["doctor_detail_spider"]


def test_crawl_all_command_uses_the_same_main_chain_order() -> None:
    assert Command.spider_list == SPIDER_NAMES
