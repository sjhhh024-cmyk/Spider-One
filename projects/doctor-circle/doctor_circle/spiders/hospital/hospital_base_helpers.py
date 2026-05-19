"""医院基础信息补全辅助函数。"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import uuid
from collections.abc import Iterable
from time import gmtime, strftime

from gmssl import sm2, sm4


EDGE_NOISE_CHARS = "'\"`,，。.;；:：、/\\|+-_!！?？*"
DECORATIVE_CHARS = "✔️✓✘✖★☆"
PLACEHOLDER_HOSPITAL_NAMES = {
    "医生圈平台",
}
MEDICAL_INSTITUTION_KEYWORDS = (
    "医院",
    "总医院",
    "中医院",
    "妇幼保健院",
    "儿童医院",
    "人民医院",
    "社区卫生服务中心",
    "社区卫生服务站",
    "卫生服务中心",
    "卫生服务站",
    "卫生院",
    "卫生室",
    "卫生所",
    "门诊部",
    "门诊",
    "诊所",
    "医疗中心",
    "医学中心",
    "康复医院",
    "康复中心",
    "疗养院",
    "医务室",
    "分院",
    "院区",
    "附属医院",
    "附院",
)
WORD_PATTERN = re.compile(r"[A-Za-z\u4e00-\u9fff]")
SYMBOL_ONLY_PATTERN = re.compile(r"[^A-Za-z\u4e00-\u9fff]+")
MATCH_NAME_PATTERN = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")
NHSA_APP_VERSION = "1.0.0"
NHSA_ENCRYPT_TYPE = "SM4"
NHSA_SIGN_TYPE = "SM2"
NHSA_SOURCE_URL = "https://fuwu.nhsa.gov.cn/nationalHallSt/#/search/medical"


def normalize_hospital_name(hospital_name: str) -> str:
    """归一化医院名，清理首尾空白和常见脏字符。"""

    normalized_name = (hospital_name or "").strip()
    previous_name = None
    while normalized_name != previous_name:
        previous_name = normalized_name
        normalized_name = normalized_name.strip(EDGE_NOISE_CHARS).strip()
        normalized_name = normalized_name.strip(DECORATIVE_CHARS).strip()

    return re.sub(r"\s+", " ", normalized_name)


def is_viable_hospital_name(hospital_name: str) -> bool:
    """判断医院名是否值得调用公开医院基础接口查询。"""

    normalized_name = normalize_hospital_name(hospital_name)
    if not normalized_name or len(normalized_name) < 2:
        return False
    if normalized_name in PLACEHOLDER_HOSPITAL_NAMES:
        return False
    if normalized_name.isdigit():
        return False
    if not WORD_PATTERN.search(normalized_name):
        return False
    if SYMBOL_ONLY_PATTERN.fullmatch(normalized_name):
        return False
    if any(character in normalized_name for character in DECORATIVE_CHARS):
        return False

    return any(keyword in normalized_name for keyword in MEDICAL_INSTITUTION_KEYWORDS)


def hospital_name_sort_key(hospital_name: str) -> tuple[bool, bool, str]:
    """优先把常规中文医院名排在前面，便于运行时观察日志。"""

    first_character = hospital_name[:1]
    starts_with_chinese = bool(re.match(r"^[\u4e00-\u9fff]$", first_character))
    starts_with_digit = first_character.isdigit()
    return starts_with_digit, not starts_with_chinese, hospital_name


def prepare_hospital_name_candidates(
    raw_hospital_names: Iterable[object],
    *,
    sample_limit: int = 20,
) -> tuple[list[str], dict[str, object]]:
    """清洗并过滤医院名，返回可查询候选和统计信息。"""

    candidate_names: set[str] = set()
    filtered_examples: list[dict[str, str]] = []
    raw_count = 0
    filtered_count = 0
    merged_count = 0

    for raw_name in raw_hospital_names:
        raw_count += 1
        raw_text = str(raw_name)
        normalized_name = normalize_hospital_name(raw_text)

        if not is_viable_hospital_name(normalized_name):
            filtered_count += 1
            if len(filtered_examples) < sample_limit:
                filtered_examples.append(
                    {
                        "raw": raw_text,
                        "normalized": normalized_name,
                    }
                )
            continue

        if normalized_name in candidate_names:
            merged_count += 1
            continue
        candidate_names.add(normalized_name)

    sorted_candidates = sorted(candidate_names, key=hospital_name_sort_key)
    summary = {
        "raw_count": raw_count,
        "candidate_count": len(sorted_candidates),
        "filtered_count": filtered_count,
        "merged_count": merged_count,
        "filtered_examples": filtered_examples,
    }
    return sorted_candidates, summary


def normalize_hospital_match_name(hospital_name: str) -> str:
    """把医院名归一化成更适合做匹配判断的字符串。"""

    normalized_name = normalize_hospital_name(hospital_name)
    return MATCH_NAME_PATTERN.sub("", normalized_name)


def build_nhsa_hospital_search_payload(
    hospital_name: str,
    *,
    regn_code: str = "",
    page_num: int = 1,
    page_size: int = 10,
) -> dict[str, object]:
    """构造国家医保服务平台的医院检索请求体。"""

    return {
        "addr": "",
        "regnCode": regn_code,
        "medinsName": normalize_hospital_name(hospital_name),
        "medinsLvCode": "",
        "medinsTypeCode": "",
        "outMedOpenFlag": "",
        "pageNum": page_num,
        "pageSize": page_size,
        "queryDataSource": "es",
    }


def _sort_mapping(mapping: dict[str, object]) -> dict[str, object]:
    return {key: mapping[key] for key in sorted(mapping)}


def _js_unicode_escape(text: str) -> str:
    return "".join(
        f"\\u{ord(character):04x}" if ord(character) > 127 else character
        for character in text
    )


def _sm4_encrypt_hex(key_bytes: bytes, plain_text: str) -> str:
    crypt = sm4.CryptSM4()
    crypt.set_key(key_bytes, sm4.SM4_ENCRYPT)
    return crypt.crypt_ecb(plain_text.encode("utf-8")).hex()


def derive_nhsa_sm4_key(app_code: str, app_secret: str) -> bytes:
    """按前端同样的规则派生医保平台请求用的 SM4 key。"""

    encrypted_secret = _sm4_encrypt_hex(app_code[:16].encode("utf-8"), app_secret).upper()
    return encrypted_secret[:16].encode("utf-8")


def _canonicalize_nhsa_sign_data(payload: dict[str, object], app_secret: str) -> str:
    parts: list[str] = []
    for key, value in payload.items():
        if key == "data":
            nested = dict(value)
            for nested_key in list(nested):
                nested_value = nested[nested_key]
                if isinstance(nested_value, bool):
                    nested[nested_key] = "true" if nested_value else "false"
                elif isinstance(nested_value, (int, float)):
                    nested[nested_key] = str(nested_value)
                elif isinstance(nested_value, list):
                    if not nested_value:
                        del nested[nested_key]
                        continue
                    nested[nested_key] = [
                        _sort_mapping(item) if isinstance(item, dict) else item
                        for item in nested_value
                    ]

                if nested_key in nested and not nested[nested_key]:
                    del nested[nested_key]

            parts.append(
                "data="
                + json.dumps(
                    _sort_mapping(nested),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            continue

        if value or f"{value}":
            parts.append(f"{key}={value}")

    parts.append(f"key={app_secret}")
    return "&".join(parts)


def build_nhsa_signed_request(
    *,
    app_code: str,
    app_secret: str,
    public_key_base64: str,
    private_key_base64: str,
    payload: dict[str, object],
    timestamp: int | None = None,
    nonce: str | None = None,
) -> tuple[dict[str, str], dict[str, object]]:
    """构造国家医保服务平台接口所需的签名请求头和请求体。"""

    request_timestamp = int(timestamp or time.time())
    request_nonce = nonce or uuid.uuid4().hex
    public_key = base64.b64decode(public_key_base64).hex()[2:]
    private_key = base64.b64decode(private_key_base64).hex()[2:]

    sign_payload = _sort_mapping(
        {
            "appCode": app_code,
            "data": payload,
            "encType": NHSA_ENCRYPT_TYPE,
            "signType": NHSA_SIGN_TYPE,
            "timestamp": request_timestamp,
            "version": NHSA_APP_VERSION,
        }
    )
    sign_text = _canonicalize_nhsa_sign_data(sign_payload, app_secret)
    crypt_sm2 = sm2.CryptSM2(public_key=public_key, private_key=private_key, asn1=False)
    sign_data_hex = crypt_sm2.sign_with_sm3(sign_text.encode("utf-8"))

    encrypted_payload = _sm4_encrypt_hex(
        derive_nhsa_sm4_key(app_code, app_secret),
        _js_unicode_escape(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
    ).upper()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "contentType": "application/x-www-form-urlencoded",
        "channel": "web",
        "x-tif-paasid": "",
        "x-tif-signature": hashlib.sha256(
            f"{request_timestamp}{request_nonce}{request_timestamp}".encode("utf-8")
        ).hexdigest(),
        "x-tif-timestamp": str(request_timestamp),
        "x-tif-nonce": request_nonce,
        "Origin": "https://fuwu.nhsa.gov.cn",
        "Referer": NHSA_SOURCE_URL,
    }
    body = {
        "data": {
            "data": {"encData": encrypted_payload},
            "appCode": app_code,
            "version": NHSA_APP_VERSION,
            "encType": NHSA_ENCRYPT_TYPE,
            "signType": NHSA_SIGN_TYPE,
            "timestamp": request_timestamp,
            "signData": base64.b64encode(bytes.fromhex(sign_data_hex)).decode("utf-8"),
        }
    }
    return headers, body


def decrypt_nhsa_response_data(
    app_code: str,
    app_secret: str,
    response_json: dict[str, object],
) -> dict[str, object]:
    """解密国家医保服务平台响应里的 encData。"""

    encrypted_data = (
        response_json.get("data", {})
        .get("data", {})
        .get("encData", "")
    )
    if not encrypted_data:
        return {}

    crypt = sm4.CryptSM4()
    crypt.set_key(derive_nhsa_sm4_key(app_code, app_secret), sm4.SM4_DECRYPT)
    decrypted_text = crypt.crypt_ecb(bytes.fromhex(str(encrypted_data))).decode("utf-8")
    return json.loads(decrypted_text)


def choose_best_hospital_match(
    hospital_name: str,
    page_data: list[dict[str, object]],
) -> dict[str, object] | None:
    """优先精确同名，其次接受唯一的“前缀挂靠但尾部同名”命中。"""

    normalized_query = normalize_hospital_match_name(hospital_name)
    exact_matches: list[dict[str, object]] = []
    suffix_matches: list[dict[str, object]] = []

    for record in page_data:
        record_name = normalize_hospital_match_name(str(record.get("medinsName", "")))
        if not record_name:
            continue
        if record_name == normalized_query:
            exact_matches.append(record)
            continue
        if normalized_query and record_name.endswith(normalized_query):
            suffix_matches.append(record)

    if exact_matches:
        return exact_matches[0]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def build_hospital_search_payload(
    access_token: str,
    hospital_name: str,
    *,
    page_index: int = 0,
    page_size: int = 20,
) -> dict[str, object]:
    """按已验证参数构造医院搜索请求体。"""

    return {
        "access_token": access_token,
        "pageIndex": page_index,
        "pageSize": page_size,
        "keyWord": normalize_hospital_name(hospital_name),
    }


def choose_exact_hospital_match(
    hospital_name: str,
    page_data: list[dict[str, object]],
) -> dict[str, object] | None:
    """只接受与医院名完全一致的命中，避免误匹配。"""

    target_name = normalize_hospital_name(hospital_name)
    for record in page_data:
        record_name = normalize_hospital_name(str(record.get("name", "")))
        if record_name == target_name:
            return record
    return None


def build_hospital_base_item(
    hospital_name: str,
    matched_record: dict[str, object] | None,
) -> dict[str, object]:
    """把国家医保服务平台结果整理成医院基础信息文档。"""

    normalized_name = normalize_hospital_name(hospital_name)
    crawl_time = strftime("%Y-%m-%d", gmtime())

    if not matched_record:
        return {
            "_id": normalized_name,
            "query_hospital_name": normalized_name,
            "hospital_name": normalized_name,
            "hospital_id": "",
            "hospital_address": "",
            "hospital_level": "",
            "hospital_type": "",
            "resolved": "N",
            "website": "国家医保服务平台",
            "source_url": NHSA_SOURCE_URL,
            "crawl_time": crawl_time,
            "uscc": "",
        }

    hospital_id = str(matched_record.get("medinsCode", "")).strip()
    medins_type_name = str(matched_record.get("medinsTypeName", "")).strip()
    medins_level_name = str(matched_record.get("medinsLvName", "")).strip()
    return {
        "_id": hospital_id if hospital_id else normalized_name,
        "query_hospital_name": normalized_name,
        "hospital_name": normalize_hospital_name(
            str(matched_record.get("medinsName", normalized_name))
        ),
        "hospital_id": hospital_id,
        "hospital_address": str(matched_record.get("addr", "")).strip(),
        "hospital_level": medins_level_name,
        "hospital_type": medins_type_name,
        "resolved": "Y",
        "website": "国家医保服务平台",
        "source_url": NHSA_SOURCE_URL,
        "crawl_time": crawl_time,
        "uscc": str(matched_record.get("uscc", "")).strip(),
    }
