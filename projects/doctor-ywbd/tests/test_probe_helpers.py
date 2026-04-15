from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_ywbd.probe_helpers import (  # noqa: E402
    extract_area_seed_urls,
    build_entry_seed_records,
    build_hospital_expert_ajax_request_specs,
    build_next_disease_list_page_url,
    extract_department_seed_urls,
    extract_doctor_info_urls,
    extract_hospital_expert_ajax_context,
    extract_hospital_expert_doctor_urls,
    extract_hospital_area_seed_urls,
    extract_hospital_list_urls,
    extract_knownsec_block_reason,
    extract_list_urls,
    is_first_disease_index_page,
    is_first_list_page,
)


def test_extract_knownsec_block_reason_from_waf_html() -> None:
    html = """
    <script>
    var data = {"error_403_type":"foregin_ip","error_403":"Knownsec CloudWAF: Your IP is not allowed to visit this website!"};
    </script>
    """
    assert extract_knownsec_block_reason(html) == "foregin_ip"


def test_build_entry_seed_records_cover_four_confirmed_entries() -> None:
    assert build_entry_seed_records() == [
        {"category": "disease", "url": "https://data.120ask.com/yisheng/jibing.html"},
        {"category": "department", "url": "https://data.120ask.com/yisheng/keshi.html"},
        {"category": "area", "url": "https://data.120ask.com/yisheng/area.html"},
        {"category": "hospital", "url": "https://data.120ask.com/yiyuan/area.html"},
    ]


def test_extract_list_urls_for_disease_flow() -> None:
    html = """
    <div class="page"><span>共3页</span></div>
    <a href="/yisheng/jibing_p2.html">第二页</a>
    <a href="/yisheng/jibing_p3.html">第三页</a>
    <a href="/yisheng/list_j1072.html">白癜风医生</a>
    <a href="/yisheng/list_j1072p2.html">下一页</a>
    <a href="/yisheng/jibing_b2.html">按部位筛选</a>
    <a href="/yisheng/list_d1.html">ignore</a>
    """
    assert extract_list_urls("disease", "https://data.120ask.com/yisheng/jibing.html", html) == [
        "https://data.120ask.com/yisheng/jibing.html",
        "https://data.120ask.com/yisheng/jibing_p2.html",
        "https://data.120ask.com/yisheng/jibing_p3.html",
        "https://data.120ask.com/yisheng/list_j1072.html",
    ]


def test_extract_list_urls_for_department_flow() -> None:
    html = """
    <a href="/yisheng/list_d1.html">内科</a>
    <a href="/yisheng/list_d1p2.html">下一页</a>
    <a href="/yisheng/list_d19.html">心血管内科</a>
    <a href="/yisheng/list_a110000.html">ignore</a>
    """
    assert extract_list_urls("department", "https://data.120ask.com/yisheng/keshi.html", html) == [
        "https://data.120ask.com/yisheng/list_d1.html",
        "https://data.120ask.com/yisheng/list_d1p2.html",
        "https://data.120ask.com/yisheng/list_d19.html",
    ]


def test_extract_list_urls_for_department_page_keep_only_same_department_pagination() -> None:
    html = """
    <span>共200页</span>
    <a href="/yisheng/list_d1.html">内科</a>
    <a href="/yisheng/list_d1p2.html">下一页</a>
    <a href="/yisheng/list_d1p200.html">末页</a>
    <a href="/yisheng/list_d19.html">心血管内科</a>
    <a href="/yisheng/list_d19p2.html">心血管内科第二页</a>
    """
    result = extract_list_urls("department", "https://data.120ask.com/yisheng/list_d1.html", html)
    assert result[0] == "https://data.120ask.com/yisheng/list_d1.html"
    assert result[1] == "https://data.120ask.com/yisheng/list_d1p2.html"
    assert result[-1] == "https://data.120ask.com/yisheng/list_d1p200.html"
    assert len(result) == 200
    assert "https://data.120ask.com/yisheng/list_d19.html" not in result


def test_extract_department_seed_urls_keep_leaf_departments() -> None:
    html = """
    <div class="keshi-list">
      <div class="nav-box">
        <div class="box">
          <strong><a href="/yisheng/list_d1.html">内科</a></strong>
          <strong><a href="/yisheng/list_d19.html">心血管内科</a></strong>
          <strong><a href="/yisheng/list_d20.html">神经内科</a></strong>
        </div>
      </div>
      <div class="nav-box">
        <div class="box">
          <strong><a href="/yisheng/list_d511.html">营养科</a></strong>
        </div>
      </div>
    </div>
    """
    assert extract_department_seed_urls("https://data.120ask.com/yisheng/keshi.html", html) == [
        "https://data.120ask.com/yisheng/list_d19.html",
        "https://data.120ask.com/yisheng/list_d20.html",
        "https://data.120ask.com/yisheng/list_d511.html",
    ]


def test_extract_list_urls_for_area_flow() -> None:
    html = """
    <a href="/yisheng/list_a110000.html">北京</a>
    <a href="/yisheng/list_a110000p2.html">下一页</a>
    <a href="/yisheng/list_a110105.html">朝阳区</a>
    <a href="/yisheng/8ly2pltyawkim7p7.html">ignore-doctor</a>
    """
    assert extract_list_urls("area", "https://data.120ask.com/yisheng/area.html", html) == [
        "https://data.120ask.com/yisheng/list_a110000.html",
        "https://data.120ask.com/yisheng/list_a110000p2.html",
        "https://data.120ask.com/yisheng/list_a110105.html",
    ]


def test_extract_list_urls_for_area_page_keep_only_same_area_pagination() -> None:
    html = """
    <span>共200页</span>
    <a href="/yisheng/list_a110105.html">朝阳区</a>
    <a href="/yisheng/list_a110105p2.html">下一页</a>
    <a href="/yisheng/list_a110105p200.html">末页</a>
    <a href="/yisheng/list_a110108.html">海淀区</a>
    <a href="/yisheng/list_a110108p2.html">海淀第二页</a>
    """
    result = extract_list_urls("area", "https://data.120ask.com/yisheng/list_a110105.html", html)
    assert result[0] == "https://data.120ask.com/yisheng/list_a110105.html"
    assert result[1] == "https://data.120ask.com/yisheng/list_a110105p2.html"
    assert result[-1] == "https://data.120ask.com/yisheng/list_a110105p200.html"
    assert len(result) == 200
    assert "https://data.120ask.com/yisheng/list_a110108.html" not in result


def test_extract_area_seed_urls_keep_only_leaf_areas() -> None:
    html = """
    <div class="keshi-list">
      <div class="nav-box">
        <div class="box">
          <strong><a href="/yisheng/list_a110000.html">北京市</a></strong>
          <strong><a href="/yisheng/list_a110101.html">东城区</a></strong>
          <strong><a href="/yisheng/list_a110105.html">朝阳区</a></strong>
        </div>
      </div>
      <div class="nav-box">
        <div class="box">
          <strong><a href="/yisheng/list_a130000.html">河北省</a></strong>
          <strong><a href="/yisheng/list_a130100.html">石家庄市</a></strong>
          <strong><a href="/yisheng/list_a130102.html">长安区</a></strong>
          <strong><a href="/yisheng/list_a130121.html">井陉县</a></strong>
        </div>
      </div>
    </div>
    """
    assert extract_area_seed_urls("https://data.120ask.com/yisheng/area.html", html) == [
        "https://data.120ask.com/yisheng/list_a110101.html",
        "https://data.120ask.com/yisheng/list_a110105.html",
        "https://data.120ask.com/yisheng/list_a130102.html",
        "https://data.120ask.com/yisheng/list_a130121.html",
    ]


def test_extract_hospital_list_urls_include_list_detail_and_expert_pages() -> None:
    html = """
    <a href="/yiyuan/list_a110000.html">北京医院列表</a>
    <a href="/yiyuan/list_a110000p2.html">下一页</a>
    <a href="/yiyuan/0387pltyawkim7pa.html">广安门医院</a>
    <a href="/yiyuan/yisheng/0387pltyawkim7pa.html">专家出诊</a>
    <a href="/yiyuan/jieshao/0387pltyawkim7pa.html">ignore</a>
    """
    assert extract_hospital_list_urls("https://data.120ask.com/yiyuan/area.html", html) == [
        "https://data.120ask.com/yiyuan/list_a110000.html",
        "https://data.120ask.com/yiyuan/list_a110000p2.html",
        "https://data.120ask.com/yiyuan/0387pltyawkim7pa.html",
        "https://data.120ask.com/yiyuan/yisheng/0387pltyawkim7pa.html",
    ]


def test_extract_hospital_list_urls_for_area_page_keep_only_same_area_pagination_and_hospital_targets() -> None:
    html = """
    <span>共15页</span>
    <a href="/yiyuan/list_a110105.html">朝阳区医院</a>
    <a href="/yiyuan/list_a110105p2.html">下一页</a>
    <a href="/yiyuan/list_a110105p15.html">末页</a>
    <a href="/yiyuan/list_a110108.html">海淀区医院</a>
    <a href="/yiyuan/0387pltyawkim7pa.html">广安门医院</a>
    <a href="/yiyuan/yisheng/0387pltyawkim7pa.html">专家出诊</a>
    """
    result = extract_hospital_list_urls("https://data.120ask.com/yiyuan/list_a110105.html", html)
    assert result[:3] == [
        "https://data.120ask.com/yiyuan/list_a110105.html",
        "https://data.120ask.com/yiyuan/list_a110105p2.html",
        "https://data.120ask.com/yiyuan/list_a110105p3.html",
    ]
    assert result[14] == "https://data.120ask.com/yiyuan/list_a110105p15.html"
    assert result[-2:] == [
        "https://data.120ask.com/yiyuan/0387pltyawkim7pa.html",
        "https://data.120ask.com/yiyuan/yisheng/0387pltyawkim7pa.html",
    ]
    assert len(result) == 17
    assert "https://data.120ask.com/yiyuan/list_a110108.html" not in result


def test_extract_hospital_area_seed_urls_keep_only_leaf_areas() -> None:
    html = """
    <div class="keshi-list">
      <div class="nav-box">
        <div class="box">
          <strong><a href="/yiyuan/list_a110000.html">北京市</a></strong>
          <strong><a href="/yiyuan/list_a110101.html">东城区</a></strong>
          <strong><a href="/yiyuan/list_a110105.html">朝阳区</a></strong>
        </div>
      </div>
      <div class="nav-box">
        <div class="box">
          <strong><a href="/yiyuan/list_a130000.html">河北省</a></strong>
          <strong><a href="/yiyuan/list_a130100.html">石家庄市</a></strong>
          <strong><a href="/yiyuan/list_a130102.html">长安区</a></strong>
          <strong><a href="/yiyuan/list_a130121.html">井陉县</a></strong>
        </div>
      </div>
    </div>
    """
    assert extract_hospital_area_seed_urls("https://data.120ask.com/yiyuan/area.html", html) == [
        "https://data.120ask.com/yiyuan/list_a110101.html",
        "https://data.120ask.com/yiyuan/list_a110105.html",
        "https://data.120ask.com/yiyuan/list_a130102.html",
        "https://data.120ask.com/yiyuan/list_a130121.html",
    ]


def test_extract_doctor_info_urls_only_keep_final_doctor_pages() -> None:
    html = """
    <a href="/yisheng/f06faia2nlwg3h0f.html">医生 A</a>
    <a href="https://data.120ask.com/yisheng/0hj2fia2nlwg3h0f.html">医生 B</a>
    <a href="/yisheng/jibing_b2.html">body-disease-filter</a>
    <a href="/yisheng/abc123.html">ignore-short-slug</a>
    <a href="/yisheng/list_d1.html">ignore-list</a>
    <a href="/yisheng/area.html">ignore-entry</a>
    <a href="/yiyuan/yisheng/0387pltyawkim7pa.html">ignore-hospital-expert</a>
    """
    assert extract_doctor_info_urls("https://data.120ask.com/yisheng/list_d1.html", html) == [
        "https://data.120ask.com/yisheng/f06faia2nlwg3h0f.html",
        "https://data.120ask.com/yisheng/0hj2fia2nlwg3h0f.html",
    ]


def test_extract_list_urls_keep_real_pagination_links() -> None:
    html = """
    <span>共200页</span>
    <a href="/yisheng/list_j719.html">第一页</a>
    <a href="/yisheng/list_j719p2.html">第二页</a>
    <a href="/yisheng/list_j719p200.html">末页</a>
    <a href="/yisheng/list_j888.html">别的疾病</a>
    <a href="/yisheng/list_j888p2.html">别的疾病翻页</a>
    <a href="/yisheng/f06faia2nlwg3h0f.html">医生详情</a>
    """
    result = extract_list_urls("disease", "https://data.120ask.com/yisheng/list_j719.html", html)
    assert result[0] == "https://data.120ask.com/yisheng/list_j719.html"
    assert result[1] == "https://data.120ask.com/yisheng/list_j719p2.html"
    assert result[-1] == "https://data.120ask.com/yisheng/list_j719p200.html"
    assert len(result) == 200
    assert "https://data.120ask.com/yisheng/list_j888.html" not in result


def test_extract_list_urls_for_disease_page_use_page_count_to_expand_full_range() -> None:
    html = """
    <div class="page">
      <a class="w_aa2" href="/yisheng/list_j520.html">第一页</a>
      <a class="w_aa2" href="/yisheng/list_j520p11.html">上一页</a>
      <a class='page-num'>12</a>
      <span>共12页</span>
    </div>
    """
    assert extract_list_urls("disease", "https://data.120ask.com/yisheng/list_j520p12.html", html) == [
        "https://data.120ask.com/yisheng/list_j520.html",
        "https://data.120ask.com/yisheng/list_j520p2.html",
        "https://data.120ask.com/yisheng/list_j520p3.html",
        "https://data.120ask.com/yisheng/list_j520p4.html",
        "https://data.120ask.com/yisheng/list_j520p5.html",
        "https://data.120ask.com/yisheng/list_j520p6.html",
        "https://data.120ask.com/yisheng/list_j520p7.html",
        "https://data.120ask.com/yisheng/list_j520p8.html",
        "https://data.120ask.com/yisheng/list_j520p9.html",
        "https://data.120ask.com/yisheng/list_j520p10.html",
        "https://data.120ask.com/yisheng/list_j520p11.html",
        "https://data.120ask.com/yisheng/list_j520p12.html",
    ]


def test_build_next_disease_list_page_url_from_first_page() -> None:
    assert (
        build_next_disease_list_page_url("https://data.120ask.com/yisheng/list_j520.html")
        == "https://data.120ask.com/yisheng/list_j520p2.html"
    )


def test_build_next_disease_list_page_url_from_page_200() -> None:
    assert (
        build_next_disease_list_page_url("https://data.120ask.com/yisheng/list_j520p200.html")
        == "https://data.120ask.com/yisheng/list_j520p201.html"
    )


def test_is_first_disease_index_page_only_match_entry_page() -> None:
    assert is_first_disease_index_page("https://data.120ask.com/yisheng/jibing.html") is True
    assert is_first_disease_index_page("https://data.120ask.com/yisheng/jibing_p2.html") is False


def test_is_first_list_page_only_match_non_paginated_root_page() -> None:
    assert is_first_list_page("disease", "https://data.120ask.com/yisheng/list_j520.html") is True
    assert is_first_list_page("disease", "https://data.120ask.com/yisheng/list_j520p2.html") is False
    assert is_first_list_page("department", "https://data.120ask.com/yisheng/list_d19.html") is True
    assert is_first_list_page("department", "https://data.120ask.com/yisheng/list_d19p2.html") is False
    assert is_first_list_page("area", "https://data.120ask.com/yisheng/list_a110105.html") is True
    assert is_first_list_page("area", "https://data.120ask.com/yisheng/list_a110105p2.html") is False
    assert is_first_list_page("hospital", "https://data.120ask.com/yiyuan/list_a110105.html") is True
    assert is_first_list_page("hospital", "https://data.120ask.com/yiyuan/list_a110105p2.html") is False


def test_extract_hospital_expert_ajax_context_from_real_script_shape() -> None:
    html = """
    <div id="depart_list">
      <a class="on" href="javascript:;" depart-id="0">全部</a>
    </div>
    <div id="doctor_title">
      <a class="on" href="javascript:;" doctor-title="0">全部</a>
    </div>
    <div id="chuzheng_time">
      <a class="on" href="javascript:;" apm-id="0" week-id="0">全部</a>
    </div>
    <div id="chuzheng_type">
      <a class="on" href="javascript:;" chuzheng-type="0">全部</a>
    </div>
    <script>
    function getList(pid, did = 0, zid = 0, sid = 0, wid = 0, tid = 0){
        var hid = 125;
        var kid = 0;
        var limit = 8;
        $.getJSON('/public/ajaxyisheng',{'hid':hid,'pid':pid,'did':did,'zid':zid,'sid':sid,'wid':wid,'tid':tid,'kid':kid,'limit':limit},function(obj){});
    }
    </script>
    <div class="page">
      <a onclick='getList("2")' href='javascript:;'>2</a>
      <a onclick='getList("68")' href='javascript:;'>最后一页</a>
      <span>共68页</span>
    </div>
    """
    assert extract_hospital_expert_ajax_context(
        "https://data.120ask.com/yiyuan/yisheng/0387pltyawkim7pa.html",
        html,
    ) == {
        "ajax_url": "https://data.120ask.com/public/ajaxyisheng",
        "hid": "125",
        "kid": "0",
        "limit": "8",
        "did": "0",
        "zid": "0",
        "sid": "0",
        "wid": "0",
        "tid": "0",
        "page_count": 68,
    }


def test_extract_hospital_expert_doctor_urls_from_ajax_payload() -> None:
    payload = """
    {"rsList":[{"url":"\\/yisheng\\/lcof5wxc47ivbonf.html"},{"url":"\\/yisheng\\/lcofvpb62vc9f5af.html"}],"pageCount":68}
    """
    assert extract_hospital_expert_doctor_urls(payload) == [
        "https://data.120ask.com/yisheng/lcof5wxc47ivbonf.html",
        "https://data.120ask.com/yisheng/lcofvpb62vc9f5af.html",
    ]


def test_extract_hospital_expert_doctor_urls_returns_empty_on_non_json_payload() -> None:
    payload = "<html><title>403</title></html>"
    assert extract_hospital_expert_doctor_urls(payload) == []


def test_build_hospital_expert_ajax_request_specs_fix_cookiejar_and_headers() -> None:
    context = {
        "ajax_url": "https://data.120ask.com/public/ajaxyisheng",
        "hid": "125",
        "kid": "0",
        "limit": "8",
        "did": "0",
        "zid": "0",
        "sid": "0",
        "wid": "0",
        "tid": "0",
        "page_count": 3,
    }
    assert build_hospital_expert_ajax_request_specs(
        source_url="https://data.120ask.com/yiyuan/yisheng/0387pltyawkim7pa.html",
        ajax_context=context,
        cookiejar_id="hospital-expert-1",
    ) == [
        {
            "url": "https://data.120ask.com/public/ajaxyisheng?hid=125&pid=2&did=0&zid=0&sid=0&wid=0&tid=0&kid=0&limit=8",
            "page_number": 2,
            "headers": {
                "Referer": "https://data.120ask.com/yiyuan/yisheng/0387pltyawkim7pa.html",
                "X-Requested-With": "XMLHttpRequest",
            },
            "meta": {
                "cookiejar": "hospital-expert-1",
            },
        },
        {
            "url": "https://data.120ask.com/public/ajaxyisheng?hid=125&pid=3&did=0&zid=0&sid=0&wid=0&tid=0&kid=0&limit=8",
            "page_number": 3,
            "headers": {
                "Referer": "https://data.120ask.com/yiyuan/yisheng/0387pltyawkim7pa.html",
                "X-Requested-With": "XMLHttpRequest",
            },
            "meta": {
                "cookiejar": "hospital-expert-1",
            },
        },
    ]
