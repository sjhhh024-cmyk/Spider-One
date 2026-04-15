from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


doctor_detail_module = importlib.import_module("doctor_ywbd.spiders.doctor.12_doctor_detail_spider")


def test_extract_doctor_detail_fields_from_detail_html() -> None:
    html = """
    <html>
      <head>
        <title>【王小渝】四川省第三人民医院血液内科王小渝介绍_王小渝出诊时间_王小渝怎么样-快速问医生</title>
      </head>
      <body>
        <div class="dor-msg">
          <dl class="clears">
            <dt><img src="//cdn.120askimages.com/ask/newdata/images/ys/f06faia2nlwg3h0f.jpg"></dt>
            <dd class="name"><b><strong>王小渝</strong>  其他</b></dd>
            <dd class="msg">
              <p><span>所在医院：</span><var><a href="/yiyuan/0nwfblgaszpknec8.html">四川省第三人民医院</a></var></p>
              <p><span>所在科室：</span><var><a href="/keshi/l26iblgaszpknec8.html">血液内科</a></var></p>
              <p><span>擅　　长：</span><var>擅长治疗各种贫血、白血病、淋巴瘤、多发性骨髓瘤。</var></p>
              <p><span>简　　介：</span><var>王小渝，血液科一级，主任医师。从医四十余年。</var></p>
            </dd>
          </dl>
          <div class="experience"><b class="title">医生介绍</b>王小渝，血液科一级，主任医师。从医四十余年，曾任中华医学会四川省分会血液专委会常委。</div>
        </div>
      </body>
    </html>
    """
    assert doctor_detail_module.extract_doctor_detail_fields(
        "https://data.120ask.com/yisheng/f06faia2nlwg3h0f.html",
        html,
    ) == {
        "_id": "f06faia2nlwg3h0f",
        "url": "https://data.120ask.com/yisheng/f06faia2nlwg3h0f.html",
        "website": "有问必答",
        "doctor_name": "王小渝",
        "title": "主任医师",
        "gender": "",
        "hospital_name": "四川省第三人民医院",
        "department_name": "血液内科",
        "good_at": "擅长治疗各种贫血、白血病、淋巴瘤、多发性骨髓瘤。",
        "intro": "王小渝，血液科一级，主任医师。从医四十余年，曾任中华医学会四川省分会血液专委会常委。",
        "avatar_url": "https://cdn.120askimages.com/ask/newdata/images/ys/f06faia2nlwg3h0f.jpg",
    }


def test_extract_doctor_detail_fields_parse_gender_and_title_when_present() -> None:
    html = """
    <html>
      <body>
        <div class="dor-msg">
          <dl class="clears">
            <dt><img src="//cdn.120askimages.com/ask/newdata/images/ys_default.jpg"></dt>
            <dd class="name"><b><strong>马烈</strong> 主任医师</b></dd>
            <dd class="msg">
              <p><span>所在医院：</span><var><a href="/yiyuan/abc.html">北京地坛医院</a></var></p>
              <p><span>所在科室：</span><var><a href="/keshi/abc.html">肝病中心</a></var></p>
              <p><span>擅　　长：</span><var>乙型及丙型病毒性肝炎的抗病毒治疗。</var></p>
              <p><span>简　　介：</span><var>马烈，女，肝病中心主任医师。</var></p>
            </dd>
          </dl>
          <div class="experience"><b class="title">医生介绍</b>马烈，女，肝病中心主任医师，1984年毕业于北京医科大学。</div>
        </div>
      </body>
    </html>
    """
    assert doctor_detail_module.extract_doctor_detail_fields(
        "https://data.120ask.com/yisheng/f0f5aeb62vc9f5a6.html",
        html,
    ) == {
        "_id": "f0f5aeb62vc9f5a6",
        "url": "https://data.120ask.com/yisheng/f0f5aeb62vc9f5a6.html",
        "website": "有问必答",
        "doctor_name": "马烈",
        "title": "主任医师",
        "gender": "女",
        "hospital_name": "北京地坛医院",
        "department_name": "肝病中心",
        "good_at": "乙型及丙型病毒性肝炎的抗病毒治疗。",
        "intro": "马烈，女，肝病中心主任医师，1984年毕业于北京医科大学。",
        "avatar_url": "https://cdn.120askimages.com/ask/newdata/images/ys_default.jpg",
    }
