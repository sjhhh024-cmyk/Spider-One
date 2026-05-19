"""单独启动医院详情 spider。"""

from __future__ import annotations

from doctor_wygk.start import run_spider


SPIDER_NAME = "hospital_detail_spider"


def main() -> None:
    run_spider(SPIDER_NAME)


if __name__ == "__main__":
    main()
