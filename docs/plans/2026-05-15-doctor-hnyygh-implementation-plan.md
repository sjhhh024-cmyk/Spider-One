# doctor_hnyygh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 建一个放在 `projects/doctor_hnyygh` 下的 `Scrapy + scrapy-redis` 医生采集项目，主链路使用 `https://www.169000.net/` 的公开 `fastGh` 接口完成 `区域 -> 医院 -> 科室 -> 医生` 扩展，再用 `https://guahao.169000.net/` 的公开旧站 HTML 页面补齐医生详情字段，并在医生链路中顺手把医院基础信息写入 `hospital_hnyygh` 集合。

**Architecture:** 项目沿用仓库里 `doctor-ywbd` 的阶段式 spider 结构，但只保留当前站点需要的最小阶段：入口种子、区域医院扩展、科室扩展、医生详情扩展。新站 `fastGh` 接口负责提供稳定 ID 链路；旧站 `guahao.169000.net` 负责提供稳定详情 HTML。医院不做独立主链路，而是在医生详情链路中通过医院映射与旧站医院页补充基础字段后直接入库。

**Tech Stack:** Python, Scrapy, scrapy-redis, pymongo, pytest

---

### Task 1: 固化站点结论与命名约定

**Files:**
- Create: `projects/doctor_hnyygh/README.md`
- Create: `projects/doctor_hnyygh/findings.md`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/route_hypotheses.py`

**Step 1: 写失败测试**

新建：
- `projects/doctor_hnyygh/tests/test_route_hypotheses.py`

覆盖以下事实：
- 主站常量：`https://www.169000.net`
- 旧站常量：`https://guahao.169000.net`
- 首阶段入口 URL 必须是 `https://www.169000.net/fastGh/1`
- Redis key 需要至少包含：
  `area_index_url`
  `hospital_list_url`
  `department_list_url`
  `doctor_list_url`
  `doctor_info_url`
- Mongo 集合名固定为：
  `doctor_hnyygh`
  `hospital_hnyygh`

**Step 2: 跑测试确认失败**

Run:

```powershell
pytest projects/doctor_hnyygh/tests/test_route_hypotheses.py -q
```

Expected:
- 失败，原因是模块和常量还不存在

**Step 3: 写最小实现**

在 `route_hypotheses.py` 里提供：
- 站点常量
- 集合名常量
- `build_redis_keys()`
- 入口记录构造函数

**Step 4: 重新跑测试**

Run:

```powershell
pytest projects/doctor_hnyygh/tests/test_route_hypotheses.py -q
```

Expected:
- 全绿

### Task 2: 为 fastGh 主链路解析写测试与实现

**Files:**
- Create: `projects/doctor_hnyygh/tests/test_probe_helpers.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/probe_helpers.py`

**Step 1: 写失败测试**

覆盖以下行为：
- 解析 `fastGh/1` 返回区域列表
- 解析 `fastGh/2-<city_id>` 返回医院列表
- 解析 `fastGh/3-<hospital_id>` 返回科室列表
- 解析 `fastGh/4-<dept_id>` 返回医生列表
- 生成：
  区域请求、
  医院请求、
  科室请求、
  医生详情任务
- 医院基础记录构造函数能输出：
  `_id`
  `hospital_id`
  `hospital_name`
  `source_site`
  `source_url`
  `crawl_time`

**Step 2: 跑测试确认失败**

Run:

```powershell
pytest projects/doctor_hnyygh/tests/test_probe_helpers.py -q
```

Expected:
- 失败，原因是 helper 不存在

**Step 3: 写最小实现**

要求：
- 只支持当前站点已证实 JSON 结构
- 不提前抽象未来站点
- JSON 解析失败时返回空列表而不是抛复杂异常

**Step 4: 重新跑测试**

Run:

```powershell
pytest projects/doctor_hnyygh/tests/test_probe_helpers.py -q
```

Expected:
- 全绿

### Task 3: 为旧站详情桥接写测试与实现

**Files:**
- Create: `projects/doctor_hnyygh/tests/test_legacy_bridge.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/legacy_bridge.py`

**Step 1: 写失败测试**

覆盖以下行为：
- `GBK` 表单编码函数能正确构造请求体
- 旧站医生搜索结果页能提取多个 `op=6&id=...` 候选详情链接
- 旧站医院搜索结果页能提取 `op=3&id=...` 医院页链接
- 旧站医院页能提取 `op=4&id=...` 科室页链接
- 旧站科室页能提取 `op=6&id=...` 医生详情页链接
- 旧站医生详情页能提取：
  `doctor_name`
  `doctor_hospital`
  `doctor_department`
  `doctor_title`
  `doctor_avatar_url`
  `doctor_specialties`
  `intro`
- 旧站医院详情页能提取：
  `hospital_name`
  `hospital_phone`
  `hospital_address`
  `hospital_website`
  `hospital_intro`

**Step 2: 跑测试确认失败**

Run:

```powershell
pytest projects/doctor_hnyygh/tests/test_legacy_bridge.py -q
```

Expected:
- 失败，原因是桥接模块还不存在

**Step 3: 写最小实现**

要求：
- 详情桥接优先级：
  1. 医院页 + 科室名 -> 科室页 -> 医生详情页
  2. 医生名搜索结果过滤
- 过滤逻辑必须尽量使用：
  医院名
  科室名
  医生名
- 只实现当前证实需要的 HTML 解析规则

**Step 4: 重新跑测试**

Run:

```powershell
pytest projects/doctor_hnyygh/tests/test_legacy_bridge.py -q
```

Expected:
- 全绿

### Task 4: 建 Scrapy 项目骨架与项目配置

**Files:**
- Create: `projects/doctor_hnyygh/scrapy.cfg`
- Create: `projects/doctor_hnyygh/start.ps1`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/__init__.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/items.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/pipelines.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/redis_requests.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/settings.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/start.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/commands/__init__.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/commands/crawl_all.py`

**Step 1: 复用 doctor-ywbd 的结构**

要求：
- BOT 名称切到 `doctor_hnyygh`
- Redis key 切到 `doctor_hnyygh:*`
- Mongo 集合切到：
  `doctor_hnyygh`
  `hospital_hnyygh`

**Step 2: Item 只保留当前必须字段**

医生字段至少包括：
- `_id`
- `doctor_id`
- `doctor_name`
- `doctor_hospital`
- `doctor_department`
- `doctor_title`
- `doctor_avatar_url`
- `doctor_specialties`
- `intro`
- `source_site`
- `source_url`
- `crawl_time`

医院字段至少包括：
- `_id`
- `hospital_id`
- `hospital_name`
- `hospital_address`
- `hospital_phone`
- `hospital_intro`
- `hospital_website`
- `source_site`
- `source_url`
- `crawl_time`

### Task 5: 建阶段 spider 骨架并接主链路

**Files:**
- Create: `projects/doctor_hnyygh/doctor_hnyygh/spiders/__init__.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/spiders/doctor/__init__.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/spiders/doctor/01_entry_seed_spider.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/spiders/doctor/02_area_hospital_spider.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/spiders/doctor/03_department_spider.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/spiders/doctor/04_doctor_list_spider.py`
- Create: `projects/doctor_hnyygh/doctor_hnyygh/spiders/doctor/05_doctor_detail_spider.py`

**Step 1: 入口种子 spider**

职责：
- 把 `fastGh/1` 写入区域入口队列

**Step 2: 区域医院 spider**

职责：
- 消费区域入口
- 对每个区域调用 `fastGh/1`
- 为每个城市生成 `fastGh/2-<city_id>`
- 解析医院列表后：
  1. 写入医院基础队列或详情上下文
  2. 为每家医院生成 `fastGh/3-<hospital_id>`

**Step 3: 科室 spider**

职责：
- 消费 `fastGh/3-<hospital_id>`
- 解析科室列表
- 为每个科室生成 `fastGh/4-<dept_id>`

**Step 4: 医生列表 spider**

职责：
- 消费 `fastGh/4-<dept_id>`
- 解析医生 ID 与姓名
- 生成统一医生详情任务，meta 里带：
  `doctor_id`
  `doctor_name`
  `hospital_id`
  `hospital_name`
  `department_id`
  `department_name`
  `city_id`
  `city_name`

**Step 5: 医生详情 spider**

职责：
- 不直接依赖新站 SPA 详情页解析
- 用旧站桥接模块补齐详情字段
- 医生入库前做最小字段合流
- 顺手构造医院记录并入库 `hospital_hnyygh`

### Task 6: 做最小集成验证

**Files:**
- Modify: `projects/doctor_hnyygh/README.md`
- Modify: `projects/doctor_hnyygh/findings.md`

**Step 1: 跑单测**

Run:

```powershell
pytest projects/doctor_hnyygh/tests -q
```

**Step 2: 跑语法校验**

Run:

```powershell
py -3 -m py_compile projects/doctor_hnyygh/doctor_hnyygh/route_hypotheses.py
py -3 -m py_compile projects/doctor_hnyygh/doctor_hnyygh/probe_helpers.py
py -3 -m py_compile projects/doctor_hnyygh/doctor_hnyygh/legacy_bridge.py
py -3 -m py_compile projects/doctor_hnyygh/doctor_hnyygh/settings.py
```

**Step 3: 记录当前已证实桥接结论**

README 和 findings 必须说明：
- 新站 `fastGh` 主链路已确认可用
- 旧站搜索提交需使用 `GBK`
- 旧站医生详情页可直接抽取完整字段
- 某些新站“院区名”和旧站“医院主名”不完全一致，第一版需要名称归一或模糊匹配
