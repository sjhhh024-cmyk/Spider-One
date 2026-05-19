from __future__ import annotations

import base64
import sys
from unittest.mock import patch

import pytest
import requests


from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from qdggzy_core import (  # noqa: E402
    HOME_URL,
    MoneyParser,
    PARENT_TYPE_MAPPING,
    QdggzySpider,
    build_record,
    build_records,
    extract_dynamic_list_records,
    extract_left_nav_tasks,
    build_static_list_page_url,
    extract_attachment_entries,
    extract_homepage_tasks,
    extract_list_records,
    extract_main_detail_html,
    normalize_text,
    parse_detail,
    resolve_output_board,
)


SAMPLES = {
    "qd_home.html": """
    <div class="tab-one public-upper">
      <ul class="clearfix">
        <li class="fl hdl public-upper-name active" data-target="3"><a href="javascript:void(0)">资源交易</a></li>
        <li class="fl hdl public-upper-name" data-target="4"><a href="javascript:void(0)">产权交易</a></li>
      </ul>
    </div>
    <div class="bdl tabview clearfix" data-target="3">
      <div class="tab-two fl">
        <ul>
          <li class="jsgc hdl active" data-target="1"><a href="javascript:void(0)"><span>土地出让公告</span></a></li>
          <li class="jsgc hdl" data-target="9"><a href="javascript:void(0)"><span>海洋资源成交结果</span></a></li>
        </ul>
      </div>
      <div>
        <div class="bdl fl notice-title" data-target="1" data-type="3" data-flag="1" data-pagesize="8" data-htmlid="tdcr1">
          <a href="/Tradeinfo-GGGSList/2-2-0">查看更多</a>
        </div>
        <div class="bdl fl notice-title" data-target="9" data-type="4" data-flag="204" data-pagesize="8" data-htmlid="tdcr9">
          <a href="/Tradeinfo-GGGSList/3-2-204">查看更多</a>
        </div>
      </div>
    </div>
    <div class="bdl tabview clearfix" data-target="4">
      <div class="tab-two fl">
        <ul>
          <li class="jsgc hdl active" data-target="1"><a href="javascript:void(0)"><span>企业国有产权挂牌披露</span></a></li>
          <li class="jsgc hdl" data-target="6"><a href="javascript:void(0)"><span>其他产权交易结果</span></a></li>
        </ul>
      </div>
      <div>
        <div class="bdl fl notice-title" data-target="1" data-type="4" data-flag="1" data-pagesize="8" data-htmlid="cqjy1">
          <a href="/Tradeinfo-GGGSList/3-3-1">查看更多</a>
        </div>
        <div class="bdl fl notice-title" data-target="6" data-type="4" data-flag="14" data-pagesize="8" data-htmlid="cqjy6">
          <a href="/Tradeinfo-GGGSList/3-3-14">查看更多</a>
        </div>
      </div>
    </div>
    """,
    "qd_list_build_bid.html": """
    <table>
      <tr>
        <td><a target="_blank" href="/TradeDetals-ZtbShow/179805-5021-0-0-0/67bfb4a4-982f-4f9e-81d8-2927a97ed697" title="平度市2026年高标准农田建设项目勘察设计">· [平度][公开] 平度市2026年高标准农田建设项目勘察设计</a></td>
        <td>2026-05-08 16:01:23</td>
      </tr>
      <tr>
        <td><a target="_blank" href="/TradeDetals-ZtbShow/179610-5021-0-0-0/432fd5fa-790e-4e15-b7d7-a84ceb702231" title="大荒庄村庄改造项目（集体经济发展用房）电梯采购及安装工程（暂估价）">· [西海岸][公开] 大荒庄村庄改造项目（集体经济发展用房）电梯采购及安装工程（暂估价）</a></td>
        <td>2026-05-08 15:00:00</td>
      </tr>
      <tr>
        <td><a target="_blank" href="/TradeDetals-ZtbShow/178709-5021-0-0-0/a76ca700-8f9e-4563-a0bb-b826ba6ca7d2" title="经控未来云谷项目（一期、二期）（第二批）施工（评定分离）">· [西海岸][公开] 经控未来云谷项目（一期、二期）（第二批）施工（评定分离）</a></td>
        <td>2026-05-08 14:00:00</td>
      </tr>
    </table>
    """,
    "qd_detail_gov.html": """
    <html><body>
      <div id="htmlTable">
        <p class="title_p"><span>青岛市疾病预防控制中心青岛市公共卫生中心疾控内配物资（办公家具）采购项目公开招标公告</span></p>
        <p class="details_p"><span class="l_span">采购项目编号（建议书编号）：</span><span class="r_span">SDGP370200000202601001909</span></p>
        <p class="details_p"><span class="l_span">采购项目名称：</span><span class="r_span">青岛市公共卫生中心疾控内配物资（办公家具）采购项目</span></p>
        <p class="details_p"><span class="l_span">预算金额与最高限价：</span></p>
        <p class="details_p"><span class="r_span">本项目预算金额为 3290500.00 元，其中：第 一 包 3290500.00 元。</span></p>
        <p class="details_p"><span class="l_span">联系人（采购人）：</span><span class="r_span">青岛市疾病预防控制中心</span></p>
        <p class="details_p"><span class="l_span">项目联系人（代理机构）：</span><span class="r_span">倪工</span></p>
        <a href="/PortalQDManage/PortalQD/GetZbDownLoad?id=109738&filePOrB=2">青岛市公共卫生中心疾控内配物资（办公家具）采购项目.pdf</a>
        <a href="/PortalQDManage/PortalQD/GetZbDownLoad?id=179992&filePOrB=1">下载电子招标文件</a>
      </div>
    </body></html>
    """,
    "qd_detail_build.html": """
    <html><body>
      <div id="htmlTable">
        <div class="tle">平度市2026年高标准农田建设项目勘察设计招标公告</div>
        <table>
          <tr><td>公告发布日期：</td><td>2026/05/08 16:01:23</td></tr>
          <tr><td>项目名称:</td><td>平度市2026年高标准农田建设项目勘察设计</td></tr>
          <tr><td>建设单位：</td><td>平度市农业农村局</td></tr>
          <tr><td>招标单位：</td><td>平度市农业农村局</td></tr>
          <tr><td>项目统一代码（编码）：</td><td>2502-370283-04-01-286243</td></tr>
        </table>
        <a href="/PortalQDManage/PortalQD/GetZbDownLoad?id=109728&filePOrB=2">平度市2026年高标准农田建设项目勘察设计1标段.pdf</a>
        <a href="/PortalQDManage/PortalQD/GetZbDownLoad?id=179805&filePOrB=1">下载电子招标文件</a>
      </div>
    </body></html>
    """,
}


def read_sample(name: str) -> str:
    return SAMPLES[name]


def test_resolve_output_board_maps_common_notice_names() -> None:
    cases = {
        "采购公告": "招标公告",
        "公开招标公告": "招标公告",
        "竞争性磋商公告": "招标公告",
        "需求公示": "采购意向",
        "招标计划": "采购意向",
        "预中标公示": "候选人公告",
        "入围投标人公示（评定分离）": "候选人公告",
        "中标公告": "中标公告",
        "合同签订公示": "中标公告",
        "废标公告": "中标公告",
    }

    for notice_name, expected in cases.items():
        assert resolve_output_board(notice_name) == expected


def test_extract_homepage_tasks_reads_module_and_notice_config() -> None:
    html = """
    <div class="tab-one public-upper">
      <ul class="clearfix">
        <li class="fl hdl public-upper-name active" data-target="1" data-type="0" data-flag="0" data-pagesize="10" data-htmlid="jsgc1">
          <a href="javascript:void(0)">建设工程</a>
        </li>
      </ul>
    </div>
    <div class="bdl tabview clearfix" data-target="1" style="display: block;">
      <div class="tab-two fl">
        <ul>
          <li class="jsgc hdl active" data-target="1"><a href="javascript:void(0)"><span>招标公告</span></a></li>
          <li class="jsgc hdl" data-target="3"><a href="javascript:void(0)"><span>预中标公示</span></a></li>
        </ul>
      </div>
      <div>
        <div class="bdl fl notice-title" data-target="1" data-type="0" data-flag="0" data-pagesize="10" data-htmlid="jsgc1" style="display: block;">
          <a href="/Tradeinfo-GGGSList/0-0-0" target="_blank">查看更多 &gt;</a>
        </div>
        <div class="bdl fl notice-title" data-target="3" data-type="0" data-flag="2" data-pagesize="10" data-htmlid="jsgc3" style="display: none;">
          <a href="/Tradeinfo-GGGSList/0-0-2" target="_blank">查看更多 &gt;</a>
        </div>
      </div>
    </div>
    """

    tasks = extract_homepage_tasks(html)

    assert len(tasks) == 2
    assert tasks[0]["module_name"] == "建设工程"
    assert tasks[0]["notice_type"] == "招标公告"
    assert tasks[0]["type"] == "0"
    assert tasks[0]["flag"] == "0"
    assert tasks[0]["list_path"] == "/Tradeinfo-GGGSList/0-0-0"
    assert tasks[1]["notice_type"] == "预中标公示"
    assert tasks[1]["flag"] == "2"


def test_extract_main_detail_html_prefers_html_table() -> None:
    html = """
    <html><body>
      <div class="box_bg">壳层内容</div>
      <div id="htmlTable">
        <p class="title_p">公告标题</p>
        <p class="content_p">正文内容</p>
      </div>
    </body></html>
    """

    detail_html = extract_main_detail_html(html)

    assert "公告标题" in detail_html
    assert "正文内容" in detail_html
    assert "壳层内容" not in normalize_text(detail_html)


def test_extract_attachment_entries_collects_download_links() -> None:
    html = """
    <div id="htmlTable">
      <a href="/PortalQDManage/PortalQD/GetZbDownLoad?id=109738&filePOrB=2">
        青岛市公共卫生中心疾控内配物资（办公家具）采购项目.pdf
      </a>
      <a href="/PortalQDManage/PortalQD/GetZbDownLoad?id=179992&filePOrB=1">下载电子招标文件</a>
    </div>
    """

    attachments = extract_attachment_entries(
        html,
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )

    assert attachments == [
        {
            "fileUrl": "https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/GetZbDownLoad?id=109738&filePOrB=2",
            "fileType": "pdf",
            "fileName": "青岛市公共卫生中心疾控内配物资（办公家具）采购项目.pdf",
        },
        {
            "fileUrl": "https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/GetZbDownLoad?id=179992&filePOrB=1",
            "fileType": "",
            "fileName": "下载电子招标文件",
        },
    ]


def test_extract_list_records_reads_build_list_cards() -> None:
    records = extract_list_records(
        read_sample("qd_list_build_bid.html"),
        "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/0-0-0",
    )

    assert len(records) >= 3
    assert records[0]["title"] == "平度市2026年高标准农田建设项目勘察设计"
    assert records[0]["detail_url"].startswith("https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179805-5021-0-0-0/")
    assert records[0]["region"] == "平度"
    assert records[0]["trade_method"] == "公开"


def test_extract_dynamic_list_records_reads_api_json_cards() -> None:
    payload = {
        "Code": 100,
        "msg": "查询成功",
        "data": {
            "classId": "5021",
            "type": 0,
            "flag": 0,
            "zbflag": 0,
            "Ggglist": [
                {
                    "ID": 179792,
                    "classid": 1009,
                    "ProjectName": "青岛青铁智慧城市服务运营管理有限公司（青岛地铁集团有限公司）登瀛车辆段二期1.742MW光伏项目（工程总承包）",
                    "keyguid": "b5fca7de-2897-497f-94e7-a7dce301bd45",
                    "type": 0,
                    "flag": 2,
                    "zbflag": 0,
                    "Dates": "2026-05-09",
                    "AreaName": "崂山区",
                    "ZBflagName": "公开",
                }
            ]
        },
    }

    records = extract_dynamic_list_records(payload)

    assert records == [
        {
            "title": "青岛青铁智慧城市服务运营管理有限公司（青岛地铁集团有限公司）登瀛车辆段二期1.742MW光伏项目（工程总承包）",
            "detail_url": "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179792-5021-0-0-0/b5fca7de-2897-497f-94e7-a7dce301bd45",
            "region": "崂山区",
            "trade_method": "公开",
            "publish_time": "2026-05-09",
        }
    ]


def test_extract_dynamic_list_records_uses_guoqi_detail_url_pattern() -> None:
    payload = {
        "Code": 100,
        "msg": "查询成功",
        "data": {
            "classId": "5021",
            "type": 7,
            "flag": 2,
            "zbflag": 0,
            "Ggglist": [
                {
                    "ID": 17067,
                    "ProjectName": "离心机采购项目(二次)中标结果公示",
                    "keyguid": "",
                    "Dates": "2026-05-10",
                    "AreaName": "青岛市",
                    "ZBflagName": "",
                }
            ],
        },
    }

    records = extract_dynamic_list_records(payload)

    assert records == [
        {
            "title": "离心机采购项目(二次)中标结果公示",
            "detail_url": "https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/17067?flag=2",
            "region": "青岛市",
            "trade_method": "",
            "publish_time": "2026-05-10",
        }
    ]


def test_extract_homepage_tasks_keeps_resource_and_property_modules() -> None:
    tasks = extract_homepage_tasks(read_sample("qd_home.html"))

    notice_pairs = {(task["module_name"], task["notice_type"]) for task in tasks}

    assert ("资源交易", "土地出让公告") in notice_pairs
    assert ("资源交易", "海洋资源成交结果") in notice_pairs
    assert ("产权交易", "企业国有产权挂牌披露") in notice_pairs
    assert ("产权交易", "其他产权交易结果") in notice_pairs
    assert PARENT_TYPE_MAPPING["资源交易"] == "资源交易"
    assert PARENT_TYPE_MAPPING["产权交易"] == "产权交易"


def test_extract_left_nav_tasks_reads_guoqi_and_wuxingzichan_groups() -> None:
    html = """
    <div class="vtitle" id="nav8"><em class="v v01"></em>国企采购</div>
    <div class="vcon" style="display: none;">
      <ul class="vconlist clearfix">
        <li><a id="gy1" href="/Tradeinfo-GGGSList/7-7-0">采购公告</a></li>
        <li><a id="gy3" href="/Tradeinfo-GGGSList/7-7-2">中标公告</a></li>
      </ul>
    </div>
    <div class="vtitle" id="nav100"><em class="v v01"></em>无形资产</div>
    <div class="vcon" style="display: none;">
      <ul class="vconlist clearfix">
        <li><a id="txjy1" href="/Tradeinfo-GGGSList/0-99-0">招标公告</a></li>
        <li><a id="txjy2" href="/Tradeinfo-GGGSList/0-99-4">资格审查</a></li>
        <li><a id="txjy3" href="/Tradeinfo-GGGSList/0-99-2">预中标公示</a></li>
        <li><a id="txjy4" href="/Tradeinfo-GGGSList/0-99-3">废标公告</a></li>
        <li><a id="txjy5" href="/Tradeinfo-GGGSList/0-99-8">中标公告</a></li>
        <li><a id="txjy8" href="/Tradeinfo-GGGSList/0-99-18">合同签订公示</a></li>
      </ul>
    </div>
    """

    tasks = extract_left_nav_tasks(html)
    notice_pairs = {(task["module_name"], task["notice_type"], task["list_path"]) for task in tasks}

    assert ("国企采购", "采购公告", "/Tradeinfo-GGGSList/7-7-0") in notice_pairs
    assert ("国企采购", "中标公告", "/Tradeinfo-GGGSList/7-7-2") in notice_pairs
    assert ("无形资产", "招标公告", "/Tradeinfo-GGGSList/0-99-0") in notice_pairs
    assert ("无形资产", "合同签订公示", "/Tradeinfo-GGGSList/0-99-18") in notice_pairs


def test_filter_tasks_keeps_split_guoqi_and_wuxingzichan_entries() -> None:
    spider = QdggzySpider()
    tasks = [
        {
            "module_name": "国企采购",
            "notice_type": "采购公告",
            "type": "7",
            "flag": "0",
            "page_size": "10",
            "html_id": "gy1",
            "class_id": "",
            "list_path": "/Tradeinfo-GGGSList/7-7-0",
        },
        {
            "module_name": "国企采购",
            "notice_type": "中标公告",
            "type": "7",
            "flag": "2",
            "page_size": "10",
            "html_id": "gy3",
            "class_id": "",
            "list_path": "/Tradeinfo-GGGSList/7-7-2",
        },
        {
            "module_name": "无形资产",
            "notice_type": "中标公告",
            "type": "99",
            "flag": "8",
            "page_size": "10",
            "html_id": "txjy5",
            "class_id": "",
            "list_path": "/Tradeinfo-GGGSList/0-99-8",
        },
    ]

    filtered = spider.filter_tasks(tasks)
    notice_pairs = {(task.module_name, task.notice_type, task.list_path) for task in filtered}

    assert ("国企采购", "采购公告", "/Tradeinfo-GGGSList/7-7-0") in notice_pairs
    assert ("国企采购", "中标公告", "/Tradeinfo-GGGSList/7-7-2") in notice_pairs
    assert ("无形资产", "中标公告", "/Tradeinfo-GGGSList/0-99-8") in notice_pairs


def test_filter_tasks_limits_scope_to_requested_modules_and_notice_types() -> None:
    spider = QdggzySpider()
    tasks = [
        {"module_name": "建设工程", "notice_type": "招标公告", "type": "0", "flag": "0", "page_size": "10", "html_id": "a", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-0-0"},
        {"module_name": "建设工程", "notice_type": "资格审查", "type": "0", "flag": "4", "page_size": "10", "html_id": "b", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-0-4"},
        {"module_name": "建设工程", "notice_type": "入围投标人公示（评定分离）", "type": "0", "flag": "20", "page_size": "10", "html_id": "c", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-0-20"},
        {"module_name": "建设工程", "notice_type": "预中标公示", "type": "0", "flag": "2", "page_size": "10", "html_id": "d", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-0-2"},
        {"module_name": "建设工程", "notice_type": "中标公告", "type": "0", "flag": "8", "page_size": "10", "html_id": "e", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-0-8"},
        {"module_name": "建设工程", "notice_type": "合同签订公示", "type": "0", "flag": "18", "page_size": "10", "html_id": "e2", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-0-18"},
        {"module_name": "政府采购", "notice_type": "采购公告", "type": "1", "flag": "0", "page_size": "10", "html_id": "f", "class_id": "", "list_path": "/Tradeinfo-GGGSList/1-1-0"},
        {"module_name": "政府采购", "notice_type": "中标公告", "type": "1", "flag": "2", "page_size": "10", "html_id": "g", "class_id": "", "list_path": "/Tradeinfo-GGGSList/1-1-2"},
        {"module_name": "政府采购", "notice_type": "合同签订公示", "type": "1", "flag": "18", "page_size": "10", "html_id": "g2", "class_id": "", "list_path": "/Tradeinfo-GGGSList/1-1-18"},
        {"module_name": "政府采购", "notice_type": "废标公告", "type": "1", "flag": "3", "page_size": "10", "html_id": "h", "class_id": "", "list_path": "/Tradeinfo-GGGSList/1-1-3"},
        {"module_name": "国企采购", "notice_type": "采购公告", "type": "7", "flag": "0", "page_size": "10", "html_id": "i", "class_id": "", "list_path": "/Tradeinfo-GGGSList/7-7-0"},
        {"module_name": "国企采购", "notice_type": "中标公告", "type": "7", "flag": "2", "page_size": "10", "html_id": "j", "class_id": "", "list_path": "/Tradeinfo-GGGSList/7-7-2"},
        {"module_name": "无形资产", "notice_type": "招标公告", "type": "99", "flag": "0", "page_size": "10", "html_id": "k", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-99-0"},
        {"module_name": "无形资产", "notice_type": "预中标公示", "type": "99", "flag": "2", "page_size": "10", "html_id": "l", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-99-2"},
        {"module_name": "无形资产", "notice_type": "中标公告", "type": "99", "flag": "8", "page_size": "10", "html_id": "m", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-99-8"},
        {"module_name": "无形资产", "notice_type": "合同签订公示", "type": "99", "flag": "18", "page_size": "10", "html_id": "n", "class_id": "", "list_path": "/Tradeinfo-GGGSList/0-99-18"},
        {"module_name": "产权交易", "notice_type": "企业国有产权挂牌披露", "type": "4", "flag": "1", "page_size": "10", "html_id": "o", "class_id": "", "list_path": "/Tradeinfo-GGGSList/3-3-1"},
    ]

    filtered = spider.filter_tasks(tasks)
    notice_pairs = {(task.module_name, task.notice_type) for task in filtered}

    assert notice_pairs == {
        ("建设工程", "招标公告"),
        ("建设工程", "入围投标人公示（评定分离）"),
        ("建设工程", "预中标公示"),
        ("建设工程", "中标公告"),
        ("建设工程", "合同签订公示"),
        ("政府采购", "采购公告"),
        ("政府采购", "中标公告"),
        ("政府采购", "合同签订公示"),
        ("国企采购", "采购公告"),
        ("国企采购", "中标公告"),
        ("无形资产", "招标公告"),
        ("无形资产", "预中标公示"),
        ("无形资产", "中标公告"),
        ("无形资产", "合同签订公示"),
    }


def test_build_static_list_page_url_returns_first_page_path_for_special_modules() -> None:
    task = {"module_name": "产权交易", "list_path": "/Tradeinfo-GGGSList/3-3-1"}

    assert build_static_list_page_url(task, 1) == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/3-3-1"
    assert build_static_list_page_url(task, 2) == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/3-3-1?pageIndex=2"


def test_extract_list_records_reads_guoqi_static_detail_links() -> None:
    html = """
    <table>
      <tr>
        <td><a target="_blank" href="/PortalQDManage/PortalQD/ZtbShowGY/30000?flag=0" title="测试国企采购公告">· [市直][公开] 测试国企采购公告</a></td>
        <td>2026-05-10</td>
      </tr>
    </table>
    """

    records = extract_list_records(html, "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/7-7-0")

    assert records == [
        {
            "title": "测试国企采购公告",
            "detail_url": "https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/30000?flag=0",
            "region": "市直",
            "trade_method": "公开",
            "publish_time": "2026-05-10",
        }
    ]


def test_extract_list_records_reads_contract_htgs_detail_links() -> None:
    html = """
    <table>
      <tr>
        <td class="box_td"><a target="_blank" href="/Contact-HTGS/208215" title="山东港口青岛港前湾港区干散货码头配套工程监理合同">· 山东港口青岛港前湾港区干散货码头配套工程监理合同</a></td>
        <td>2026-04-30</td>
      </tr>
    </table>
    """

    records = extract_list_records(html, "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/0-0-18")

    assert records == [
        {
            "title": "山东港口青岛港前湾港区干散货码头配套工程监理合同",
            "detail_url": "https://ggzy.qingdao.gov.cn/Contact-HTGS/208215",
            "region": "",
            "trade_method": "",
            "publish_time": "2026-04-30",
        }
    ]


def test_parse_detail_falls_back_to_page_title_when_html_table_missing() -> None:
    html = """
    <html>
      <head><title>青岛产权交易所-医疗生产机器设备及其配套设备资产包（A资产包）项目详情</title></head>
      <body>
        <div class="article">
          <h1>医疗生产机器设备及其配套设备资产包（A资产包）项目详情</h1>
          <p>挂牌日期：2026-05-01</p>
        </div>
      </body>
    </html>
    """

    detail = parse_detail(html, "https://cqjy.qdcq.net/portal/pro/index.jsp?packId=&proId=abc")

    assert detail["title"] == "医疗生产机器设备及其配套设备资产包（A资产包）项目详情"
    assert "挂牌日期" in detail["plain_text"]


def test_parse_detail_reads_guoqi_box_item_layout() -> None:
    html = """
    <div id="htmlTable">
      <style>
        .box-content { color: red; }
      </style>
      <div class="box-content">
        <div class="box-title">项目概况</div>
        <div class="box-item">
          <div class="item-title">项目名称:</div>
          <div class="item-msg">青岛海水淡化有限公司2025年度企业所得税汇算清缴纳税申报审核项目</div>
        </div>
        <div class="box-item">
          <div class="item-title">标段编号:</div>
          <div class="item-msg">JJCG（SWZY）20260506000005-0001</div>
        </div>
      </div>
      <div class="box-content">
        <div class="box-item">
          <div class="item-title">中标单位名称:</div>
          <div class="item-msg">青岛正业税务师事务所有限责任公司</div>
        </div>
      </div>
    </div>
    """

    detail = parse_detail(html, "https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/17052?flag=2")

    assert detail["title"] == "青岛海水淡化有限公司2025年度企业所得税汇算清缴纳税申报审核项目"
    assert detail["field_map"]["项目名称"] == "青岛海水淡化有限公司2025年度企业所得税汇算清缴纳税申报审核项目"
    assert detail["field_map"]["标段编号"] == "JJCG（SWZY）20260506000005-0001"
    assert detail["field_map"]["中标单位名称"] == "青岛正业税务师事务所有限责任公司"
    assert ".box-content" not in detail["plain_text"]


def test_build_record_outputs_win_record_for_result_notice() -> None:
    detail = parse_detail(
        read_sample("qd_detail_gov.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )
    task = {"module_name": "政府采购", "notice_type": "中标公告"}
    card = {"publish_time": "2026-05-06 21:04", "region": "市本级"}

    class _FakeTenderModel:
        def get_result(self, content: str) -> dict[str, object]:
            assert "采购项目名称" in content
            return {
                "tenderTitle": "模型中标标题",
                "tenderNumber": "MODEL-WIN-001",
                "procurementUnit": "模型采购单位",
                "result": [
                    {
                        "relationCompanyName": "模型中标供应商",
                        "contactName": "模型联系人",
                        "contactTelephone": "400-800-1234",
                        "renderMoney": "3284600.00元",
                    }
                ],
            }

    record = build_record(task, card, detail, model_clients={"中标公告": _FakeTenderModel()})

    assert record["announcementType"] == 2
    assert record["tenderTitle"] == "模型中标标题"
    assert record["tenderNumber"] == "MODEL-WIN-001"
    assert record["procurementUnit"] == "模型采购单位"
    assert record["renderMoney"] == "3284600.00元"
    assert record["relationCompanyName"] == "模型中标供应商"
    assert record["contactName"] == "模型联系人"
    assert record["contactTelephone"] == "400-800-1234"


def test_build_records_keeps_only_first_win_model_result() -> None:
    detail = parse_detail(
        read_sample("qd_detail_gov.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )
    task = {"module_name": "政府采购", "notice_type": "中标公告"}
    card = {"publish_time": "2026-05-06 21:04", "region": "市本级"}

    class _FakeTenderModel:
        def get_result(self, content: str) -> dict[str, object]:
            return {
                "tenderTitle": "模型中标标题",
                "tenderNumber": "MODEL-WIN-002",
                "procurementUnit": "模型采购单位",
                "result": [
                    {
                        "relationCompanyName": "供应商甲",
                        "contactName": "联系人甲",
                        "contactTelephone": "111",
                        "renderMoney": "100元",
                    },
                    {
                        "relationCompanyName": "供应商乙",
                        "contactName": "联系人乙",
                        "contactTelephone": "222",
                        "renderMoney": "200元",
                    },
                ],
            }

    records = build_records(task, card, detail, model_clients={"中标公告": _FakeTenderModel()})

    assert len(records) == 1
    assert records[0]["relationCompanyName"] == "供应商甲"
    assert records[0]["renderMoney"] == "100元"


def test_spider_filters_tasks_by_output_board_when_requested() -> None:
    spider = QdggzySpider(output_board_filter="候选人公告")
    tasks = [
        {"module_name": "建设工程", "notice_type": "招标公告", "type": "0", "flag": "0", "page_size": "10", "html_id": "a", "class_id": "", "list_path": "/a"},
        {"module_name": "建设工程", "notice_type": "预中标公示", "type": "0", "flag": "2", "page_size": "10", "html_id": "b", "class_id": "", "list_path": "/b"},
        {"module_name": "政府采购", "notice_type": "中标公告", "type": "1", "flag": "2", "page_size": "10", "html_id": "c", "class_id": "", "list_path": "/c"},
    ]

    filtered = spider.filter_tasks(tasks)

    assert len(filtered) == 1
    assert filtered[0].notice_type == "预中标公示"


def test_spider_filters_tasks_by_notice_type_when_requested() -> None:
    spider = QdggzySpider(module_name="建设工程", notice_type_filter="合同签订公示")
    tasks = [
        {"module_name": "建设工程", "notice_type": "招标公告", "type": "0", "flag": "0", "page_size": "10", "html_id": "a", "class_id": "", "list_path": "/a"},
        {"module_name": "建设工程", "notice_type": "中标公告", "type": "0", "flag": "8", "page_size": "10", "html_id": "b", "class_id": "", "list_path": "/b"},
        {"module_name": "建设工程", "notice_type": "合同签订公示", "type": "0", "flag": "18", "page_size": "10", "html_id": "c", "class_id": "", "list_path": "/c"},
        {"module_name": "政府采购", "notice_type": "合同签订公示", "type": "1", "flag": "18", "page_size": "10", "html_id": "d", "class_id": "", "list_path": "/d"},
    ]

    filtered = spider.filter_tasks(tasks)

    assert len(filtered) == 1
    assert filtered[0].module_name == "建设工程"
    assert filtered[0].notice_type == "合同签订公示"


def test_fetch_list_page_posts_page_size_parameter_for_dynamic_modules() -> None:
    spider = QdggzySpider()
    called: dict[str, object] = {}

    class _FakeResponse:
        text = "ok"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int):
        called["home_get"] = {"url": url, "timeout": timeout}
        return _FakeResponse()

    def fake_post(url: str, data: dict[str, str], timeout: int):
        called["post"] = {"url": url, "data": data, "timeout": timeout}
        return _FakeResponse()

    spider.session.get = fake_get  # type: ignore[assignment]
    spider.session.post = fake_post  # type: ignore[assignment]
    task = type(
        "Task",
        (),
        {
            "module_name": "建设工程",
            "notice_type": "招标公告",
            "type": "0",
            "flag": "0",
            "page_size": 8,
            "html_id": "x",
            "class_id": "",
            "list_path": "/Tradeinfo-GGGSList/0-0-0",
        },
    )()

    spider.fetch_list_page(task, 2)

    assert called["post"] == {
        "url": "https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/PartialZTBNew",
        "data": {
            "type": "0",
            "flag": "0",
            "page": "2",
            "pageSize": "10",
        },
        "timeout": 20,
    }


def test_fetch_list_page_returns_dynamic_api_json_text() -> None:
    spider = QdggzySpider()

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    spider.session.get = lambda url, timeout: _FakeResponse("<html></html>")  # type: ignore[assignment]
    spider.session.post = lambda url, data, timeout: _FakeResponse('{"Code":100,"data":{"Ggglist":[]}}')  # type: ignore[assignment]
    task = type(
        "Task",
        (),
        {
            "module_name": "建设工程",
            "notice_type": "招标公告",
            "type": "0",
            "flag": "0",
            "page_size": 8,
            "html_id": "x",
            "class_id": "",
            "list_path": "/Tradeinfo-GGGSList/0-0-0",
        },
    )()

    result = spider.fetch_list_page(task, 1)

    assert '"Ggglist"' in result


def test_fetch_list_page_uses_static_page_index_for_guoqi_module() -> None:
    spider = QdggzySpider()
    get_calls: list[dict[str, object]] = []
    post_calls: list[dict[str, object]] = []

    class _FakeResponse:
        text = "<html></html>"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int):
        get_calls.append({"url": url, "timeout": timeout})
        return _FakeResponse()

    def fake_post(url: str, data: dict[str, str], timeout: int):
        post_calls.append({"url": url, "data": data, "timeout": timeout})
        return _FakeResponse()

    spider.session.get = fake_get  # type: ignore[assignment]
    spider.session.post = fake_post  # type: ignore[assignment]
    task = type(
        "Task",
        (),
        {
            "module_name": "国企采购",
            "notice_type": "采购公告",
            "type": "7",
            "flag": "0",
            "page_size": 10,
            "html_id": "gy1",
            "class_id": "",
            "list_path": "/Tradeinfo-GGGSList/7-7-0",
        },
    )()

    spider.fetch_list_page(task, 2)

    assert get_calls == [
        {"url": HOME_URL, "timeout": 20},
        {"url": "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/7-7-0?pageIndex=2", "timeout": 20},
    ]
    assert post_calls == []


def test_fetch_list_page_uses_static_page_index_for_contract_notice() -> None:
    spider = QdggzySpider()
    get_calls: list[dict[str, object]] = []
    post_calls: list[dict[str, object]] = []

    class _FakeResponse:
        text = "<html></html>"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int):
        get_calls.append({"url": url, "timeout": timeout})
        return _FakeResponse()

    def fake_post(url: str, data: dict[str, str], timeout: int):
        post_calls.append({"url": url, "data": data, "timeout": timeout})
        return _FakeResponse()

    spider.session.get = fake_get  # type: ignore[assignment]
    spider.session.post = fake_post  # type: ignore[assignment]
    task = type(
        "Task",
        (),
        {
            "module_name": "建设工程",
            "notice_type": "合同签订公示",
            "type": "0",
            "flag": "18",
            "page_size": 10,
            "html_id": "jsgc7",
            "class_id": "",
            "list_path": "/Tradeinfo-GGGSList/0-0-18?ClassId=1",
            "sub_type": "房屋建筑",
        },
    )()

    spider.fetch_list_page(task, 2)

    assert get_calls == [
        {"url": HOME_URL, "timeout": 20},
        {"url": "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/0-0-18?ClassId=1&pageIndex=2", "timeout": 20},
    ]
    assert post_calls == []


def test_fetch_detail_sets_home_referer_for_guoqi_detail_page() -> None:
    spider = QdggzySpider()
    calls: list[tuple[str, str, dict[str, str] | None]] = []

    class _FakeResponse:
        def __init__(self, text: str = "ok") -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int, headers: dict[str, str] | None = None):
        calls.append((url, str(timeout), headers))
        return _FakeResponse("<div id='htmlTable'><h1>详情页</h1></div>")

    spider.session.get = fake_get  # type: ignore[assignment]

    spider.fetch_detail("https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/30000?flag=0")

    assert calls[0] == (HOME_URL, "20", None)
    assert calls[1][0] == "https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/30000?flag=0"
    assert calls[1][2] == {"Referer": HOME_URL}


def test_fetch_detail_retries_guoqi_shell_page_until_real_content() -> None:
    spider = QdggzySpider()
    calls: list[tuple[str, str, dict[str, str] | None]] = []
    shell_html = "<div id='htmlTable'><div>交易信息详情</div></div>"
    content_html = """
    <div id="htmlTable">
      <div class="divMainContent">
        <div class="big_title"><h2>公告名称：测试国企采购公告</h2></div>
        <div class="table-box">
          <table><tr><td>采购单位</td><td>测试公司</td></tr></table>
        </div>
      </div>
    </div>
    """
    responses = ["<html></html>", shell_html, shell_html, content_html]

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int, headers: dict[str, str] | None = None):
        calls.append((url, str(timeout), headers))
        return _FakeResponse(responses.pop(0))

    spider.session.get = fake_get  # type: ignore[assignment]

    detail = spider.fetch_detail("https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/30000?flag=0")

    assert len(calls) == 4
    assert calls[0] == (HOME_URL, "20", None)
    assert calls[1][2] == {"Referer": HOME_URL}
    assert calls[2][2] == {"Referer": HOME_URL}
    assert calls[3][2] == {"Referer": HOME_URL}
    assert "采购单位" in detail["plain_text"]
    assert "测试公司" in detail["plain_text"]


def test_fetch_detail_retries_guoqi_request_errors_until_real_content() -> None:
    spider = QdggzySpider()
    calls: list[tuple[str, str, dict[str, str] | None]] = []
    content_html = """
    <div id="htmlTable">
      <div class="divMainContent">
        <div class="big_title"><h2>公告名称：测试国企采购公告</h2></div>
        <div class="table-box">
          <table><tr><td>采购单位</td><td>测试公司</td></tr></table>
        </div>
      </div>
    </div>
    """
    responses: list[object] = [
        "<html></html>",
        requests.ConnectionError("boom-1"),
        requests.ConnectionError("boom-2"),
        content_html,
    ]

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int, headers: dict[str, str] | None = None):
        calls.append((url, str(timeout), headers))
        current = responses.pop(0)
        if isinstance(current, Exception):
            raise current
        return _FakeResponse(current)

    spider.session.get = fake_get  # type: ignore[assignment]

    detail = spider.fetch_detail("https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/30000?flag=0")

    assert len(calls) == 4
    assert calls[0] == (HOME_URL, "20", None)
    assert calls[1][2] == {"Referer": HOME_URL}
    assert calls[2][2] == {"Referer": HOME_URL}
    assert calls[3][2] == {"Referer": HOME_URL}
    assert "采购单位" in detail["plain_text"]
    assert "测试公司" in detail["plain_text"]


def test_fetch_detail_raises_when_guoqi_shell_page_retries_exhausted() -> None:
    spider = QdggzySpider()
    calls: list[tuple[str, str, dict[str, str] | None]] = []
    shell_html = "<div id='htmlTable'><div>交易信息详情</div></div>"
    responses = ["<html></html>"] + [shell_html] * 6

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int, headers: dict[str, str] | None = None):
        calls.append((url, str(timeout), headers))
        return _FakeResponse(responses.pop(0))

    spider.session.get = fake_get  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="壳页"):
        spider.fetch_detail("https://ggzy.qingdao.gov.cn/PortalQDManage/PortalQD/ZtbShowGY/30000?flag=0")

    assert len(calls) == 7


def test_fetch_homepage_tasks_merges_left_nav_tasks_from_static_list_page() -> None:
    spider = QdggzySpider()
    calls: list[str] = []

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    home_html = """
    <div class="tab-one public-upper">
      <ul class="clearfix">
        <li class="fl hdl public-upper-name active" data-target="7"><a href="javascript:void(0)">国企采购</a></li>
      </ul>
    </div>
    <div class="bdl tabview clearfix" data-target="7">
      <div class="tab-two fl">
        <ul>
          <li class="jsgc hdl active" data-target="1"><a href="javascript:void(0)"><span>国企采购</span></a></li>
        </ul>
      </div>
      <div>
        <div class="bdl fl notice-title" data-target="1" data-type="7" data-flag="0" data-pagesize="10" data-htmlid="gy1">
          <a href="/Tradeinfo-GGGSList/7-7-0">查看更多</a>
        </div>
      </div>
    </div>
    """
    left_nav_html = """
    <div class="vtitle" id="nav8"><em class="v v01"></em>国企采购</div>
    <div class="vcon" style="display: none;">
      <ul class="vconlist clearfix">
        <li><a id="gy1" href="/Tradeinfo-GGGSList/7-7-0">采购公告</a></li>
        <li><a id="gy3" href="/Tradeinfo-GGGSList/7-7-2">中标公告</a></li>
      </ul>
    </div>
    <div class="vtitle" id="nav100"><em class="v v01"></em>无形资产</div>
    <div class="vcon" style="display: none;">
      <ul class="vconlist clearfix">
        <li><a id="txjy1" href="/Tradeinfo-GGGSList/0-99-0">招标公告</a></li>
        <li><a id="txjy5" href="/Tradeinfo-GGGSList/0-99-8">中标公告</a></li>
      </ul>
    </div>
    """

    def fake_get(url: str, timeout: int):
        calls.append(url)
        if url == "https://ggzy.qingdao.gov.cn/PortalQDManage/":
            return _FakeResponse(home_html)
        if url == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/6-6-12":
            return _FakeResponse(left_nav_html)
        raise AssertionError(f"unexpected url: {url}")

    spider.session.get = fake_get  # type: ignore[assignment]

    tasks = spider.fetch_homepage_tasks()
    notice_pairs = {(task.module_name, task.notice_type, task.list_path) for task in tasks}

    assert ("国企采购", "采购公告", "/Tradeinfo-GGGSList/7-7-0") in notice_pairs
    assert ("国企采购", "中标公告", "/Tradeinfo-GGGSList/7-7-2") in notice_pairs
    assert ("无形资产", "招标公告", "/Tradeinfo-GGGSList/0-99-0") in notice_pairs
    assert ("无形资产", "中标公告", "/Tradeinfo-GGGSList/0-99-8") in notice_pairs
    assert "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/6-6-12" in calls


def test_fetch_homepage_tasks_prefers_left_nav_notice_name_over_mixed_homepage_name() -> None:
    spider = QdggzySpider()

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    home_html = """
    <div class="tab-one public-upper">
      <ul class="clearfix">
        <li class="fl hdl public-upper-name active" data-target="99"><a href="javascript:void(0)">无形资产</a></li>
      </ul>
    </div>
    <div class="bdl tabview clearfix" data-target="99">
      <div class="tab-two fl">
        <ul>
          <li class="jsgc hdl active" data-target="5"><a href="javascript:void(0)"><span>中标公告 合同签订公示</span></a></li>
        </ul>
      </div>
      <div>
        <div class="bdl fl notice-title" data-target="5" data-type="99" data-flag="8" data-pagesize="10" data-htmlid="txjy5">
          <a href="/Tradeinfo-GGGSList/0-99-8">查看更多</a>
        </div>
      </div>
    </div>
    """
    left_nav_html = """
    <div class="vtitle" id="nav100"><em class="v v01"></em>无形资产</div>
    <div class="vcon" style="display: none;">
      <ul class="vconlist clearfix">
        <li><a id="txjy5" href="/Tradeinfo-GGGSList/0-99-8">中标公告</a></li>
      </ul>
    </div>
    """

    def fake_get(url: str, timeout: int):
        if url == "https://ggzy.qingdao.gov.cn/PortalQDManage/":
            return _FakeResponse(home_html)
        if url == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/6-6-12":
            return _FakeResponse(left_nav_html)
        raise AssertionError(f"unexpected url: {url}")

    spider.session.get = fake_get  # type: ignore[assignment]

    tasks = spider.fetch_homepage_tasks()
    matching = [task for task in tasks if task.list_path == "/Tradeinfo-GGGSList/0-99-8"]

    assert len(matching) == 1
    assert matching[0].notice_type == "中标公告"


def test_fetch_homepage_tasks_expands_construction_contract_secondary_types() -> None:
    spider = QdggzySpider(
        module_name="建设工程",
        notice_type_filter="合同签订公示",
    )

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    home_html = """
    <div class="tab-one public-upper">
      <ul class="clearfix">
        <li class="fl hdl public-upper-name active" data-target="1"><a href="javascript:void(0)">建设工程</a></li>
      </ul>
    </div>
    <div class="bdl tabview clearfix" data-target="1">
      <div class="tab-two fl">
        <ul>
          <li class="jsgc hdl active" data-target="7"><a href="javascript:void(0)"><span>合同签订公示</span></a></li>
        </ul>
      </div>
      <div>
        <div class="bdl fl notice-title" data-target="7" data-type="0" data-flag="18" data-pagesize="10" data-htmlid="jsgc7">
          <a href="/Tradeinfo-GGGSList/0-0-18">查看更多</a>
        </div>
      </div>
    </div>
    """
    contract_list_html = """
    <table>
      <tr>
        <td class="classId"><label class="fr">行业&nbsp;&nbsp;</label></td>
        <td class="classId">
          <select class="fl" id="slClassId">
            <option value="" selected>不限</option>
            <option value="1">房屋建筑</option>
            <option value="2">公路工程</option>
          </select>
        </td>
        <td class="ZCzbflag"><label class="fr">采购方式&nbsp;&nbsp;</label></td>
        <td class="ZCzbflag">
          <select class="fl" id="ZCzbflag">
            <option value="" selected>不限</option>
            <option value="0">公开招标</option>
          </select>
        </td>
      </tr>
      <tr>
        <td class="box_td"><a href="/Contact-HTGS/208215" title="测试合同A">· 测试合同A</a></td>
        <td>2026-04-30</td>
      </tr>
    </table>
    """

    def fake_get(url: str, timeout: int):
        if url == HOME_URL:
            return _FakeResponse(home_html)
        if url == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/6-6-12":
            return _FakeResponse("<html></html>")
        if url == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/0-0-18":
            return _FakeResponse(contract_list_html)
        raise AssertionError(f"unexpected url: {url}")

    spider.session.get = fake_get  # type: ignore[assignment]

    tasks = spider.fetch_homepage_tasks()

    assert [(task.sub_type, task.list_path) for task in tasks] == [
        ("房屋建筑", "/Tradeinfo-GGGSList/0-0-18?ClassId=1"),
        ("公路工程", "/Tradeinfo-GGGSList/0-0-18?ClassId=2"),
    ]


def test_fetch_homepage_tasks_keeps_government_contract_as_single_task() -> None:
    spider = QdggzySpider(
        module_name="政府采购",
        notice_type_filter="合同签订公示",
    )

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    home_html = """
    <div class="tab-one public-upper">
      <ul class="clearfix">
        <li class="fl hdl public-upper-name active" data-target="2"><a href="javascript:void(0)">政府采购</a></li>
      </ul>
    </div>
    <div class="bdl tabview clearfix" data-target="2">
      <div class="tab-two fl">
        <ul>
          <li class="jsgc hdl active" data-target="6"><a href="javascript:void(0)"><span>合同签订公示</span></a></li>
        </ul>
      </div>
      <div>
        <div class="bdl fl notice-title" data-target="6" data-type="1" data-flag="18" data-pagesize="8" data-htmlid="zfcg6">
          <a href="/Tradeinfo-GGGSList/1-1-18">查看更多</a>
        </div>
      </div>
    </div>
    """
    contract_list_html = """
    <table>
      <tr>
        <td class="classId"><label class="fr">行业&nbsp;&nbsp;</label></td>
        <td class="classId">
          <select class="fl" id="slClassId">
            <option value="" selected>不限</option>
            <option value="1">房屋建筑</option>
          </select>
        </td>
        <td class="ZCzbflag"><label class="fr">采购方式&nbsp;&nbsp;</label></td>
        <td class="ZCzbflag">
          <select class="fl" id="ZCzbflag">
            <option value="" selected>不限</option>
            <option value="0">公开招标</option>
            <option value="6">竞争性磋商</option>
          </select>
        </td>
      </tr>
      <tr>
        <td class="box_td"><a href="/Contact-HTGS/200500" title="测试合同B">· 测试合同B</a></td>
        <td>2026-11-03</td>
      </tr>
    </table>
    """

    def fake_get(url: str, timeout: int):
        if url == HOME_URL:
            return _FakeResponse(home_html)
        if url == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/6-6-12":
            return _FakeResponse("<html></html>")
        if url == "https://ggzy.qingdao.gov.cn/Tradeinfo-GGGSList/1-1-18":
            return _FakeResponse(contract_list_html)
        raise AssertionError(f"unexpected url: {url}")

    spider.session.get = fake_get  # type: ignore[assignment]

    tasks = spider.fetch_homepage_tasks()

    assert [(task.sub_type, task.list_path) for task in tasks] == [
        ("", "/Tradeinfo-GGGSList/1-1-18"),
    ]


def test_spider_primes_session_once_before_requests() -> None:
    spider = QdggzySpider()
    calls: list[tuple[str, str]] = []

    class _FakeResponse:
        def __init__(self, text: str = "ok") -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int, headers: dict[str, str] | None = None):
        calls.append(("get", url))
        if url == "https://ggzy.qingdao.gov.cn/PortalQDManage/":
            return _FakeResponse("<html></html>")
        return _FakeResponse("<table></table>")

    spider.session.get = fake_get  # type: ignore[assignment]

    spider.fetch_detail("https://ggzy.qingdao.gov.cn/c/TradeDetals-ZtbShow/demo.html")
    spider.fetch_detail("https://ggzy.qingdao.gov.cn/c/TradeDetals-ZtbShow/demo2.html")

    assert calls[0] == ("get", "https://ggzy.qingdao.gov.cn/PortalQDManage/")
    assert calls[1] == ("get", "https://ggzy.qingdao.gov.cn/c/TradeDetals-ZtbShow/demo.html")
    assert calls[2] == ("get", "https://ggzy.qingdao.gov.cn/c/TradeDetals-ZtbShow/demo2.html")
    assert len([item for item in calls if item[1] == "https://ggzy.qingdao.gov.cn/PortalQDManage/"]) == 1


def test_run_reports_monitor_status_with_real_secondary_biz_type(monkeypatch) -> None:
    spider = QdggzySpider()
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

    monkeypatch.setattr("qdggzy_core.SpiderMonitor", _FakeMonitor)

    spider.fetch_homepage_tasks = lambda: [  # type: ignore[assignment]
        type(
            "Task",
            (),
            {
                "module_name": "建设工程",
                "notice_type": "合同签订公示",
                "type": "0",
                "flag": "18",
                "page_size": 10,
                "html_id": "jsgc7",
                "class_id": "",
                "list_path": "/Tradeinfo-GGGSList/0-0-18?ClassId=1",
                "sub_type": "房屋建筑",
            },
        )()
    ]
    spider.fetch_list_page = lambda task, page_no: "<table></table>"  # type: ignore[assignment]
    monkeypatch.setattr(
        "qdggzy_core.extract_list_records",
        lambda html, list_url: [
            {
                "title": "测试合同",
                "detail_url": "https://ggzy.qingdao.gov.cn/Contact-HTGS/1",
                "region": "",
                "trade_method": "",
                "publish_time": "2026-05-01",
            }
        ],
    )
    spider.fetch_detail = lambda detail_url: {  # type: ignore[assignment]
        "detail_url": detail_url,
        "title": "测试合同",
        "main_html": "<div>测试正文</div>",
        "plain_text": "测试正文",
        "field_map": {},
        "attachments": [],
    }
    monkeypatch.setattr(
        "qdggzy_core.build_records",
        lambda task, card, detail, model_clients=None: [
            {
                "tenderTitle": "测试合同",
                "relationCompanyName": "测试公司",
            }
        ],
    )

    spider.run()

    assert flushed == [
        {
            "WasSuccessful": 1,
            "WebsiteError": 1,
            "HasContent": 1,
            "HasNewData": 1,
            "IsValidData": 1,
            "WebName": "青岛市公共资源交易电子服务系统",
            "BizType": "建设工程-房屋建筑",
        }
    ]


def test_board_entry_scripts_append_output_board_argument() -> None:
    import qdggzy_houxuanren  # noqa: E402
    import qdggzy_zhaobiao  # noqa: E402
    import qdggzy_zhongbiao  # noqa: E402

    with patch("qdggzy_houxuanren.QdggzyCandidateSpider") as mocked_candidate_spider:
        mocked_candidate_spider.return_value.run.return_value = []
        qdggzy_houxuanren.main(["--module-name", "建设工程"])
        assert mocked_candidate_spider.call_args.kwargs["module_name"] == "建设工程"
        assert mocked_candidate_spider.call_args.kwargs["output_board_filter"] == "候选人公告"
        mocked_candidate_spider.return_value.run.assert_called_once()

    with patch("qdggzy_zhaobiao.QdggzyBidSpider") as mocked_bid_spider:
        mocked_bid_spider.return_value.run.return_value = []
        qdggzy_zhaobiao.main(["--module-name", "政府采购"])
        assert mocked_bid_spider.call_args.kwargs["module_name"] == "政府采购"
        assert mocked_bid_spider.call_args.kwargs["output_board_filter"] == "招标公告"
        mocked_bid_spider.return_value.run.assert_called_once()

    with patch("qdggzy_zhongbiao.QdggzyWinSpider") as mocked_win_spider:
        mocked_win_spider.return_value.run.return_value = []
        qdggzy_zhongbiao.main(["--module-name", "政府采购"])
        assert mocked_win_spider.call_args.kwargs["module_name"] == "政府采购"
        assert mocked_win_spider.call_args.kwargs["output_board_filter"] == "中标公告"
        mocked_win_spider.return_value.run.assert_called_once()


def test_board_entry_scripts_use_run_config_by_default() -> None:
    import qdggzy_core  # noqa: E402
    import qdggzy_houxuanren  # noqa: E402
    import qdggzy_zhaobiao  # noqa: E402
    import qdggzy_zhongbiao  # noqa: E402

    with patch.dict(
        qdggzy_core.RUN_CONFIG,
        {
            "module_name": "政府采购",
            "notice_type": "中标公告",
            "output_board": "中标公告",
            "start_page": 3,
            "max_pages": 2,
            "page_size": 6,
            "timeout_seconds": 12,
            "detail_delay_seconds": 0.2,
        },
        clear=True,
    ):
        with patch("qdggzy_core.QdggzySpider") as mocked_core_spider:
            mocked_core_spider.return_value.run.return_value = []
            qdggzy_core.main()
            assert mocked_core_spider.call_args.kwargs["module_name"] == "政府采购"
            assert mocked_core_spider.call_args.kwargs["notice_type_filter"] == "中标公告"
            assert mocked_core_spider.call_args.kwargs["output_board_filter"] == "中标公告"
            assert mocked_core_spider.call_args.kwargs["start_page"] == 3
            assert mocked_core_spider.call_args.kwargs["max_pages"] == 2
            assert mocked_core_spider.call_args.kwargs["page_size"] == 6

    with patch.dict(
        qdggzy_zhaobiao.RUN_CONFIG,
        {
            "module_name": "政府采购",
            "notice_type": "采购公告",
            "start_page": 2,
            "max_pages": 3,
            "page_size": 5,
            "timeout_seconds": 11,
            "detail_delay_seconds": 0.5,
        },
        clear=True,
    ):
        with patch("qdggzy_zhaobiao.QdggzyBidSpider") as mocked_bid_spider:
            mocked_bid_spider.return_value.run.return_value = []
            qdggzy_zhaobiao.main()
            assert mocked_bid_spider.call_args.kwargs["module_name"] == "政府采购"
            assert mocked_bid_spider.call_args.kwargs["notice_type_filter"] == "采购公告"
            assert mocked_bid_spider.call_args.kwargs["start_page"] == 2
            assert mocked_bid_spider.call_args.kwargs["max_pages"] == 3
            assert mocked_bid_spider.call_args.kwargs["page_size"] == 5
            assert mocked_bid_spider.call_args.kwargs["timeout_seconds"] == 11
            assert mocked_bid_spider.call_args.kwargs["detail_delay_seconds"] == 0.5
    with patch.dict(
        qdggzy_zhongbiao.RUN_CONFIG,
        {
            "module_name": "建设工程",
            "notice_type": "合同签订公示",
            "start_page": 1,
            "max_pages": 1,
            "page_size": 10,
            "timeout_seconds": 20,
            "detail_delay_seconds": 0.0,
        },
        clear=True,
    ):
        with patch("qdggzy_zhongbiao.QdggzyWinSpider") as mocked_win_spider:
            mocked_win_spider.return_value.run.return_value = []
            qdggzy_zhongbiao.main()
            assert mocked_win_spider.call_args.kwargs["module_name"] == "建设工程"
            assert mocked_win_spider.call_args.kwargs["notice_type_filter"] == "合同签订公示"

    with patch.dict(
        qdggzy_houxuanren.RUN_CONFIG,
        {
            "module_name": "无形资产",
            "notice_type": "预中标公示",
            "start_page": 1,
            "max_pages": 1,
            "page_size": 10,
            "timeout_seconds": 20,
            "detail_delay_seconds": 0.0,
        },
        clear=True,
    ):
        with patch("qdggzy_houxuanren.QdggzyCandidateSpider") as mocked_candidate_spider:
            mocked_candidate_spider.return_value.run.return_value = []
            qdggzy_houxuanren.main()
            assert mocked_candidate_spider.call_args.kwargs["module_name"] == "无形资产"
            assert mocked_candidate_spider.call_args.kwargs["notice_type_filter"] == "预中标公示"


def test_parse_detail_extracts_government_procurement_fields() -> None:
    detail = parse_detail(
        read_sample("qd_detail_gov.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )

    assert detail["title"] == "青岛市公共卫生中心疾控内配物资（办公家具）采购项目公开招标公告"
    assert detail["field_map"]["采购项目编号（建议书编号）"] == "SDGP370200000202601001909"
    assert detail["field_map"]["采购项目名称"] == "青岛市公共卫生中心疾控内配物资（办公家具）采购项目"
    assert detail["field_map"]["联系人（采购人）"] == "青岛市疾病预防控制中心"
    assert detail["field_map"]["项目联系人（代理机构）"] == "倪工"
    assert "3290500.00 元" in detail["field_map"]["预算金额与最高限价"]
    assert len(detail["attachments"]) == 2


def test_parse_detail_extracts_build_project_fields() -> None:
    detail = parse_detail(
        read_sample("qd_detail_build.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179805-5021-0-0-0/67bfb4a4-982f-4f9e-81d8-2927a97ed697",
    )

    assert detail["title"] == "平度市2026年高标准农田建设项目勘察设计招标公告"
    assert detail["field_map"]["项目名称"] == "平度市2026年高标准农田建设项目勘察设计"
    assert detail["field_map"]["建设单位"] == "平度市农业农村局"
    assert detail["field_map"]["招标单位"] == "平度市农业农村局"
    assert detail["field_map"]["项目统一代码（编码）"] == "2502-370283-04-01-286243"
    assert detail["field_map"]["公告发布日期"] == "2026/05/08 16:01:23"
    assert len(detail["attachments"]) == 2


def test_build_record_outputs_bid_record_for_government_procurement() -> None:
    detail = parse_detail(
        read_sample("qd_detail_gov.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )
    task = {"module_name": "政府采购", "notice_type": "采购公告"}
    card = {"publish_time": "2026-05-06 21:04", "region": "市本级"}

    class _FakeBidModel:
        def get_result(self, content: str) -> dict[str, object]:
            assert "预算金额与最高限价" in content
            return {
                "projectNum": "MODEL-BID-001",
                "projectName": "模型招标项目",
                "budgetAmount": "3290500.00元",
                "procurementMethod": "竞争性磋商",
                "releaseSource": "模型采购人",
                "purchaserAddress": "模型采购人地址",
                "consultationInfo": {
                    "purchasingInfor": ["名称：模型采购人"],
                    "projectInfor": ["项目联系人：模型经办人", "电话：0532-12345678"],
                },
            }

    record = build_record(task, card, detail, model_clients={"招标公告": _FakeBidModel()})

    assert record["announcementType"] == "采购公告"
    assert record["parentType"] == "政府采购"
    assert record["projectNum"] == "MODEL-BID-001"
    assert record["projectName"] == "模型招标项目"
    assert record["announcementTitle"] == "模型招标项目"
    assert record["budgetAmount"] == "3290500.00元"
    assert record["releaseSource"] == "模型采购人"
    assert record["procurementMethod"] == "竞争性磋商"
    assert record["consultationInfo"] == {
        "purchasingInfor": ["名称：模型采购人"],
        "projectInfor": ["项目联系人：模型经办人", "电话：0532-12345678"],
    }
    assert record["contentType"] == 1
    assert record["fileInfo"][0]["fileType"] == "pdf"
    decoded_html = base64.b64decode(record["htmlContent"]).decode("utf-8")
    assert "采购项目编号（建议书编号）" in decoded_html
    assert "GetZbDownLoad" not in decoded_html


def test_build_record_does_not_use_task_sub_type_as_procurement_method_for_government_procurement() -> (
    None
):
    detail = parse_detail(
        read_sample("qd_detail_gov.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )
    task = {
        "module_name": "政府采购",
        "notice_type": "采购公告",
        "sub_type": "公开招标",
    }
    card = {"publish_time": "2026-05-06 21:04", "region": "市本级"}

    class _FakeBidModel:
        def get_result(self, content: str) -> dict[str, object]:
            return {
                "projectNum": "MODEL-BID-002",
                "projectName": "模型招标项目",
                "budgetAmount": "3290500.00元",
                "procurementMethod": "",
                "releaseSource": "模型采购人",
                "purchaserAddress": "模型采购人地址",
            }

    record = build_record(task, card, detail, model_clients={"招标公告": _FakeBidModel()})

    assert record["procurementMethod"] == ""


def test_build_record_outputs_candidate_record_for_build_project() -> None:
    detail = parse_detail(
        read_sample("qd_detail_build.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179805-5021-0-0-0/67bfb4a4-982f-4f9e-81d8-2927a97ed697",
    )
    task = {"module_name": "建设工程", "notice_type": "预中标公示"}
    card = {"publish_time": "2026-05-08 16:01:23", "region": "平度"}

    class _FakeCandidateModel:
        def get_result(self, content: str) -> dict[str, object]:
            assert "项目统一代码（编码）" in content
            return {
                "tenderTitle": "模型候选人标题",
                "procurementUnit": "模型采购单位",
                "extra": {"tenderNumber": "MODEL-CAND-001"},
                "result": [
                    {
                        "relationCompanyName": "候选人甲",
                        "candidateSort": ["第一候选人：候选人甲"],
                    },
                    {
                        "relationCompanyName": "候选人乙",
                        "candidateSort": ["第二候选人：候选人乙"],
                    },
                ],
            }

    record = build_record(task, card, detail, model_clients={"候选人公告": _FakeCandidateModel()})

    assert record["announcementType"] == "候选人公告"
    assert record["parentType"] == "工程建设"
    assert record["tenderTitle"] == "模型候选人标题"
    assert record["procurementUnit"] == "模型采购单位"
    assert record["relationCompanyName"] == "候选人甲"
    assert record["extra"] == {"candidateSort": ["第一候选人：候选人甲"], "tenderNumber": "MODEL-CAND-001"}
    assert isinstance(record["uploadFileUrl"], list)
    assert record["uploadFileUrl"][0]["fileType"] == "pdf"


def test_build_record_normalizes_candidate_extra_from_general_model_shape() -> None:
    detail = parse_detail(
        read_sample("qd_detail_build.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/161133-5070-0-20-0/ffe22f0e-6527-4808-b65d-8eb4bce734f3",
    )
    task = {"module_name": "建设工程", "notice_type": "预中标公示"}
    card = {"publish_time": "2026-05-08 16:01:23", "region": "平度"}

    class _RawCandidateModel:
        def get_result(self, content: str) -> dict[str, object]:
            assert "项目统一代码（编码）" in content
            return {
                "tenderTitle": "模型候选人标题",
                "procurementUnit": "模型采购单位",
                "extra": {"tenderNumber": "K3504242026000003"},
                "result": [
                    {
                        "relationCompanyName": "福州兴建工程造价咨询有限公司,福建联审工程管理咨询有限公司,建融建设管理集团有限责任公司",
                        "candidateSort": [
                            {"候选人名称": "福州兴建工程造价咨询有限公司"},
                            {"候选人名称": "福建联审工程管理咨询有限公司"},
                            {"候选人名称": "建融建设管理集团有限责任公司"},
                        ],
                    }
                ],
            }

    record = build_record(task, card, detail, model_clients={"候选人公告": _RawCandidateModel()})

    assert record["relationCompanyName"] == "福州兴建工程造价咨询有限公司,福建联审工程管理咨询有限公司,建融建设管理集团有限责任公司"
    assert record["extra"] == {"candidateSort": [{}, {}, {}], "tenderNumber": "K3504242026000003"}


def test_build_record_prefers_ranked_candidate_sort_from_general_model_shape() -> None:
    detail = parse_detail(
        read_sample("qd_detail_build.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/161133-5070-0-20-0/ffe22f0e-6527-4808-b65d-8eb4bce734f3",
    )
    task = {"module_name": "建设工程", "notice_type": "入围投标人公示（评定分离）"}
    card = {"publish_time": "2026-05-07", "region": "西海岸"}

    class _RankedCandidateModel:
        def get_result(self, content: str) -> dict[str, object]:
            assert "项目统一代码（编码）" in content
            return {
                "tenderTitle": "模型候选人标题",
                "procurementUnit": "模型采购单位",
                "extra": {"tenderNumber": "E3702002313022531"},
                "result": [
                    {
                        "relationCompanyName": "烟建集团有限公司,中铁四局集团有限公司/中铁四局集团第七工程有限公司/青岛西海岸城市建设集团有限公司,青岛中建联合集团有限公司",
                        "candidateSort": [
                            {
                                "候选人排序": [
                                    "第一候选人：烟建集团有限公司",
                                    "第二候选人：中铁四局集团有限公司/中铁四局集团第七工程有限公司/青岛西海岸城市建设集团有限公司",
                                    "第三候选人：青岛中建联合集团有限公司",
                                ],
                                "候选人名称": "烟建集团有限公司,中铁四局集团有限公司/中铁四局集团第七工程有限公司/青岛西海岸城市建设集团有限公司,青岛中建联合集团有限公司",
                            }
                        ],
                    }
                ],
            }

    record = build_record(task, card, detail, model_clients={"候选人公告": _RankedCandidateModel()})

    assert record["relationCompanyName"] == "烟建集团有限公司,中铁四局集团有限公司/中铁四局集团第七工程有限公司/青岛西海岸城市建设集团有限公司,青岛中建联合集团有限公司"
    assert record["extra"] == {
        "candidateSort": [
            {
                "候选人排序": [
                    "第一候选人：烟建集团有限公司",
                    "第二候选人：中铁四局集团有限公司/中铁四局集团第七工程有限公司/青岛西海岸城市建设集团有限公司",
                    "第三候选人：青岛中建联合集团有限公司",
                ]
            }
        ],
        "tenderNumber": "E3702002313022531",
    }


def test_build_record_does_not_fallback_to_rule_fields_when_bid_model_returns_empty() -> None:
    detail = parse_detail(
        read_sample("qd_detail_gov.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )
    task = {"module_name": "政府采购", "notice_type": "采购公告"}
    card = {"publish_time": "2026-05-06 21:04", "region": "市本级"}

    class _EmptyBidModel:
        def get_result(self, content: str) -> dict[str, object]:
            return {}

    record = build_record(task, card, detail, model_clients={"招标公告": _EmptyBidModel()})

    assert record["projectNum"] == ""
    assert record["projectName"] == ""
    assert record["announcementTitle"] == ""
    assert record["budgetAmount"] == ""
    assert record["releaseSource"] == ""
    assert record["consultationInfo"] == {"purchasingInfor": [], "projectInfor": []}
    assert record["originalWebsiteAddress"] == detail["detail_url"]


def test_build_record_keeps_general_bid_model_procurement_method_and_address() -> None:
    detail = parse_detail(
        read_sample("qd_detail_gov.html"),
        "https://ggzy.qingdao.gov.cn/TradeDetals-ZtbShow/179992-5021-1-0-0/51f0626e-49dc-4110-abe9-1d19f555cda2",
    )
    task = {"module_name": "政府采购", "notice_type": "采购公告"}
    card = {"publish_time": "2026-05-06 21:04", "region": "市本级"}

    class _FakeBidModel:
        def get_result(self, content: str) -> dict[str, object]:
            return {
                "projectNum": "MODEL-BID-003",
                "projectName": "模型招标项目",
                "budgetAmount": "3290500.00元",
                "procurementMethod": "其他方式",
                "releaseSource": "模型采购人",
                "purchaserAddress": "模型采购人地址",
                "consultationInfo": {
                    "purchasingInfor": ["名称：模型采购人"],
                    "projectInfor": ["项目联系人：模型经办人", "电话：0532-12345678"],
                },
            }

    record = build_record(task, card, detail, model_clients={"招标公告": _FakeBidModel()})

    assert record["procurementMethod"] == "其他方式"
    assert record["purchaserAddress"] == "模型采购人地址"


def test_money_parser_is_used_for_amount_normalization() -> None:
    assert MoneyParser is not None
    assert MoneyParser().convert_amount("3.6万元") == "36000元"
