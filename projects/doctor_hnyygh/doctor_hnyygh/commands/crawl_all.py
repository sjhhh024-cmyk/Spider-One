"""crawl_all command wrapper."""

from scrapy.commands import ScrapyCommand
from scrapy.utils.project import get_project_settings

from doctor_hnyygh.start import DEFAULT_SPIDER_NAMES, run_pipeline


class Command(ScrapyCommand):
    requires_project = True

    def short_desc(self):
        return "Run the configured doctor_hnyygh spider pipeline"

    def run(self, args, opts):
        get_project_settings()
        run_pipeline(list(DEFAULT_SPIDER_NAMES))
