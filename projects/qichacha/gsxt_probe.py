from __future__ import annotations

import re


WAF_EVENT_RE = re.compile(r'<span id="wafId">([^<]+)</span>', re.IGNORECASE)


def classify_gsxt_response(status_code: int, html: str) -> str:
    lowered = html.lower()
    if "__jsl_clearance_s" in html and "location.href" in html:
        return "jsl_challenge"
    if status_code == 521 and "document.cookie" in html and "location.href" in html:
        return "jsl_challenge"
    if status_code == 412 and "environment checking" in lowered:
        return "environment_check"
    if "nwaf页面" in html or 'id="wafId"' in html:
        return "waf_block"
    if status_code == 200:
        return "ok"
    return "unknown"


def extract_waf_event_id(html: str) -> str | None:
    match = WAF_EVENT_RE.search(html)
    if not match:
        return None
    return match.group(1).strip()
