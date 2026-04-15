"""知道创宇 JS 解盾备份代码，不参与当前运行时。"""

from __future__ import annotations

import hashlib
import json
import re

try:
    import quickjs
except ImportError:  # pragma: no cover - 备份模块，不作为主流程依赖
    quickjs = None


SCRIPT_BODY_PATTERN = re.compile(r"<script>([\s\S]*?)</script>", re.IGNORECASE)
GO_CHALLENGE_PATTERN = re.compile(r"go\((\{.*?\})\)</script>", re.IGNORECASE | re.DOTALL)
COOKIE_ASSIGNMENT_PATTERN = re.compile(
    r"document\.cookie\s*=\s*(.*?)(?:;location(?:\.href)?=|;</script>)",
    re.IGNORECASE | re.DOTALL,
)


def extract_script_body(html: str) -> str:
    """提取拦截页中的 script 内容。"""

    match = SCRIPT_BODY_PATTERN.search(html or "")
    return match.group(1) if match else (html or "")


def solve_cookie_assignment_script(html: str, *, location_path: str) -> tuple[str, int]:
    """执行 document.cookie 型 challenge，返回完整 cookie 字符串。"""

    match = COOKIE_ASSIGNMENT_PATTERN.search(html or "")
    if not match:
        return "", 0
    if quickjs is None:
        raise RuntimeError("quickjs 不可用，无法解析 document.cookie 型 challenge。")

    script_body = extract_script_body(html)
    js_context = quickjs.Context()
    bootstrap = (
        "var __cookie='';"
        "var document={};"
        "Object.defineProperty(document,'cookie',{"
        "get:function(){return __cookie;},"
        "set:function(v){__cookie=v;}"
        "});"
        f"var location={{pathname:{json.dumps(location_path)},search:'',href:''}};"
    )
    js_context.eval(bootstrap + script_body)
    cookie_string = str(js_context.eval("__cookie")).strip()
    return cookie_string, 0


def solve_go_challenge(html: str) -> tuple[str, int]:
    """解析 go({...}) 型 challenge，返回完整 cookie 字符串。"""

    match = GO_CHALLENGE_PATTERN.search(html or "")
    if not match:
        return "", 0

    challenge_data = json.loads(match.group(1))
    chars = str(challenge_data["chars"])
    prefix, suffix = challenge_data["bts"]
    expected_hash = str(challenge_data["ct"]).strip().lower()
    hash_name = str(challenge_data.get("ha", "md5")).strip().lower() or "md5"

    for first_char in chars:
        for second_char in chars:
            candidate = f"{prefix}{first_char}{second_char}{suffix}"
            try:
                hashed_candidate = hashlib.new(hash_name, candidate.encode("utf-8")).hexdigest()
            except ValueError:
                return "", 0
            if hashed_candidate == expected_hash:
                cookie_name = str(challenge_data.get("tn", "__jsl_clearance_s")).strip()
                max_age = str(challenge_data.get("vt", "3600")).strip() or "3600"
                wait_ms = int(str(challenge_data.get("wt", "0")).strip() or "0")
                cookie_string = (
                    f"{cookie_name}={candidate}; Max-age={max_age}; Path=/; SameSite=None; Secure"
                )
                return cookie_string, wait_ms

    return "", 0
