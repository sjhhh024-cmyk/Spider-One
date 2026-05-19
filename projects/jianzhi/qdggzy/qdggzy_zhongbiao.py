from __future__ import annotations

from qdggzy_core import QdggzySpider, build_arg_parser


RUN_CONFIG = {
    "module_name": "全部模块",
    "notice_type": "",
    "start_page": 1,
    "max_pages": 0,
    "page_size": 10,
    "timeout_seconds": 20,
    "detail_delay_seconds": 0.0,
}


class QdggzyWinSpider(QdggzySpider):
    pass


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        spider = QdggzyWinSpider(
            module_name=RUN_CONFIG["module_name"] if RUN_CONFIG["module_name"] != "全部模块" else None,
            notice_type_filter=RUN_CONFIG["notice_type"] or None,
            output_board_filter="中标公告",
            start_page=int(RUN_CONFIG["start_page"]),
            max_pages=int(RUN_CONFIG["max_pages"]),
            page_size=int(RUN_CONFIG["page_size"]),
            timeout_seconds=int(RUN_CONFIG["timeout_seconds"]),
            detail_delay_seconds=float(RUN_CONFIG["detail_delay_seconds"]),
        )
        spider.run()
        return 0

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    spider = QdggzyWinSpider(
        module_name=args.module_name or None,
        notice_type_filter=args.notice_type or None,
        output_board_filter="中标公告",
        start_page=args.start_page,
        max_pages=args.max_pages,
        page_size=args.page_size,
        timeout_seconds=args.timeout_seconds,
        detail_delay_seconds=args.detail_delay_seconds,
    )
    spider.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
