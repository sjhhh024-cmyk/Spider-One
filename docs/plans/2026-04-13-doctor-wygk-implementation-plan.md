# doctor_wygk Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `projects/doctor_wygk` 下建立一个以公开接口为主的 Scrapy 医生采集项目，先固化“医院 -> 科室 -> 医生列表 -> 医生详情”的稳定主链路，并为后续课程、直播、手术、协会等公开来源预留统一详情回流口，所有医生详情统一合流到一个详情 spider 和一个 Mongo 集合。

**Architecture:** 采用 `doctor-ywbd` 风格的 `Scrapy + scrapy_redis + pymongo` 结构，但把任务拆成更清楚的多层 spider：入口投放、医院科室、科室医生列表、医生详情。所有来源最终只允许向统一的 `doctor_info_url` 队列回流，不允许并行存在多套详情落库逻辑。

**Tech Stack:** Python, Scrapy, scrapy-redis, pymongo, pytest

---

### Task 1: 固化 doctor_wygk 的设计与侦察结论

**Files:**
- Create: `projects/doctor_wygk/README.md`
- Create: `projects/doctor_wygk/findings.md`
- Reference: `doctor_wygk_process/doctor_wygk_research.md`

**Step 1: 写 README 最小骨架**

README 里必须写清楚：

- 项目定位是“唯医骨科医生采集”
- 当前稳定主链路是医院科室接口
- 浏览器缓存态不进入主链路

**Step 2: 写 findings.md**

记录已证实接口：

- `getDeptList`
- `getFrontDoctorList`
- `getMapById`
- `getDoctorArticle`

并记录当前已确认参数：

- `visitSiteId=27`
- `hospitalId=1`

### Task 2: 为项目命名、Redis key 和主链路常量写失败测试

**Files:**
- Create: `projects/doctor_wygk/tests/test_routes.py`
- Create: `projects/doctor_wygk/tests/test_redis_keys.py`

**Step 1: 写失败测试**

覆盖下面这些约束：

- Mongo 集合名必须是 `doctor_wygk`
- Redis key 必须包含：
  - `doctor_wygk:hospital_home_url`
  - `doctor_wygk:dept_task`
  - `doctor_wygk:doctor_list_task`
  - `doctor_wygk:doctor_info_url`
- 主链路接口常量必须包含：
  - `getDeptList`
  - `getFrontDoctorList`
  - `getMapById`
  - `getDoctorArticle`

**Step 2: 运行测试并确认失败**

Run:

```powershell
pytest projects/doctor_wygk/tests/test_routes.py projects/doctor_wygk/tests/test_redis_keys.py -q
```

Expected:
- 失败，因为模块和常量还不存在

### Task 3: 实现 routes 与 redis_keys 基础模块

**Files:**
- Create: `projects/doctor_wygk/doctor_wygk/__init__.py`
- Create: `projects/doctor_wygk/doctor_wygk/routes.py`
- Create: `projects/doctor_wygk/doctor_wygk/redis_keys.py`

**Step 1: 写最小实现**

在 `routes.py` 中定义：

- `BASE_WEB_URL`
- `BASE_GATEWAY_URL`
- 主链路接口常量
- 默认参数模板

在 `redis_keys.py` 中定义：

- `DOCTOR_COLLECTION_NAME`
- `build_redis_keys(prefix="doctor_wygk")`

**Step 2: 重新运行测试**

Run:

```powershell
pytest projects/doctor_wygk/tests/test_routes.py projects/doctor_wygk/tests/test_redis_keys.py -q
```

Expected:
- 全绿

### Task 4: 建 Scrapy 项目骨架并接入 doctor_wygk 命名

**Files:**
- Create: `projects/doctor_wygk/scrapy.cfg`
- Create: `projects/doctor_wygk/start.ps1`
- Create: `projects/doctor_wygk/doctor_wygk/items.py`
- Create: `projects/doctor_wygk/doctor_wygk/settings.py`
- Create: `projects/doctor_wygk/doctor_wygk/pipelines.py`
- Create: `projects/doctor_wygk/doctor_wygk/middlewares.py`
- Create: `projects/doctor_wygk/doctor_wygk/start.py`
- Create: `projects/doctor_wygk/doctor_wygk/commands/__init__.py`
- Create: `projects/doctor_wygk/doctor_wygk/commands/crawl_all.py`

**Step 1: 复用 doctor-ywbd 的运行方式**

要求：

- Redis、Mongo 连接方式沿用现有项目
- 集合名切到 `doctor_wygk`
- `ITEM_PIPELINES` 只保留一个 Mongo pipeline
- `crawl_all` 顺序预留四个 spider 名

**Step 2: 保持配置可读**

不要过度封装环境配置。`settings.py` 里直接能看清：

- Mongo 连接
- Redis 连接
- key 常量
- 下载并发参数

### Task 5: 为请求构造和解析辅助函数写失败测试

**Files:**
- Create: `projects/doctor_wygk/tests/test_request_builders.py`
- Create: `projects/doctor_wygk/tests/test_parse_helpers.py`

**Step 1: 写请求构造测试**

测试覆盖：

- 医院科室请求参数包含 `visitSiteId`、`hospitalId`
- 科室医生请求参数包含 `visitSiteId`、`deptId`、`deptName`
- 医生详情请求参数包含 `doctorId`、`visitSiteId`

**Step 2: 写解析测试**

准备最小样例 JSON，验证：

- 科室列表能抽出 `id`、`deptName`
- 医生列表能抽出 `doctorId`
- 医生详情能抽出 `_id`、`doctor_id`、`source_url`

**Step 3: 运行测试并确认失败**

Run:

```powershell
pytest projects/doctor_wygk/tests/test_request_builders.py projects/doctor_wygk/tests/test_parse_helpers.py -q
```

Expected:
- 失败，因为辅助模块尚未实现

### Task 6: 实现 request_builders、parse_helpers 和 detail_merge

**Files:**
- Create: `projects/doctor_wygk/doctor_wygk/request_builders.py`
- Create: `projects/doctor_wygk/doctor_wygk/parse_helpers.py`
- Create: `projects/doctor_wygk/doctor_wygk/detail_merge.py`

**Step 1: 实现请求构造器**

要求：

- 每个接口单独一个函数
- 返回值明确包含 `url` 和 `params`
- 参数默认值统一在这里收口

**Step 2: 实现解析器**

要求：

- 科室、医生列表、医生详情分别一个函数
- 函数名直接表达用途
- 不在函数里做网络请求

**Step 3: 实现详情合流器**

要求：

- 输入为来源上下文和详情字段
- 输出统一医生文档
- 在这里补：
  - `_id`
  - `website`
  - `source_site`
  - `source_url`
  - `crawl_time`

**Step 4: 重新运行测试**

Run:

```powershell
pytest projects/doctor_wygk/tests/test_request_builders.py projects/doctor_wygk/tests/test_parse_helpers.py -q
```

Expected:
- 全绿

### Task 7: 建主链路 spider 骨架

**Files:**
- Create: `projects/doctor_wygk/doctor_wygk/spiders/__init__.py`
- Create: `projects/doctor_wygk/doctor_wygk/spiders/doctor/__init__.py`
- Create: `projects/doctor_wygk/doctor_wygk/spiders/doctor/01_entry_seed_spider.py`
- Create: `projects/doctor_wygk/doctor_wygk/spiders/doctor/02_hospital_department_spider.py`
- Create: `projects/doctor_wygk/doctor_wygk/spiders/doctor/03_department_doctor_list_spider.py`
- Create: `projects/doctor_wygk/doctor_wygk/spiders/doctor/04_doctor_detail_spider.py`

**Step 1: 入口种子 spider**

职责：

- 写入医院入口或医院科室任务
- 记录写入数量

**Step 2: 医院科室 spider**

职责：

- 读取 `dept_task`
- 调用 `getDeptList`
- 把科室任务写入 `doctor_list_task`

**Step 3: 科室医生列表 spider**

职责：

- 调用 `getFrontDoctorList`
- 把每个医生统一写入 `doctor_info_url`
- 日志打印“科室名 / 当前条数 / 累计详情任务数”

**Step 4: 医生详情 spider**

职责：

- 调用 `getMapById`
- 用 `detail_merge` 产出统一 item
- yield 到 Mongo pipeline

### Task 8: 为 pipeline 和启动顺序写验证测试

**Files:**
- Create: `projects/doctor_wygk/tests/test_start_modes.py`
- Create: `projects/doctor_wygk/tests/test_pipelines.py`

**Step 1: 写启动顺序测试**

验证：

- `crawl_all` 默认顺序包含 01-04
- 不包含已删除的 probe spider

**Step 2: 写 pipeline 测试**

验证：

- `replace_one(..., upsert=True)` 使用 `_id` 入库
- 集合名来自 `settings.py`

**Step 3: 运行测试并确认通过**

Run:

```powershell
pytest projects/doctor_wygk/tests -q
```

Expected:
- 全绿

### Task 9: 做基础语法校验和 README 收口

**Files:**
- Modify: `projects/doctor_wygk/README.md`

**Step 1: 运行语法校验**

Run:

```powershell
python -m py_compile projects/doctor_wygk/doctor_wygk/routes.py
python -m py_compile projects/doctor_wygk/doctor_wygk/request_builders.py
python -m py_compile projects/doctor_wygk/doctor_wygk/parse_helpers.py
python -m py_compile projects/doctor_wygk/doctor_wygk/spiders/doctor/04_doctor_detail_spider.py
```

Expected:
- 无报错

**Step 2: README 收口说明**

README 必须写清楚：

- 当前正式主链路
- 当前只保留的 4 个正式 Redis key
- 为什么当前不把未稳定来源直接并入主采集流程
- 如何只跑主链路
- 后续课程、直播、手术、协会来源如何统一回流 `doctor_info_url`
