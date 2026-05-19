from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_DIR / "samples"
DOC_TEMPLATE_PATH = PROJECT_DIR.parents[1] / "docs" / "doctor_common_template.md"


def load_module(module_name: str, filename: str):
    module_path = PROJECT_DIR / filename
    assert module_path.exists(), f"缺少实现文件: {module_path}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doctor_common_template_mentions_trimmed_hospital_fields() -> None:
    text = DOC_TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "doctor_research_direction" in text
    assert "doctor_person_honor" in text
    assert "hospital_property" in text
    assert '"doctor_job_title"' not in text
    assert '"doctor_hospital_full_name"' not in text
    assert '"doctor_work_time"' not in text
    assert '"doctor_page_path"' not in text
    assert '"doctor_source_doctor_id"' not in text
    assert '"doctor_hospital_id"' not in text
    assert '"hospital_full_name"' not in text
    assert '"hospital_url"' not in text
    assert '"hospital_logo"' not in text
    assert '"hospital_level_text"' not in text
    assert "hospital_mobile_website" not in text
    assert "hospital_found_date" not in text
    assert "hospital_manage_department" not in text
    assert "hospital_dean" not in text
    assert "expert_team" not in text


def test_build_doctor_list_page_url_uses_nested_route_style() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")

    assert (
        module.build_doctor_list_page_url("https://www.dayi.org.cn", 1)
        == "https://www.dayi.org.cn/list/3"
    )
    assert (
        module.build_doctor_list_page_url("https://www.dayi.org.cn", 2)
        == "https://www.dayi.org.cn/list/3/2"
    )


def test_build_hospital_list_page_url_uses_nested_route_style() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")

    assert (
        module.build_hospital_list_page_url("https://www.dayi.org.cn", 1)
        == "https://www.dayi.org.cn/list/2"
    )
    assert (
        module.build_hospital_list_page_url("https://www.dayi.org.cn", 2)
        == "https://www.dayi.org.cn/list/2/2"
    )


def test_parse_doctor_list_page_extracts_page_and_records() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "doctor_zgyyxx_doctorList.html").read_text(encoding="utf-8")

    result = module.parse_doctor_list_page("https://www.dayi.org.cn/list/3", html)

    assert result["total"] == 1000
    assert result["page_size"] == 10
    assert result["page_num"] == 1
    assert result["total_pages"] == 100
    assert result["doctors"][0] == {
        "_id": "1120165",
        "doctor_id": "1120165",
        "doctor_name": "王友彬",
        "doctor_hospital": "北京协和医院",
        "doctor_department": "整形美容外科",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://image.dayi.org.cn/public/uploads/20180505/0ab591db5bc597a04d7e6060724bad04.png?x-oss-process=image/resize,w_150",
        "doctor_specialties": "",
        "intro": "王友彬，男，主任医师，教授，博士生导师，现就职于北京协和医院整形美容外科。兼任国家中医药管理局名词术语成果转化与规范推广项目评审专家、中华医学会整形外科分会瘢痕学组副组长。",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/doctor/1120165.html",
        "crawl_time": "",
    }


def test_parse_doctor_list_page_page2_uses_current_url_page_num() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "doctor_zgyyxx_doctorList_page2.html").read_text(encoding="utf-8")

    result = module.parse_doctor_list_page("https://www.dayi.org.cn/list/3/2", html)

    assert result["page_num"] == 2
    assert result["page_size"] == 10
    assert result["doctors"][0]["doctor_name"] == "樊朝美"


def test_parse_doctor_list_page_supports_alias_department_name() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "debug_doctor_list_page3_runtime.html").read_text(encoding="utf-8")

    result = module.parse_doctor_list_page("https://www.dayi.org.cn/list/3/3", html)

    assert result["page_num"] == 3
    assert result["page_size"] == 10
    assert len(result["doctors"]) == 10
    liu_wali = next(item for item in result["doctors"] if item["doctor_id"] == "1156356")
    assert liu_wali["doctor_name"] == "刘瓦利"
    assert liu_wali["doctor_department"] == "皮肤科"
    assert liu_wali["doctor_hospital"] == "中国中医科学院广安门医院"


def test_parse_doctor_list_page_prefers_total_count_when_visible_page_links_are_short() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = """
    <html><body>
    <a href="/list/3/1">1</a><a href="/list/3/2">2</a><a href="/list/3/3">3</a><a href="/list/3/4">4</a>
    <a href="/list/3/5">5</a><a href="/list/3/6">6</a><a href="/list/3/7">7</a><a href="/list/3/8">8</a>
    <a href="/list/3/9">9</a><a href="/list/3/10">10</a>
    <script>
    window.__NUXT__=(function(a,b,c,d,e){return {fetch:{"data-v-526967ff:0":{
    pageNo:10,pageSize:10,list:[{id:1,title:"测试医生",thumbnail:"https:\\u002F\\u002Fexample.com\\u002Fa.jpg",introduction:"\\u003Cp\\u003E简介\\u003C\\u002Fp\\u003E",clinicProfessional:b,departmentName:c,institutionName:d,classType:e}],
    efficientQaConfigCount:0,baikeEnd:false,totalCount:1000,detailRouteName:"doctorDetail",detailPath:"\\u002Fdoctor"}}}})(true,"主任医师","测试科室","测试医院","baike");
    </script></body></html>
    """

    result = module.parse_doctor_list_page("https://www.dayi.org.cn/list/3/10", html)

    assert result["page_num"] == 10
    assert result["page_size"] == 10
    assert result["total_pages"] == 100


def test_parse_doctor_list_page_supports_alias_page_meta_on_runtime_page10() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "debug_doctor_list_page10_runtime.html").read_text(encoding="utf-8")

    result = module.parse_doctor_list_page("https://www.dayi.org.cn/list/3/10", html)

    assert result["page_num"] == 10
    assert result["page_size"] == 10
    assert result["total_pages"] == 100
    assert len(result["doctors"]) == 10


def test_parse_doctor_list_page_tolerates_missing_department_or_hospital_fields_on_page20() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "debug_doctor_list_page20_runtime.html").read_text(encoding="utf-8")

    result = module.parse_doctor_list_page("https://www.dayi.org.cn/list/3/20", html)

    assert result["page_num"] == 20
    assert result["page_size"] == 10
    assert result["total_pages"] == 100
    assert len(result["doctors"]) == 10

    wu_yubin = next(item for item in result["doctors"] if item["doctor_id"] == "1132932")
    assert wu_yubin["doctor_name"] == "吴玉彬"
    assert wu_yubin["doctor_hospital"] == ""
    assert wu_yubin["doctor_department"] == ""
    assert "河南省职工医院副院长" in wu_yubin["intro"]

    lv_zhiping = next(item for item in result["doctors"] if item["doctor_id"] == "1126286")
    assert lv_zhiping["doctor_name"] == "吕志平"
    assert lv_zhiping["doctor_hospital"] == "南方医科大学南方医院"
    assert lv_zhiping["doctor_department"] == ""


def test_parse_doctor_detail_page_extracts_core_and_optional_fields() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "doctor_zgyyxx_doctorDetail_1120165.html").read_text(encoding="utf-8")

    result = module.parse_doctor_detail_page(
        "https://www.dayi.org.cn/doctor/1120165.html",
        html,
    )

    assert result["_id"] == "1120165"
    assert result["doctor_id"] == "1120165"
    assert result["doctor_name"] == "王友彬"
    assert result["doctor_hospital"] == "中国医学科学院北京协和医院"
    assert result["doctor_department"] == "整形美容外科"
    assert result["doctor_title"] == "主任医师"
    assert result["doctor_avatar_url"].startswith("https://image.dayi.org.cn/")
    assert result["doctor_specialties"] == "瘢痕和创面修复，面部年轻化，鼻部整形美容，唇裂及继发畸形修复。"
    assert result["doctor_prof_title"] == "教授、博士生导师"
    assert result["doctor_graduated"] == "北京协和医学院"
    assert result["doctor_edu_process"].startswith("1987年9月-1992年7月")
    assert result["doctor_work_process"].startswith("1992年9月-1997年7月")
    assert result["doctor_summary"] == "瘢痕和创面修复，面部年轻化，鼻部整形美容，唇裂及继发畸形修复。"
    assert result["doctor_social_job"] == "中华医学会整形外科分会瘢痕学组副组长"
    assert result["doctor_research_direction"] == "瘢痕和创面修复机制，面部皮肤衰老和防治。"
    assert result["doctor_published_works"] == "《牵手美容》\n\n《整形美容随笔》\n\n《整形美容札记》"
    assert "医疗成果三等奖" in result["doctor_achievements"]
    assert "doctor_job_title" not in result
    assert "doctor_work_time" not in result
    assert "doctor_hospital_id" not in result
    assert "doctor_hospital_full_name" not in result
    assert "doctor_page_path" not in result
    assert "doctor_source_doctor_id" not in result


def test_parse_doctor_detail_page_supports_dynamic_nuxt_object_name() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "tmp_1118653.html").read_text(encoding="utf-8")

    result = module.parse_doctor_detail_page(
        "https://www.dayi.org.cn/doctor/1118653.html",
        html,
    )

    assert result["_id"] == "1118653"
    assert result["doctor_id"] == "1118653"
    assert result["doctor_name"] == "杨爱明"
    assert result["doctor_hospital"] == "中国医学科学院北京协和医院"
    assert result["doctor_department"] == "消化内科"
    assert result["doctor_title"] == "主任医师"
    assert result["doctor_prof_title"] == "教授、博士生导师"
    assert result["doctor_summary"] == "食管胃底静脉曲张、胃早期癌、胆石症、胰腺癌、慢性胰腺炎、胆管癌、ERCP、超声内镜、内镜下微创治疗。"
    assert "国家中医药管理局名词术语成果转化与规范推广项目评审专家" not in result["doctor_social_job"]
    assert "doctor_hospital_id" not in result
    assert "doctor_page_path" not in result
    assert "doctor_source_doctor_id" not in result


def test_parse_doctor_detail_page_tolerates_raw_control_characters_in_long_text_fields() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "debug_doctor_1123728_runtime.html").read_text(encoding="utf-8")

    result = module.parse_doctor_detail_page(
        "https://www.dayi.org.cn/doctor/1123728.html",
        html,
    )

    assert result["_id"] == "1123728"
    assert result["doctor_id"] == "1123728"
    assert result["doctor_name"] == "李学松"
    assert result["doctor_hospital"] == "北京大学第一医院"
    assert result["doctor_department"] == "泌尿外科"
    assert result["doctor_title"] == "主任医师"
    assert result["doctor_prof_title"] == "教授、博士生导师"
    assert result["doctor_graduated"] == "北京医科大学"
    assert result["doctor_work_process"].startswith("2004年9月-2009年8月")
    assert "郭应禄泌尿外科青年医师奖" in result["doctor_person_honor"]
    assert "Aging (Albany NY)." not in result.get("doctor_social_job", "")


def test_parse_doctor_detail_page_only_keeps_optional_fields_when_present() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")

    html = """
    <html><body><script>
    window.__NUXT__=(function(){var l={};l.id=1;l.mapping=[{institutionId:2,institutionName:"测试医院",departmentName:"测试科室"}];
    l.name="测试医生";l.thumbnail="https://example.com/a.png";l.clinicProfessional="主任医师";
    l.mapHospital="测试医院";l.mapDepartment="测试科室";return {layout:"default"}})();
    </script></body></html>
    """

    result = module.parse_doctor_detail_page("https://www.dayi.org.cn/doctor/1.html", html)

    assert result["doctor_name"] == "测试医生"
    assert result["doctor_hospital"] == "测试医院"
    assert result["doctor_department"] == "测试科室"
    assert result["doctor_title"] == "主任医师"
    assert "doctor_job_title" not in result
    assert "doctor_prof_title" not in result
    assert "doctor_graduated" not in result
    assert "doctor_edu_process" not in result
    assert "doctor_work_process" not in result
    assert "doctor_research_direction" not in result


def test_parse_hospital_list_page_extracts_page_and_records() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "doctor_zgyyxx_hospitalList.html").read_text(encoding="utf-8")

    result = module.parse_hospital_list_page("https://www.dayi.org.cn/list/2", html)

    assert result["total"] == 1000
    assert result["page_size"] == 10
    assert result["page_num"] == 1
    assert result["total_pages"] == 100
    assert result["hospitals"][0] == {
        "_id": "1125632",
        "hospital_id": "1125632",
        "hospital_name": "中国人民解放军总医院",
        "hospital_intro": "中国人民解放军总医院（301医院）位于北京市海淀区复兴路28号，始建于1953年，是一所集医疗、保健、教学、科研于一体的综合性医院，是北京市医保和新农合定点医院，是解放军医学院，是全军重症监护示范基地和中华护理学会的培训基地，先后荣获国际模范爱婴医院、全国百佳医院、全国百姓放心医院、全国百姓放心示范医院、全军为部队服务先进医院、全国卫生系统文化建设创新奖、医院改革创新奖等荣誉称号。",
        "hospital_level": "",
        "hospital_nature": "",
        "hospital_type": "",
        "hospital_property": "",
        "hospital_website": "",
        "hospital_insurance": "",
        "hospital_offices": "",
        "hospital_special": "",
        "hospital_advantage": "",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/hospital/1125632.html",
        "crawl_time": "",
    }


def test_parse_hospital_detail_page_extracts_hospital_fields() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "doctor_zgyyxx_hospitalDetail_1125632.html").read_text(encoding="utf-8")

    result = module.parse_hospital_detail_page(
        "https://www.dayi.org.cn/hospital/1125632.html",
        html,
    )

    assert result["hospital_id"] == "1125632"
    assert result["_id"] == "1125632"
    assert result["hospital_name"] == "中国人民解放军总医院"
    assert result["hospital_address"] == "北京市复兴路28号"
    assert result["hospital_phone"] == "010-68182255"
    assert result["hospital_level"] == "三甲"
    assert result["hospital_nature"] == "非营利性"
    assert result["hospital_type"] == "综合医院"
    assert result["hospital_website"] == "http://www.301hospital.com.cn/"
    assert result["hospital_insurance"] == "是"
    assert result["hospital_offices"].startswith("医院设有神经内科")
    assert result["hospital_special"].startswith("一、国家临床重点专科")
    assert result["hospital_advantage"].startswith("一、优势病种")
    assert result["source_site"] == "中国医药信息查询平台"
    assert result["source_url"] == "https://www.dayi.org.cn/hospital/1125632.html"


def test_parse_hospital_expert_doctors_extracts_doctor_records() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "doctor_zgyyxx_hospitalDetail_1125632.html").read_text(encoding="utf-8")

    result = module.parse_hospital_expert_doctors(
        "https://www.dayi.org.cn/hospital/1125632.html",
        html,
    )

    assert result
    first = result[0]
    assert first["doctor_id"] == "hospital_1125632_于生元"
    assert first["doctor_name"] == "于生元"
    assert first["doctor_hospital"] == "中国人民解放军总医院"
    assert first["doctor_title"] == "主任医师"
    assert first["doctor_summary"].startswith("各种神经系统疾病")
    assert "doctor_job_title" not in first
    assert "doctor_hospital_id" not in first
    assert "doctor_hospital_full_name" not in first


def test_parse_hospital_expert_doctors_supports_alias_name_value() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    html = (SAMPLES_DIR / "debug_hospital_1016_runtime.html").read_text(encoding="utf-8")

    result = module.parse_hospital_expert_doctors(
        "https://www.dayi.org.cn/hospital/1016.html",
        html,
    )

    assert result
    first = result[0]
    assert first["doctor_name"] == "高象民"
    assert first["doctor_hospital"] == "义县人民医院"
    assert first["doctor_title"] == "副主任医师"
    assert first["doctor_summary"] == "各种消化疾病的内镜下诊断治疗。"


def test_in_memory_redis_task_roundtrip_and_empty_means_done() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    redis_client = module.InMemoryRedisClient()

    task = {"url": "https://www.dayi.org.cn/list/3", "page_no": 1}
    task_key = "doctor_zgyyxx:doctor_list_task"

    assert module.push_task(redis_client, task_key, task) == 1
    assert module.push_task(redis_client, task_key, task) == 0

    loaded = module.pop_tasks(redis_client, task_key)
    assert loaded == [(module.dump_task(task), task)]
    assert redis_client.scard(task_key) == 1

    module.remove_task(redis_client, task_key, module.dump_task(task))
    assert redis_client.scard(task_key) == 0
    assert module.pop_tasks(redis_client, task_key) == []


def test_hospital_detail_queue_is_independent_from_doctor_line() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    redis_client = module.InMemoryRedisClient()

    doctor_task = {"url": "https://www.dayi.org.cn/doctor/1120165.html", "doctor_id": "1120165"}
    hospital_task = {"url": "https://www.dayi.org.cn/hospital/1125632.html", "hospital_id": "1125632"}

    module.push_task(redis_client, "doctor_zgyyxx:doctor_detail_task", doctor_task)
    module.push_task(redis_client, "doctor_zgyyxx:hospital_detail_task", hospital_task)

    doctor_tasks = module.pop_tasks(redis_client, "doctor_zgyyxx:doctor_detail_task")
    hospital_tasks = module.pop_tasks(redis_client, "doctor_zgyyxx:hospital_detail_task")

    assert doctor_tasks == [(module.dump_task(doctor_task), doctor_task)]
    assert hospital_tasks == [(module.dump_task(hospital_task), hospital_task)]


def test_hospital_record_from_list_is_overridden_by_detail_fields() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")

    list_record = {
        "_id": "1125632",
        "hospital_id": "1125632",
        "hospital_name": "中国人民解放军总医院",
        "hospital_intro": "列表简介",
        "hospital_level": "",
        "hospital_nature": "",
        "hospital_type": "",
        "hospital_property": "",
        "hospital_website": "",
        "hospital_insurance": "",
        "hospital_offices": "",
        "hospital_special": "",
        "hospital_advantage": "",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/hospital/1125632.html",
        "crawl_time": "",
    }
    detail_record = {
        "_id": "1125632",
        "hospital_id": "1125632",
        "hospital_name": "中国人民解放军总医院",
        "hospital_address": "北京市复兴路28号",
        "hospital_phone": "010-68182255",
        "hospital_intro": "详情简介",
        "hospital_level": "三甲",
        "hospital_nature": "非营利性",
        "hospital_type": "综合医院",
        "hospital_property": "",
        "hospital_website": "http://www.301hospital.com.cn/",
        "hospital_insurance": "是",
        "hospital_offices": "神经内科",
        "hospital_special": "国家临床重点专科",
        "hospital_advantage": "优势病种",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/hospital/1125632.html",
        "crawl_time": "",
    }

    merged = module.merge_hospital_data(list_record, detail_record)

    assert merged["hospital_intro"] == "详情简介"
    assert merged["hospital_level"] == "三甲"
    assert merged["hospital_offices"] == "神经内科"


def test_run_doctor_line_and_hospital_line_write_to_different_collections() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    saved_doctors: list[dict[str, str]] = []
    saved_hospitals: list[dict[str, str]] = []

    class FakeCollection:
        def __init__(self, bucket: list[dict[str, str]]) -> None:
            self.bucket = bucket

        def replace_one(self, _filter, data, upsert=False):  # noqa: ANN001, FBT002
            self.bucket.append(data)

    class FakeDatabase:
        def __getitem__(self, name: str):
            if name == "doctor_zgyyxx":
                return FakeCollection(saved_doctors)
            if name == "hospital_zgyyxx":
                return FakeCollection(saved_hospitals)
            raise KeyError(name)

    class FakeClient:
        def __getitem__(self, _name: str):
            return FakeDatabase()

    module.build_mongo_client = lambda _config: FakeClient()
    module.build_redis_client = lambda _config: module.InMemoryRedisClient()

    doctor_html = "<html></html>"
    hospital_html = "<html></html>"
    doctor_list_html = "<html></html>"
    hospital_list_html = "<html></html>"

    module.parse_doctor_list_page = lambda _url, _html: {
        "total": 1000,
        "page_size": 1,
        "page_num": 1,
        "total_pages": 1,
        "doctors": [
            module.build_doctor_record(
                doctor_id="1120165",
                doctor_name="王友彬",
                doctor_hospital="北京协和医院",
                doctor_department="整形美容外科",
                doctor_title="主任医师",
                doctor_avatar_url="https://example.com/doctor.jpg",
                doctor_specialties="",
                intro="列表简介",
                source_url="https://www.dayi.org.cn/doctor/1120165.html",
                crawl_time="",
            )
        ],
    }
    module.parse_doctor_detail_page = lambda _url, _html: {
        "_id": "1120165",
        "doctor_id": "1120165",
        "doctor_name": "王友彬",
        "doctor_hospital": "北京协和医院",
        "doctor_department": "整形美容外科",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://example.com/doctor.jpg",
        "doctor_specialties": "瘢痕和创面修复",
        "intro": "详情简介",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/doctor/1120165.html",
        "crawl_time": "",
    }
    module.parse_hospital_list_page = lambda _url, _html: {
        "total": 1000,
        "page_size": 1,
        "page_num": 1,
        "total_pages": 1,
        "hospitals": [
            {
                "_id": "1125632",
                "hospital_id": "1125632",
                "hospital_name": "中国人民解放军总医院",
                "hospital_intro": "列表简介",
                "hospital_level": "",
                "hospital_nature": "",
                "hospital_type": "",
                "hospital_property": "",
                "hospital_website": "",
                "hospital_insurance": "",
                "hospital_offices": "",
                "hospital_special": "",
                "hospital_advantage": "",
                "source_site": "中国医药信息查询平台",
                "source_url": "https://www.dayi.org.cn/hospital/1125632.html",
                "crawl_time": "",
            }
        ],
    }
    module.parse_hospital_detail_page = lambda _url, _html: {
        "_id": "1125632",
        "hospital_id": "1125632",
        "hospital_name": "中国人民解放军总医院",
        "hospital_address": "北京市复兴路28号",
        "hospital_phone": "010-68182255",
        "hospital_intro": "详情简介",
        "hospital_level": "三甲",
        "hospital_nature": "非营利性",
        "hospital_type": "综合医院",
        "hospital_property": "",
        "hospital_website": "http://www.301hospital.com.cn/",
        "hospital_insurance": "是",
        "hospital_offices": "神经内科",
        "hospital_special": "国家临床重点专科",
        "hospital_advantage": "优势病种",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/hospital/1125632.html",
        "crawl_time": "",
    }

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    spider = module.DoctorZgyyxxSpider(profile)

    def fake_request_html(url: str) -> str:
        if "/list/3" in url:
            return doctor_list_html
        if "/list/2" in url:
            return hospital_list_html
        if "/doctor/" in url:
            return doctor_html
        if "/hospital/" in url:
            return hospital_html
        raise AssertionError(url)

    spider.request_html = fake_request_html

    result = spider.run()

    assert result["doctor_upsert_count"] == 1
    assert result["hospital_upsert_count"] == 1
    assert saved_doctors[0]["_id"] == "1120165"
    assert saved_hospitals[0]["hospital_id"] == "1125632"


def test_run_expands_doctor_pages_and_hospital_expert_doctors() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    saved_doctors: list[dict[str, str]] = []
    saved_hospitals: list[dict[str, str]] = []

    class FakeCollection:
        def __init__(self, bucket: list[dict[str, str]]) -> None:
            self.bucket = bucket

        def replace_one(self, _filter, data, upsert=False):  # noqa: ANN001, FBT002
            self.bucket.append(data)

    class FakeDatabase:
        def __getitem__(self, name: str):
            if name == "doctor_zgyyxx":
                return FakeCollection(saved_doctors)
            if name == "hospital_zgyyxx":
                return FakeCollection(saved_hospitals)
            raise KeyError(name)

    class FakeClient:
        def __getitem__(self, _name: str):
            return FakeDatabase()

    module.build_mongo_client = lambda _config: FakeClient()
    module.build_redis_client = lambda _config: module.InMemoryRedisClient()

    page_calls: list[int] = []

    def fake_parse_doctor_list_page(url: str, _html: str):
        if url.endswith("/list/3"):
            page_calls.append(1)
            return {
                "total": 2,
                "page_size": 1,
                "page_num": 1,
                "total_pages": 2,
                "doctors": [
                    module.build_doctor_record(
                        doctor_id="d1",
                        doctor_name="医生1",
                        doctor_hospital="医院A",
                        doctor_department="科室A",
                        doctor_title="主任医师",
                        doctor_avatar_url="https://example.com/d1.jpg",
                        doctor_specialties="",
                        intro="列表1",
                        source_url="https://www.dayi.org.cn/doctor/d1.html",
                        crawl_time="",
                    )
                ],
            }
        if url.endswith("/list/3/2"):
            page_calls.append(2)
            return {
                "total": 2,
                "page_size": 1,
                "page_num": 2,
                "total_pages": 2,
                "doctors": [
                    module.build_doctor_record(
                        doctor_id="d2",
                        doctor_name="医生2",
                        doctor_hospital="医院B",
                        doctor_department="科室B",
                        doctor_title="主任医师",
                        doctor_avatar_url="https://example.com/d2.jpg",
                        doctor_specialties="",
                        intro="列表2",
                        source_url="https://www.dayi.org.cn/doctor/d2.html",
                        crawl_time="",
                    )
                ],
            }
        raise AssertionError(url)

    module.parse_doctor_list_page = fake_parse_doctor_list_page
    module.parse_doctor_detail_page = lambda url, _html: {
        "_id": url.rsplit("/", 1)[-1].replace(".html", ""),
        "doctor_id": url.rsplit("/", 1)[-1].replace(".html", ""),
        "doctor_name": f"详情{url.rsplit('/', 1)[-1].replace('.html', '')}",
        "doctor_hospital": "详情医院",
        "doctor_department": "详情科室",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://example.com/detail.jpg",
        "doctor_specialties": "详情擅长",
        "intro": "详情简介",
        "source_site": "中国医药信息查询平台",
        "source_url": url,
        "crawl_time": "",
    }
    module.parse_hospital_list_page = lambda _url, _html: {
        "total": 1,
        "page_size": 1,
        "page_num": 1,
        "total_pages": 1,
        "hospitals": [
            {
                "hospital_id": "h1",
                "_id": "h1",
                "hospital_name": "医院1",
                "hospital_intro": "医院列表简介",
                "hospital_level": "",
                "hospital_nature": "",
                "hospital_type": "",
                "hospital_property": "",
                "hospital_website": "",
                "hospital_insurance": "",
                "hospital_offices": "",
                "hospital_special": "",
                "hospital_advantage": "",
                "source_site": "中国医药信息查询平台",
                "source_url": "https://www.dayi.org.cn/hospital/h1.html",
                "crawl_time": "",
            }
        ],
    }
    module.parse_hospital_detail_page = lambda _url, _html: {
        "_id": "h1",
        "hospital_id": "h1",
        "hospital_name": "医院1",
        "hospital_address": "地址1",
        "hospital_phone": "电话1",
        "hospital_intro": "医院详情简介",
        "hospital_level": "三甲",
        "hospital_nature": "非营利性",
        "hospital_type": "综合医院",
        "hospital_property": "",
        "hospital_website": "http://example.com/",
        "hospital_insurance": "是",
        "hospital_offices": "科室1",
        "hospital_special": "特色1",
        "hospital_advantage": "优势1",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/hospital/h1.html",
        "crawl_time": "",
    }
    module.parse_hospital_expert_doctors = lambda _url, _html: [
        module.build_doctor_record(
            doctor_id="hospital_h1_专家1",
            doctor_name="专家1",
            doctor_hospital="医院1",
            doctor_department="",
            doctor_title="主任医师",
            doctor_avatar_url="https://example.com/expert1.jpg",
            doctor_specialties="专家擅长",
            intro="专家简介",
            source_url="https://www.dayi.org.cn/hospital/h1.html",
            crawl_time="",
        )
    ]

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    spider = module.DoctorZgyyxxSpider(profile)

    def fake_request_html(url: str) -> str:
        if "/list/3" in url:
            return "<html></html>"
        if "/list/2" in url:
            return "<html></html>"
        if "/doctor/" in url:
            return "<html></html>"
        if "/hospital/" in url:
            return "<html></html>"
        raise AssertionError(url)

    spider.request_html = fake_request_html

    result = spider.run()

    assert page_calls == [1, 2]
    assert result["doctor_upsert_count"] == 3
    assert result["hospital_upsert_count"] == 1
    assert any(item["doctor_id"] == "d1" for item in saved_doctors)
    assert any(item["doctor_id"] == "d2" for item in saved_doctors)
    assert any(item["doctor_id"] == "hospital_h1_专家1" for item in saved_doctors)


def test_run_skips_doctor_list_when_doctor_detail_queue_already_has_tasks() -> None:
    module = load_module("doctor_zgyyxx", "doctor_zgyyxx.py")
    saved_doctors: list[dict[str, str]] = []
    saved_hospitals: list[dict[str, str]] = []

    class FakeCollection:
        def __init__(self, bucket: list[dict[str, str]]) -> None:
            self.bucket = bucket

        def replace_one(self, _filter, data, upsert=False):  # noqa: ANN001, FBT002
            self.bucket.append(data)

    class FakeDatabase:
        def __getitem__(self, name: str):
            if name == "doctor_zgyyxx":
                return FakeCollection(saved_doctors)
            if name == "hospital_zgyyxx":
                return FakeCollection(saved_hospitals)
            raise KeyError(name)

    class FakeClient:
        def __getitem__(self, _name: str):
            return FakeDatabase()

    redis_client = module.InMemoryRedisClient()
    module.build_mongo_client = lambda _config: FakeClient()
    module.build_redis_client = lambda _config: redis_client

    doctor_detail_key = module.DEFAULT_PROFILE["redis"]["doctor_detail_task"]
    hospital_detail_key = module.DEFAULT_PROFILE["redis"]["hospital_detail_task"]

    module.push_task(
        redis_client,
        doctor_detail_key,
        {"url": "https://www.dayi.org.cn/doctor/1120165.html", "doctor_id": "1120165"},
    )

    module.parse_doctor_detail_page = lambda url, _html: {
        "_id": "1120165",
        "doctor_id": "1120165",
        "doctor_name": "王友彬",
        "doctor_hospital": "北京协和医院",
        "doctor_department": "整形美容外科",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://example.com/doctor.jpg",
        "doctor_specialties": "详情擅长",
        "intro": "详情简介",
        "source_site": "中国医药信息查询平台",
        "source_url": url,
        "crawl_time": "",
    }
    module.parse_hospital_list_page = lambda _url, _html: {
        "total": 1,
        "page_size": 1,
        "page_num": 1,
        "total_pages": 1,
        "hospitals": [
            {
                "_id": "h1",
                "hospital_id": "h1",
                "hospital_name": "医院1",
                "hospital_intro": "医院列表简介",
                "hospital_level": "",
                "hospital_nature": "",
                "hospital_type": "",
                "hospital_property": "",
                "hospital_website": "",
                "hospital_insurance": "",
                "hospital_offices": "",
                "hospital_special": "",
                "hospital_advantage": "",
                "source_site": "中国医药信息查询平台",
                "source_url": "https://www.dayi.org.cn/hospital/h1.html",
                "crawl_time": "",
            }
        ],
    }
    module.parse_hospital_detail_page = lambda _url, _html: {
        "_id": "h1",
        "hospital_id": "h1",
        "hospital_name": "医院1",
        "hospital_address": "地址1",
        "hospital_phone": "电话1",
        "hospital_intro": "医院详情简介",
        "hospital_level": "三甲",
        "hospital_nature": "非营利性",
        "hospital_type": "综合医院",
        "hospital_property": "",
        "hospital_website": "http://example.com/",
        "hospital_insurance": "是",
        "hospital_offices": "科室1",
        "hospital_special": "特色1",
        "hospital_advantage": "优势1",
        "source_site": "中国医药信息查询平台",
        "source_url": "https://www.dayi.org.cn/hospital/h1.html",
        "crawl_time": "",
    }
    module.parse_hospital_expert_doctors = lambda _url, _html: []

    profile = copy.deepcopy(module.DEFAULT_PROFILE)
    spider = module.DoctorZgyyxxSpider(profile)

    requested_urls: list[str] = []

    def fake_request_html(url: str) -> str:
        requested_urls.append(url)
        if "/list/3" in url:
            raise AssertionError("已有医生详情任务时不应再请求医生列表页")
        if "/doctor/" in url:
            return "<html></html>"
        if "/list/2" in url:
            return "<html></html>"
        if "/hospital/" in url:
            return "<html></html>"
        raise AssertionError(url)

    spider.request_html = fake_request_html

    result = spider.run()

    assert result["doctor_upsert_count"] == 1
    assert result["hospital_upsert_count"] == 1
    assert requested_urls[0] == "https://www.dayi.org.cn/doctor/1120165.html"
    assert redis_client.scard(doctor_detail_key) == 0
    assert redis_client.scard(hospital_detail_key) == 0
