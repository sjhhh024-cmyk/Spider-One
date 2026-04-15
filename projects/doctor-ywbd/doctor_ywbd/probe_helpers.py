"""doctor-ywbd 页面解析辅助函数。"""

from __future__ import annotations

import json
import re
from urllib.parse import urlencode, urljoin, urlparse

from doctor_ywbd.route_hypotheses import BASE_URL, ENTRY_POINTS


KNOWNSEC_BLOCK_REASON_PATTERN = re.compile(r'"error_403_type"\s*:\s*"([^"]+)"')
HREF_PATTERN = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)
LIST_D_HREF_PATTERN = re.compile(r"""href=["']([^"']*/yisheng/list_d[^"']+\.html)["']""", re.IGNORECASE)
LIST_A_HREF_PATTERN = re.compile(r"""href=["']([^"']*/yisheng/list_a[^"']+\.html)["']""", re.IGNORECASE)
HOSPITAL_LIST_A_HREF_PATTERN = re.compile(r"""href=["']([^"']*/yiyuan/list_a[^"']+\.html)["']""", re.IGNORECASE)
HOSPITAL_EXPERT_AJAX_PATTERN = re.compile(
    r"""\$\.getJSON\(\s*['"]([^'"]*?/public/ajaxyisheng[^'"]*)['"]""",
    re.IGNORECASE,
)

DOCTOR_INFO_PATH_PATTERN = re.compile(
    r"^/yisheng/[a-z0-9]{16}\.html$",
    re.IGNORECASE,
)
DISEASE_LIST_PATH_PATTERN = re.compile(
    r"^/yisheng/(?:jibing(?:_p\d+)?|list_j[^/]+)\.html$",
    re.IGNORECASE,
)
DISEASE_INDEX_PATH_PATTERN = re.compile(r"^/yisheng/jibing(?:_p\d+)?\.html$", re.IGNORECASE)
DISEASE_DOCTOR_LIST_PAGE_PATTERN = re.compile(r"^/yisheng/list_j(?P<disease_id>\d+)(?:p\d+)?\.html$", re.IGNORECASE)
DISEASE_DOCTOR_FIRST_PAGE_PATTERN = re.compile(r"^/yisheng/list_j\d+\.html$", re.IGNORECASE)
DEPARTMENT_LIST_PATH_PATTERN = re.compile(r"^/yisheng/list_d[^/]+\.html$", re.IGNORECASE)
DEPARTMENT_FIRST_PAGE_PATTERN = re.compile(r"^/yisheng/list_d\d+\.html$", re.IGNORECASE)
AREA_LIST_PATH_PATTERN = re.compile(r"^/yisheng/list_a[^/]+\.html$", re.IGNORECASE)
AREA_FIRST_PAGE_PATTERN = re.compile(r"^/yisheng/list_a\d+\.html$", re.IGNORECASE)
HOSPITAL_LIST_PATH_PATTERN = re.compile(r"^/yiyuan/list_a[^/]+\.html$", re.IGNORECASE)
HOSPITAL_FIRST_PAGE_PATTERN = re.compile(r"^/yiyuan/list_a\d+\.html$", re.IGNORECASE)
HOSPITAL_DETAIL_PATH_PATTERN = re.compile(
    r"^/yiyuan/(?!area\.html$|jibing\.html$|keshi\.html$|list_|yisheng/|jieshao/|jibing/|ditu/)[^/]+\.html$",
    re.IGNORECASE,
)
HOSPITAL_EXPERT_PATH_PATTERN = re.compile(r"^/yiyuan/yisheng/[^/]+\.html$", re.IGNORECASE)
PAGE_COUNT_PATTERN = re.compile(r"共\s*(\d+)\s*页")
NAV_BOX_PATTERN = re.compile(
    r"""<div\s+class=["']nav-box["'][\s\S]*?<div\s+class=["']box["']>([\s\S]*?)</div>\s*</div>""",
    re.IGNORECASE,
)


def _iter_normalized_urls(base_url: str, html: str) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for raw_url in HREF_PATTERN.findall(html or ""):
        absolute_url = urljoin(base_url, raw_url)
        if not absolute_url.startswith(BASE_URL):
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        results.append(absolute_url)

    return results


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        results.append(url)

    return results


def _filter_urls(base_url: str, html: str, path_pattern: re.Pattern[str]) -> list[str]:
    results: list[str] = []

    for absolute_url in _iter_normalized_urls(base_url, html):
        if path_pattern.match(urlparse(absolute_url).path):
            results.append(absolute_url)

    return results


def _extract_page_count(html: str) -> int:
    match = PAGE_COUNT_PATTERN.search(html or "")
    return int(match.group(1)) if match else 1


def _build_disease_index_urls(page_count: int) -> list[str]:
    results = [f"{BASE_URL}/yisheng/jibing.html"]
    for page_number in range(2, page_count + 1):
        results.append(f"{BASE_URL}/yisheng/jibing_p{page_number}.html")
    return results


def _build_disease_doctor_list_urls(disease_id: str, page_count: int) -> list[str]:
    results = [f"{BASE_URL}/yisheng/list_j{disease_id}.html"]
    for page_number in range(2, page_count + 1):
        results.append(f"{BASE_URL}/yisheng/list_j{disease_id}p{page_number}.html")
    return results


def _build_paginated_urls(base_path: str, page_count: int) -> list[str]:
    absolute_base = urljoin(BASE_URL, base_path)
    results = [f"{absolute_base}.html"]
    for page_number in range(2, page_count + 1):
        results.append(f"{absolute_base}p{page_number}.html")
    return results


def _extract_active_attr(html: str, container_id: str, attribute_name: str, default: str = "0") -> str:
    pattern = re.compile(
        rf"""id=["']{re.escape(container_id)}["'][\s\S]*?<a[^>]*class=["'][^"']*\bon\b[^"']*["'][^>]*{re.escape(attribute_name)}=["']([^"']+)["']""",
        re.IGNORECASE,
    )
    match = pattern.search(html or "")
    return match.group(1).strip() if match else default


def _extract_js_var(html: str, variable_name: str, default: str = "") -> str:
    pattern = re.compile(
        rf"""var\s+{re.escape(variable_name)}\s*=\s*['"]?([^'";]+)['"]?\s*;""",
        re.IGNORECASE,
    )
    match = pattern.search(html or "")
    return match.group(1).strip() if match else default




def extract_knownsec_block_reason(html: str) -> str:
    """从拦截页 HTML 中提取知道创宇的封禁原因。"""

    match = KNOWNSEC_BLOCK_REASON_PATTERN.search(html or "")
    return match.group(1) if match else ""


def is_first_disease_index_page(url: str) -> bool:
    """判断是否为疾病索引第一页。"""

    return urlparse(url).path.lower() == "/yisheng/jibing.html"


def is_first_list_page(category: str, url: str) -> bool:
    """判断是否为某条列表链路的第一页。"""

    path = urlparse(url).path
    category_name = str(category).strip().lower()

    if category_name == "disease":
        return bool(DISEASE_DOCTOR_FIRST_PAGE_PATTERN.match(path))
    if category_name == "department":
        return bool(DEPARTMENT_FIRST_PAGE_PATTERN.match(path))
    if category_name == "area":
        return bool(AREA_FIRST_PAGE_PATTERN.match(path))
    if category_name == "hospital":
        return bool(HOSPITAL_FIRST_PAGE_PATTERN.match(path))
    raise ValueError(f"unsupported category: {category}")


def build_entry_seed_records() -> list[dict[str, str]]:
    """返回四条入口种子记录。"""

    return [{"category": category, "url": url} for category, url in ENTRY_POINTS.items()]


def build_next_disease_list_page_url(url: str) -> str:
    """构造疾病列表的顺序下一页 URL。"""

    match = re.match(r"^(https://data\.120ask\.com/yisheng/list_j\d+)(?:p(\d+))?\.html$", url, re.IGNORECASE)
    if not match:
        raise ValueError(f"unsupported disease list url: {url}")

    base = match.group(1)
    current_page = int(match.group(2) or "1")
    return f"{base}p{current_page + 1}.html"


def extract_department_seed_urls(base_url: str, html: str) -> list[str]:
    """从科室入口页提取叶子科室 URL。"""

    seen: set[str] = set()
    results: list[str] = []

    for block in NAV_BOX_PATTERN.findall(html or ""):
        block_urls = []
        for raw_url in LIST_D_HREF_PATTERN.findall(block):
            absolute_url = urljoin(base_url, raw_url)
            if absolute_url not in block_urls:
                block_urls.append(absolute_url)

        if not block_urls:
            continue

        leaf_urls = block_urls[1:] if len(block_urls) > 1 else block_urls
        for url in leaf_urls:
            if url in seen:
                continue
            seen.add(url)
            results.append(url)

    return results


def extract_area_seed_urls(base_url: str, html: str) -> list[str]:
    """从地区入口页提取区县级叶子地区 URL。"""

    seen: set[str] = set()
    results: list[str] = []

    for raw_url in LIST_A_HREF_PATTERN.findall(html or ""):
        absolute_url = urljoin(base_url, raw_url)
        path = urlparse(absolute_url).path
        match = re.match(r"^/yisheng/list_a(\d{6})\.html$", path, re.IGNORECASE)
        if not match:
            continue
        area_code = match.group(1)
        if area_code.endswith("00"):
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        results.append(absolute_url)

    return results


def extract_hospital_area_seed_urls(base_url: str, html: str) -> list[str]:
    """从医院地区入口页提取区县级叶子地区 URL。"""

    seen: set[str] = set()
    results: list[str] = []

    for raw_url in HOSPITAL_LIST_A_HREF_PATTERN.findall(html or ""):
        absolute_url = urljoin(base_url, raw_url)
        path = urlparse(absolute_url).path
        match = re.match(r"^/yiyuan/list_a(\d{6})\.html$", path, re.IGNORECASE)
        if not match:
            continue
        area_code = match.group(1)
        if area_code.endswith("00"):
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        results.append(absolute_url)

    return results


def extract_list_urls(category: str, base_url: str, html: str) -> list[str]:
    """按入口分类提取上游列表页。"""

    category_name = str(category).strip().lower()
    if category_name == "disease":
        base_path = urlparse(base_url).path
        if DISEASE_INDEX_PATH_PATTERN.match(base_path):
            page_count = _extract_page_count(html)
            index_urls = _build_disease_index_urls(page_count)
            disease_first_page_urls = _filter_urls(base_url, html, DISEASE_DOCTOR_FIRST_PAGE_PATTERN)
            return _dedupe_urls(index_urls + disease_first_page_urls)

        disease_match = DISEASE_DOCTOR_LIST_PAGE_PATTERN.match(base_path)
        if disease_match:
            disease_id = disease_match.group("disease_id")
            page_count = _extract_page_count(html)
            if page_count > 1:
                return _build_disease_doctor_list_urls(disease_id, page_count)

            same_disease_pattern = re.compile(
                rf"^/yisheng/list_j{re.escape(disease_id)}(?:p\d+)?\.html$",
                re.IGNORECASE,
            )
            return _filter_urls(base_url, html, same_disease_pattern)

        return _filter_urls(base_url, html, DISEASE_LIST_PATH_PATTERN)
    if category_name == "department":
        base_path = urlparse(base_url).path
        if base_path == "/yisheng/keshi.html":
            return _filter_urls(base_url, html, DEPARTMENT_LIST_PATH_PATTERN)

        department_match = re.match(r"^/yisheng/list_d(?P<department_id>\d+)(?:p\d+)?\.html$", base_path, re.IGNORECASE)
        if department_match:
            department_id = department_match.group("department_id")
            page_count = _extract_page_count(html)
            if page_count > 1:
                return _build_paginated_urls(f"/yisheng/list_d{department_id}", page_count)

            same_department_pattern = re.compile(
                rf"^/yisheng/list_d{re.escape(department_id)}(?:p\d+)?\.html$",
                re.IGNORECASE,
            )
            return _filter_urls(base_url, html, same_department_pattern)

        return _filter_urls(base_url, html, DEPARTMENT_LIST_PATH_PATTERN)
    if category_name == "area":
        base_path = urlparse(base_url).path
        if base_path == "/yisheng/area.html":
            return _filter_urls(base_url, html, AREA_LIST_PATH_PATTERN)

        area_match = re.match(r"^/yisheng/list_a(?P<area_id>\d+)(?:p\d+)?\.html$", base_path, re.IGNORECASE)
        if area_match:
            area_id = area_match.group("area_id")
            page_count = _extract_page_count(html)
            if page_count > 1:
                return _build_paginated_urls(f"/yisheng/list_a{area_id}", page_count)

            same_area_pattern = re.compile(
                rf"^/yisheng/list_a{re.escape(area_id)}(?:p\d+)?\.html$",
                re.IGNORECASE,
            )
            return _filter_urls(base_url, html, same_area_pattern)

        return _filter_urls(base_url, html, AREA_LIST_PATH_PATTERN)
    raise ValueError(f"unsupported category: {category}")


def extract_hospital_list_urls(base_url: str, html: str) -> list[str]:
    """提取医院入口链路上的列表页、医院详情页和专家页。"""

    seen: set[str] = set()
    results: list[str] = []
    base_path = urlparse(base_url).path

    if base_path == "/yiyuan/area.html":
        patterns = (
            HOSPITAL_LIST_PATH_PATTERN,
            HOSPITAL_DETAIL_PATH_PATTERN,
            HOSPITAL_EXPERT_PATH_PATTERN,
        )
    else:
        area_match = re.match(r"^/yiyuan/list_a(?P<area_id>\d+)(?:p\d+)?\.html$", base_path, re.IGNORECASE)
        if area_match:
            area_id = area_match.group("area_id")
            page_count = _extract_page_count(html)
            if page_count > 1:
                for url in _build_paginated_urls(f"/yiyuan/list_a{area_id}", page_count):
                    if url in seen:
                        continue
                    seen.add(url)
                    results.append(url)
                patterns = (
                    HOSPITAL_DETAIL_PATH_PATTERN,
                    HOSPITAL_EXPERT_PATH_PATTERN,
                )
            else:
                same_area_pattern = re.compile(
                    rf"^/yiyuan/list_a{re.escape(area_id)}(?:p\d+)?\.html$",
                    re.IGNORECASE,
                )
                patterns = (
                    same_area_pattern,
                    HOSPITAL_DETAIL_PATH_PATTERN,
                    HOSPITAL_EXPERT_PATH_PATTERN,
                )
        else:
            patterns = (
                HOSPITAL_LIST_PATH_PATTERN,
                HOSPITAL_DETAIL_PATH_PATTERN,
                HOSPITAL_EXPERT_PATH_PATTERN,
            )

    for pattern in patterns:
        for url in _filter_urls(base_url, html, pattern):
            if url in seen:
                continue
            seen.add(url)
            results.append(url)

    return results


def extract_doctor_info_urls(base_url: str, html: str) -> list[str]:
    """提取最终医生详情链接。"""

    return _filter_urls(base_url, html, DOCTOR_INFO_PATH_PATTERN)


def extract_hospital_expert_ajax_context(page_url: str, html: str) -> dict[str, str | int]:
    """从医院专家页提取 ajax 接口和默认参数。"""

    ajax_match = HOSPITAL_EXPERT_AJAX_PATTERN.search(html or "")
    ajax_url = urljoin(page_url, ajax_match.group(1)) if ajax_match else urljoin(page_url, "/public/ajaxyisheng")
    page_count_match = PAGE_COUNT_PATTERN.search(html or "")

    return {
        "ajax_url": ajax_url,
        "hid": _extract_js_var(html, "hid", "0"),
        "kid": _extract_js_var(html, "kid", "0"),
        "limit": _extract_js_var(html, "limit", "8"),
        "did": _extract_active_attr(html, "depart_list", "depart-id"),
        "zid": _extract_active_attr(html, "doctor_title", "doctor-title"),
        "sid": _extract_active_attr(html, "chuzheng_time", "apm-id"),
        "wid": _extract_active_attr(html, "chuzheng_time", "week-id"),
        "tid": _extract_active_attr(html, "chuzheng_type", "chuzheng-type"),
        "page_count": int(page_count_match.group(1)) if page_count_match else 1,
    }


def extract_hospital_expert_doctor_urls(payload: str) -> list[str]:
    """从 /public/ajaxyisheng 响应体提取医生详情链接。"""

    try:
        data = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return []
    candidates = data.get("rsList") or data.get("tjList") or []
    seen: set[str] = set()
    results: list[str] = []

    for record in candidates:
        raw_url = str(record.get("url", "")).strip()
        if not raw_url:
            continue
        absolute_url = urljoin(BASE_URL, raw_url)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        results.append(absolute_url)

    return results


def build_hospital_expert_ajax_request_specs(
    *,
    source_url: str,
    ajax_context: dict[str, str | int],
    cookiejar_id: str | int,
) -> list[dict[str, object]]:
    """根据专家页上下文生成 ajax 分页请求规格。"""

    results: list[dict[str, object]] = []
    page_count = int(ajax_context["page_count"])

    for page_number in range(2, page_count + 1):
        params = {
            "hid": str(ajax_context["hid"]),
            "pid": str(page_number),
            "did": str(ajax_context["did"]),
            "zid": str(ajax_context["zid"]),
            "sid": str(ajax_context["sid"]),
            "wid": str(ajax_context["wid"]),
            "tid": str(ajax_context["tid"]),
            "kid": str(ajax_context["kid"]),
            "limit": str(ajax_context["limit"]),
        }
        results.append(
            {
                "url": f"{ajax_context['ajax_url']}?{urlencode(params)}",
                "page_number": page_number,
                "headers": {
                    "Referer": source_url,
                    "X-Requested-With": "XMLHttpRequest",
                },
                "meta": {
                    "cookiejar": cookiejar_id,
                },
            }
        )

    return results
