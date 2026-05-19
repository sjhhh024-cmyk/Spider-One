"""只跑医院链路并落 hospital_ywbd。"""

from __future__ import annotations

from doctor_ywbd.start import run_pipeline


HOSPITAL_ONLY_SPIDER_NAMES = [
    "entry_seed_spider",
    "hospital_area_index_spider",
    "hospital_list_spider",
    "hospital_detail_spider",
]


def main():
    run_pipeline(HOSPITAL_ONLY_SPIDER_NAMES)


if __name__ == "__main__":
    main()
