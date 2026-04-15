"""只消费最终医生详情队列。"""

from __future__ import annotations

from doctor_ywbd.start import DETAIL_ONLY_SPIDER_NAMES, run_pipeline


def main():
    run_pipeline(DETAIL_ONLY_SPIDER_NAMES)


if __name__ == "__main__":
    main()
