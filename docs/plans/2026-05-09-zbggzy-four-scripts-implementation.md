# ZBGGZY Four Scripts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `zbggzy` 从单脚本改成共享核心加四个固定入口脚本，分别只输出招标公告、中标公告、候选人公告、采购意向。

**Architecture:** 保留现有采集、解析、模型增强逻辑为共享核心，新增 `target_board` 过滤能力；四个入口脚本只负责固定 `target_board` 并调用核心 `main`。`采购意向` 只恢复到最小支持范围，不恢复已明确排除的 `需求（意向）公示`。

**Tech Stack:** Python 3.12, requests, pytest

---

### Task 1: 拆分前补测试

**Files:**
- Modify: `projects/jianzhi/zbggzy/tests/test_zbggzy_core.py`

**Step 1: Write the failing test**

- 新增 `采购意向` 映射测试
- 新增 `target_board` 过滤测试
- 新增四类 `build_record` 模板测试
- 新增 `procurementMethod` 不再从正文兜底测试

**Step 2: Run test to verify it fails**

Run: `E:\python3.12.2\python.exe -m pytest projects\jianzhi\zbggzy\tests -q`

Expected: 至少出现导入或断言失败，证明当前代码还不支持四脚本与新口径。

### Task 2: 抽共享核心并加入按板块过滤

**Files:**
- Create: `projects/jianzhi/zbggzy/zbggzy_core.py`
- Modify: `projects/jianzhi/zbggzy/zbggzy.py`

**Step 1: Write minimal implementation**

- 将现有主逻辑迁到 `zbggzy_core.py`
- `resolve_output_board()` 恢复 `采购意向` 映射
- `ZbggzySpider` 增加 `target_board`
- `discover_module_tasks()` 只发现目标板块任务
- `build_record()` 增加 `采购意向` 分支
- `build_context()` 移除 `procurementMethod` 正文兜底

**Step 2: Run tests**

Run: `E:\python3.12.2\python.exe -m pytest projects\jianzhi\zbggzy\tests -q`

Expected: 新增测试转绿。

### Task 3: 添加四个薄入口脚本

**Files:**
- Create: `projects/jianzhi/zbggzy/zbggzy_zhaobiao.py`
- Create: `projects/jianzhi/zbggzy/zbggzy_zhongbiao.py`
- Create: `projects/jianzhi/zbggzy/zbggzy_houxuanren.py`
- Create: `projects/jianzhi/zbggzy/zbggzy_caigouyixiang.py`

**Step 1: Write minimal implementation**

- 每个脚本只固定一个 `target_board`
- 不复制业务逻辑

**Step 2: Compile verification**

Run: `E:\python3.12.2\python.exe -m py_compile projects\jianzhi\zbggzy\zbggzy_core.py projects\jianzhi\zbggzy\zbggzy.py projects\jianzhi\zbggzy\zbggzy_zhaobiao.py projects\jianzhi\zbggzy\zbggzy_zhongbiao.py projects\jianzhi\zbggzy\zbggzy_houxuanren.py projects\jianzhi\zbggzy\zbggzy_caigouyixiang.py`

Expected: exit 0

### Task 4: 更新说明并做事实验证

**Files:**
- Modify: `projects/jianzhi/zbggzy/README.md`

**Step 1: Update docs**

- 说明四个脚本入口
- 说明采购意向仅最小恢复，不包含已排除的 `需求（意向）公示`

**Step 2: Fresh verification**

Run:
- `E:\python3.12.2\python.exe -m pytest projects\jianzhi\zbggzy\tests -q`
- `E:\python3.12.2\python.exe -m py_compile projects\jianzhi\zbggzy\zbggzy_core.py projects\jianzhi\zbggzy\zbggzy.py projects\jianzhi\zbggzy\zbggzy_zhaobiao.py projects\jianzhi\zbggzy\zbggzy_zhongbiao.py projects\jianzhi\zbggzy\zbggzy_houxuanren.py projects\jianzhi\zbggzy\zbggzy_caigouyixiang.py`
- 条件允许时，各脚本各跑 1 页冒烟

Expected: 单测、编译通过，冒烟结果与固定板块一致。
