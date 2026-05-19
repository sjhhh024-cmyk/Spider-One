from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ytggzy_core import (  # noqa: E402
    SpiderTask,
    YtggzySpider,
    build_release_content_mix,
    build_bid_record,
    build_candidate_record,
    build_win_record,
    extract_attachment_entries,
    extract_module_tasks,
    parse_detail,
    resolve_output_board,
)


def test_resolve_output_board_handles_intention_candidate_and_win() -> None:
    assert resolve_output_board("政府采购", "采购需求(意向)") == "采购意向"
    assert resolve_output_board("自主选择进场-采购项目", "采购需求(意向)") == "采购意向"
    assert resolve_output_board("工程建设", "招标计划") == "招标公告"
    assert resolve_output_board("工程建设", "中（定）标候选人公示") == "候选人公告"
    assert resolve_output_board("工程建设", "中标结果公示") == "中标公告"
    assert resolve_output_board("工程建设", "招标公告") == "招标公告"


def test_extract_module_tasks_reads_category_items() -> None:
    html = """
    <div id="sx-ggtype">
      <a data-categorynum="003002001">采购需求(意向)</a>
      <a data-categorynum="003002002">采购公告</a>
      <a data-categorynum="003002003">更正公告</a>
    </div>
    """
    tasks = extract_module_tasks(html, "政府采购", "https://example.com")
    assert [(task.notice_type, task.output_board) for task in tasks] == [
        ("采购需求(意向)", "采购意向"),
        ("采购公告", "招标公告"),
    ]


def test_parse_detail_reads_main_html_and_files() -> None:
    html = """
    <html>
      <body>
        <span id="info_ly">龙口市</span>
        <div class="txt-content"><p>正文</p></div>
        <div class="com-files"><a href="/file/a.pdf">附件A</a></div>
      </body>
    </html>
    """
    detail = parse_detail(html, "https://ggzyjy.yantai.gov.cn/a.html", {"title": "标题", "webdate": "2026-05-13 10:00:00"})
    assert detail["title"] == "标题"
    assert "正文" in detail["plain_text"]
    assert detail["attachments"][0]["fileName"] == "附件A"


def test_build_bid_record_uses_model_fields_without_extra_rebuild() -> None:
    task = SpiderTask(
        module_name="政府采购",
        notice_type="采购公告",
        categorynum="003002002",
        output_board="招标公告",
        page_url="https://example.com/list.html",
    )
    list_record = {"projectnumber": "LIST-001", "xiaqucode": "370685", "xiaquname": "招远市"}
    detail = {
        "title": "列表标题",
        "detail_url": "https://example.com/a.html",
        "main_html": "<div>正文</div>",
        "plain_text": "正文",
        "attachments": [],
        "source": "招远市",
        "publish_time": "2026-05-13 10:00:00",
    }
    record = build_bid_record(
        task,
        list_record,
        detail,
        {
            "projectNum": "YT-BID-001",
            "projectName": "烟台测试项目",
            "budgetAmount": "1000元",
            "procurementMethod": "其他方式",
            "releaseSource": "烟台采购人",
            "purchaserAddress": "烟台采购人地址",
            "consultationInfo": {
                "purchasingInfor": ["名称：烟台采购人"],
                "projectInfor": ["项目联系人：张三", "电话：0535-1234567"],
            },
        },
    )

    assert record["projectNum"] == "YT-BID-001"
    assert record["projectName"] == "烟台测试项目"
    assert record["announcementTitle"] == "烟台测试项目"
    assert record["budgetAmount"] == "1000元"
    assert record["procurementMethod"] == "其他方式"
    assert record["releaseSource"] == "烟台采购人"
    assert record["purchaserAddress"] == "烟台采购人地址"
    assert record["consultationInfo"] == {
        "purchasingInfor": ["名称：烟台采购人"],
        "projectInfor": ["项目联系人：张三", "电话：0535-1234567"],
    }


def test_build_candidate_record_keeps_only_first_model_result() -> None:
    task = SpiderTask(
        module_name="工程建设",
        notice_type="中（定）标候选人公示",
        categorynum="003001002",
        output_board="候选人公告",
        page_url="https://example.com/list.html",
    )
    list_record = {}
    detail = {
        "title": "项目",
        "detail_url": "https://example.com/a.html",
        "main_html": "<div>正文</div>",
        "plain_text": "正文",
        "attachments": [],
        "source": "招远市",
        "publish_time": "2026-05-13 10:00:00",
    }
    record = build_candidate_record(
        task,
        list_record,
        detail,
        {
            "tenderTitle": "模型标题",
            "procurementUnit": "模型单位",
            "extra": {"tenderNumber": "1"},
            "result": [
                {"relationCompanyName": "A", "candidateSort": [1]},
                {"relationCompanyName": "B", "candidateSort": [2]},
            ],
        },
    )
    assert record["relationCompanyName"] == "A"
    assert record["extra"] == {"candidateSort": [1], "tenderNumber": "1"}
    assert record["renderType"] == "中标候选人"


def test_build_candidate_record_strips_disallowed_candidate_sort_fields() -> None:
    task = SpiderTask(
        module_name="工程建设",
        notice_type="中（定）标候选人公示",
        categorynum="003001002",
        output_board="候选人公告",
        page_url="https://example.com/list.html",
    )
    detail = {
        "title": "项目",
        "detail_url": "https://example.com/a.html",
        "main_html": "<div>正文</div>",
        "plain_text": "正文",
        "attachments": [],
        "source": "招远市",
        "publish_time": "2026-05-13 10:00:00",
    }
    record = build_candidate_record(
        task,
        {},
        detail,
        {
            "tenderTitle": "项目",
            "procurementUnit": "单位",
            "extra": {"tenderNumber": "1"},
            "result": [
                {
                    "relationCompanyName": "A",
                    "candidateSort": [
                        {
                            "候选人排序": [
                                "第一候选人：恒华数字科技集团有限公司",
                                "第二候选人：捷通智慧科技股份有限公司",
                            ],
                            "包号": "",
                            "候选人名称": "恒华数字科技集团有限公司,捷通智慧科技股份有限公司",
                        }
                    ],
                }
            ],
        },
    )
    assert record["extra"]["candidateSort"] == [
        {
            "候选人排序": [
                "第一候选人：恒华数字科技集团有限公司",
                "第二候选人：捷通智慧科技股份有限公司",
            ]
        }
    ]


def test_build_win_record_uses_first_model_result_without_reformatting() -> None:
    task = SpiderTask(
        module_name="工程建设",
        notice_type="中标结果公示",
        categorynum="003001003",
        output_board="中标公告",
        page_url="https://example.com/list.html",
    )
    list_record = {"projectnumber": "LIST-001", "zbtype": "施工"}
    detail = {
        "title": "项目",
        "detail_url": "https://example.com/a.html",
        "main_html": "<div>正文</div>",
        "plain_text": "正文",
        "attachments": [],
        "source": "招远市",
        "publish_time": "2026-05-13 10:00:00",
    }
    record = build_win_record(
        task,
        list_record,
        detail,
        {
            "tenderTitle": "项目",
            "tenderNumber": "1",
            "procurementUnit": "单位",
            "result": [
                {"relationCompanyName": "A", "renderMoney": "100.00万元"},
                {"relationCompanyName": "B,C", "renderMoney": "200.00万元"},
            ],
        },
    )

    assert record["relationCompanyName"] == "A"
    assert record["renderMoney"] == "100.00万元"
    assert record["isUnion"] == 0


def test_build_win_record_keeps_union_flag_from_first_result() -> None:
    task = SpiderTask(
        module_name="工程建设",
        notice_type="中标结果公示",
        categorynum="003001003",
        output_board="中标公告",
        page_url="https://example.com/list.html",
    )
    detail = {
        "title": "项目",
        "detail_url": "https://example.com/a.html",
        "main_html": "<div>正文</div>",
        "plain_text": "正文",
        "attachments": [],
        "source": "招远市",
        "publish_time": "2026-05-13 10:00:00",
    }
    record = build_win_record(
        task,
        {"projectnumber": "LIST-001", "zbtype": "施工"},
        detail,
        {
            "tenderTitle": "项目",
            "tenderNumber": "1",
            "procurementUnit": "单位",
            "result": [{"relationCompanyName": "B,C"}],
        },
    )
    assert record["isUnion"] == 1


def test_trade_type_is_used_for_construction_bid_and_win_records() -> None:
    task = SpiderTask(
        module_name="工程建设",
        notice_type="招标公告",
        categorynum="003001003",
        output_board="招标公告",
        page_url="https://example.com",
    )
    list_record = {"zbtype": "施工", "projectnumber": "1", "xiaqucode": "370600", "xiaquname": "烟台市"}
    detail = {"title": "项目", "detail_url": "https://example.com/a.html", "source": "烟台市", "publish_time": "2026-05-13 10:00:00", "main_html": "<p>正文</p>", "attachments": []}
    bid_record = build_bid_record(task, list_record, detail)
    win_record = build_win_record(task, list_record, detail)
    assert bid_record["bidType"] == "施工"
    assert win_record["renderType"] == "施工"


def test_build_release_content_mix_splits_text_and_table() -> None:
    html = """
    <div class="txt-content">
      <p>前置说明文字</p>
      <table>
        <tr><td>序号</td><td>采购项目名称</td><td>备注</td></tr>
        <tr><td>1</td><td>项目A</td><td></td></tr>
      </table>
      <p>本次公开的采购意向是本单位政府采购工作的初步安排。</p>
      <p>某单位</p>
    </div>
    """
    content_mix = build_release_content_mix(html)
    assert content_mix["1"] == "前置说明文字"
    assert content_mix["2"]["head"] == ["序号", "采购项目名称", "备注"]
    assert content_mix["2"]["body"] == [["1", "项目A", ""]]
    assert "本次公开的采购意向" in content_mix["3"]


def test_build_release_content_mix_keeps_intro_and_footer_for_nested_table() -> None:
    html = """
    <div class="txt-content">
      <p>招远市自然资源和规划局2026年05月(至)06月政府采购意向</p>
      <p>为便于供应商及时了解政府采购信息，现将采购意向公开如下：</p>
      <div align="center">
        <table>
          <tr><td>序号</td><td>采购项目名称</td></tr>
          <tr><td>1</td><td>项目A</td></tr>
        </table>
      </div>
      <p>本次公开的采购意向是本单位政府采购工作的初步安排。</p>
      <p>招远市自然资源和规划局</p>
      <p>2026年05月13日</p>
    </div>
    """
    content_mix = build_release_content_mix(
        html,
        "招远市自然资源和规划局2026年05月(至)06月政府采购意向",
    )
    assert content_mix["1"] == "为便于供应商及时了解政府采购信息，现将采购意向公开如下："
    assert content_mix["2"]["head"] == ["序号", "采购项目名称"]
    assert content_mix["2"]["body"] == [["1", "项目A"]]
    assert "本次公开的采购意向是本单位政府采购工作的初步安排。" in content_mix["3"]
    assert "招远市自然资源和规划局" in content_mix["3"]
    assert "2026年05月13日" in content_mix["3"]


def test_run_reports_monitor_status_on_success(monkeypatch) -> None:
    spider = YtggzySpider()
    flushed: list[dict[str, object]] = []

    class _FakeMonitor:
        def __init__(self, *, province: str, city: str, webname: str, biz_type: str, logger=None) -> None:
            self.logo_info = {
                "WasSuccessful": 1,
                "WebsiteError": 1,
                "HasContent": 0,
                "HasNewData": 0,
                "IsValidData": 1,
                "WebName": webname,
                "BizType": biz_type,
            }

        def mark_run_failed(self) -> None:
            self.logo_info["WasSuccessful"] = 0

        def mark_website_error(self) -> None:
            self.logo_info["WebsiteError"] = 0

        def mark_has_content(self) -> None:
            self.logo_info["HasContent"] = 1

        def mark_has_new_data(self) -> None:
            self.logo_info["HasNewData"] = 1

        def mark_invalid_data(self) -> None:
            self.logo_info["IsValidData"] = 0

        def flush(self) -> bool:
            flushed.append(self.logo_info.copy())
            return True

    monkeypatch.setattr("ytggzy_core.SpiderMonitor", _FakeMonitor, raising=False)
    monkeypatch.setattr("ytggzy_core.build_biz_type", lambda module_name, notice_type, sub_type="": module_name, raising=False)

    spider.discover_tasks = lambda: [  # type: ignore[assignment]
        SpiderTask(
            module_name="政府采购",
            notice_type="采购公告",
            categorynum="003002002",
            output_board="招标公告",
            page_url="https://example.com/list.html",
        )
    ]
    spider.fetch_list_records = lambda task, page_number: (  # type: ignore[assignment]
        [
            {
                "title": "测试公告",
                "linkurl": "/detail/a.html",
                "xiaqucode": "370685",
                "xiaquname": "招远市",
                "projectnumber": "ZY-001",
                "webdate": "2026-05-13 10:00:00",
            }
        ],
        1,
    )
    spider.fetch_detail = lambda detail_url, list_record: {  # type: ignore[assignment]
        "title": "测试公告",
        "detail_url": detail_url,
        "main_html": "<div>正文</div>",
        "plain_text": "正文",
        "attachments": [],
        "source": "招远市",
        "publish_time": "2026-05-13 10:00:00",
    }
    spider.build_records = lambda task, list_record, detail: [  # type: ignore[assignment]
        {"projectName": "测试公告"}
    ]

    spider.run()

    assert flushed == [
        {
            "WasSuccessful": 1,
            "WebsiteError": 1,
            "HasContent": 1,
            "HasNewData": 1,
            "IsValidData": 1,
            "WebName": "烟台市公共资源交易网",
            "BizType": "政府采购",
        }
    ]


def test_run_flushes_monitor_when_list_fetch_fails(monkeypatch) -> None:
    spider = YtggzySpider()
    flushed: list[dict[str, object]] = []

    class _FakeMonitor:
        def __init__(self, *, province: str, city: str, webname: str, biz_type: str, logger=None) -> None:
            self.logo_info = {
                "WasSuccessful": 1,
                "WebsiteError": 1,
                "HasContent": 0,
                "HasNewData": 0,
                "IsValidData": 1,
                "WebName": webname,
                "BizType": biz_type,
            }

        def mark_run_failed(self) -> None:
            self.logo_info["WasSuccessful"] = 0

        def mark_website_error(self) -> None:
            self.logo_info["WebsiteError"] = 0

        def mark_has_content(self) -> None:
            self.logo_info["HasContent"] = 1

        def mark_has_new_data(self) -> None:
            self.logo_info["HasNewData"] = 1

        def mark_invalid_data(self) -> None:
            self.logo_info["IsValidData"] = 0

        def flush(self) -> bool:
            flushed.append(self.logo_info.copy())
            return True

    monkeypatch.setattr("ytggzy_core.SpiderMonitor", _FakeMonitor, raising=False)
    monkeypatch.setattr("ytggzy_core.build_biz_type", lambda module_name, notice_type, sub_type="": module_name, raising=False)

    spider.discover_tasks = lambda: [  # type: ignore[assignment]
        SpiderTask(
            module_name="工程建设",
            notice_type="招标公告",
            categorynum="003001001",
            output_board="招标公告",
            page_url="https://example.com/list.html",
        )
    ]

    def _raise_fetch_error(task: SpiderTask, page_number: int) -> tuple[list[dict[str, object]], int]:
        raise requests.RequestException("boom")

    spider.fetch_list_records = _raise_fetch_error  # type: ignore[assignment]

    with pytest.raises(requests.RequestException):
        spider.run()

    assert flushed == [
        {
            "WasSuccessful": 0,
            "WebsiteError": 0,
            "HasContent": 0,
            "HasNewData": 0,
            "IsValidData": 1,
            "WebName": "烟台市公共资源交易网",
            "BizType": "工程建设",
        }
    ]
