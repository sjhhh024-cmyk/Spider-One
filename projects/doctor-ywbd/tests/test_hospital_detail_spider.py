from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


hospital_detail_module = importlib.import_module("doctor_ywbd.spiders.doctor.10_hospital_detail_spider")


def test_extract_hospital_detail_fields_from_intro_page() -> None:
    html = """
    <html>
      <head>
        <title>四川省第三人民医院介绍_科室查询-快速问医生</title>
      </head>
      <body>
        <div class="hospital-page">
          <div class="right">
            <div class="hospital-describe">
              <div class="data">
                <div class="basic">
                  <b>四川省第三人民医院基本资料：</b>
                  <p>
                    门诊信息：19位医生<a href="/yiyuan/yisheng/0nwfblgaszpknec8.html">查看门诊信息</a><br>
                    医院电话：028-87013885<br>
                    医院地址：成都市青羊区望仙村3号 <a href="/yiyuan/ditu/0nwfblgaszpknec8.html">查看地图</a>
                  </p>
                </div>
              </div>
              <div class="detail">
                <b>四川省第三人民医院介绍</b>
                <p>四川省第三人民医院是成都市卫生局所属的一所综合性三级甲等医院，创建于1941年。</p>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    assert hospital_detail_module.extract_hospital_detail_fields(
        "https://data.120ask.com/yiyuan/jieshao/0nwfblgaszpknec8.html",
        html,
    ) == {
        "_id": "0nwfblgaszpknec8",
        "hospital_name": "四川省第三人民医院",
        "hospital_url": "https://data.120ask.com/yiyuan/0nwfblgaszpknec8.html",
        "hospital_address": "成都市青羊区望仙村3号",
        "hospital_phone": "028-87013885",
        "hospital_intro": "四川省第三人民医院是成都市卫生局所属的一所综合性三级甲等医院，创建于1941年。",
        "website": "有问必答",
    }
