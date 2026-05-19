from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd import settings as project_settings  # noqa: E402
from doctor_ywbd.start import DEFAULT_SPIDER_NAMES, DETAIL_ONLY_SPIDER_NAMES  # noqa: E402
from doctor_ywbd.start_hospital import HOSPITAL_ONLY_SPIDER_NAMES  # noqa: E402


def test_full_start_pipeline_runs_split_stage_spiders_in_order() -> None:
    assert DEFAULT_SPIDER_NAMES == [
        "entry_seed_spider",
        "disease_index_spider",
        "disease_list_spider",
        "department_index_spider",
        "department_list_spider",
        "area_index_spider",
        "area_list_spider",
        "hospital_area_index_spider",
        "hospital_list_spider",
        "hospital_detail_spider",
        "hospital_expert_spider",
        "doctor_detail_spider",
    ]


def test_detail_only_start_mode_runs_only_final_consumer() -> None:
    assert DETAIL_ONLY_SPIDER_NAMES == [
        "doctor_detail_spider",
    ]


def test_hospital_only_start_mode_runs_hospital_chain() -> None:
    assert HOSPITAL_ONLY_SPIDER_NAMES == [
        "entry_seed_spider",
        "hospital_area_index_spider",
        "hospital_list_spider",
        "hospital_detail_spider",
    ]


def test_scrapy_cookie_middleware_is_disabled_for_manual_cookie_header() -> None:
    assert project_settings.COOKIES_ENABLED is False
