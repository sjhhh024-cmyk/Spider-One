from __future__ import annotations

import sys
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_wygk.parse_helpers import (  # noqa: E402
    merge_doctor_task,
    parse_course_navigation_records,
    parse_course_timetable_doctor_records,
    parse_department_records,
    parse_doctor_home_fans_records,
    parse_doctor_home_info,
    parse_live_doctor_records,
    parse_organization_homepage_records,
    parse_personal_info_doctor_item,
    parse_resource_doctor_records,
    parse_doctor_list_records,
)


def test_parse_department_records_extracts_leaf_departments() -> None:
    payload = {
        "responseObject": {
            "responseData": {
                "dataList": [
                    {"id": 10, "deptName": "脊柱外科"},
                    {"id": 11, "deptName": "创伤骨科"},
                ]
            }
        }
    }

    assert parse_department_records(payload, hospital_id=1) == [
        {"hospital_id": 1, "dept_id": "10", "dept_name": "脊柱外科"},
        {"hospital_id": 1, "dept_id": "11", "dept_name": "创伤骨科"},
    ]


def test_parse_doctor_list_records_extracts_doctor_identity_from_department_list() -> None:
    payload = {
        "responseObject": {
            "responseData": {
                "dataList": [
                    {
                        "doctorId": 1450269515500,
                        "doctorName": "张三",
                        "medicalTitle": "主任医师",
                    }
                ]
            }
        }
    }

    assert parse_doctor_list_records(
        payload,
        hospital_id=1,
        dept_id="10",
        dept_name="脊柱外科",
    ) == [
        {
            "hospital_id": 1,
            "dept_id": "10",
            "dept_name": "脊柱外科",
            "doctor_id": "1450269515500",
            "doctor_name": "张三",
            "doctor_title": "主任医师",
        }
    ]


def test_parse_personal_info_doctor_item_merges_richer_detail_payloads() -> None:
    auth_payload = {
        "responseData": {
            "data_list": {
                "customerId": 1450269515500,
                "fullName": "张三",
                "medicalTitleShow": "主任医师",
                "company": "北京积水潭医院",
                "department": "脊柱外科",
                "expertise": "脊柱退变",
                "summary": "长期从事脊柱外科临床与教学工作",
                "illnessNameList": "腰椎间盘突出症,脊柱侧弯",
            }
        }
    }
    cards_payload = {
        "responseData": {
            "data_list": {
                "occupationList": [
                    {
                        "unit": "北京积水潭医院",
                        "department": "脊柱外科",
                        "medicalTitle": "主任医师",
                        "startTime": "2010-01-01 00:00:00.0",
                        "endTime": "",
                    }
                ],
                "educationList": [
                    {
                        "university": "北京大学",
                        "major": "外科学",
                        "education": "博士",
                        "startTime": "1998-09-01 00:00:00.0",
                        "endTime": "2001-07-01 00:00:00.0",
                    }
                ],
                "socialList": [
                    {
                        "organization": "中华医学会骨科分会",
                        "socialTitle": "委员",
                        "startTime": "2019-01-01 00:00:00.0",
                        "endTime": "",
                    }
                ],
                "honorList": [
                    {
                        "honorName": "国家科技进步二等奖",
                        "awardDepartment": "国务院",
                        "awardYear": "2022-01-01 00:00:00.0",
                    }
                ],
                "patentList": [
                    {
                        "patentName": "一种脊柱固定装置",
                        "patentCode": "ZL202010000001.0",
                        "patentTime": "2023-01-01 00:00:00.0",
                        "country": "中国",
                    }
                ],
            }
        }
    }
    legacy_payload = {
        "responseData": {
            "doctorId": 1450269515500,
            "logoUrl": "https://img05.allinmd.cn/a.jpg",
            "practiceIntroduction": "从事脊柱外科工作二十年",
            "abilityAcademicList": [
                {"contentDescribe": "发表 SCI 论文 20 篇"},
            ],
            "abilityPracticeList": [
                {"contentDescribe": "完成复杂脊柱手术 3000 余例"},
            ],
        }
    }
    big_event_payload = {
        "responseData": {
            "dataList": [
                {"event_name": "担任骨科中心主任"},
            ]
        }
    }

    item = parse_personal_info_doctor_item(
        auth_payload=auth_payload,
        cards_payload=cards_payload,
        legacy_payload=legacy_payload,
        big_event_payload=big_event_payload,
        source_context={"dept_name": "脊柱外科"},
    )

    assert item["_id"] == "1450269515500"
    assert item["doctor_id"] == "1450269515500"
    assert item["doctor_name"] == "张三"
    assert item["doctor_title"] == "主任医师"
    assert item["hospital_name"] == "北京积水潭医院"
    assert item["department_name"] == "脊柱外科"
    assert item["doctor_expertise"] == "脊柱退变"
    assert item["doctor_introduction"] == "长期从事脊柱外科临床与教学工作"
    assert item["doctor_avatar_url"] == "https://img05.allinmd.cn/a.jpg"
    assert item["doctor_illnesses"] == ["腰椎间盘突出症", "脊柱侧弯"]
    assert item["doctor_social_titles"] == [
        {
            "organization": "中华医学会骨科分会",
            "social_title": "委员",
            "start_date": "2019-01",
            "end_date": "",
        }
    ]
    assert item["doctor_honors"] == [
        {
            "honor_name": "国家科技进步二等奖",
            "award_department": "国务院",
            "award_date": "2022-01",
        }
    ]
    assert item["doctor_academic_achievements"] == ["发表 SCI 论文 20 篇"]
    assert item["doctor_practice_achievements"] == ["完成复杂脊柱手术 3000 余例"]
    assert item["doctor_work_experiences"] == [
        {
            "organization": "北京积水潭医院",
            "department_name": "脊柱外科",
            "doctor_title": "主任医师",
            "start_date": "2010-01",
            "end_date": "",
        }
    ]
    assert item["doctor_educations"] == [
        {
            "school_name": "北京大学",
            "major_name": "外科学",
            "education_name": "博士",
            "start_date": "1998-09",
            "end_date": "2001-07",
        }
    ]
    assert item["doctor_patents"] == [
        {
            "patent_name": "一种脊柱固定装置",
            "patent_code": "ZL202010000001.0",
            "patent_date": "2023-01",
            "country": "中国",
        }
    ]
    assert item["doctor_big_events"] == ["担任骨科中心主任"]
    assert item["website"] == "唯医骨科"
    assert item["source_url"] == "https://www.allinmd.cn/edu/personalInfo?doctorId=1450269515500"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["crawl_time"])


def test_parse_personal_info_doctor_item_backfills_hospital_and_department_from_task_context() -> None:
    item = parse_personal_info_doctor_item(
        auth_payload={
            "responseData": {
                "data_list": {
                    "customerId": 1450269515500,
                    "fullName": "张三",
                    "medicalTitleShow": "主任医师",
                }
            }
        },
        cards_payload={"responseData": {"data_list": {}}},
        legacy_payload={"responseData": {"doctorId": 1450269515500}},
        big_event_payload={"responseData": {"dataList": []}},
        source_context={
            "doctor_name": "张三",
            "company": "北京积水潭医院",
            "dept_name": "脊柱外科",
        },
    )

    assert item["doctor_name"] == "张三"
    assert item["hospital_name"] == "北京积水潭医院"
    assert item["department_name"] == "脊柱外科"


def test_parse_live_doctor_records_extracts_doctor_list_from_activity_detail() -> None:
    payload = {
        "data": {
            "doctorList": [
                {
                    "doctorId": 1450269515500,
                    "doctorName": "张三",
                    "medicalTitle": "主任医师",
                    "company": "北京积水潭医院",
                    "headUrl": "https://img05.allinmd.cn/live-doctor.jpg",
                }
            ]
        }
    }

    assert parse_live_doctor_records(
        payload,
        activity_id="3533",
        activity_title="髋关节手术围手术期管理",
    ) == [
        {
            "activity_id": "3533",
            "activity_title": "髋关节手术围手术期管理",
            "doctor_id": "1450269515500",
            "doctor_name": "张三",
            "doctor_title": "主任医师",
            "company": "北京积水潭医院",
            "doctor_avatar_url": "https://img05.allinmd.cn/live-doctor.jpg",
            "source_url": "https://www.allinmd.cn/edu/liveDetail?activityId=3533",
        }
    ]


def test_parse_doctor_home_info_extracts_homepage_identity_and_fans_count() -> None:
    payload = {
        "code": 0,
        "data": {
            "customerId": 1424958335567,
            "name": "白雪东",
            "company": "中国人民解放军总医院",
            "medicalTitle": "主任医师",
            "logoUrl": "https://img05.allinmd.cn/doctor-home.jpg",
            "fansCount": 18,
        },
    }

    assert parse_doctor_home_info(payload) == {
        "doctor_id": "1424958335567",
        "doctor_name": "白雪东",
        "company": "中国人民解放军总医院",
        "doctor_title": "主任医师",
        "doctor_avatar_url": "https://img05.allinmd.cn/doctor-home.jpg",
        "fans_count": 18,
    }


def test_parse_doctor_home_fans_records_filters_non_hospital_accounts() -> None:
    payload = {
        "responseData": {
            "data_list": [
                {
                    "customer_auth": {
                        "customerId": 1478873433316,
                        "fullName": "姜志利",
                        "company": "河北省吴桥县第二医院",
                        "medicalTitleShow": "主治医师",
                    },
                    "customer_att": {
                        "logoUrl": "https://img05.allinmd.cn/fans-doctor.jpg",
                    },
                },
                {
                    "customer_auth": {
                        "customerId": 10001,
                        "fullName": "普通用户",
                        "company": "北京朝阳区",
                        "medicalTitleShow": "",
                    }
                },
            ]
        }
    }

    assert parse_doctor_home_fans_records(payload, source_doctor_id="1424958335567") == [
        {
            "doctor_id": "1478873433316",
            "doctor_name": "姜志利",
            "doctor_title": "主治医师",
            "company": "河北省吴桥县第二医院",
            "doctor_avatar_url": "https://img05.allinmd.cn/fans-doctor.jpg",
            "source_url": "https://www.allinmd.cn/edu/doctorHome?doctorId=1424958335567",
        }
    ]


def test_parse_course_navigation_records_flattens_public_property_ids() -> None:
    payload = {
        "data": {
            "dataList": [
                {
                    "propertyId": 406,
                    "children": [
                        {"propertyId": 407},
                        {"propertyId": 408, "children": [{"propertyId": 409}]},
                    ],
                }
            ]
        }
    }

    assert parse_course_navigation_records(payload) == [406, 407, 408, 409]


def test_parse_course_timetable_doctor_records_reads_nested_res_customer_list() -> None:
    payload = {
        "data": {
            "courseGroupResultList": [
                {
                    "courseGroupList": [
                        {
                            "resourceId": 1770268780482,
                            "resourceName": "反肩置换的适应症",
                            "comboActionJump": {
                                "comboActionJumpV3": {
                                    "pcLink": "https://www.allinmd.cn/edu/videoTerminal?resourceId=1770268780482"
                                }
                            },
                            "resCustomerList": [
                                {
                                    "customerId": 1514989538784,
                                    "name": "杨春喜",
                                    "company": "上海市第一人民医院",
                                    "medicalTitle": "主任医师",
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }

    assert parse_course_timetable_doctor_records(payload, project_id="550", channel_id="1524") == [
        {
            "project_id": "550",
            "channel_id": "1524",
            "resource_id": "1770268780482",
            "resource_name": "反肩置换的适应症",
            "doctor_id": "1514989538784",
            "doctor_name": "杨春喜",
            "doctor_title": "主任医师",
            "company": "上海市第一人民医院",
            "doctor_avatar_url": "",
            "source_url": "https://www.allinmd.cn/edu/videoTerminal?resourceId=1770268780482",
        }
    ]


def test_parse_resource_doctor_records_reads_res_customer_list_from_resource_pages() -> None:
    payload = {
        "data": {
            "pageList": [
                {
                    "resId": 1568883284161,
                    "resName": "胫骨平台骨折切开复位内固定术",
                    "comboActionJump": {
                        "comboActionJumpV3": {
                            "pcLink": "https://www.allinmd.cn/edu/videoTerminal?resourceId=1568883284161"
                        }
                    },
                    "resCustomerList": [
                        {
                            "customerId": 1397640871173,
                            "name": "王秋根",
                            "company": "上海市第一人民医院",
                            "medicalTitle": "主任医师",
                        }
                    ],
                }
            ]
        }
    }

    assert parse_resource_doctor_records(payload, source_channel="surgery_feed") == [
        {
            "resource_id": "1568883284161",
            "resource_name": "胫骨平台骨折切开复位内固定术",
            "doctor_id": "1397640871173",
            "doctor_name": "王秋根",
            "doctor_title": "主任医师",
            "company": "上海市第一人民医院",
            "doctor_avatar_url": "",
            "source_channel": "surgery_feed",
            "source_url": "https://www.allinmd.cn/edu/videoTerminal?resourceId=1568883284161",
        }
    ]


def test_parse_organization_homepage_records_reads_customer_ids_from_video_sections() -> None:
    payload = {
        "data": {
            "dataList": [
                {
                    "configInfo": {"columnName": "视频"},
                    "videoList": [
                        {
                            "resId": 1397797441747,
                            "resName": "股骨近端骨折翻修术-经验分享",
                            "resCustomerList": [
                                {
                                    "customerId": 1397640884624,
                                    "name": "张长青",
                                    "company": "上海市第六人民医院",
                                    "medicalTitle": "主任医师",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }

    assert parse_organization_homepage_records(payload, organization_id="14") == [
        {
            "organization_id": "14",
            "resource_id": "1397797441747",
            "resource_name": "股骨近端骨折翻修术-经验分享",
            "doctor_id": "1397640884624",
            "doctor_name": "张长青",
            "doctor_title": "主任医师",
            "company": "上海市第六人民医院",
            "doctor_avatar_url": "",
            "source_channel": "organization_homepage",
            "source_url": "https://www.allinmd.cn/edu/organization?organizationId=14",
        }
    ]


def test_merge_doctor_task_outputs_clean_final_document() -> None:
    task = {
        "doctor_id": "1514989538784",
        "doctor_name": "杨春喜",
        "doctor_title": "主任医师",
        "company": "上海市第一人民医院",
        "source_url": "https://www.allinmd.cn/edu/videoTerminal?resourceId=1770268780482",
        "doctor_avatar_url": "https://img05.allinmd.cn/a.jpg",
    }

    item = merge_doctor_task(task)

    assert item["_id"] == "1514989538784"
    assert item["doctor_id"] == "1514989538784"
    assert item["hospital_name"] == "上海市第一人民医院"
    assert item["doctor_title"] == "主任医师"
    assert item["doctor_avatar_url"] == "https://img05.allinmd.cn/a.jpg"
    assert item["website"] == "唯医骨科"
    assert item["source_url"] == "https://www.allinmd.cn/edu/videoTerminal?resourceId=1770268780482"
    assert "detail_mode" not in item
    assert "company" not in item
