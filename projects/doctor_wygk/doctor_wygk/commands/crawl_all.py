"""按固定顺序启动所有 spider。"""

from __future__ import annotations

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError
from scrapy.utils.conf import arglist_to_dict


class Command(ScrapyCommand):
    """一条命令跑完整个“入口 -> 列表 -> 详情”链路。"""

    requires_project = True
    spider_list = [
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

    def syntax(self):
        return "[options]"

    def short_desc(self):
        return "按固定顺序运行 doctor_wygk 项目里的所有 spider"

    def add_options(self, parser):
        super().add_options(parser)
        parser.add_argument(
            "-a",
            dest="spargs",
            action="append",
            default=[],
            metavar="NAME=VALUE",
            help="设置 spider 参数，可重复传入",
        )
        parser.add_argument("-o", "--output", metavar="FILE", help="把 item 输出到文件")
        parser.add_argument(
            "-t",
            "--output-format",
            metavar="FORMAT",
            help="配合 -o 使用，指定导出格式",
        )

    def process_options(self, args, opts):
        super().process_options(args, opts)
        try:
            opts.spargs = arglist_to_dict(opts.spargs)
        except ValueError as error:
            raise UsageError("无效的 -a 参数，请使用 -a NAME=VALUE") from error

    def run(self, args, opts):
        for spider_name in self.spider_list:
            print(f"开始注册 spider: {spider_name}")
            self.crawler_process.crawl(spider_name, **opts.spargs)

        self.crawler_process.start()
