from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_circle.spiders.hospital.hospital_base_helpers import (  # noqa: E402
    build_nhsa_hospital_search_payload,
    build_nhsa_signed_request,
    build_hospital_base_item,
    build_hospital_search_payload,
    choose_best_hospital_match,
    choose_exact_hospital_match,
    decrypt_nhsa_response_data,
    derive_nhsa_sm4_key,
    is_viable_hospital_name,
    normalize_hospital_name,
    prepare_hospital_name_candidates,
)


def test_build_hospital_search_payload_uses_verified_keyword_parameter() -> None:
    payload = build_hospital_search_payload(
        access_token="token-123",
        hospital_name="北京市第六医院",
    )

    assert payload == {
        "access_token": "token-123",
        "pageIndex": 0,
        "pageSize": 20,
        "keyWord": "北京市第六医院",
    }


def test_build_nhsa_hospital_search_payload_uses_nationwide_search_shape() -> None:
    payload = build_nhsa_hospital_search_payload("上海市第一人民医院")

    assert payload == {
        "addr": "",
        "regnCode": "",
        "medinsName": "上海市第一人民医院",
        "medinsLvCode": "",
        "medinsTypeCode": "",
        "outMedOpenFlag": "",
        "pageNum": 1,
        "pageSize": 10,
        "queryDataSource": "es",
    }


def test_build_nhsa_signed_request_wraps_payload_into_encrypted_envelope() -> None:
    headers, body = build_nhsa_signed_request(
        app_code="T98HPCGN5ZVVQBS8LZQNOAEXVI9GYHKQ",
        app_secret="NMVFVILMKT13GEMD3BKPKCTBOQBPZR2P",
        public_key_base64="BEKaw3Qtc31LG/hTPHFPlriKuAn/nzTWl8LiRxLw4iQiSUIyuglptFxNkdCiNXcXvkqTH79Rh/A2sEFU6hjeK3k=",
        private_key_base64="AJxKNdmspMaPGj+onJNoQ0cgWk2E3CYFWKBJhpcJrAtC",
        payload=build_nhsa_hospital_search_payload("上海市第一人民医院"),
        timestamp=1713542400,
        nonce="nonce-123",
    )

    assert headers["channel"] == "web"
    assert headers["x-tif-timestamp"] == "1713542400"
    assert body["data"]["appCode"] == "T98HPCGN5ZVVQBS8LZQNOAEXVI9GYHKQ"
    assert body["data"]["encType"] == "SM4"
    assert body["data"]["signType"] == "SM2"
    assert body["data"]["timestamp"] == 1713542400
    assert body["data"]["data"]["encData"]
    assert body["data"]["signData"]


def test_decrypt_nhsa_response_data_can_read_sm4_payload() -> None:
    key = derive_nhsa_sm4_key(
        "T98HPCGN5ZVVQBS8LZQNOAEXVI9GYHKQ",
        "NMVFVILMKT13GEMD3BKPKCTBOQBPZR2P",
    )
    sample_plain_text = '{"list":[{"medinsName":"上海市第一人民医院"}],"total":1}'

    from gmssl import sm4

    crypt = sm4.CryptSM4()
    crypt.set_key(key, sm4.SM4_ENCRYPT)
    encrypted_text = crypt.crypt_ecb(sample_plain_text.encode("utf-8")).hex().upper()

    response_json = {
        "data": {
            "data": {
                "encData": encrypted_text,
            }
        }
    }

    assert decrypt_nhsa_response_data(
        "T98HPCGN5ZVVQBS8LZQNOAEXVI9GYHKQ",
        "NMVFVILMKT13GEMD3BKPKCTBOQBPZR2P",
        response_json,
    ) == {
        "list": [{"medinsName": "上海市第一人民医院"}],
        "total": 1,
    }


def test_normalize_hospital_name_cleans_common_edge_noise() -> None:
    assert normalize_hospital_name("'河北医科大学第二医院") == "河北医科大学第二医院"
    assert normalize_hospital_name(",白城市通榆县中医院") == "白城市通榆县中医院"
    assert normalize_hospital_name(".古楼医院") == "古楼医院"
    assert normalize_hospital_name(" 61606卫生✔️ ") == "61606卫生"


def test_is_viable_hospital_name_filters_obvious_dirty_values() -> None:
    assert is_viable_hospital_name("北京积水潭医院") is True
    assert is_viable_hospital_name("'河北医科大学第二医院") is True
    assert is_viable_hospital_name("301医院") is True
    assert is_viable_hospital_name("-") is False
    assert is_viable_hospital_name("123456") is False
    assert is_viable_hospital_name("医生圈平台") is False
    assert is_viable_hospital_name("3C睡眠解决方案室") is False
    assert is_viable_hospital_name("健民珍所") is False


def test_prepare_hospital_name_candidates_filters_and_merges_dirty_values() -> None:
    hospital_names, summary = prepare_hospital_name_candidates(
        [
            "'河北医科大学第二医院",
            "河北医科大学第二医院",
            "-",
            "123456",
            "医生圈平台",
            "北京积水潭医院",
            "301医院",
        ],
        sample_limit=3,
    )

    assert hospital_names == [
        "北京积水潭医院",
        "河北医科大学第二医院",
        "301医院",
    ]
    assert summary["raw_count"] == 7
    assert summary["candidate_count"] == 3
    assert summary["filtered_count"] == 3
    assert summary["merged_count"] == 1
    assert summary["filtered_examples"] == [
        {"raw": "-", "normalized": ""},
        {"raw": "123456", "normalized": "123456"},
        {"raw": "医生圈平台", "normalized": "医生圈平台"},
    ]


def test_choose_best_hospital_match_accepts_exact_and_unique_suffix_match() -> None:
    page_data = [
        {
            "medinsCode": "1",
            "medinsName": "首都医科大学附属北京积水潭医院",
        },
        {
            "medinsCode": "2",
            "medinsName": "北京积水潭医院聊城医院",
        },
        {
            "medinsCode": "3",
            "medinsName": "山东大学齐鲁医院",
        },
    ]

    assert choose_best_hospital_match("北京积水潭医院", page_data) == page_data[0]
    assert choose_best_hospital_match("山东大学齐鲁医院", page_data) == page_data[2]
    assert choose_best_hospital_match("上海人民医院", page_data) is None


def test_choose_exact_hospital_match_ignores_partial_or_address_only_hits() -> None:
    page_data = [
        {
            "id": "1",
            "name": "北京市和平里医院",
            "address": "北京市东城区和平里街道北京市和平里医院",
        },
        {
            "id": "2",
            "name": "北京市第六医院",
            "address": "北京市东城区北新桥街道东直门内大街184号北京市第六医院(二部)",
        },
    ]

    assert choose_exact_hospital_match("北京市第六医院", page_data) == page_data[1]
    assert choose_exact_hospital_match("乌鲁木齐市友谊医院", page_data) is None


def test_build_hospital_base_item_marks_resolution_status() -> None:
    resolved = build_hospital_base_item(
        hospital_name="北京市第六医院",
        matched_record={
            "medinsCode": "H11010100001",
            "medinsName": "北京市第六医院",
            "addr": "北京市东城区东直门内大街184号",
            "medinsLvName": "二级",
            "medinsLv": "2",
            "medinsTypeName": "综合医院",
            "medinsType": "A100",
            "hospLv": "02",
            "uscc": "12110000400686291H",
            "lat": "39.1",
            "lnt": "116.4",
        },
    )
    unresolved = build_hospital_base_item(
        hospital_name="乌鲁木齐市友谊医院",
        matched_record=None,
    )

    assert resolved["_id"] == "H11010100001"
    assert resolved["query_hospital_name"] == "北京市第六医院"
    assert resolved["hospital_name"] == "北京市第六医院"
    assert resolved["hospital_address"] == "北京市东城区东直门内大街184号"
    assert resolved["hospital_level"] == "二级"
    assert resolved["hospital_type"] == "综合医院"
    assert resolved["website"] == "国家医保服务平台"
    assert sorted(resolved.keys()) == [
        "_id",
        "crawl_time",
        "hospital_address",
        "hospital_id",
        "hospital_level",
        "hospital_name",
        "hospital_type",
        "query_hospital_name",
        "resolved",
        "source_url",
        "uscc",
        "website",
    ]
    assert resolved["uscc"] == "12110000400686291H"
    assert resolved["resolved"] == "Y"
    assert unresolved["_id"] == "乌鲁木齐市友谊医院"
    assert unresolved["query_hospital_name"] == "乌鲁木齐市友谊医院"
    assert unresolved["hospital_name"] == "乌鲁木齐市友谊医院"
    assert unresolved["hospital_address"] == ""
    assert unresolved["website"] == "国家医保服务平台"
    assert unresolved["uscc"] == ""
    assert unresolved["resolved"] == "N"
