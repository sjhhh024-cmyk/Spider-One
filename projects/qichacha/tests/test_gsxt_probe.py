from __future__ import annotations

from gsxt_probe import extract_waf_event_id, classify_gsxt_response


JSL_CHALLENGE_HTML = """
<script>
document.cookie=('__jsl_clearance_s=abc123');location.href=location.pathname+location.search
</script>
"""


OBFUSCATED_JSL_CHALLENGE_HTML = """
<script>
document.cookie=('__')+('jsl')+('_')+('clearance')+('_')+('s')+('=' )+('abc123');window.location.href=window.location.pathname+window.location.search
</script>
"""


ENV_CHECKING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head><title>Environment Checking</title></head>
<body></body>
</html>
"""


WAF_BLOCK_HTML = """
<html>
<head><title>NWAF页面</title></head>
<body>
事件ID :<span id="wafId">1777533880207100000837356733450555</span>
</body>
</html>
"""


def test_classify_jsl_challenge_response() -> None:
    assert classify_gsxt_response(status_code=521, html=JSL_CHALLENGE_HTML) == "jsl_challenge"


def test_classify_obfuscated_jsl_challenge_response() -> None:
    assert classify_gsxt_response(status_code=521, html=OBFUSCATED_JSL_CHALLENGE_HTML) == "jsl_challenge"


def test_classify_environment_check_response() -> None:
    assert classify_gsxt_response(status_code=412, html=ENV_CHECKING_HTML) == "environment_check"


def test_classify_waf_block_response() -> None:
    assert classify_gsxt_response(status_code=405, html=WAF_BLOCK_HTML) == "waf_block"


def test_extract_waf_event_id() -> None:
    assert extract_waf_event_id(WAF_BLOCK_HTML) == "1777533880207100000837356733450555"
