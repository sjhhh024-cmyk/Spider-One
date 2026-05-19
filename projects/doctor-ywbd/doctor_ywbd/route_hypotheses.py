"""doctor-ywbd 项目的真实入口和存储命名。"""

from __future__ import annotations


BASE_URL = "https://data.120ask.com"

ENTRY_POINTS = {
    "disease": f"{BASE_URL}/yisheng/jibing.html",
    "department": f"{BASE_URL}/yisheng/keshi.html",
    "area": f"{BASE_URL}/yisheng/area.html",
    "hospital": f"{BASE_URL}/yiyuan/area.html",
}

REDIS_KEY_BY_CATEGORY = {
    "disease": "disease_index_url",
    "department": "department_index_url",
    "area": "area_index_url",
    "hospital": "hospital_area_index_url",
}

DOCTOR_COLLECTION_NAME = "doctor_ywbd"
HOSPITAL_COLLECTION_NAME = "hospital_ywbd"


def build_redis_keys(prefix: str = "doctor_ywbd") -> dict[str, str]:
    """统一生成当前项目的 Redis key。"""

    normalized_prefix = str(prefix).strip() or "doctor_ywbd"
    return {
        "disease_index_url": f"{normalized_prefix}:disease_index_url",
        "disease_list_url": f"{normalized_prefix}:disease_list_url",
        "department_index_url": f"{normalized_prefix}:department_index_url",
        "department_list_url": f"{normalized_prefix}:department_list_url",
        "area_index_url": f"{normalized_prefix}:area_index_url",
        "area_list_url": f"{normalized_prefix}:area_list_url",
        "hospital_area_index_url": f"{normalized_prefix}:hospital_area_index_url",
        "hospital_list_url": f"{normalized_prefix}:hospital_list_url",
        "hospital_detail_url": f"{normalized_prefix}:hospital_detail_url",
        "hospital_expert_url": f"{normalized_prefix}:hospital_expert_url",
        "doctor_info_url": f"{normalized_prefix}:doctor_info_url",
    }
