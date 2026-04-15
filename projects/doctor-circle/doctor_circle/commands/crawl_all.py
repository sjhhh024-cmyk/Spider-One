"""按固定顺序启动所有 spider。"""

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError
from scrapy.utils.conf import arglist_to_dict


class Command(ScrapyCommand):
    """一条命令跑完整个“圈子 -> 医生详情”链路。"""

    requires_project = True
    spider_list = [
        "circle_list_spider",
        "circle_doctor_list_spider",
        "doctor_detail_url_spider",
        "doctor_detail_spider",
    ]

    def syntax(self):
        """返回命令语法提示。"""

        return "[options]"

    def short_desc(self):
        """返回命令简介。"""

        return "按固定顺序运行医生圈项目里的所有 spider"

    def add_options(self, parser):
        """补充 spider 参数透传能力。"""

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
        """解析 spider 参数。"""

        super().process_options(args, opts)
        try:
            opts.spargs = arglist_to_dict(opts.spargs)
        except ValueError as error:
            raise UsageError("无效的 -a 参数，请使用 -a NAME=VALUE") from error

    def run(self, args, opts):
        """循环注册 spider，然后统一启动。"""

        for spider_name in self.spider_list:
            print(f"开始注册 spider: {spider_name}")
            self.crawler_process.crawl(spider_name, **opts.spargs)

        self.crawler_process.start()
