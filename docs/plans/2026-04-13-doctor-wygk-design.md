# doctor_wygk 架构设计

## 目标

为 `https://www.allinmd.cn/` / `https://patient.allinmd.cn/` 构建一个放在 `projects/doctor_wygk` 下的 Scrapy 医生采集项目。

当前阶段的目标不是一次性吃掉所有字段，而是先把“最可能覆盖全站医生”的稳定链路做成一个能长期扩展的项目骨架：

- 主链路优先走匿名可访问的公开接口
- 当前优先固化“医院 -> 科室 -> 医生列表 -> 医生详情”这条已验证链路
- 项目结构从第一天就保留清晰扩源边界，后续再按已验证来源逐个并入
- 最终所有医生详情统一合流到一个详情队列和一个详情 spider，避免多套详情结构并存

用户当前已明确的约束如下：

- 主架构采用“分层多 spider，详情统一合流”
- 公开接口为主，浏览器缓存态只作为辅助侦察，不作为正式采集主链路
- 字段后续再补，当前先把全站覆盖能力和项目结构设计好
- 数据库沿用现有项目约定，不重新设计新的数据库体系

## 当前已验证事实

本次侦察已经确认以下入口和接口真实可用：

### 1. 医院页链路

- 页面路由：`/interrogation/hospitalHome`
- 科室接口：
  `GET /tocure-api-platform/services/tocure/dept/getDeptList`
- 科室医生列表接口：
  `GET /tocure-api-platform/services/tocure/dept/getFrontDoctorList`
- 医生详情接口：
  `GET /tocure-api-platform/services/tocure/customer/auth/chongqing/procedure/getMapById`

这条链路当前是最稳的主链路，因为：

- 不依赖登录态
- 参数简单
- 列表接口直接返回 `doctorId`
- 详情接口能返回足够丰富的医生核心信息

### 2. 补充内容接口

- 医生文章接口：
  `GET /base_patienteducation_platform/cms/patient/education/api/getDoctorArticle`

该接口本身不能替代医生主链路，但可以作为后续补字段来源。

## 设计原则

`doctor_wygk` 的设计遵循四个原则：

### 1. 链路分层，不把不同职责揉进一个 spider

入口发现、列表扩展、详情合流、字段入库分别拆开。一个 spider 只做一类页面或接口，不承担多种来源的混杂逻辑。

### 2. 主链路稳定优先，扩源单独并入

当前把已验证的医院科室链路作为正式生产链路。课程、直播、手术、协会等公开来源，后续在验证覆盖和字段稳定性后再独立并入，不和当前主链路混写。

### 3. 统一详情口径

所有来源最终只生成一种“医生详情任务”，统一进入同一个 Redis key 和同一个详情 spider。这样字段清洗和 Mongo upsert 只做一套。

### 4. Key 拆分清楚，队列语义单一

Redis key 不做“万物都扔一个 list”这种设计。每个 key 只对应一种任务语义，便于补采、排障和断点续跑。

## 推荐项目结构

建议采用和 `doctor-ywbd` 同风格、但更贴合当前站点的项目结构：

```text
projects/doctor_wygk/
  scrapy.cfg
  README.md
  findings.md
  start.ps1
  doctor_wygk/
    __init__.py
    items.py
    settings.py
    pipelines.py
    middlewares.py
    start.py
    commands/
      __init__.py
      crawl_all.py
    spiders/
      __init__.py
      doctor/
        __init__.py
        01_entry_seed_spider.py
        02_hospital_department_spider.py
        03_department_doctor_list_spider.py
        04_doctor_detail_spider.py
    routes.py
    redis_keys.py
    request_builders.py
    parse_helpers.py
    detail_merge.py
```

其中各文件职责固定如下：

- `routes.py`
  统一存放站点基础 URL、已验证接口、候补接口、固定参数模板
- `redis_keys.py`
  专门生成所有 Redis key，项目命名只在这里定义一次
- `request_builders.py`
  负责把 URL 和参数拼成请求，不把 query 直接散在 spider 里
- `parse_helpers.py`
  负责从接口 JSON 或 HTML 中提取字段
- `detail_merge.py`
  负责把来自不同入口的字段归并成统一详情字典

## Redis 队列设计

当前只保留 4 个正式主链路 key，不再保留 probe / hint 队列。

- `doctor_wygk:hospital_home_url`
  医院入口任务
- `doctor_wygk:dept_task`
  医院科室任务
- `doctor_wygk:doctor_list_task`
  科室医生列表任务
- `doctor_wygk:doctor_info_url`
  统一医生详情任务

这样拆的好处是：

- 队列语义单一，不会把侦察任务和正式任务混在一起
- 当前主链路可以稳定顺序推进
- 后续若新增课程 / 直播 / 手术 / 协会来源，也统一回流 `doctor_info_url`

## Spider 编排

### 1. `01_entry_seed_spider`

职责：

- 只负责把主链路种子写入 Redis
- 当前先写医院入口和已验证的接口入口
- 记录当前写入数量、入口类型、参数模板版本

这个 spider 不抓页面，不解析详情，只做“项目启动时的任务投放”。

### 2. `02_hospital_department_spider`

职责：

- 读取 `dept_task`
- 请求医院科室接口 `getDeptList`
- 产出标准化科室记录
- 为每个科室写入 `doctor_list_task`

如果未来发现多个 `hospitalId` 或多个 `visitSiteId`，这一层最适合扩。它应该把“院区维度”与“科室维度”清晰保存到任务 meta 里，而不是只传一个裸 URL。

### 3. `03_department_doctor_list_spider`

职责：

- 请求 `getFrontDoctorList`
- 解析列表返回的 `doctorId`
- 生成统一详情任务写入 `doctor_info_url`
- 同时输出一份轻量“医生线索记录”到日志，便于看采集进度

这层只负责“把可见医生尽可能枚举出来”，不负责拼最终医生文档。

### 4. `04_doctor_detail_spider`

职责：

- 请求 `getMapById`
- 把医生详情转成统一 item
- 统一补来源字段、任务上下文、采集时间
- 入库前做最小归一化

这个 spider 是整个项目唯一的正式详情汇合点。

## 统一详情模型

虽然字段暂时不细化，但从架构上必须先定义“统一详情模型”的角色。

建议把最终入库 item 分成四块：

- `identity`
  医生身份主键和稳定标识，如 `_id`、`doctor_id`
- `core`
  当前主链路稳定能拿到的姓名、医院、职称、擅长等核心字段
- `source`
  来源信息，例如 `source_site`、`source_url`、`source_channel`
- `trace`
  跟任务有关的追踪字段，例如 `visit_site_id`、`hospital_id`、`dept_id`、`crawl_time`

这里的关键不是字段数量，而是先把“字段角色”分明。后面无论接搜索入口、文章入口还是浏览器侦察入口，都只能往这个统一模型里补，不允许每个 spider 各写各的文档结构。

## Mongo 入库策略

数据库沿用现有项目约定，继续使用 `replace_one(..., upsert=True)` 风格，但建议只保留一个医生集合：

- 集合名：`doctor_wygk`

原因：

- 当前项目的主实体就是医生
- 列表记录只是详情任务的前置，不值得单独长期存库
- 若要保留过程样本，更适合写本地日志或样本 JSON，而不是把 Mongo 变成任务中间态仓库

主键建议优先用公开接口已返回的 `doctorId`，例如：

- `_id = f"doctor_wygk:{doctor_id}"`

如果未来某些候补入口只拿到医生 URL 没拿到 `doctorId`，再由 `detail_merge.py` 统一决定兜底主键规则，而不是每个 spider 自己生成。

## 启动方式

项目运行建议仍然保持“能被人一眼看懂”的顺序执行：

- `start.ps1`
- `python doctor_wygk/start.py`
- `scrapy crawl_all`

`crawl_all` 默认顺序建议是：

1. `entry_seed_spider`
2. `hospital_department_spider`
3. `department_doctor_list_spider`
4. `doctor_detail_spider`

## 当前阶段结论

`doctor_wygk` 当前最合理的形态不是“全站万能 spider”，而是“稳定主链路 + 后续独立扩源 + 单一详情合流”的 Scrapy 项目。

第一阶段先把医院科室链路做透，确保：

- 可以稳定枚举当前已公开可见的医生
- 所有医生最后进入同一个详情口径
- Redis key、Spider 职责和项目命名都清楚

第二阶段再把课程、直播、手术、协会等已验证公开来源逐个接入，不反向污染主干结构。
