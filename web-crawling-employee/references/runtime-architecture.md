# Runtime Architecture

## Purpose

当任务已经不再是一次性脚本，而是要长期承载多站点、多项目、百万级采集时，使用这份参考来约束运行架构。重点不是把所有能力塞进一个框架，而是明确平台内核、项目包、调度层、执行层和数据层的边界。

先说明边界：这份文档描述的是 `Skill` 下游要对接的运行时体系，不是 skill 本体。  
如果当前讨论的是“skill 本身的大框架”，优先阅读 `skill-framework.md`，再回来看这份运行时参考。

## 核心原则

- `Skill` 负责理解自然语言任务、决定路线、指导执行，不直接承担长期运行状态。
- `Runtime` 负责调度、重试、限流、验证、导出，是公共运行内核。
- `Project Package` 负责站点个性逻辑和项目级数据隔离，必须既能挂到平台里运行，也能脱离平台独立运行。
- `Redis` 只做运行时调度层，不做长期事实存储。
- `SQLite` 做项目级任务账本，负责断点续跑、失败重放、任务追踪。
- `MongoDB` 只做最终业务数据存储，不承载任务调度状态。
- `profile.yml` 是项目唯一配置文件，Redis、MongoDB、代理和运行参数都从这里读取。

## 总体分层

```text
User Request
  -> Skill
  -> Runtime Dispatcher / Scheduler
  -> Redis Execution Window
  -> Workers
  -> Project Artifacts / Outputs
  -> SQLite Task Ledger
  -> MongoDB Business Data
```

推荐理解方式：

- `Skill` 是大脑
- `Runtime` 是中控
- `Worker` 是执行工种
- `Project Package` 是具体项目
- `SQLite` 是项目账本
- `MongoDB` 是最终结果库

## 平台内核与项目包

平台内核只放共性能力：

- dispatcher
- scheduler
- worker 基类和通用执行协议
- Redis 适配
- 通用 validator
- 通用 exporter
- 通用日志和监控

项目包只放个性能力：

- 站点配置
- 采集器
- 解析器
- 字段映射
- 项目级 validator
- 项目级 exporter
- 项目级 SQLite 账本和产物目录

不要把具体站点逻辑写进平台内核。平台要服务多个项目，项目才服务单个站点或一组站点。

## 数据层边界

### Redis

放这些：

- 待执行任务队列
- 延迟重试队列
- 分布式锁
- worker 心跳
- 限流令牌
- 短期去重键

不要放这些：

- 全量任务真相
- 原始 HTML 或大 JSON 响应
- 长期去重全集
- 完整结果数据

### SQLite

每个项目一份，用于：

- 主任务和子任务账本
- 任务状态机
- checkpoint
- failed task 列表
- artifact 索引
- 本项目的运行统计

SQLite 是“项目事实账本”，负责在 Redis 波动、进程重启、机器重启后恢复现场。

### MongoDB

只放最终业务数据，例如：

- doctor collection
- hospital collection
- department collection
- embedded or referenced relation documents

如果需要中间索引，也应当是偏业务意义的索引，而不是运行态任务索引。

## 执行器策略

按成本和稳定性优先级选择：

1. `http worker`
   适用于接口重放、分页、检索、详情请求，是默认主力。
2. `browser worker`
   适用于动态页面侦察、发现真实接口、补 Cookie、验证渲染数据。
3. `scrapy worker`
   适用于规则稳定、列表详情结构清晰、批量规模大的传统抓取。
4. `reverse worker`
   适用于签名、加密参数、时间戳、nonce 等必要逻辑的复现。

不要让所有任务都经过所有 worker。调度层要先侦察，再选最便宜可靠的执行器。

## 独立运行约束

项目包必须能在没有平台调度器的情况下运行，至少支持：

```bash
python -m project_name run
python -m project_name validate
python -m project_name export
```

平台存在时，项目包接入统一调度；平台不存在时，项目包仍能在单机上完成采集、校验和导出。

## 目录约束

平台代码和项目代码分离。

如果是首版单项目，且目标是“先让人一眼看懂并且能直接运行”，优先采用单机脚本结构：

- `profile.yml`
- `{entity}_{source}_start.py`
- `start.ps1`
- `profile.yml`

例如：

- `doctor_hxq_start.py`
- `article_xxx_start.py`

这种结构适合：

- 单站点
- 单接口或少量接口
- 直接采集并写 MongoDB
- Redis 只做 checkpoint 或轻量运行辅助

单机脚本风格默认再补一条约束：

- 代码形态优先接近传统工程师可直接接手的脚本写法
- 请求、解析、字段整理、写库的主流程要容易顺着读
- 不要把本来几步能讲清楚的逻辑包装成多层抽象
- MongoDB 写库如果已经存在稳定业务主键，默认就拿这个业务主键做 `_id`

只有当项目已经明显变复杂，再升级到包化目录。

如果是 Scrapy 或分布式项目，不要强行套这套单机脚本结构，直接按 Scrapy 原生结构组织。

Scrapy 项目也固定一条风格要求：

- 保持 `scrapy.cfg`、项目包、`settings.py`、`pipelines.py`、`middlewares.py`、`spiders/` 这些原生位置
- 可以增加一个很薄的 `start.py`、`start.ps1` 或自定义 command 作为总入口
- spider 可以按阶段拆分，例如列表、详情 URL、详情页，不必为了“统一抽象”强行揉成一层
- `settings.py` 主要放配置，`pipelines.py` 主要放存储，spider 主要放抓取和解析
- 代码风格依然优先朴素、直接、容易接手，不要在 Scrapy 项目里额外套很多 manager、service、workflow
- 目标不是“看起来像平台”，而是“熟悉 Scrapy 的人打开后很快知道从哪里改”

分阶段 Scrapy 项目再补充几条很实用的运行约束：

- 如果某个阶段不是从 Redis 消费起始任务，而是自己直接请求固定入口，这个阶段优先使用普通 `scrapy.Spider`
- 只有确实需要从 Redis 读取种子的阶段，才使用 `RedisSpider`
- `RedisSpider` 阶段必须明确空闲退出策略，避免数据已采完但进程一直等待 Redis 不退出
- 如果总入口是串行跑多个 spider，要先验证每个阶段都能按预期结束，后一个阶段才能接上
- 如果 Redis 依赖 SSH 隧道，总入口优先先做隧道拉起或 Redis 端口连通性检查
- Windows 下的 `scrapy.cfg` 建议保持纯 ASCII，避免因为本地编码导致 Scrapy 启动前就失败

如果是要长期演进、多人维护、能力明显增多的项目，目录至少包含：

- `src/`
- `state/`
- `artifacts/`
- `outputs/`
- `exports/`
- `logs/`

包化项目的代码只放在 `src/`。无论单机脚本还是包化项目，运行状态、原始数据、结果文件、日志都应该按目录分开，避免后期无法维护。

## 扩容规则

- Redis 只保留执行窗口，避免 2GB 内存被全量任务压爆。
- 全量详情种子由项目账本分批灌入 Redis，不要一次性推满。
- 重试必须分级：瞬时失败自动退避，逻辑失败转复核，阻断失败挂起站点分片。
- 当项目量增长时，优先扩 worker 数量和分片粒度，而不是先重构整套平台。

## 推荐技术组合

- Python 3.12
- httpx
- Playwright
- Scrapy
- Redis
- SQLite
- MongoDB
- pytest
- ruff

这是一套偏实用的组合：足够承接百万级任务，又不会在首版就把系统做得过重。
