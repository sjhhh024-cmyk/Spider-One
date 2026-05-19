from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from doctor_dzys import (  # noqa: E402
    DEFAULT_REDIS_URL,
    InMemoryRedisClient,
    dump_task,
    extract_detail_urls_from_sitemap,
    is_placeholder_doctor_name,
    is_viable_hospital_name,
    parse_doctor_detail_page,
)


def test_extract_detail_urls_from_sitemap_dedupes_and_preserves_order() -> None:
    html = """
    <a href="/hospital/doctor_home/1.html">A</a>
    <a href="/hospital/doctor_home/2.html">B</a>
    <a href="/hospital/doctor_home/1.html">A2</a>
    """
    urls = extract_detail_urls_from_sitemap("https://www.dazhong.com/hospital/sitemap_doctor", html)
    assert urls == [
        "https://www.dazhong.com/hospital/doctor_home/1.html",
        "https://www.dazhong.com/hospital/doctor_home/2.html",
    ]


def test_parse_doctor_detail_page_extracts_common_fields() -> None:
    html = """
    <div class="docad_doctor shadow clearfix mt30">
      <i class="docad_img">
        <img class="img" src="https://static.cndzys.com/doctor_img/doctor-100.jpg" alt="李劲松"/>
      </i>
      <div class="det_doctor ml20 pr20">
        <div class="info">
          <h1 class="name">李劲松</h1>
          <span class="depart">外科</span>
        </div>
        <div class="info">
          <p class="level"><a href="/hospital_detail/1381.html">梅州市人民医院</a> 主任医师</p>
        </div>
        <p class="intro"><strong>擅长：</strong><span>脑血管疾病的诊断和介入手术治疗。</span></p>
        <p class="intro"><strong>简介：</strong><span>从事神经外科工作多年。</span></p>
      </div>
    </div>
    """
    record = parse_doctor_detail_page("https://www.dazhong.com/hospital/doctor_home/100.html", html)
    assert record["doctor_id"] == "100"
    assert record["doctor_name"] == "李劲松"
    assert record["doctor_hospital"] == "梅州市人民医院"
    assert record["doctor_department"] == "外科"
    assert record["doctor_title"] == "主任医师"
    assert record["doctor_avatar_url"] == "https://static.cndzys.com/doctor_img/doctor-100.jpg"
    assert record["doctor_specialties"] == "脑血管疾病的诊断和介入手术治疗。"
    assert record["intro"] == "从事神经外科工作多年。"


def test_parse_doctor_detail_page_skips_default_doctor_avatar() -> None:
    html = """
    <div class="docad_doctor shadow clearfix mt30">
      <i class="docad_img">
        <img class="img" src="https://static.cndzys.com/doctor_img/doctor-0.jpg" alt="张三"/>
        <img class="img" src="https://static.cndzys.com/doctor_img/doctor-1820.jpg" alt="李四"/>
      </i>
      <div class="det_doctor ml20 pr20">
        <div class="info">
          <h1 class="name">张三</h1>
          <span class="depart">外科</span>
        </div>
        <div class="info">
          <p class="level"><a href="/hospital_detail/1381.html">梅州市人民医院</a> 主任医师</p>
        </div>
      </div>
    </div>
    """
    record = parse_doctor_detail_page("https://www.dazhong.com/hospital/doctor_home/101.html", html)
    assert record["doctor_avatar_url"] == ""


def test_in_memory_redis_client_stages_detail_tasks() -> None:
    redis_client = InMemoryRedisClient()
    task = dump_task(
        {
            "doctor_id": "100",
            "detail_url": "https://www.dazhong.com/hospital/doctor_home/100.html",
            "source_url": "https://www.dazhong.com/hospital/doctor_home/100.html",
        }
    )

    assert redis_client.sadd("doctor_dzys:doctor_info_url", task) == 1
    assert redis_client.sadd("doctor_dzys:doctor_info_url", task) == 0
    assert redis_client.scard("doctor_dzys:doctor_info_url") == 1
    assert task in redis_client.smembers("doctor_dzys:doctor_info_url")
    assert redis_client.srem("doctor_dzys:doctor_info_url", task) == 1
    assert redis_client.scard("doctor_dzys:doctor_info_url") == 0


def test_filters_reject_placeholder_doctor_and_suspicious_hospital() -> None:
    assert is_placeholder_doctor_name("张医生") is True
    assert is_placeholder_doctor_name("李劲松") is False
    assert is_viable_hospital_name("梅州市人民医院") is True
    assert is_viable_hospital_name("日喀则地区割包皮医院") is False


def test_default_redis_url_uses_shared_cluster_db1() -> None:
    assert "117.50.131.232" in DEFAULT_REDIS_URL
    assert DEFAULT_REDIS_URL.endswith("/1")
