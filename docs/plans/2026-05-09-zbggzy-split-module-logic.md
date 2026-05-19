# ZBGGZY Split Module Logic Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `zbggzy_core.py` 调整为轻包装启动器/公共能力层，把招标、中标、候选人三类模块逻辑分别下沉到三个独立脚本中。

**Architecture:** 保留站点常量、请求、详情解析、上下文构建等共享能力在 `zbggzy_core.py`。新增三个板块脚本各自定义板块模板与模型增强逻辑，并通过 core 提供的基类/工厂完成单独启动。core 默认作为“全量混合入口”启动器。

**Tech Stack:** Python 3.12, requests, pytest

---

### Task 1: 先补结构约束测试

**Files:**
- Modify: `projects/jianzhi/zbggzy/tests/test_zbggzy_core.py`

**Step 1: Write the failing test**

- 验证三个脚本各自暴露独立 spider/main
- 验证 core 不再直接承载三套 `build_record`

**Step 2: Run test to verify it fails**

Run: `E:\python3.12.2\python.exe -m pytest projects\jianzhi\zbggzy\tests -q`

Expected: 因导入路径或结构变化未完成而失败。

### Task 2: 提取公共基础 spider

**Files:**
- Modify: `projects/jianzhi/zbggzy/zbggzy_core.py`

**Step 1: Write minimal implementation**

- 引入 `BaseZbggzySpider`
- 保留共享解析、上下文、抓取、调度
- 把模板构造与模型增强留作可覆写方法

**Step 2: Run tests**

Run: `E:\python3.12.2\python.exe -m pytest projects\jianzhi\zbggzy\tests -q`

Expected: 共享行为测试仍为绿色。

### Task 3: 下沉三块模块逻辑

**Files:**
- Modify: `projects/jianzhi/zbggzy/zbggzy_zhaobiao.py`
- Modify: `projects/jianzhi/zbggzy/zbggzy_zhongbiao.py`
- Modify: `projects/jianzhi/zbggzy/zbggzy_houxuanren.py`

**Step 1: Write minimal implementation**

- 每个脚本定义自己的 spider 子类
- 各自实现本板块 `build_record`
- 各自实现本板块 `apply_model_enrichment`
- 各自直接 `main()`

**Step 2: Run tests**

Run: `E:\python3.12.2\python.exe -m pytest projects\jianzhi\zbggzy\tests -q`

Expected: 板块输出口径不变。

### Task 4: 轻量化 core 启动器

**Files:**
- Modify: `projects/jianzhi/zbggzy/zbggzy_core.py`
- Modify: `projects/jianzhi/zbggzy/README.md`

**Step 1: Update core entry**

- `zbggzy_core.py` 默认跑混合 spider
- README 明确：core 是总入口，三个脚本可独立启动

**Step 2: Fresh verification**

Run:
- `E:\python3.12.2\python.exe -m pytest projects\jianzhi\zbggzy\tests -q`
- `E:\python3.12.2\python.exe -m py_compile projects\jianzhi\zbggzy\zbggzy_core.py projects\jianzhi\zbggzy\zbggzy_zhaobiao.py projects\jianzhi\zbggzy\zbggzy_zhongbiao.py projects\jianzhi\zbggzy\zbggzy_houxuanren.py`

Expected: 测试与编译通过。
