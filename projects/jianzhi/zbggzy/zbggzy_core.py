from __future__ import annotations

import sys
from typing import Callable

import zbggzy_houxuanren
import zbggzy_zhaobiao
import zbggzy_zhongbiao


RUNNERS: list[tuple[str, Callable[[list[str] | None], int]]] = [
    ("招标公告", zbggzy_zhaobiao.main),
    ("中标公告", zbggzy_zhongbiao.main),
    ("候选人公告", zbggzy_houxuanren.main),
]


def main(argv: list[str] | None = None) -> int:
    for board_name, runner in RUNNERS:
        print("")
        print(f"========== 启动模块: {board_name} ==========")
        exit_code = runner(None)
        if exit_code:
            return int(exit_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
