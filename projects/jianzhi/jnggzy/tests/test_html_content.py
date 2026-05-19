from __future__ import annotations

import base64
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from jnggzy import clean_html_content, normalize_text  # noqa: E402


def test_normalize_text_converts_none_and_null_like_values_to_empty() -> None:
    assert normalize_text(None) == ""
    assert normalize_text("None") == ""
    assert normalize_text("null") == ""
    assert normalize_text(" 正文 ") == "正文"


def test_clean_html_content_removes_anchor_tags_but_keeps_text() -> None:
    html = (
        '<html><body>'
        '<div>当前位置：<a href="/index">首页</a> > <a href="/gcjs">建设工程</a></div>'
        '<p>ca办理及相关咨询请点击 <a href="http://124.128.84.51:9000/jnggzy/jnggzyca/index.jsp#nav-7">查看</a></p>'
        '<div>正文内容保留</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "<a " not in cleaned
    assert "</a>" not in cleaned
    assert "href=" not in cleaned
    assert "当前位置" not in cleaned
    assert "首页" not in cleaned
    assert "建设工程" not in cleaned
    assert "查看" not in cleaned
    assert "124.128.84.51:9000" not in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_removes_prompt_and_attachment_links_only() -> None:
    html = (
        '<html><body>'
        '<p>尊敬的用户您好！如页面信息无法正常显示，请更换360浏览器后，点击以下链接尝试 '
        '<a href="https://example.com/test">链接地址</a></p>'
        '<a href="/attach/download.do?id=1">附件下载</a>'
        '<a href="/notice/detail?id=1">普通跳转</a>'
        '<a href="/files/result.pdf">结果文件</a>'
        '<div>正文内容保留</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "尊敬的用户您好" not in cleaned
    assert "附件下载" not in cleaned
    assert "结果文件" not in cleaned
    assert '<a href="/notice/detail?id=1">普通跳转</a>' not in cleaned
    assert "普通跳转" in cleaned
    assert "正文内容保留" in cleaned


def test_html_content_value_is_base64_of_cleaned_original_html() -> None:
    html = '<html><body><div><a href="/index">首页</a></div><div>正文</div></body></html>'

    encoded = base64.b64encode(clean_html_content(html).encode("utf-8")).decode("utf-8")
    decoded = base64.b64decode(encoded).decode("utf-8")

    assert decoded == clean_html_content(html)
    assert decoded.startswith("<html>")
    assert "<a " not in decoded
    assert "首页" in decoded


def test_clean_html_content_removes_join_button_only() -> None:
    html = (
        '<html><body>'
        '<div>请点击“我要参与”登录系统下载文件。</div>'
        '<input type="button" id="cqdy" onclick="wycyfunction();" style="width: 200px;" value="我要参与" />'
        '<div>正文内容保留</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "<input" not in cleaned
    assert "wycyfunction" not in cleaned
    assert "请点击“我要参与”登录系统下载文件。" in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_removes_close_page_button() -> None:
    html = (
        '<html><body>'
        '<!--  关闭本页-->'
        '<span class="closes" style="cursor: pointer" onclick="window.close();">关闭本页</span>'
        '<div>正文内容保留</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "window.close" not in cleaned
    assert "关闭本页" not in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_removes_clarification_button_and_popup() -> None:
    html = (
        '<html><body>'
        '<input type="button" id="cqdy" onclick="cqdyfunction();" style="width: 200px;" value="澄清答疑" />'
        '<div class="shows hide" style="display: none">'
        '<div class="zdrqda_tit">澄清答疑<div class="tcclose"></div></div>'
        '<iframe id="cqdyifram" src="" width="1050px"></iframe>'
        '</div>'
        '<script>function cqdyfunction() { $("#cqdyifram").attr("src", "http://example.com"); }</script>'
        '<div>正文内容保留</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "cqdyfunction" not in cleaned
    assert "cqdyifram" not in cleaned
    assert "澄清答疑" not in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_removes_breadcrumb_block() -> None:
    html = (
        '<html><body>'
        '<div class="crumb">当前位置：首页 > 建设工程 > 中标结果公告</div>'
        '<div>正文内容保留</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "当前位置" not in cleaned
    assert "首页 > 建设工程 > 中标结果公告" not in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_removes_attachment_intro_and_help_blocks_but_keeps_publish_info() -> None:
    html = (
        '<html><body>'
        '<div>附件：</div>'
        '<p>PDF版招标文件(评审咨询服务)</p>'
        '<p>请点击“我要参与”登录济南公共资源交易中心网站选择进入济南公共资源交易电子平台-政府采购交易系统，点击“跳转新系统”按钮，跳转后下载ztbml版响应文件。登录地址：http://jnggzy.jinan.gov.cn/jnggzyztb/new_flogin/login.do</p>'
        '<p>发布人：山东邦卓招标有限责任公司</p>'
        '<p>发布时间：2026年05月08日</p>'
        '<div>请点击此处下载</div>'
        '<div>ca办理及相关咨询请点击</div>'
        '<div>http://124.128.84.51:9000/jnggzy/jnggzyca/index.jsp#nav-7查看</div>'
        '<div>技术支持电话 0531-59596642、0531-59596643</div>'
        '<div>相关附件：</div>'
        '<div>正文内容保留</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert '<div>附件：</div>' not in cleaned
    assert "PDF版招标文件" not in cleaned
    assert "请点击“我要参与”登录济南公共资源交易中心网站" not in cleaned
    assert "请点击此处下载" not in cleaned
    assert "ca办理及相关咨询请点击" not in cleaned
    assert "124.128.84.51:9000" not in cleaned
    assert "发布人：山东邦卓招标有限责任公司" in cleaned
    assert "发布时间：2026年05月08日" in cleaned
    assert "技术支持电话 0531-59596642、0531-59596643" in cleaned
    assert "相关附件：" not in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_does_not_delete_publish_info_after_attachment_area() -> None:
    html = (
        '<html><body>'
        '<div class="notice-main">'
        '<div>附件：</div>'
        '<ul><li><a href="/downloadfile/notice.pdf">PDF版招标文件</a></li></ul>'
        '<p>发布人：济南公共资源交易中心</p>'
        '<p>发布时间：2026年05月09日</p>'
        '<p>技术支持电话：0531-59596642</p>'
        '</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "附件：" not in cleaned
    assert "PDF版招标文件" not in cleaned
    assert "发布人：济南公共资源交易中心" in cleaned
    assert "发布时间：2026年05月09日" in cleaned
    assert "技术支持电话：0531-59596642" in cleaned


def test_clean_html_content_handles_colon_variants_and_keeps_tail_metadata() -> None:
    html = (
        '<html><body>'
        '<div>当前位置:首页 &gt; 建设工程 &gt; 中标结果公告</div>'
        '<div>正文内容保留</div>'
        '<div>CA办理及相关咨询请点击</div>'
        '<div>HTTP://124.128.84.51:9000/jnggzy/jnggzyca/index.jsp#nav-7查看</div>'
        '<p>发布人：济南公共资源交易中心</p>'
        '<p>发布时间：2026年05月09日</p>'
        '<p>技术支持电话：0531-59596642</p>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "当前位置" not in cleaned
    assert "CA办理及相关咨询请点击" not in cleaned
    assert "124.128.84.51:9000" not in cleaned
    assert "正文内容保留" in cleaned
    assert "发布人：济南公共资源交易中心" in cleaned
    assert "发布时间：2026年05月09日" in cleaned
    assert "技术支持电话：0531-59596642" in cleaned


def test_clean_html_content_removes_detached_login_url_but_keeps_normal_site_mentions() -> None:
    html = (
        '<html><body>'
        '<p>方式：须在济南公共资源交易中心网站（jnggzy.jinan.gov.cn）自行下载采购文件。</p>'
        '<p><span></span><span>http://jnggzy.jinan.gov.cn/jnggzyztb/new_flogin/login.do</span></p>'
        '<p>发布人：山东华远项目管理有限公司</p>'
        '<p>发布时间：2026年05月07日</p>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "济南公共资源交易中心网站（jnggzy.jinan.gov.cn）自行下载采购文件" in cleaned
    assert "new_flogin/login.do" not in cleaned
    assert "发布人：山东华远项目管理有限公司" in cleaned
    assert "发布时间：2026年05月07日" in cleaned


def test_clean_html_content_removes_script_and_link_tags() -> None:
    html = (
        '<html><head>'
        '<link href="/jnggzyztb/ui/css/global.css" rel="stylesheet" />'
        '<script>$("#gtqrlj").attr("href", "/jump");</script>'
        '</head><body><div>正文内容保留</div></body></html>'
    )

    cleaned = clean_html_content(html)

    assert "<link" not in cleaned
    assert "<script" not in cleaned
    assert "href=" not in cleaned
    assert "gtqrlj" not in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_makes_hidden_main_content_visible() -> None:
    html = (
        '<html><body>'
        '<div class="wrapper" style="display:none">'
        '<table style="display:none"><tr><td><div>正文主内容</div></td></tr></table>'
        '<p>发布时间：2026年05月09日</p>'
        '</div>'
        '<div class="shows hide" style="display:none">'
        '<div>澄清答疑</div>'
        '<iframe id="cqdyifram"></iframe>'
        '</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "正文主内容" in cleaned
    assert "发布时间：2026年05月09日" in cleaned
    assert 'display:none' not in cleaned.lower()
    assert 'class="shows hide"' not in cleaned
    assert "澄清答疑" not in cleaned


def test_clean_html_content_keeps_core_body_text_visible_without_hidden_style() -> None:
    html = (
        '<html><body>'
        '<table style="display:none"><tr><td>'
        '<p class="details_p">项目名称：土地矿产测试项目</p>'
        '<p class="fbsj_p">发布时间：2026年05月09日</p>'
        '</td></tr></table>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "土地矿产测试项目" in cleaned
    assert "发布时间：2026年05月09日" in cleaned
    assert "display:none" not in cleaned.lower()


def test_clean_html_content_extracts_nested_html_from_table_shell() -> None:
    html = (
        '<html><head><title>公告详情</title></head><body>'
        '<div class="main"><div class="list">'
        '<h1>外层标题</h1>'
        '<table border="1" class="table2" width="100%">'
        '<html><head>'
        '<meta http-equiv="content-type" content="text/html; charset=utf-8" />'
        '<div id="$(0,#caid1)" key="ca1">$(0,#cadata1)</div>'
        '<div id="$(0,#caid2)" key="ca2">$(0,#cadata2)</div>'
        '<title></title>'
        '</head><body>'
        '<div class="tle">真正正文标题</div>'
        '<table class="table_one"><tr><td>项目编号</td><td>JL02202604300127</td></tr></table>'
        '</body></html>'
        '</table>'
        '</div></div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "真正正文标题" in cleaned
    assert "JL02202604300127" in cleaned
    assert "$(0,#cadata1)" not in cleaned
    assert "$(0,#cadata2)" not in cleaned
    assert cleaned.count("<html") == 1


def test_clean_html_content_removes_bottom_change_notice_li() -> None:
    html = (
        '<html><body>'
        '<div>正文内容保留</div>'
        '<ul><li class="bggg">变更公告</li></ul>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert 'class="bggg"' not in cleaned
    assert "变更公告" not in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_does_not_cut_normal_page_when_no_cadata_markers() -> None:
    html = (
        '<html><head><title>公告详情</title></head><body>'
        '<div class="main">'
        '<p>项目名称: 正常页面项目</p>'
        '<p>投标人资格要求</p>'
        '<p>1. 正文内容保留</p>'
        '</div>'
        '<html><head><meta charset="utf-8" /></head><body><p>空壳片段</p></body></html>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "正常页面项目" in cleaned
    assert "投标人资格要求" in cleaned
    assert "正文内容保留" in cleaned


def test_clean_html_content_extracts_real_inner_document_after_link_prompt() -> None:
    html = (
        '<!DOCTYPE html><html lang="en"><head><title>公告详情</title></head><body>'
        '<div>尊敬的用户您好！如页面信息无法正常显示，请更换360浏览器后，点击以下链接尝试 '
        '<a id="gtqrlj" href="">链接地址</a></div>'
        '<table class="table2" border="1" width="100%">'
        '<html><head><title>全省招标类信息系统</title></head><body>'
        '<table width="80%" align="center"><tr><td><h2>资格预审不通过单位名单</h2></td></tr>'
        '<tr><td><b>项目编号:</b>2026LLQC01Z5807001</td></tr>'
        '<tr><td><b>项目名称:</b>英雄山工作部办公区西侧区域综合提升项目施工总承包</td></tr>'
        '<tr><td><b>投标人资格要求</b></td></tr>'
        '<tr><td>1、本次招标要求潜在投标人须具备独立法人资格。</td></tr>'
        '</table>'
        '</body></html>'
        '</table>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "资格预审不通过单位名单" in cleaned
    assert "2026LLQC01Z5807001" in cleaned
    assert "投标人资格要求" in cleaned
    assert "1、本次招标要求潜在投标人须具备独立法人资格。" in cleaned
    assert "链接地址" not in cleaned


def test_clean_html_content_keeps_body_when_main_container_starts_with_breadcrumb_and_prompt() -> None:
    html = (
        '<html><body>'
        '<div class="main">'
        '<div class="bread">当前位置：首页>产权交易>招标公告</div>'
        '<div class="infor">尊敬的用户您好！如页面信息无法正常显示，请更换360浏览器后，点击以下链接尝试链接地址</div>'
        '<table class="table2" border="1" width="100%">'
        '<tr><td><p>一、标的基本情况</p></td></tr>'
        '<tr><td><p>单位名称：济南绿地商城有限责任公司</p></td></tr>'
        '</table>'
        '<div class="close"><span class="closes" onclick="window.close();">关闭本页</span></div>'
        '</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "一、标的基本情况" in cleaned
    assert "济南绿地商城有限责任公司" in cleaned
    assert "当前位置" not in cleaned
    assert "尊敬的用户您好" not in cleaned
    assert "关闭本页" not in cleaned


def test_clean_html_content_keeps_rural_property_body_in_main_container() -> None:
    html = (
        '<html><body>'
        '<div class="main">'
        '<div class="bread">当前位置：首页>农村产权>成交公告</div>'
        '<h1>济阳区新市镇王家村水泥路承包项目</h1>'
        '<table>'
        '<tr><td>项目编号</td><td>370115-2025-JSXMZB-024080</td></tr>'
        '<tr><td>成交方名称</td><td>济南鑫鹏建设有限公司新市分公司</td></tr>'
        '</table>'
        '<div class="close"><span class="closes" onclick="window.close();">关闭本页</span></div>'
        '</div>'
        '</body></html>'
    )

    cleaned = clean_html_content(html)

    assert "济阳区新市镇王家村水泥路承包项目" in cleaned
    assert "370115-2025-JSXMZB-024080" in cleaned
    assert "济南鑫鹏建设有限公司新市分公司" in cleaned
    assert "当前位置" not in cleaned
    assert "关闭本页" not in cleaned
