# Crawler Platform Architecture Design

**目标**

设计一套面向“AI 爬虫员工”的运行体系。它既要支持自然语言派单、多站点、多项目、分页、检索、顺序采集、动态页面和 JS 逆向，又要保证目录清晰、代码可读、可改、可扩展，并且生成出来的项目包在脱离平台时仍能独立运行。

**设计原则**

- 平台和项目解耦：平台只负责共性能力，项目只负责站点个性。
- MySQL 只存最终业务数据，不承担任务状态。
- Redis 负责运行时调度，SQLite 负责项目级事实账本。
- 项目包必须独立可执行。
- 代码边界清晰，遵守 Python 官方风格，优先人类可读性和后续变更成本。

## 1. 总体结构

```text
User
  -> Skill
  -> Runtime
  -> Redis
  -> Workers
  -> Project Package
  -> SQLite / Artifacts / Outputs
  -> MySQL
```

可拆成三层：

1. `Skill`
负责理解任务、站点侦察思路、路线选择和验收标准。

2. `Runtime`
负责统一调度、任务拆解、重试、限流、验证、导出和日志。

3. `Project Package`
负责每个项目自己的采集器、解析器、配置、状态账本和产物目录。

## 2. 为什么不是纯 Scrapy

纯 Scrapy 更适合“我已经知道该怎么爬”的稳定站点，而这套系统要解决的是“接到自然语言任务后，先判断怎么爬，再组织不同执行器去干活”。所以 Scrapy 不能当总指挥，只能作为执行器之一。

推荐路线是：

- 调度层自研
- 执行层多引擎
- Scrapy 只处理它最擅长的稳定规则型批量抓取

这样既保留 Scrapy 的成熟抓取能力，又不把整套系统锁死在单一范式里。

## 3. 数据分层

### Redis：运行时调度层

职责：

- 待执行队列
- 延迟重试队列
- 分布式锁
- worker 心跳
- 限流
- 短期去重

限制：

- 不存长期任务事实
- 不存原始 HTML / 大 JSON
- 不存最终结果
- 不做全量明细主仓

2GB Redis 在这种边界下可以起步使用。如果把全量详情 URL、原始响应或大体积对象都堆进去，很快就会成为瓶颈。

### SQLite：项目事实账本

每个项目单独一份，负责：

- 主任务和子任务的状态机
- checkpoint
- 失败任务清单
- artifact 索引
- 本项目运行轨迹

SQLite 的价值在于：即使 Redis 被清空、进程崩溃或机器重启，项目也能恢复到已知状态继续执行。

### MySQL：最终业务数据

职责明确为“最终采集数据”：

- doctor
- hospital
- department
- relation tables

MySQL 不承载运行态任务表，这样业务库保持干净，后续给分析、业务或下游系统使用时不会混入调度噪音。

## 4. 任务模型

任务不是“整站一次跑完”，而是任务树：

- 主任务：一句自然语言派单
- 站点任务：针对一个站点
- 子任务：侦察、列表、详情、检索、校验、导出
- 分片任务：按页码、城市、关键词、科室、医院等维度拆分

建议状态：

- `pending`
- `queued`
- `running`
- `waiting_retry`
- `blocked`
- `done`
- `failed`
- `cancelled`

关键要求：

- 幂等
- 可断点续跑
- 可失败重放
- 可按分片恢复

## 5. 执行层

执行器采用多工种协作：

- `http worker`
  默认主力，负责接口重放、分页、检索、详情请求。
- `browser worker`
  负责动态侦察、定位接口、必要的浏览器采集。
- `scrapy worker`
  负责规则稳定、批量规模大的站点抓取。
- `reverse worker`
  负责签名、加密参数、nonce、时间戳等逻辑的最小复现。

调度顺序遵循“便宜且稳定优先”：

`http -> browser -> scrapy -> reverse`

其中 `reverse worker` 是辅助工种，不应承担整站流程。

## 6. 项目包独立运行

项目包必须既能接入平台，也能单独运行。最低要求：

```bash
python -m project_name run
python -m project_name validate
python -m project_name export
```

这意味着平台不能把关键逻辑藏在平台私有状态里。项目包要自带配置、账本访问、collector、parser、validator 和 exporter。

## 7. 目录与代码风格

平台推荐结构：

```text
crawler-platform/
  runtime/
    app/
    tests/
    pyproject.toml
  projects/
    <project-name>/
```

单项目推荐结构：

```text
project/
  src/
  state/
  artifacts/
  outputs/
  exports/
  logs/
```

代码约束：

- 遵守 PEP 8
- 公共接口写类型标注
- 单个模块只承担一类职责
- 避免“大杂烩 utils”
- collector、parser、pipeline、validator、exporter 明确分层

## 8. 失败与恢复

失败必须分级：

- 瞬时失败：自动退避重试
- 逻辑失败：转重新侦察或人工复核
- 阻断失败：挂起该站点分片

Redis 只保留执行窗口，SQLite 保存任务事实。恢复流程为：

1. 从 SQLite 找到未完成任务
2. 重新灌入 Redis
3. worker 继续消费
4. 成功后写回 SQLite 和产物目录
5. 结构化结果写入 MySQL

## 9. 首版范围建议

不要首版就做“大而全平台”。先做这几块：

- 项目包标准结构
- SQLite 任务账本
- Redis 调度
- http worker
- browser worker
- MySQL 结果写入
- 基础 validator / exporter

`scrapy worker` 和 `reverse worker` 放第二阶段接入。先把任务流、状态流和数据流跑顺，比先做全功能更重要。

## 10. 结论

这套架构的核心不是追求技术炫耀，而是让 AI 能像一个真正可管理的爬虫员工一样工作：

- 会接任务
- 会判断路线
- 会拆任务
- 会稳定运行
- 会在失败后恢复
- 会把最终结果干净地落到业务库

在你当前已知条件下，推荐技术组合是：

`Python 3.12 + Redis + SQLite + MySQL + httpx + Playwright + Scrapy + pytest + ruff`
