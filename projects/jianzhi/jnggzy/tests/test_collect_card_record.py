from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from jnggzy import JnggzySpider, filter_tasks_by_notice_type, get_module_tasks, is_blank_notice_detail, load_profile  # noqa: E402


class DummySpider(JnggzySpider):
    def __init__(self, profile: dict):
        super().__init__(profile, session=object())

    def fetch_notice_detail_by_url(self, detail_url: str) -> tuple[str, str]:
        return detail_url, "<html><body><div> </div></body></html>"


def test_collect_card_record_skips_blank_land_notice_detail() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    profile = load_profile(project_dir / "profile.yml")
    spider = DummySpider(profile)
    task = {
        "module_name": "土地矿产",
        "type": "2",
        "notice_type": "招标公告",
        "list_api": "homepage",
        "list_key": "str0",
    }
    card = {
        "title": "空白详情测试",
        "detail_url": "https://example.com/blank",
        "notice_type": "招标公告",
        "is_new": 1,
    }

    record = spider.collect_card_record(card, task, "2026-05-09T20:30:00")

    assert record is None


def test_is_blank_notice_detail_treats_title_and_boilerplate_only_as_blank() -> None:
    task = {"module_name": "土地矿产", "notice_type": "招标公告"}
    detail = {
        "title": "济南市莱芜区国有建设用地使用权网上挂牌出让公告",
        "field_map": {"公共资源交易编号": "2021TDGP16G0417"},
        "result_rows": [],
        "plain_text": "\n".join(
            [
                "公告详情",
                "当前位置：",
                "首页",
                ">土地矿产",
                ">招标公告",
                "济南市莱芜区国有建设用地使用权网上挂牌出让公告",
                "公共资源交易编号：2021TDGP16G0417",
                "发布日期：2021-09-03",
                "尊敬的用户您好！如页面信息无法正常显示，请更换360浏览器后，点击以下链接尝试",
                "链接地址",
                "关闭本页",
                "澄清答疑",
            ]
        ),
        "content_text": "",
    }

    assert is_blank_notice_detail(task, detail, "<html></html>") is True


def test_is_blank_notice_detail_keeps_land_notice_with_real_body() -> None:
    task = {"module_name": "土地矿产", "notice_type": "招标公告"}
    detail = {
        "title": "济南市莱芜区国有建设用地使用权网上挂牌出让公告",
        "field_map": {"公共资源交易编号": "2021TDGP16G0417"},
        "result_rows": [],
        "plain_text": "\n".join(
            [
                "济南市莱芜区国有建设用地使用权网上挂牌出让公告",
                "公共资源交易编号：2021TDGP16G0417",
                "挂牌起始价：100万元",
                "竞买保证金：20万元",
            ]
        ),
        "content_text": "",
    }

    assert is_blank_notice_detail(task, detail, "<html></html>") is False


def test_is_blank_notice_detail_also_applies_to_land_result_notice() -> None:
    task = {"module_name": "土地矿产", "notice_type": "结果公示"}
    detail = {
        "title": "",
        "field_map": {},
        "result_rows": [],
        "plain_text": "\n".join(
            [
                "公告详情",
                "当前位置：",
                "首页",
                ">土地矿产",
                ">中标公告",
                "尊敬的用户您好！如页面信息无法正常显示，请更换360浏览器后，点击以下链接尝试",
                "链接地址",
                "关闭本页",
            ]
        ),
        "content_text": "",
    }

    assert is_blank_notice_detail(task, detail, "<html></html>") is True


def test_is_blank_notice_detail_does_not_apply_to_other_modules() -> None:
    other_tasks = [
        {"module_name": "产权交易", "notice_type": "项目信息"},
        {"module_name": "水利工程", "notice_type": "招标公告"},
        {"module_name": "农村产权", "notice_type": "挂牌项目"},
        {"module_name": "农村产权", "notice_type": "成交公告"},
    ]
    detail = {
        "title": "",
        "field_map": {},
        "result_rows": [],
        "plain_text": "\n".join(
            [
                "公告详情",
                "当前位置：",
                "首页",
                "尊敬的用户您好！如页面信息无法正常显示，请更换360浏览器后，点击以下链接尝试",
                "链接地址",
                "关闭本页",
            ]
        ),
        "content_text": "",
    }

    for task in other_tasks:
        assert is_blank_notice_detail(task, detail, "<html></html>") is False


def test_filter_tasks_by_notice_type_keeps_only_requested_notice() -> None:
    tasks = get_module_tasks("土地矿产")
    filtered = filter_tasks_by_notice_type(tasks, "结果公示")

    assert len(filtered) == 1
    assert filtered[0]["module_name"] == "土地矿产"
    assert filtered[0]["notice_type"] == "结果公示"


def test_parent_type_keeps_original_module_name() -> None:
    from jnggzy import get_parent_type

    assert get_parent_type("铁路工程") == "铁路工程"
    assert get_parent_type("建设工程") == "建设工程"


def test_land_result_notice_iframe_payload_maps_to_win_template() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    profile = load_profile(project_dir / "profile.yml")

    class LandResultSpider(JnggzySpider):
        def __init__(self, profile: dict):
            super().__init__(profile, session=object())

        def fetch_notice_detail(self, notice_id: str, is_new: int, notice_type: str, detail_path: str) -> tuple[str, str]:
            html = (
                '<html><body>'
                '<iframe src="http://119.164.252.44:8001/portal/noticeDetail.html?targetId=2026033017180533326772"></iframe>'
                '</body></html>'
            )
            return "https://jnggzy.jinan.gov.cn/jnggzyztb/front/showResultNotice.do?iid=20260330171436635775510000000000&isnew=1", html

        def fetch_notice_detail_by_url(self, detail_url: str) -> tuple[str, str]:
            html = (
                '<html><body>'
                '<div class="wrap">'
                '<div class="fixclear category_tit"><span class="f29 f2 c1 fb c5"><span id="notice_xh"> </span> </span></div>'
                '<div id="img_bag"><ul id="top_id"></ul></div>'
                '<table class="notice_info">'
                '<tr><td id="goods_no"></td><td id="goods_name"></td><td id="business_name"></td><td id="trans_type"></td></tr>'
                '<tr><td id="land_area"></td><td id="address"></td><td id="use_years"></td><td id="develop"></td></tr>'
                '<tr><td id="apply_time"></td><td id="list_time"></td><td id="begin_price"></td><td id="price_step"></td></tr>'
                '<tr><td id="allow_union"></td><td id="end_trans_time"></td><td id="trans_bidder"></td><td id="trans_price"></td></tr>'
                '<tr><td id="trans_time"></td><td id="goods_use"></td><td id="build_height"></td><td id="plot1"></td></tr>'
                '<tr><td id="plot2"></td><td id="build_density"></td><td id="green_ratio"></td><td id="otherCondition"></td></tr>'
                '<tr><td id="remark"></td></tr>'
                '</table>'
                '</div>'
                '</body></html>'
            )
            return detail_url, html

        def fetch_land_result_notice_payload(self, target_id: str) -> dict:
            assert target_id == "2026033017180533326772"
            return {
                "target": {
                    "no": "2026TDGP12R0007",
                    "name": "王舍人片区071街区韩仓河以东、响泉路以南Dws-071-16地块",
                    "trans_bidder": "济南中海华山商业地产有限公司",
                    "trans_price": 313450000,
                    "end_trans_time": "2026-04-29 09:30:00",
                    "organ_his_name": "济南市自然资源和规划局",
                    "trans_type_label": "网上交易（挂牌）",
                    "notice_xh": "26006",
                    "unit": "万元",
                },
                "goods": [
                    {
                        "target_no": "2026TDGP12R0007",
                        "target_name": "王舍人片区071街区韩仓河以东、响泉路以南Dws-071-16地块",
                        "business_name": "土地出让",
                        "address": "历城区王舍人片区韩仓河以东、响泉路以南",
                        "land_area": "24565",
                        "goods_use": "城镇住宅用地",
                        "use_years": "70",
                        "goods_no": "2026TDGP12R0007",
                        "goods_name": "王舍人片区071街区韩仓河以东、响泉路以南Dws-071-16地块",
                        "trans_type": "0",
                        "begin_apply_time": "2026-04-19 09:00:00",
                        "end_apply_time": "2026-04-27 16:00:00",
                        "begin_list_time": "2026-04-19 09:00:00",
                        "end_list_time": "2026-04-29 09:30:00",
                        "begin_price": 313450000,
                        "price_step": 2000000,
                        "allow_union": 1,
                        "trans_goods_price": 313450000,
                    }
                ],
            }

    spider = LandResultSpider(profile)
    task = {
        "module_name": "土地矿产",
        "type": "2",
        "notice_type": "结果公示",
        "list_api": "search",
        "list_key": "str1",
    }
    card = {
        "title": "测试地块结果公示",
        "notice_id": "20260330171436635775510000000000",
        "notice_type": "中标公告",
        "is_new": 1,
        "detail_url": "",
    }

    record = spider.collect_card_record(card, task, "2026-05-09T23:30:00")

    assert record is not None
    assert record["tenderTitle"] == "王舍人片区071街区韩仓河以东、响泉路以南Dws-071-16地块"
    assert record["tenderNumber"] == "2026TDGP12R0007"
    assert record["relationCompanyName"] == "济南中海华山商业地产有限公司"
    assert record["renderMoney"] == "313450000元"
    assert record["renderDate"] == "2026-04-29 09:30"
    assert record["renderType"] == "土地出让"
    assert record["procurementUnit"] == "济南市自然资源和规划局"
    assert record["originalWebsiteAddress"].endswith("iid=20260330171436635775510000000000&isnew=1")
    assert record["htmlContent"]


def test_land_result_notice_html_removes_mining_block_and_keeps_target_fields() -> None:
    from jnggzy import build_land_result_notice_detail

    payload = {
        "target": {
            "no": "2026TDGP12R0007",
            "name": "王舍人片区071街区韩仓河以东、响泉路以南Dws-071-16地块",
            "trans_bidder": "济南中海华山商业地产有限公司",
            "trans_price": 313450000,
            "end_trans_time": "2026-04-29 09:30:00",
            "organ_his_name": "济南市自然资源和规划局",
            "trans_type_label": "网上交易（挂牌）",
            "notice_xh": "26006",
            "unit": "万元",
            "crjyjkhz": 0,
        },
        "earnest": [{"currency": "CNY", "amount": 62690000}],
        "goods": [
            {
                "goods_no": "2026TDGP12R0007",
                "goods_name": "王舍人片区071街区韩仓河以东、响泉路以南Dws-071-16地块",
                "business_name": "土地出让",
                "trans_type": "0",
                "land_area": "24565",
                "address": "历城区王舍人片区韩仓河以东、响泉路以南",
                "use_years": "70",
                "end_earnest_time": "2026-04-27 16:00:00",
                "deposit_price": "6269",
                "allow_union": 1,
                "trans_goods_price": 313450000,
                "goods_use": "城镇住宅用地",
            }
        ],
    }
    template_html = (
        '<html><body><div class="wrap">'
        '<div id="img_bag"></div>'
        '<span id="notice_xh"></span>'
        '<div id="target_maxprice_label"></div><div id="target_maxprice"></div>'
        '<div id="end_earnest_time"></div><div id="earnest_money"></div>'
        '<div id="th_crj"></div><div id="crj_yjk"></div><div id="th_zje"></div><div id="yj_zje"></div>'
        '<div id="kuanginfo">矿区面积: 使用年限: 矿种:</div>'
        '<div id="trans_time"></div>'
        '</div></body></html>'
    )

    _, html = build_land_result_notice_detail(payload, "https://example.com/detail", template_html)

    assert "项目编号：2026TDGP12R0007" in html
    assert "最高价:" in html
    assert "31,345" in html
    assert "万元" in html
    assert "2026-04-27 16:00" in html
    assert "62690000元" in html
    assert "出让金预交款" not in html
    assert "缴纳总金额" not in html
    assert "矿区面积" not in html
    assert "矿种" not in html
