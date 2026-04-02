# Runtime Architecture

## Purpose

当任务已经不再是一次性脚本，而是要长期承载多站点、多项目、百万级采集时，使用这份参考来约束运行架构。重点不是把所有能力塞进一个框架，而是明确平台内核、项目包、调度层、执行层和数据层的边界。

## 核心原则

- `Skill` 负责理解自然语言任务、决定路线、指导执行，不直接承担长期运行状态。
- `Runtime` 负责调度、重试、限流、验证、导出，是公共运行内核。
- `Project Package` 负责站点个性逻辑和项目级数据隔离，必须既能挂到平台里运行，也能脱离平台独立运行。
- `Redis` 只做运行时调度层，不做长期事实存储。
- `SQLite` 做项目级任务账本，负责断点续跑、失败重放、任务追踪。
- `MySQL` 只做最终业务数据存储，不承载任务调度状态。

## 总体分层

```text
User Request
  -> Skill
  -> Runtime Dispatcher / Scheduler
  -> Redis Execution Window
  -> Workers
  -> Project Artifacts / Outputs
  -> SQLite Task Ledger
  -> MySQL Business Data
```

推荐理解方式：

- `Skill` 是大脑
- `Runtime` 是中控
- `Worker` 是执行工种
- `Project Package` 是具体项目
- `SQLite` 是项目账本
- `MySQL` 是最终结果库

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

### MySQL

只放最终业务数据，例如：

- doctor
- hospital
- department
- doctor_hospital_relation
- doctor_department_relation

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

平台代码和项目代码分离。项目目录至少包含：

- `src/`
- `state/`
- `artifacts/`
- `outputs/`
- `exports/`
- `logs/`

代码只放在 `src/`。运行状态、原始数据、结果文件、日志必须按目录分开，避免后期无法维护。

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
- MySQL
- pytest
- ruff

这是一套偏实用的组合：足够承接百万级任务，又不会在首版就把系统做得过重。
