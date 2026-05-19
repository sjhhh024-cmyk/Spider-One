# Jianzhi Jinan Public Resources Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `projects/jianzhi` 下创建一个可复现的济南公共资源交易网公告采集项目，先覆盖已确认的 `政府采购 -> 招标公告` 主链路，并支持列表翻页、详情解析、控制台日志和可配置输出。

**Architecture:** 采用单机脚本结构，优先走稳定的请求重放：列表首屏读取 `front/noticelist.do`，后续翻页走 `front/search.do`，详情读取 `front/showNotice.do`。项目保持“读配置 -> 拉列表 -> 解析列表 -> 拉详情 -> 解析字段 -> 输出结果”的直线流程，并把解析逻辑拆成纯函数，方便测试。

**Tech Stack:** Python 3.12, requests, BeautifulSoup4, PyYAML, pytest

---

### Task 1: 搭项目骨架和红灯测试

**Files:**
- Create: `projects/jianzhi/README.md`
- Create: `projects/jianzhi/profile.example.yml`
- Create: `projects/jianzhi/jianzhi_start.py`
- Create: `projects/jianzhi/start.ps1`
- Create: `projects/jianzhi/tests/test_jianzhi_parser.py`
- Create: `projects/jianzhi/tests/test_jianzhi_flow.py`

**Step 1: Write the failing test**

```python
def test_parse_search_response_extracts_notice_cards() -> None:
    payload = {
        "success": True,
        "params": {
            "str": (
                "<ul class='list'>"
                "<li><span class='span1'>[代理机构]</span>"
                "<a onclick=\"showview('ABC123',1,'招标公告')\" "
                "title='测试公告标题'>测试公告标题</a>"
                "<span class='span2'>2026-05-06</span></li>"
                "</ul>"
            ),
            "pagenum": "2",
            "pagesum": 3745,
        },
    }

    records = parse_search_response(payload, source_url="https://example.com/search.do")

    assert records == [
        {
            "notice_id": "ABC123",
            "is_new": 1,
            "notice_type": "招标公告",
            "title": "测试公告标题",
            "publish_date": "2026-05-06",
            "trading_place": "代理机构",
            "source_url": "https://example.com/search.do",
        }
    ]
```

**Step 2: Run test to verify it fails**

Run: `pytest projects/jianzhi/tests/test_jianzhi_parser.py::test_parse_search_response_extracts_notice_cards -v`
Expected: FAIL with `ImportError` or `NameError`

**Step 3: Write minimal implementation**

```python
def parse_search_response(payload: dict[str, Any], source_url: str) -> list[dict[str, Any]]:
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest projects/jianzhi/tests/test_jianzhi_parser.py::test_parse_search_response_extracts_notice_cards -v`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/plans/2026-05-07-jianzhi-jinan-public-resources-implementation-plan.md projects/jianzhi
git commit -m "feat: scaffold jianzhi parser tests"
```

### Task 2: 补详情页解析测试和实现

**Files:**
- Modify: `projects/jianzhi/tests/test_jianzhi_parser.py`
- Modify: `projects/jianzhi/jianzhi_start.py`

**Step 1: Write the failing test**

```python
def test_parse_notice_detail_extracts_core_fields() -> None:
    html = """
    <div class="list">
      <h1>测试公告</h1>
      <div class="infor">
        <span>公共资源交易编号：2025CGFW01C5490</span>
        <span> 发布日期：2025-11-17</span>
      </div>
      <div class="WordSection1">
        <p class="details_p"><span class="l_span">项目编号（建议书编号）：</span><span class="r_span">SDGP001</span></p>
        <p class="details_p"><span class="l_span">项目名称：</span><span class="r_span">举报辟谣网上宣传推广项目</span></p>
        <p class="details_p"><span class="l_span">采购方式：</span><span class="r_span">竞争性磋商</span></p>
      </div>
    </div>
    """

    detail = parse_notice_detail(
        html=html,
        detail_url="https://example.com/showNotice.do?iid=ABC123",
    )

    assert detail["title"] == "测试公告"
    assert detail["public_resource_code"] == "2025CGFW01C5490"
    assert detail["publish_date"] == "2025-11-17"
    assert detail["project_number"] == "SDGP001"
    assert detail["project_name"] == "举报辟谣网上宣传推广项目"
    assert detail["procurement_method"] == "竞争性磋商"
```

**Step 2: Run test to verify it fails**

Run: `pytest projects/jianzhi/tests/test_jianzhi_parser.py::test_parse_notice_detail_extracts_core_fields -v`
Expected: FAIL because parser does not yet extract fields

**Step 3: Write minimal implementation**

```python
def parse_notice_detail(html: str, detail_url: str) -> dict[str, Any]:
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest projects/jianzhi/tests/test_jianzhi_parser.py::test_parse_notice_detail_extracts_core_fields -v`
Expected: PASS

**Step 5: Commit**

```bash
git add projects/jianzhi/tests/test_jianzhi_parser.py projects/jianzhi/jianzhi_start.py
git commit -m "feat: add jianzhi detail parser"
```

### Task 3: 补流程测试和采集主流程

**Files:**
- Modify: `projects/jianzhi/tests/test_jianzhi_flow.py`
- Modify: `projects/jianzhi/jianzhi_start.py`
- Modify: `projects/jianzhi/profile.example.yml`

**Step 1: Write the failing test**

```python
def test_spider_runs_one_page_and_one_detail() -> None:
    profile = build_test_profile()
    spider = JinanPublicResourcesSpider(profile, session=FakeSession(...))

    result = spider.run()

    assert result["list_page_count"] == 1
    assert result["detail_success_count"] == 1
    assert result["record_count"] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest projects/jianzhi/tests/test_jianzhi_flow.py::test_spider_runs_one_page_and_one_detail -v`
Expected: FAIL because the run loop is incomplete

**Step 3: Write minimal implementation**

```python
class JinanPublicResourcesSpider:
    def run(self) -> dict[str, Any]:
        ...
```

**Step 4: Run test to verify it passes**

Run: `pytest projects/jianzhi/tests/test_jianzhi_flow.py::test_spider_runs_one_page_and_one_detail -v`
Expected: PASS

**Step 5: Commit**

```bash
git add projects/jianzhi/tests/test_jianzhi_flow.py projects/jianzhi/jianzhi_start.py projects/jianzhi/profile.example.yml
git commit -m "feat: add jianzhi crawl flow"
```

### Task 4: 补文档、启动入口和人工可读日志

**Files:**
- Modify: `projects/jianzhi/README.md`
- Modify: `projects/jianzhi/start.ps1`
- Modify: `projects/jianzhi/jianzhi_start.py`

**Step 1: Write the failing test**

```python
def test_build_detail_url_supports_notice_id_and_type() -> None:
    url = build_detail_url("ABC123", "招标公告", 1)
    assert "showNotice.do" in url
    assert "iid=ABC123" in url
    assert "isnew=1" in url
```

**Step 2: Run test to verify it fails**

Run: `pytest projects/jianzhi/tests/test_jianzhi_parser.py::test_build_detail_url_supports_notice_id_and_type -v`
Expected: FAIL because helper is missing or incorrect

**Step 3: Write minimal implementation**

```python
def build_detail_url(notice_id: str, notice_type: str, is_new: int) -> str:
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest projects/jianzhi/tests/test_jianzhi_parser.py::test_build_detail_url_supports_notice_id_and_type -v`
Expected: PASS

**Step 5: Commit**

```bash
git add projects/jianzhi/README.md projects/jianzhi/start.ps1 projects/jianzhi/jianzhi_start.py
git commit -m "feat: document jianzhi runner"
```

### Task 5: 全量验证

**Files:**
- Verify only

**Step 1: Run focused tests**

Run: `pytest projects/jianzhi/tests -v`
Expected: all tests pass

**Step 2: Run syntax verification**

Run: `python -m py_compile projects/jianzhi/jianzhi_start.py`
Expected: no output

**Step 3: Smoke-check CLI help**

Run: `python projects/jianzhi/jianzhi_start.py --help`
Expected: show CLI help and exit 0

**Step 4: Review README and profile template**

Confirm:
- 配置项和代码一致
- 已记录确认过的站点链路
- 明确说明腾讯文档正文尚未自动接入，字段可继续扩展

**Step 5: Commit**

```bash
git add projects/jianzhi
git commit -m "feat: initialize jianzhi public resources crawler"
```
