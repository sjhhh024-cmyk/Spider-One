from __future__ import annotations

import json

import pymongo
import requests


MONGO_CONFIG = {
    "host": "101.200.125.240",
    "port": 27017,
    "username": "admin",
    "password": "a@Mfv8k!r@8r@8&R",
    "authSource": "admin",
}

DATABASE_NAME = "Doctor_Database"
COLLECTION_NAME = "doctor_zgyyxx"

BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
API_KEY = "tp-ca5ge6g6qwyo6fde4pdj3isfi2somjjcx4g9ufkvu7gitgef"
MODEL = "mimo-v2.5-pro"
TIMEOUT = 300
DECEASED_PATTERN = r"已故|去世|逝世|病逝|辞世|仙逝|卒于|享年|[（(]\d{4}\s*[—\-－–]\s*\d{4}[)）]"

SYSTEM_PROMPT = """你是医疗信息抽取助手。
你的任务是只根据医生简介、工作经历、擅长内容，提取医生当前或最新任职医院、当前或最新任职科室。
只输出 JSON，不要输出任何解释、Markdown、前后缀。
输出格式固定为：
{"doctor_hospital":"","doctor_department":""}
规则：
1. 优先提取“现任、现就职于、工作至今、现为、现于”等表示当前状态的信息。
2. 可以结合工作经历字段判断最新任职医院和科室，优先取时间上最新且仍然有效的信息。
3. 如果简介和工作经历里都没有明确科室，可以根据 doctor_specialties 里的擅长疾病、擅长诊疗方向，反推出一个合理的大类科室。
4. 如果只能通过擅长内容反推科室，输出最合理的标准大类科室，例如：擅长冠心病、高血压 -> 心血管内科；擅长肛瘘、痔疮 -> 肛肠科；擅长颈肩腰腿痛 -> 康复医学科或骨科中更合理的一类。
5. doctor_department 必须直接输出清洗后的标准科室名，不能输出原始脏值。
6. doctor_department 不能填写职务、头衔、岗位名称，不能输出“主任、院长、副院长、教授、医生、医师、主任医师、副主任医师、科主任、负责人、学科带头人、专家”等词。
7. doctor_department 不能输出单字符、纯方向词、纯职务词。
8. 对科室要在提取时直接标准化，例如：内四科->内科，内科二区->内科，中医系->中医科，外二科->外科。
9. 如果原文是病区、一区、二区、三区、四区、东区、西区、南区、北区等分区表达，要提取并输出其对应的标准科室，不要保留分区字样。
10. 如果原文出现“脊柱外科主任”“心内科副主任”“肛肠科主任医师”“康复医学科医生”这类“科室名称 + 职务”连写，必须提取前面的科室名称作为 doctor_department，不能因为后面带职务就漏掉科室。
11. 如果一句话里同时有科室和职务，例如“主任医师，脊柱外科主任。吉林省医学会创伤学组员。”，doctor_department 应提取为“脊柱外科”。
12. doctor_hospital 输出完整医院名。
13. doctor_department 输出当前具体科室名，而且必须是规范后的结果。
14. 提取不到就输出空字符串。
15. doctor_hospital 输出医院不要输出单独的大学名，研究所名。
"""


def build_user_content(document: dict) -> str:
    return "\n\n".join(
        [
            f"医生简介：{document.get('intro', '').strip()}",
            f"工作经历：{(document.get('doctor_work_process') or '').strip()}",
            f"擅长内容：{(document.get('doctor_specialties') or '').strip()}",
        ]
    )


def extract_hospital_department(session: requests.Session, document: dict) -> dict[str, str]:
    response = session.post(
        f"{BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_content(document)},
            ],
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data, _ = json.JSONDecoder().raw_decode(content[content.index("{") :])
    return {
        "doctor_hospital": data["doctor_hospital"].strip(),
        "doctor_department": data["doctor_department"].strip(),
    }


def main() -> None:
    client = pymongo.MongoClient(**MONGO_CONFIG)
    collection = client[DATABASE_NAME][COLLECTION_NAME]
    session = requests.Session()

    query = {
        "intro": {
            "$nin": ["", None],
            "$not": {"$regex": DECEASED_PATTERN},
        },
        "flag": {"$ne": "N"},
        "$or": [
            {"doctor_hospital": {"$in": ["", None]}},
            {"doctor_department": {"$in": ["", None, "void 0"]}},
        ],
    }
    projection = {
        "_id": 1,
        "doctor_hospital": 1,
        "doctor_department": 1,
        "intro": 1,
        "doctor_work_process": 1,
        "doctor_specialties": 1,
    }

    updated_count = 0
    for document in collection.find(query, projection):
        extracted = extract_hospital_department(session, document)
        update_fields = {}

        if (document.get("doctor_hospital") or "").strip() == "":
            update_fields["doctor_hospital"] = extracted["doctor_hospital"]

        if (document.get("doctor_department") or "").strip() in {"", "void 0"}:
            update_fields["doctor_department"] = extracted["doctor_department"]

        update_fields["flag"] = "N"

        collection.update_one(
            {"_id": document["_id"]},
            {"$set": update_fields},
        )
        updated_count += 1
        print(
            json.dumps(
                {
                    "_id": document["_id"],
                    **update_fields,
                },
                ensure_ascii=False,
            )
        )

    print(json.dumps({"updated_count": updated_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
