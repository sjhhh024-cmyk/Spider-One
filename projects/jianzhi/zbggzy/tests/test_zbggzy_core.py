from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import zbggzy_core  # noqa: E402
from zbggzy_houxuanren import (  # noqa: E402
    MODULE_SOURCES as CANDIDATE_MODULE_SOURCES,
    SUPPORTED_CANDIDATE_NOTICE_TYPES,
    ZbggzyRuntime as CandidateRuntime,
    apply_candidate_model_enrichment,
    build_candidate_record,
    extract_candidate_names,
    parse_detail as parse_candidate_detail,
)
from zbggzy_zhaobiao import (  # noqa: E402
    EXCLUDED_MODULE_NAMES,
    EXCLUDED_NOTICE_TYPES,
    MODULE_SOURCES as BID_MODULE_SOURCES,
    SUPPORTED_BID_NOTICE_TYPES,
    ModuleTask,
    ZbggzyRuntime as BidRuntime,
    apply_bid_model_enrichment,
    build_bid_record,
    clean_detail_fragment,
    normalize_money,
    parse_detail as parse_bid_detail,
)
from zbggzy_zhongbiao import (  # noqa: E402
    CONTRACT_GONGGAO_MODULES,
    CONTRACT_GONGSHI_MODULES,
    MODULE_SOURCES as WIN_MODULE_SOURCES,
    SUPPORTED_WIN_NOTICE_TYPES,
    TenderModel,
    ZbggzyRuntime as WinRuntime,
    apply_win_model_enrichment,
    build_model_result_record,
    build_win_record,
    extract_attachment_urls,
    parse_detail as parse_win_detail,
)


def make_task(notice_type: str) -> ModuleTask:
    return ModuleTask(
        module_name="政府采购",
        parent_type="政府采购",
        category_num="002002001",
        notice_type=notice_type,
        module_path="/jyxx/002002/gonggongziyuan.html",
    )


def make_bid_context() -> dict[str, object]:
    return {
        "task": make_task("招标公告"),
        "region_code": "370301",
        "region_name": "淄博市",
        "project_name": "测试项目",
        "detail_url": "http://example.com/detail.html",
        "procurement_method": "",
        "project_num": "ZB-001",
        "budget_amount": "100.00元",
        "procurement_unit": "测试单位",
        "render_date": "2026-05-09",
        "contact_name": "张三",
        "contact_phone": "0533-1234567",
        "attachments": [
            {
                "fileUrl": "http://example.com/a.pdf",
                "fileType": "pdf",
                "fileName": "a.pdf",
            }
        ],
        "html_content": "PGgxPnRlc3Q8L2gxPg==",
        "plain_text": "正文",
        "detail": {"title": "测试项目"},
        "card": {},
        "cleaned_html": "<h1>test</h1>",
    }


def make_win_context() -> dict[str, object]:
    return {
        "task": make_task("中标结果公告"),
        "region_code": "370301",
        "region_name": "淄博市",
        "project_name": "测试项目",
        "detail_url": "http://example.com/detail.html",
        "project_num": "ZB-001",
        "procurement_unit": "测试单位",
        "render_date": "2026-05-09",
        "contact_name": "张三",
        "contact_phone": "0533-1234567",
        "attachment_urls": ["http://example.com/a.pdf"],
        "html_content": "PGgxPnRlc3Q8L2gxPg==",
        "render_money": "88.00元",
        "relation_company_name": "甲公司",
    }


def make_candidate_context() -> dict[str, object]:
    return {
        "task": make_task("中标候选人公示"),
        "region_code": "370301",
        "region_name": "淄博市",
        "project_name": "测试项目",
        "detail_url": "http://example.com/detail.html",
        "project_num": "ZB-001",
        "procurement_unit": "测试单位",
        "render_date": "2026-05-09",
        "attachments": [
            {
                "fileUrl": "http://example.com/a.pdf",
                "fileType": "pdf",
                "fileName": "a.pdf",
            }
        ],
        "html_content": "PGgxPnRlc3Q8L2gxPg==",
        "relation_company_name": "甲公司,乙公司",
        "candidate_names": ["甲公司", "乙公司"],
        "candidate_sort": ["第一候选人：甲公司", "第二候选人：乙公司"],
    }


def test_optional_import_fallbacks_do_not_use_bare_exception_guards() -> None:
    source_files = [
        PROJECT_ROOT / "zbggzy_houxuanren.py",
        PROJECT_ROOT / "zbggzy_zhaobiao.py",
        PROJECT_ROOT / "zbggzy_zhongbiao.py",
    ]

    for source_file in source_files:
        source = source_file.read_text(encoding="utf-8")
        assert "except Exception:  # pragma: no cover" not in source


def test_win_tender_model_loads_from_current_jianzhi_layout() -> None:
    assert TenderModel is not None


def test_zbggzy_refactor_does_not_leave_extra_shared_helper_files() -> None:
    assert not (PROJECT_ROOT / "zbggzy_text.py").exists()
    assert not (PROJECT_ROOT / "zbggzy_support.py").exists()


def test_clean_detail_fragment_removes_site_shell_and_attachment_links() -> None:
    html = """
    <div style="display:none" id="viewGuid" value="cms_002002004_xxx"></div>
    <h2 class="article--title" style="display:none" id="iframetitle">标题</h2>
    <div class="znyd" style="display:none;"><a href="/detailforjr.html">“助农易贷”金融服务</a></div>
    <div class="znyd-button">
      “助农易贷”金融服务
    </div>
    <div class="chain" style="display:none"><div class="chain-box" data-value="">招标公告，区块链已存证</div></div>
    <div id="mainContent">
      <p>正文内容保留</p>
      <div><a href="/EpointWebBuilder_zbggzy/pages/webbuildermis/attach/downloadztbattach?attachGuid=abc&appUrlFlag=ztb003&siteGuid=7eb5f7f1-9041-43ad-8e13-8fcb82ea831a" title="中小企业声明函.pdf">中小企业声明函.pdf</a></div>
      <div>裸露下载地址：https://example.com/file.pdf</div>
    </div>
    """

    cleaned = clean_detail_fragment(html)

    assert "viewGuid" not in cleaned
    assert "iframetitle" not in cleaned
    assert "助农易贷" not in cleaned
    assert "区块链已存证" not in cleaned
    assert "downloadztbattach" not in cleaned
    assert "中小企业声明函.pdf" not in cleaned
    assert "裸露下载地址" not in cleaned
    assert "正文内容保留" in cleaned


def test_extract_attachment_urls_collects_downloadztbattach_links() -> None:
    html = """
    <div>
      <a href="/EpointWebBuilder_zbggzy/pages/webbuildermis/attach/downloadztbattach?attachGuid=abc&appUrlFlag=ztb003&siteGuid=7eb5f7f1-9041-43ad-8e13-8fcb82ea831a" title="中小企业声明函.pdf">中小企业声明函.pdf</a>
      <a href="/EpointWebBuilder_zbggzy/pages/webbuildermis/attach/downloadztbattach?attachGuid=def&appUrlFlag=ztb003&siteGuid=7eb5f7f1-9041-43ad-8e13-8fcb82ea831a" title="业绩.pdf">业绩.pdf</a>
    </div>
    """

    attachments = extract_attachment_urls(
        html,
        "http://ggzyjy.zibo.gov.cn:8082/jyxx/002002/002002004/20260508/c858af5c-da87-482c-bb99-2fe18f3e6d81.html",
    )

    assert attachments == [
        "http://ggzyjy.zibo.gov.cn:8082/EpointWebBuilder_zbggzy/pages/webbuildermis/attach/downloadztbattach?attachGuid=abc&appUrlFlag=ztb003&siteGuid=7eb5f7f1-9041-43ad-8e13-8fcb82ea831a",
        "http://ggzyjy.zibo.gov.cn:8082/EpointWebBuilder_zbggzy/pages/webbuildermis/attach/downloadztbattach?attachGuid=def&appUrlFlag=ztb003&siteGuid=7eb5f7f1-9041-43ad-8e13-8fcb82ea831a",
    ]


def test_bid_runtime_only_keeps_bid_notice_types() -> None:
    spider = BidRuntime(
        module_name="政府采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    spider.ensure_token = lambda: None  # type: ignore[assignment]
    spider.fetch_module_page = lambda module_path: (
        """
    <ul id="gglx">
      <li data-value="001">需求（意向）公示</li>
      <li data-value="002">采购公告</li>
      <li data-value="003">中标（成交）公告</li>
      <li data-value="004">招标公告</li>
      <li data-value="005">交易公告</li>
    </ul>
    """
    )  # type: ignore[assignment]

    tasks = spider.discover_module_tasks()

    assert [task.notice_type for task in tasks] == ["采购公告", "招标公告", "交易公告"]


def test_bid_runtime_supports_exact_notice_type_filter() -> None:
    spider = BidRuntime(
        module_name="政府采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="采购公告",
    )
    spider.ensure_token = lambda: None  # type: ignore[assignment]
    spider.fetch_module_page = lambda module_path: (
        """
    <ul id="gglx">
      <li data-value="001">采购公告</li>
      <li data-value="002">招标公告</li>
      <li data-value="003">中标（成交）公告</li>
    </ul>
    """
    )  # type: ignore[assignment]

    tasks = spider.discover_module_tasks()

    assert [task.notice_type for task in tasks] == ["采购公告"]


def test_win_runtime_only_keeps_win_notice_types() -> None:
    spider = WinRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    spider.ensure_token = lambda: None  # type: ignore[assignment]
    spider.fetch_module_page = lambda module_path: (
        """
    <ul id="gglx">
      <li data-value="001">招标公告</li>
      <li data-value="002">中标结果公告</li>
      <li data-value="003">结果公示</li>
      <li data-value="004">中标候选人公示</li>
    </ul>
    """
    )  # type: ignore[assignment]

    tasks = spider.discover_module_tasks()

    assert [task.notice_type for task in tasks] == ["中标结果公告", "结果公示"]


def test_win_runtime_keeps_contract_notice_for_supported_modules() -> None:
    spider = WinRuntime(
        module_name="政府采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    spider.ensure_token = lambda: None  # type: ignore[assignment]
    spider.fetch_module_page = lambda module_path: (
        """
    <ul id="gglx">
      <li data-value="001">合同公告</li>
      <li data-value="002">中标（成交）公告</li>
      <li data-value="003">澄清公告</li>
    </ul>
    """
    )  # type: ignore[assignment]

    tasks = spider.discover_module_tasks()

    assert [task.notice_type for task in tasks] == ["合同公告", "中标（成交）公告"]


def test_win_runtime_keeps_contract_notice_for_each_supported_module() -> None:
    for module_name in (
        "政府采购",
        "国企采购",
        "药械采购",
        "其他交易",
        "农村工程",
        "农村采购",
        "土地流转",
        "集体资产",
        "农业设施",
        "其他交易(农村产权)",
    ):
        assert module_name in CONTRACT_GONGGAO_MODULES | CONTRACT_GONGSHI_MODULES
        expected_contract_notice = (
            "合同公告"
            if module_name in CONTRACT_GONGGAO_MODULES
            else "合同公示"
        )
        spider = WinRuntime(
            module_name=module_name,
            start_page=1,
            max_pages=1,
            page_size=15,
            timeout_seconds=30,
            detail_delay_seconds=0,
            enable_model_enrichment=False,
            notice_type_filter="",
        )
        spider.ensure_token = lambda: None  # type: ignore[assignment]
        spider.fetch_module_page = lambda module_path: (  # type: ignore[assignment]
            f"""
        <ul id="gglx">
          <li data-value="001">{expected_contract_notice}</li>
          <li data-value="002">中标（成交）公告</li>
          <li data-value="003">澄清公告</li>
        </ul>
        """
        )

        tasks = spider.discover_module_tasks()

        assert [task.notice_type for task in tasks] == [
            expected_contract_notice,
            "中标（成交）公告",
        ]


def test_win_runtime_does_not_keep_contract_notice_for_unsupported_modules() -> None:
    spider = WinRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    spider.ensure_token = lambda: None  # type: ignore[assignment]
    spider.fetch_module_page = lambda module_path: (
        """
    <ul id="gglx">
      <li data-value="001">合同公示</li>
      <li data-value="002">中标结果公告</li>
    </ul>
    """
    )  # type: ignore[assignment]

    tasks = spider.discover_module_tasks()

    assert [task.notice_type for task in tasks] == ["中标结果公告"]


def test_win_runtime_keeps_contract_gongshi_for_supported_modules() -> None:
    for module_name in CONTRACT_GONGSHI_MODULES:
        spider = WinRuntime(
            module_name=module_name,
            start_page=1,
            max_pages=1,
            page_size=15,
            timeout_seconds=30,
            detail_delay_seconds=0,
            enable_model_enrichment=False,
            notice_type_filter="",
        )
        spider.ensure_token = lambda: None  # type: ignore[assignment]
        spider.fetch_module_page = lambda module_path: (  # type: ignore[assignment]
            """
        <ul id="gglx">
          <li data-value="001">合同公示</li>
          <li data-value="002">中标（成交）公告</li>
        </ul>
        """
        )

        tasks = spider.discover_module_tasks()

        assert [task.notice_type for task in tasks] == ["合同公示", "中标（成交）公告"]


def test_candidate_runtime_supports_exact_notice_type_filter() -> None:
    spider = CandidateRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        notice_type_filter="中标候选人公示",
    )
    spider.ensure_token = lambda: None  # type: ignore[assignment]
    spider.fetch_module_page = lambda module_path: (
        """
    <ul id="gglx">
      <li data-value="001">招标公告</li>
      <li data-value="002">中标候选人公示</li>
      <li data-value="003">中标结果公告</li>
    </ul>
    """
    )  # type: ignore[assignment]

    tasks = spider.discover_module_tasks()

    assert [task.notice_type for task in tasks] == ["中标候选人公示"]


def test_discovered_task_parent_type_uses_first_level_module_name_directly() -> None:
    spider = BidRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="招标公告",
    )
    spider.ensure_token = lambda: None  # type: ignore[assignment]
    spider.fetch_module_page = lambda module_path: (
        """
    <ul id="gglx">
      <li data-value="001">招标公告</li>
    </ul>
    """
    )  # type: ignore[assignment]

    tasks = spider.discover_module_tasks()

    assert len(tasks) == 1
    assert tasks[0].module_name == "建设工程"
    assert tasks[0].parent_type == "建设工程"


def test_module_sources_parent_type_is_same_as_first_level_module_name() -> None:
    for module_sources in (
        BID_MODULE_SOURCES,
        WIN_MODULE_SOURCES,
        CANDIDATE_MODULE_SOURCES,
    ):
        for module_name, source in module_sources.items():
            assert source["parent_type"] == module_name


def test_extract_candidate_names_from_candidate_table_rows() -> None:
    html = """
    <html>
      <h1>某项目中标候选人公示</h1>
      <table>
        <tr><td>中标候选人名称</td><td>投标报价（元）</td><td>质量</td></tr>
        <tr><td>济南市建设监理有限公司</td><td>2460967.49</td><td>合格</td></tr>
        <tr><td>山东同力建设项目管理有限公司</td><td>2464488.19</td><td>合格</td></tr>
        <tr><td>山东鑫卓越工程项目管理有限公司</td><td>2463784.05</td><td>合格</td></tr>
      </table>
    </html>
    """

    detail = parse_candidate_detail(html, "http://example.com/detail.html")

    assert extract_candidate_names(detail) == [
        "济南市建设监理有限公司",
        "山东同力建设项目管理有限公司",
        "山东鑫卓越工程项目管理有限公司",
    ]


def test_candidate_parse_detail_keeps_paragraph_boundaries_for_inline_fields() -> None:
    html = """
    <html>
      <body>
        <p>项目名称：测试项目</p>
        <p>项目编号：ZB-001</p>
        <p>采购人名称：测试单位</p>
      </body>
    </html>
    """

    detail = parse_candidate_detail(html, "http://example.com/detail.html")

    assert detail["field_map"]["项目名称"] == "测试项目"
    assert detail["field_map"]["项目编号"] == "ZB-001"
    assert detail["field_map"]["采购人名称"] == "测试单位"


def test_win_parse_detail_keeps_paragraph_boundaries_for_inline_fields() -> None:
    html = """
    <html>
      <body>
        <p>项目名称：测试项目</p>
        <p>项目编号：ZB-001</p>
        <p>采购人名称：测试单位</p>
      </body>
    </html>
    """

    detail = parse_win_detail(html, "http://example.com/detail.html")

    assert detail["field_map"]["项目名称"] == "测试项目"
    assert detail["field_map"]["项目编号"] == "ZB-001"
    assert detail["field_map"]["采购人名称"] == "测试单位"


def test_candidate_build_context_uses_all_candidate_names_from_table() -> None:
    spider = CandidateRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        notice_type_filter="",
    )
    task = ModuleTask(
        module_name="建设工程",
        parent_type="工程建设",
        category_num="002001003",
        notice_type="中标候选人公示",
        module_path="/jyxx/002001/gonggongziyuan.html",
    )
    html = """
    <html>
      <h1>某项目中标候选人公示</h1>
      <table>
        <tr><td>项目名称</td><td>某项目</td><td>项目编号</td><td>ZB-001</td></tr>
        <tr><td>中标候选人名称</td><td>投标报价（元）</td><td>质量</td></tr>
        <tr><td>济南市建设监理有限公司</td><td>2460967.49</td><td>合格</td></tr>
        <tr><td>山东同力建设项目管理有限公司</td><td>2464488.19</td><td>合格</td></tr>
        <tr><td>山东鑫卓越工程项目管理有限公司</td><td>2463784.05</td><td>合格</td></tr>
      </table>
    </html>
    """
    detail = parse_candidate_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "市本级",
            "infodate": "2026-05-09",
            "realtitle": "某项目中标候选人公示",
        },
        detail,
        html,
    )

    assert context["candidate_names"] == []
    assert context["candidate_sort"] == []
    assert context["relation_company_name"] == ""


def test_candidate_build_context_uses_tenderer_name_for_procurement_unit_and_ranked_sort() -> (
    None
):
    spider = CandidateRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        notice_type_filter="",
    )
    task = ModuleTask(
        module_name="建设工程",
        parent_type="工程建设",
        category_num="002001003",
        notice_type="中标候选人公示",
        module_path="/jyxx/002001/gonggongziyuan.html",
    )
    html = """
    <html>
      <h1>某项目中标候选人公示</h1>
      <table>
        <tr><td>项目名称</td><td>某项目</td><td>项目编号</td><td>K3504242026000003</td></tr>
        <tr><td>招标人名称</td><td>某招标人单位</td><td>第一中标候选人</td><td>福州兴建工程造价咨询有限公司</td></tr>
        <tr><td>第二中标候选人</td><td>福建联审工程管理咨询有限公司</td><td>第三中标候选人</td><td>建融建设管理集团有限责任公司</td></tr>
      </table>
    </html>
    """
    detail = parse_candidate_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "市本级",
            "infodate": "2026-05-09",
            "realtitle": "某项目中标候选人公示",
        },
        detail,
        html,
    )

    assert context["procurement_unit"] == ""
    assert context["candidate_names"] == []
    assert context["candidate_sort"] == []


def test_bid_build_context_extracts_procurement_method_from_plain_text_keyword() -> (
    None
):
    spider = BidRuntime(
        module_name="政府采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    context = spider.build_context(
        make_task("招标公告"),
        {"areacode": "市本级", "infodate": "2026-05-09", "realtitle": "测试项目"},
        {
            "field_map": {},
            "detail_url": "http://example.com/detail.html",
            "plain_text": "项目名称：测试项目\n采购方式：公开招标\n预算金额：100元",
            "title": "测试项目",
        },
        "<div>项目名称：测试项目</div><div>采购方式：公开招标</div>",
    )

    assert context["procurement_method"] == "公开招标"


def test_bid_build_context_extracts_procurement_method_from_plain_text() -> None:
    spider = BidRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    context = spider.build_context(
        make_task("招标公告"),
        {"areacode": "市本级", "infodate": "2026-05-09", "realtitle": "测试项目"},
        {
            "field_map": {},
            "detail_url": "http://example.com/detail.html",
            "plain_text": "房东村临时便民市场项目工程总承包招标公告\n4、招标文件的获取\n招标文件载明采购方式为公开招标。\n5、投标文件的上传\n其他内容",
            "title": "测试项目",
        },
        "<div>4、招标文件的获取</div><div>招标文件载明采购方式为公开招标。</div>",
    )

    assert context["procurement_method"] == "公开招标"


def test_bid_build_context_keeps_procurement_method_empty_when_plain_text_has_no_supported_method() -> (
    None
):
    spider = BidRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    context = spider.build_context(
        make_task("招标公告"),
        {"areacode": "市本级", "infodate": "2026-05-09", "realtitle": "测试项目"},
        {
            "field_map": {},
            "detail_url": "http://example.com/detail.html",
            "plain_text": "测试公告\n4、招标文件的获取\n本项目已具备招标条件。\n5、投标文件的上传\n其他内容",
            "title": "测试项目",
        },
        "<div>4、招标文件的获取</div><div>本项目已具备招标条件。</div>",
    )

    assert context["procurement_method"] == ""


def test_bid_build_context_cleans_government_procurement_fields() -> None:
    spider = BidRuntime(
        module_name="政府采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    html = """
    <html>
      <body>
        <h1>高青县人民医院车辆管理及院内安保服务采购</h1>
        <p>项目编号：SDGP370322000202602000019</p>
        <p>项目名称：高青县人民医院车辆管理及院内安保服务采购</p>
        <p>预算金额：本项目总预算为570000.00元,共分1个包,其中高青县人民医院车辆管理及院内安保服务采购:570000.00元。</p>
        <p>最高限价：570000.00元。</p>
        <p>采购需求：为医院提供车辆指挥、门卫、内部巡逻、维护治安等内部保卫工作。</p>
        <p>采购方式：竞争性磋商</p>
        <p>八、对本次招标提出询问，请按以下方式联系</p>
        <p>1.采购人信息</p>
        <p>名 称：高青县人民医院</p>
        <p>地 址：高青县青城路11号</p>
        <p>联系人：阮强</p>
        <p>联系方式：0533-6961052</p>
        <p>2.采购代理机构信息</p>
        <p>名 称：淄博青沅项目管理有限公司</p>
        <p>地 址：高青县田镇街道高苑路黄河商务楼820室</p>
        <p>联系方式：0533-6950338</p>
        <p>3.项目联系方式</p>
        <p>项目联系人：田英静</p>
        <p>电 话：0533-6950338</p>
        <script>
          function ResizeToScreen(id, pX, pY) {
            var obj = document.getElementById(id);
            obj.style.display = "";
          }
        </script>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        make_task("采购公告"),
        {
            "areacode": "高青县",
            "infodate": "2026-05-08",
            "realtitle": "高青县人民医院车辆管理及院内安保服务采购",
        },
        detail,
        html,
    )

    assert "ResizeToScreen" not in detail["plain_text"]
    assert context["project_name"] == "高青县人民医院车辆管理及院内安保服务采购"
    assert context["project_num"] == "SDGP370322000202602000019"
    assert context["budget_amount"] == "570000.00元"
    assert context["procurement_method"] == "竞争性磋商"
    assert context["procurement_unit"] == "高青县人民医院"
    assert context["contact_name"] == "田英静"
    assert context["contact_phone"] == "0533-6950338"


def test_win_build_context_extracts_union_company_and_amount_from_bid_result_table() -> (
    None
):
    spider = WinRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="中标结果公告",
    )
    task = ModuleTask(
        module_name="建设工程",
        parent_type="工程建设",
        category_num="002001004",
        notice_type="中标结果公告",
        module_path="/jyxx/002001/gonggongziyuan.html",
    )
    html = """
    <html>
      <body>
        <h1>某建设工程中标结果公告</h1>
        <table>
          <tr><td>项目名称</td><td>某建设工程</td></tr>
          <tr><td>项目编号</td><td>ZBFJSZ202605008</td></tr>
          <tr><td>招标人</td><td>淄博齐建项目运营管理有限公司</td></tr>
          <tr><td>中标情况</td></tr>
          <tr><td>标段编号</td><td>中标单位名称</td><td>中标金额 （元/优惠率）</td><td>质量</td><td>工期</td></tr>
          <tr><td>ZBFJSZ202605008001001</td><td>淄博昊通公路工程有限公司(联合体单位：淄博齐鲁通达建设工程有限公司)</td><td>16901400.21元</td><td>合格</td><td>90日历天</td></tr>
          <tr><td>项目负责人</td><td>商宜利</td><td>相关证书</td><td>二级注册建造师</td><td>证书编号</td><td>鲁2372010202404839</td></tr>
        </table>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "临淄区",
            "infodate": "2026-05-07",
            "realtitle": "某建设工程中标结果公告",
        },
        detail,
        html,
    )

    assert (
        context["relation_company_name"]
        == "淄博昊通公路工程有限公司(联合体单位：淄博齐鲁通达建设工程有限公司)"
    )
    assert context["render_money"] == "16901400.21元"

    record = build_win_record(context)

    assert record["relationCompanyName"] == ""
    assert record["renderMoney"] == ""
    assert record["isUnion"] == 0


def test_apply_win_model_enrichment_recomputes_is_union_after_relation_company_name_update() -> (
    None
):
    class _FakeClient:
        def get_result(self, text: str) -> dict[str, object]:
            return {
                "result": [
                    {
                        "relationCompanyName": "淄博昊通公路工程有限公司,淄博齐鲁通达建设工程有限公司",
                        "renderMoney": "16901400.21元",
                    }
                ]
            }

    runtime = type("Runtime", (), {"model_client": _FakeClient()})()
    context = {
        "plain_text": "测试正文",
        "cleaned_html": "<div>测试正文</div>",
    }
    record = {
        "relationCompanyName": "",
        "renderMoney": "",
        "contactName": "",
        "contactTelephone": "",
        "isUnion": 0,
    }

    records = apply_win_model_enrichment(runtime, record, context)

    assert len(records) == 1
    enriched = records[0]
    assert (
        enriched["relationCompanyName"]
        == "淄博昊通公路工程有限公司,淄博齐鲁通达建设工程有限公司"
    )
    assert enriched["isUnion"] == 1


def test_build_win_record_leaves_model_managed_fields_empty_before_model_enrichment() -> (
    None
):
    record = build_win_record(make_win_context())

    assert record["tenderTitle"] == ""
    assert record["tenderNumber"] == ""
    assert record["procurementUnit"] == ""
    assert record["relationCompanyName"] == ""
    assert record["contactName"] == ""
    assert record["contactTelephone"] == ""
    assert record["renderMoney"] == ""
    assert record["isUnion"] == 0


def test_build_model_result_record_ignores_none_render_money() -> None:
    base_record = build_win_record(make_win_context())
    model_result = {
        "tenderTitle": "模型项目",
        "tenderNumber": "ZB-001",
        "procurementUnit": "测试单位",
    }
    item = {
        "relationCompanyName": "测试公司",
        "contactName": "联系人",
        "contactTelephone": "123",
        "renderMoney": None,
    }

    record = build_model_result_record(base_record, model_result, item)

    assert record["renderMoney"] == ""
    assert record["relationCompanyName"] == "测试公司"


def test_apply_win_model_enrichment_only_fills_fields_provided_by_model() -> None:
    class _FakeClient:
        def get_result(self, text: str) -> dict[str, object]:
            return {
                "tenderTitle": "模型项目名",
                "procurementUnit": "模型采购人",
                "result": [],
            }

    runtime = type("Runtime", (), {"model_client": _FakeClient()})()
    record = build_win_record(make_win_context())
    context = {
        "plain_text": "测试正文",
        "cleaned_html": "<div>测试正文</div>",
    }

    records = apply_win_model_enrichment(runtime, record, context)

    assert len(records) == 1
    enriched = records[0]
    assert enriched["tenderTitle"] == "模型项目名"
    assert enriched["procurementUnit"] == "模型采购人"
    assert enriched["tenderNumber"] == ""
    assert enriched["relationCompanyName"] == ""
    assert enriched["contactName"] == ""
    assert enriched["contactTelephone"] == ""
    assert enriched["renderMoney"] == ""
    assert enriched["isUnion"] == 0


def test_win_collect_records_for_task_expands_multiple_model_results_into_multiple_records() -> (
    None
):
    spider = WinRuntime(
        module_name="政府采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="中标（成交）公告",
    )

    class _FakeClient:
        def get_result(self, text: str) -> dict[str, object]:
            return {
                "tenderTitle": "模型项目名",
                "tenderNumber": "MODEL-001",
                "procurementUnit": "模型采购人",
                "result": [
                    {
                        "relationCompanyName": "供应商A",
                        "contactName": "联系人A",
                        "contactTelephone": "111",
                        "renderMoney": "100元",
                    },
                    {
                        "relationCompanyName": "供应商B",
                        "contactName": "联系人B",
                        "contactTelephone": "222",
                        "renderMoney": "200元",
                    },
                ],
            }

    spider.model_client = _FakeClient()
    spider.fetch_list_page = lambda category_num, page_index: {  # type: ignore[assignment]
        "custom": {
            "count": 1,
            "infodata": [
                {
                    "infourl": "/detail.html",
                    "areacode": "市本级",
                    "infodate": "2026-05-09",
                    "realtitle": "测试中标公告",
                }
            ],
        }
    }
    spider.fetch_detail_html = lambda infourl: (  # type: ignore[assignment]
        "http://example.com/detail.html",
        "<html><body><h1>测试中标公告</h1></body></html>",
    )
    task = ModuleTask(
        module_name="政府采购",
        parent_type="政府采购",
        category_num="002002004",
        notice_type="中标（成交）公告",
        module_path="/jyxx/002002/gonggongziyuan.html",
    )

    records = spider.collect_records_for_task(
        task, build_win_record, apply_win_model_enrichment
    )

    assert len(records) == 2
    assert records[0]["relationCompanyName"] == "供应商A"
    assert records[0]["contactName"] == "联系人A"
    assert records[0]["contactTelephone"] == "111"
    assert records[0]["renderMoney"] == "100元"
    assert records[1]["relationCompanyName"] == "供应商B"
    assert records[1]["contactName"] == "联系人B"
    assert records[1]["contactTelephone"] == "222"
    assert records[1]["renderMoney"] == "200元"


def test_win_collect_records_for_task_expands_multiple_items_from_raw_model_response_shape() -> (
    None
):
    spider = WinRuntime(
        module_name="政府采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="中标（成交）公告",
    )

    class _FakeClient:
        def get_result(self, text: str) -> dict[str, object]:
            return {
                "success": True,
                "msg": "ok",
                "result": {
                    "项目名称": "高青县国土变更调查及森林草原湿地荒漠调查监测工作",
                    "采购人名称": "高青县自然资源局",
                    "项目编号": "SDGP370322000202602000011",
                    "采购结果": [
                        {
                            "供应商名称": "山东中远地理信息工程有限公司",
                            "中标金额": "1039900.00元",
                            "联系人电话": "",
                            "联系人姓名": "",
                        },
                        {
                            "供应商名称": "高青顺泰土地信息咨询有限公司",
                            "中标金额": "1315000.00元",
                            "联系人电话": "",
                            "联系人姓名": "",
                        },
                    ],
                },
            }

    spider.model_client = _FakeClient()
    spider.fetch_list_page = lambda category_num, page_index: {  # type: ignore[assignment]
        "custom": {
            "count": 1,
            "infodata": [
                {
                    "infourl": "/detail.html",
                    "areacode": "高青县",
                    "infodate": "2026-05-08",
                    "realtitle": "高青县国土变更调查及森林草原湿地荒漠调查监测工作中标结果公告",
                }
            ],
        }
    }
    spider.fetch_detail_html = lambda infourl: (  # type: ignore[assignment]
        "http://example.com/detail.html",
        "<html><body><h1>高青县国土变更调查及森林草原湿地荒漠调查监测工作中标结果公告</h1></body></html>",
    )
    task = ModuleTask(
        module_name="政府采购",
        parent_type="政府采购",
        category_num="002002004",
        notice_type="中标（成交）公告",
        module_path="/jyxx/002002/gonggongziyuan.html",
    )

    records = spider.collect_records_for_task(
        task, build_win_record, apply_win_model_enrichment
    )

    assert len(records) == 2
    assert (
        records[0]["tenderTitle"] == "高青县国土变更调查及森林草原湿地荒漠调查监测工作"
    )
    assert records[0]["tenderNumber"] == "SDGP370322000202602000011"
    assert records[0]["procurementUnit"] == "高青县自然资源局"
    assert records[0]["relationCompanyName"] == "山东中远地理信息工程有限公司"
    assert records[0]["renderMoney"] == "1039900.00元"
    assert records[1]["relationCompanyName"] == "高青顺泰土地信息咨询有限公司"
    assert records[1]["renderMoney"] == "1315000.00元"


def test_bid_build_context_does_not_apply_government_procurement_sections_to_construction_module() -> (
    None
):
    spider = BidRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="",
    )
    task = ModuleTask(
        module_name="建设工程",
        parent_type="工程建设",
        category_num="002001001",
        notice_type="招标公告",
        module_path="/jyxx/002001/gonggongziyuan.html",
    )
    html = """
    <html>
      <body>
        <h1>某建设工程招标公告</h1>
        <p>项目编号：GC-001</p>
        <p>项目名称：某建设工程</p>
        <p>招标人：建设单位A</p>
        <p>项目负责人：王工 电话：1111</p>
        <p>1.采购人信息</p>
        <p>名 称：不该取的采购人</p>
        <p>3.项目联系方式</p>
        <p>项目联系人：不该优先的人</p>
        <p>电 话：2222</p>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "市本级",
            "infodate": "2026-05-08",
            "realtitle": "某建设工程招标公告",
        },
        detail,
        html,
    )

    assert context["procurement_unit"] == "建设单位A"
    assert context["contact_name"] == "王工"
    assert context["contact_phone"] == "1111"


def test_bid_build_context_uses_rural_engineering_specific_fields() -> None:
    spider = BidRuntime(
        module_name="农村工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="交易公告",
    )
    task = ModuleTask(
        module_name="农村工程",
        parent_type="农村产权",
        category_num="027001001",
        notice_type="交易公告",
        module_path="/nccqjyxx/027001/gonggongziyuan_nccq.html",
    )
    html = """
    <html>
      <body>
        <h1>某农村工程交易公告</h1>
        <table>
          <tr><td>项目编号</td><td>NC-001</td><td>项目名称</td><td>某农村工程交易公告</td></tr>
          <tr><td>挂牌价格</td><td colspan="3">0.6885万元</td></tr>
          <tr><td rowspan="3">项目实施主体基本情况</td><td>名称</td><td colspan="2">高青县某村股份经济合作社</td></tr>
          <tr><td>住址</td><td colspan="2">某地址</td></tr>
          <tr><td>联系人</td><td>张三</td><td>联系电话</td><td>0533-6355733</td></tr>
          <tr><td rowspan="2">流转（需求）标的基本情况</td><td>其他</td><td colspan="2">其他内容</td></tr>
        </table>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "高青县",
            "infodate": "2026-05-08",
            "realtitle": "某农村工程交易公告",
        },
        detail,
        html,
    )

    assert context["budget_amount"] == "6885.0元"
    assert context["procurement_unit"] == "高青县某村股份经济合作社"
    assert context["contact_name"] == "张三"
    assert context["contact_phone"] == "0533-6355733"

    record = build_bid_record(context)

    assert record["budgetAmount"] == "6885.0元"
    assert record["releaseSource"] == "高青县某村股份经济合作社"
    assert record["consultationInfo"] == {
        "purchasingInfor": ["名称：高青县某村股份经济合作社"],
        "projectInfo": ["项目联系人：张三", "电话：0533-6355733"],
    }


def test_bid_build_context_uses_rural_procurement_specific_fields() -> None:
    spider = BidRuntime(
        module_name="农村采购",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="交易公告",
    )
    task = ModuleTask(
        module_name="农村采购",
        parent_type="农村产权",
        category_num="027002001",
        notice_type="交易公告",
        module_path="/nccqjyxx/027002/gonggongziyuan_nccq.html",
    )
    html = """
    <html>
      <body>
        <h1>某农村采购交易公告</h1>
        <table>
          <tr><td>项目编号</td><td>NC-002</td><td>项目名称</td><td>某农村采购交易公告</td></tr>
          <tr><td>挂牌价格</td><td colspan="3">4.5万元</td></tr>
          <tr><td rowspan="3">项目实施主体基本情况</td><td>名称</td><td colspan="2">山东省淄博市张店区人民政府四宝山街道办事处韩庙村村民委员会</td></tr>
          <tr><td>住址</td><td colspan="2">某地址</td></tr>
          <tr><td>联系人</td><td>尹波</td><td>联系电话</td><td>13869324648</td></tr>
          <tr><td rowspan="2">流转（需求）标的基本情况</td><td>标的说明</td><td colspan="2">经民主决策，现采购韩庙村一期住宅楼电梯维保项目，提供服务12个月，预计总价4.5万元。</td></tr>
        </table>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "高新区",
            "infodate": "2026-05-07",
            "realtitle": "某农村采购交易公告",
        },
        detail,
        html,
    )

    assert context["budget_amount"] == "45000.0元"
    assert (
        context["procurement_unit"]
        == "山东省淄博市张店区人民政府四宝山街道办事处韩庙村村民委员会"
    )
    assert context["contact_name"] == "尹波"
    assert context["contact_phone"] == "13869324648"

    record = build_bid_record(context)

    assert record["budgetAmount"] == "45000.0元"
    assert (
        record["releaseSource"]
        == "山东省淄博市张店区人民政府四宝山街道办事处韩庙村村民委员会"
    )
    assert record["consultationInfo"] == {
        "purchasingInfor": [
            "名称：山东省淄博市张店区人民政府四宝山街道办事处韩庙村村民委员会"
        ],
        "projectInfo": ["项目联系人：尹波", "电话：13869324648"],
    }


def test_bid_build_context_uses_land_transfer_subject_fields() -> None:
    spider = BidRuntime(
        module_name="土地流转",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="交易公告",
    )
    task = ModuleTask(
        module_name="土地流转",
        parent_type="农村产权",
        category_num="027003001",
        notice_type="交易公告",
        module_path="/nccqjyxx/027003/gonggongziyuan_nccq.html",
    )
    html = """
    <html>
      <body>
        <h1>某土地流转交易公告</h1>
        <table>
        <tr><td>项目编号</td><td>TD-001</td><td>项目名称</td><td>某土地流转交易公告</td></tr>
          <tr><td>挂牌价格</td><td colspan="3">1.2万元</td></tr>
          <tr><td rowspan="3">项目实施主体基本情况</td><td>名称</td><td colspan="2">高青县某村村民委员会</td></tr>
          <tr><td>住址</td><td colspan="2">某地址</td></tr>
          <tr><td>联系人</td><td>李四</td><td>联系电话</td><td>13900000000</td></tr>
        </table>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "高青县",
            "infodate": "2026-05-07",
            "realtitle": "某土地流转交易公告",
        },
        detail,
        html,
    )

    assert context["budget_amount"] == "12000.0元"
    assert context["procurement_unit"] == "高青县某村村民委员会"
    assert context["contact_name"] == "李四"
    assert context["contact_phone"] == "13900000000"

    record = build_bid_record(context)

    assert record["budgetAmount"] == "12000.0元"
    assert record["releaseSource"] == "高青县某村村民委员会"
    assert record["consultationInfo"] == {
        "purchasingInfor": ["名称：高青县某村村民委员会"],
        "projectInfo": ["项目联系人：李四", "电话：13900000000"],
    }


def test_bid_build_context_uses_collective_asset_specific_fields() -> None:
    spider = BidRuntime(
        module_name="集体资产",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="交易公告",
    )
    task = ModuleTask(
        module_name="集体资产",
        parent_type="农村产权",
        category_num="027004001",
        notice_type="交易公告",
        module_path="/nccqjyxx/027004/gonggongziyuan_nccq.html",
    )
    html = """
    <html>
      <body>
        <h1>某集体资产交易公告</h1>
        <table>
          <tr><td>项目编号</td><td>JT-001</td><td>项目名称</td><td>某集体资产交易公告</td></tr>
          <tr><td>挂牌价格</td><td colspan="3">2.3万元</td></tr>
          <tr><td rowspan="3">项目实施主体基本情况</td><td>名称</td><td colspan="2">某集体资产股份经济合作社</td></tr>
          <tr><td>住址</td><td colspan="2">某地址</td></tr>
          <tr><td>联系人</td><td>王五</td><td>联系电话</td><td>13700000000</td></tr>
        </table>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "高青县",
            "infodate": "2026-05-07",
            "realtitle": "某集体资产交易公告",
        },
        detail,
        html,
    )

    assert context["budget_amount"] == "23000.0元"
    assert context["procurement_unit"] == "某集体资产股份经济合作社"
    assert context["contact_name"] == "王五"
    assert context["contact_phone"] == "13700000000"

    record = build_bid_record(context)

    assert record["budgetAmount"] == "23000.0元"
    assert record["releaseSource"] == "某集体资产股份经济合作社"
    assert record["consultationInfo"] == {
        "purchasingInfor": ["名称：某集体资产股份经济合作社"],
        "projectInfo": ["项目联系人：王五", "电话：13700000000"],
    }


def test_bid_build_context_uses_agricultural_facility_specific_fields() -> None:
    spider = BidRuntime(
        module_name="农业设施",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        enable_model_enrichment=False,
        notice_type_filter="交易公告",
    )
    task = ModuleTask(
        module_name="农业设施",
        parent_type="农村产权",
        category_num="027005001",
        notice_type="交易公告",
        module_path="/nccqjyxx/027005/gonggongziyuan_nccq.html",
    )
    html = """
    <html>
      <body>
        <h1>某农业设施交易公告</h1>
        <table>
          <tr><td>项目编号</td><td>NY-001</td><td>项目名称</td><td>某农业设施交易公告</td></tr>
          <tr><td>挂牌价格</td><td colspan="3">3.6万元</td></tr>
          <tr><td rowspan="3">项目实施主体基本情况</td><td>名称</td><td colspan="2">某农业设施专业合作社</td></tr>
          <tr><td>住址</td><td colspan="2">某地址</td></tr>
          <tr><td>联系人</td><td>赵六</td><td>联系电话</td><td>13600000000</td></tr>
        </table>
      </body>
    </html>
    """
    detail = parse_bid_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "高青县",
            "infodate": "2026-05-07",
            "realtitle": "某农业设施交易公告",
        },
        detail,
        html,
    )

    assert context["budget_amount"] == "36000.0元"
    assert context["procurement_unit"] == "某农业设施专业合作社"
    assert context["contact_name"] == "赵六"
    assert context["contact_phone"] == "13600000000"

    record = build_bid_record(context)

    assert record["budgetAmount"] == "36000.0元"
    assert record["releaseSource"] == "某农业设施专业合作社"
    assert record["consultationInfo"] == {
        "purchasingInfor": ["名称：某农业设施专业合作社"],
        "projectInfo": ["项目联系人：赵六", "电话：13600000000"],
    }


def test_build_record_for_bid_board() -> None:
    record = build_bid_record(make_bid_context())

    assert record["bidType"] == ""
    assert record["announcementTitle"] == "测试项目"
    assert record["announcementType"] == "招标公告"


def test_normalize_money_keeps_plain_yuan_amount_format() -> None:
    assert normalize_money("460000") == "460000元"


def test_build_record_for_candidate_board() -> None:
    record = build_candidate_record(make_candidate_context())

    assert record["renderType"] == "中标候选人"
    assert record["announcementType"] == "候选人公告"
    assert record["extra"]["candidateSort"] == [
        "第一候选人：甲公司",
        "第二候选人：乙公司",
    ]


def test_candidate_build_context_does_not_parse_model_managed_fields_when_model_is_disabled() -> (
    None
):
    spider = CandidateRuntime(
        module_name="建设工程",
        start_page=1,
        max_pages=1,
        page_size=15,
        timeout_seconds=30,
        detail_delay_seconds=0,
        notice_type_filter="中标候选人公示",
    )
    task = ModuleTask(
        module_name="建设工程",
        parent_type="建设工程",
        category_num="002001003",
        notice_type="中标候选人公示",
        module_path="/jyxx/002001/gonggongziyuan.html",
    )
    html = """
    <html>
      <body>
        <h1>某项目中标候选人公示</h1>
        <table>
          <tr><td>项目名称</td><td>某项目</td><td>项目编号</td><td>ZB-001</td></tr>
          <tr><td>招标人名称</td><td>某招标人单位</td><td>第一中标候选人</td><td>候选人甲</td></tr>
          <tr><td>第二中标候选人</td><td>候选人乙</td><td>项目负责人</td><td>张三</td></tr>
        </table>
      </body>
    </html>
    """
    detail = parse_candidate_detail(html, "http://example.com/detail.html")

    context = spider.build_context(
        task,
        {
            "areacode": "市本级",
            "infodate": "2026-05-09",
            "realtitle": "某项目中标候选人公示",
        },
        detail,
        html,
    )

    assert context["procurement_unit"] == ""
    assert context["relation_company_name"] == ""
    assert context["candidate_names"] == []
    assert context["candidate_sort"] == []


def test_candidate_model_enrichment_uses_general_model_result_without_local_rebuild() -> None:
    runtime = Mock()
    runtime.logger = Mock()
    runtime.model_client.get_result.return_value = {
        "tenderTitle": "模型标题",
        "procurementUnit": "模型采购单位",
        "result": [
            {
                "relationCompanyName": "候选人甲",
                "candidateSort": [
                    {"候选人名称": "候选人甲"},
                    {"候选人名称": "候选人乙"},
                ],
            }
        ],
        "extra": {"tenderNumber": "MODEL-001"},
    }
    record = build_candidate_record(make_candidate_context())
    context = make_candidate_context() | {
        "plain_text": "正文",
        "cleaned_html": "<p>正文</p>",
        "procurement_unit": "",
        "relation_company_name": "",
        "candidate_names": [],
        "candidate_sort": [],
        "project_num": "",
    }

    enriched = apply_candidate_model_enrichment(runtime, record, context)

    assert enriched["tenderTitle"] == "模型标题"
    assert enriched["procurementUnit"] == "模型采购单位"
    assert enriched["relationCompanyName"] == "候选人甲"
    assert enriched["extra"] == {
        "candidateSort": [{}, {}],
        "tenderNumber": "MODEL-001",
    }


def test_candidate_model_enrichment_logs_warning_and_falls_back_on_model_error() -> (
    None
):
    runtime = Mock()
    runtime.model_client.get_result.side_effect = ValueError("bad model response")
    runtime.logger = Mock()
    record = build_candidate_record(make_candidate_context())
    context = make_candidate_context() | {
        "plain_text": "正文",
        "cleaned_html": "<p>正文</p>",
    }

    enriched = apply_candidate_model_enrichment(runtime, record, context)

    assert enriched == record
    runtime.logger.warning.assert_called_once()


def test_build_record_for_win_board() -> None:
    record = build_win_record(make_win_context())

    assert record["renderType"] == ""
    assert record["announcementType"] == 2
    assert record["projectClassification"] == "[5]"


def test_bid_model_enrichment_logs_warning_and_falls_back_on_model_error() -> None:
    runtime = Mock()
    runtime.model_client.get_result.side_effect = ValueError("bad model response")
    runtime.logger = Mock()
    record = build_bid_record(make_bid_context())
    context = make_bid_context() | {"plain_text": "正文", "cleaned_html": "<p>正文</p>"}

    enriched = apply_bid_model_enrichment(runtime, record, context)

    assert enriched == record
    runtime.logger.warning.assert_called_once()


def test_win_model_enrichment_logs_warning_and_falls_back_on_model_error() -> None:
    runtime = Mock()
    runtime.model_client.get_result.side_effect = ValueError("bad model response")
    runtime.logger = Mock()
    record = build_win_record(make_win_context())
    context = make_win_context() | {"plain_text": "正文", "cleaned_html": "<p>正文</p>"}

    enriched = apply_win_model_enrichment(runtime, record, context)

    assert enriched == [record]
    runtime.logger.warning.assert_called_once()


def test_supported_notice_type_sets() -> None:
    assert SUPPORTED_BID_NOTICE_TYPES == {"招标公告", "采购公告", "交易公告"}
    assert SUPPORTED_WIN_NOTICE_TYPES == {
        "中标结果公告",
        "中标（成交）公告",
        "成交结果公告",
        "结果公示",
    }
    assert SUPPORTED_CANDIDATE_NOTICE_TYPES == {
        "中标候选人公示",
        "评标结果公示",
        "预中标公示",
    }


def test_excluded_notice_types_are_filtered_out() -> None:
    assert EXCLUDED_NOTICE_TYPES == {
        "招标项目计划",
        "变更公告",
        "澄清公告",
        "更正公告",
        "终止公告",
        "废标公告",
        "流标公告",
        "异常公告",
        "异议回复",
        "验收公告",
        "需求（意向）公示",
        "合同公告",
        "合同公示",
        "合同公示及变更",
        "土地信息",
    }


def test_excluded_module_names_are_filtered_out() -> None:
    assert EXCLUDED_MODULE_NAMES == {"自然资源", "供需信息", "产权交易"}


def test_core_main_runs_three_modules_in_order(monkeypatch) -> None:
    calls: list[tuple[str, list[str] | None]] = []

    def runner_factory(name: str):
        def _runner(argv: list[str] | None = None) -> int:
            calls.append((name, argv))
            return 0

        return _runner

    monkeypatch.setattr(
        zbggzy_core,
        "RUNNERS",
        [
            ("招标公告", runner_factory("招标公告")),
            ("中标公告", runner_factory("中标公告")),
            ("候选人公告", runner_factory("候选人公告")),
        ],
    )

    assert zbggzy_core.main() == 0
    assert calls == [
        ("招标公告", None),
        ("中标公告", None),
        ("候选人公告", None),
    ]
