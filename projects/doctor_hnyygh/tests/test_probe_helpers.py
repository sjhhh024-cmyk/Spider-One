from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_hnyygh.probe_helpers import (  # noqa: E402
    build_department_request_record,
    build_doctor_detail_task,
    build_doctor_info_api_url,
    build_doctor_home_url,
    build_hospital_home_url,
    build_hospital_record,
    extract_api_doctor_detail_fields,
    extract_api_hospital_detail_fields,
    extract_rendered_doctor_detail_fields,
    extract_rendered_hospital_detail_fields,
    parse_area_items,
    parse_department_items,
    parse_doctor_items,
    parse_hospital_items,
)


def test_parse_area_items_from_fastgh_level_one_response() -> None:
    payload = {
        "code": 4000,
        "data": [
            {"id": "410100", "name": "郑州市"},
            {"id": "410200", "name": "开封市"},
        ],
    }
    assert parse_area_items(payload) == [
        {"city_id": "410100", "city_name": "郑州市"},
        {"city_id": "410200", "city_name": "开封市"},
    ]


def test_parse_hospital_items_from_fastgh_level_two_response() -> None:
    payload = {
        "code": 4000,
        "data": [
            {"id": "1597528443577438208", "name": "河南省人民医院"},
            {"id": "1597528472392306688", "name": "郑州大学第一附属医院河医院区"},
        ],
    }
    assert parse_hospital_items(payload) == [
        {"hospital_id": "1597528443577438208", "hospital_name": "河南省人民医院"},
        {"hospital_id": "1597528472392306688", "hospital_name": "郑州大学第一附属医院河医院区"},
    ]


def test_parse_department_items_from_fastgh_level_three_response() -> None:
    payload = {
        "code": 4000,
        "data": [
            {"id": "1773286494975561728", "name": "妇科"},
            {"id": "1773286494765846528", "name": "心血管内科"},
        ],
    }
    assert parse_department_items(payload) == [
        {"department_id": "1773286494975561728", "department_name": "妇科"},
        {"department_id": "1773286494765846528", "department_name": "心血管内科"},
    ]


def test_parse_doctor_items_from_fastgh_level_four_response() -> None:
    payload = {
        "code": 4000,
        "data": [
            {"id": "1763127300037283840", "name": "张冬雅"},
            {"id": "1763127300494462976", "name": "冯巍"},
        ],
    }
    assert parse_doctor_items(payload) == [
        {"doctor_id": "1763127300037283840", "doctor_name": "张冬雅"},
        {"doctor_id": "1763127300494462976", "doctor_name": "冯巍"},
    ]


def test_build_hospital_request_record_keeps_city_context() -> None:
    assert build_department_request_record(
        hospital_id="1597528472392306688",
        hospital_name="郑州大学第一附属医院河医院区",
        city_id="410100",
        city_name="郑州市",
    ) == {
        "url": "https://www.169000.net/fastGh/3-1597528472392306688",
        "meta": {
            "hospital_id": "1597528472392306688",
            "hospital_name": "郑州大学第一附属医院河医院区",
            "city_id": "410100",
            "city_name": "郑州市",
        },
    }


def test_build_doctor_detail_task_merges_all_upstream_context() -> None:
    assert build_doctor_detail_task(
        doctor_id="1763127300037283840",
        doctor_name="张冬雅",
        hospital_id="1597528472392306688",
        hospital_name="郑州大学第一附属医院河医院区",
        department_id="1773286494975561728",
        department_name="妇科",
        city_id="410100",
        city_name="郑州市",
    ) == {
        "url": "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1763127300037283840",
        "meta": {
            "doctor_id": "1763127300037283840",
            "doctor_name": "张冬雅",
            "hospital_id": "1597528472392306688",
            "hospital_name": "郑州大学第一附属医院河医院区",
            "department_id": "1773286494975561728",
            "department_name": "妇科",
            "city_id": "410100",
            "city_name": "郑州市",
        },
    }


def test_build_doctor_info_api_url_from_doctor_id() -> None:
    assert build_doctor_info_api_url("1674329307792805888") == (
        "https://www.169000.net/api/doctor/getDoctorInfo?doctorId=1674329307792805888"
    )


def test_extract_api_doctor_detail_fields_from_new_site_payload() -> None:
    payload = {
        "code": 4000,
        "data": {
            "doctor_name": "金学民",
            "doctor_title": "主任医师",
            "avatar": "https://ossapi.169000.net/doctorimg/1763850958628196352.jpg",
            "good_at": "主攻眼底病。",
            "detail": "金学民，医学博士、教授。",
            "xueli": "其他",
            "office_location_hospital": "郑州大学第一附属医院",
            "hospitalId": "1597528443577438208",
        },
    }
    assert extract_api_doctor_detail_fields(
        payload,
        doctor_id="1674329307792805888",
        fallback_doctor_name="金学民",
        fallback_hospital_name="河南省人民医院",
        fallback_department_name="眼科",
    ) == {
        "doctor_name": "金学民",
        "doctor_hospital": "河南省人民医院",
        "doctor_department": "眼科",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://ossapi.169000.net/doctorimg/1763850958628196352.jpg",
        "doctor_education": "其他",
        "doctor_specialties": "主攻眼底病。",
        "intro": "金学民，医学博士、教授。",
        "hospital_id": "1597528443577438208",
        "source_site": "河南省预约挂号服务平台",
        "source_url": build_doctor_home_url("1674329307792805888"),
    }


def test_extract_api_hospital_detail_fields_from_new_site_payloads() -> None:
    hospital_info_payload = {
        "code": 4000,
        "data": {
            "plat_hospital_name": "河南省人民医院",
            "hospital_name": "河南省人民医院",
            "hospital_level": "三甲",
            "address": "郑州市纬五路7号",
            "hospital_code": "41010501A1000005",
            "area": "金水区",
            "hospital_logo": "https://ossapi.169000.net/hospitalimg/logo.png",
            "detail": "&nbsp;&nbsp;医院介绍A",
            "url": "http://www.hnsrmyy.net",
            "hospital_type": "综合医院",
            "geo": "113.693823,34.772189",
            "consult_phone": "0371-65580070",
        },
    }
    hospital_overview_payload = {
        "code": 4000,
        "data": {
            "detail": "&nbsp;&nbsp;医院介绍B",
            "deptCount": "552",
            "doctorCount": "3452",
        },
    }
    assert extract_api_hospital_detail_fields(
        hospital_info_payload,
        hospital_overview_payload,
        hospital_id="1597528443577438208",
        fallback_hospital_name="河南省人民医院",
        fallback_city_name="郑州市",
    ) == {
        "hospital_name": "河南省人民医院",
        "hospital_address": "郑州市纬五路7号",
        "hospital_phone": "0371-65580070",
        "hospital_intro": "医院介绍B",
        "hospital_website": "http://www.hnsrmyy.net",
        "hospital_level": "三甲",
        "hospital_type": "综合医院",
        "hospital_logo": "https://ossapi.169000.net/hospitalimg/logo.png",
        "hospital_code": "41010501A1000005",
        "hospital_area": "金水区",
        "hospital_geo": "113.693823,34.772189",
        "hospital_dept_count": "552",
        "hospital_doctor_count": "3452",
        "source_site": "河南省预约挂号服务平台",
        "source_url": build_hospital_home_url("1597528443577438208"),
    }


def test_build_hospital_record_outputs_minimum_subchain_fields() -> None:
    assert build_hospital_record(
        hospital_id="1597528472392306688",
        hospital_name="郑州大学第一附属医院河医院区",
        city_id="410100",
        city_name="郑州市",
        source_url="https://www.169000.net/fastGh/2-410100",
        crawl_time="2026-05-15",
    ) == {
        "_id": "1597528472392306688",
        "hospital_id": "1597528472392306688",
        "hospital_name": "郑州大学第一附属医院河医院区",
        "hospital_city_id": "410100",
        "hospital_city_name": "郑州市",
        "source_site": "河南省预约挂号服务平台",
        "source_url": "https://www.169000.net/fastGh/2-410100",
        "crawl_time": "2026-05-15",
    }


def test_extract_rendered_doctor_detail_fields_from_new_site_html() -> None:
    html = """
    <div class="hoslogo hot-type-2">
      <img src="https://ossapi.169000.net/doctorimg/1763850958628196352.jpg" alt="">
    </div>
    <div class="hosinfortoponel">
      金学民
      <span>主任医师</span>
    </div>
    <div class="hosinfortopthree">
      <div class="hosinfortopthreel">擅长：顶部擅长兜底</div>
    </div>
    <div class="hosinfortopthree">
      <div class="hosinfortopthreel">
        执业地点：
        <span class="zhiname" title="郑州大学第一附属医院河医院区">郑州大学第一附属医院河医院区</span>
        <span class="zhiname" title="河南省人民医院">河南省人民医院</span>
      </div>
    </div>
    <div class="jiuxuzhi">
      <div class="hosindextit"><div class="hosindextitltit">医生公告</div></div>
      <div class="xuzhinei">暂无医生公告</div>
    </div>
    <div class="jiuxuzhi">
      <div class="hosindextit"><div class="hosindextitltit">擅长</div></div>
      <div class="xuzhinei">原河南医学院本科、硕士毕业，主攻眼底病。</div>
      <div class="hosindextit"><div class="hosindextitltit">简介</div></div>
      <div class="xuzhinei">金学民，医学博士、教授、主任医师。</div>
      <div class="hosindextit"><div class="hosindextitltit">学历</div></div>
      <div class="xuzhinei">其他</div>
    </div>
    """
    assert extract_rendered_doctor_detail_fields(
        html,
        doctor_id="1674329307792805888",
        fallback_doctor_name="金学民",
        fallback_hospital_name="郑州大学第一附属医院河医院区",
        fallback_department_name="眼科",
    ) == {
        "doctor_name": "金学民",
        "doctor_hospital": "郑州大学第一附属医院河医院区 丨 河南省人民医院",
        "doctor_department": "眼科",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://ossapi.169000.net/doctorimg/1763850958628196352.jpg",
        "doctor_education": "其他",
        "doctor_specialties": "原河南医学院本科、硕士毕业，主攻眼底病。",
        "intro": "金学民，医学博士、教授、主任医师。",
        "source_site": "河南省预约挂号服务平台",
        "source_url": build_doctor_home_url("1674329307792805888"),
    }


def test_extract_rendered_hospital_detail_fields_from_new_site_html() -> None:
    list_html = """
    <meta
      name="description"
      content="http://www.zcxrmyy.cn/河南省预约挂号服务平台为您提供柘城县人民医院网上预约挂号相关服务。医院地址:柘城县汇泉大街93号医院电话：0370-1234567"
    >
    <div class="hoslogo">
      <img src="https://ossapi.169000.net/hospital/1597529059284488192.png" alt="">
    </div>
    <div class="hosinfortoponel">柘城县人民医院</div>
    <div class="hosinfortopthree">官网：<span>http://www.zcxrmyy.cn/</span></div>
    <div class="hosinfortopfour">
      <div class="hosinfortopfouritem">三级</div>
      <div class="hosinfortopfouritemm">综合医院</div>
    </div>
    <div class="hosdeplist">
      <div class="hosdeplistitem">
        <div class="deplistdata">
          <div class="deplistdataitem" title="心血管内科一病区"></div>
          <div class="deplistdataitem" title="神经内科二病区"></div>
        </div>
      </div>
      <div class="hosdeplistitem">
        <div class="deplistdata">
          <div class="deplistdataitem" title="消化内科"></div>
        </div>
      </div>
    </div>
    <img src="https://www.169000.net/api/hospAffiliate/getMyQrddByHospital?hospitalCode=41142412A1000002" alt="">
    """
    intro_html = """
    <div class="jiuxuzhi">
      <div class="hosindextit"><div class="hosindextitltit">医院介绍</div></div>
      <div class="xuzhinei">柘城县人民医院位于县城南关汇泉路93号，是综合医院。</div>
    </div>
    <div class="jiuxuzhi">
      <div class="hosindextit"><div class="hosindextitltit">医院地址</div></div>
      <div class="xuzhinei"><p>地址：柘城县汇泉大街93号</p></div>
    </div>
    <img src="https://www.169000.net/api/hospAffiliate/getMyQrddByHospital?hospitalCode=41142412A1000002" alt="">
    """
    assert extract_rendered_hospital_detail_fields(
        list_html,
        intro_html,
        hospital_id="1597529059284488192",
        fallback_hospital_name="柘城县人民医院",
        fallback_city_name="商丘市",
    ) == {
        "hospital_name": "柘城县人民医院",
        "hospital_address": "柘城县汇泉大街93号",
        "hospital_phone": "0370-1234567",
        "hospital_intro": "柘城县人民医院位于县城南关汇泉路93号，是综合医院。",
        "hospital_website": "http://www.zcxrmyy.cn/",
        "hospital_level": "三级",
        "hospital_type": "综合医院",
        "hospital_logo": "https://ossapi.169000.net/hospital/1597529059284488192.png",
        "hospital_code": "41142412A1000002",
        "hospital_area": "柘城县",
        "hospital_geo": "",
        "hospital_dept_count": "3",
        "hospital_doctor_count": "",
        "source_site": "河南省预约挂号服务平台",
        "source_url": build_hospital_home_url("1597529059284488192"),
    }
