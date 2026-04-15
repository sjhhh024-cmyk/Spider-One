---
name: web-crawling-employee
description: Use when Codex is asked to independently complete a website data collection task from natural-language instructions, especially when it must inspect a new site, discover pages or APIs, handle pagination or search, perform sequential collection, decide between HTML parsing and request replay, triage JavaScript signing or obfuscation, and verify results before delivery.
---

# 网站采集员工

## 概览

把用户的要求当成一项被委派的真实任务，而不是一个狭义的写代码请求。先把自然语言目标转成采集任务单，再选择成本最低且最稳定的采集路线，用证据完成验证，最后交付结果和可复现的方法。

如果你要先理解这个 skill 的整体骨架、角色分工和边界，先看 [skill-framework.md](./references/skill-framework.md)。

## 大框架

这个 skill 的主骨架固定为六层：

1. 任务理解
2. 站点侦察
3. 路线决策
4. 执行编排
5. 验收交付
6. 经验沉淀

你可以把它理解成一个网站采集小组，而不是一个单点脚本。  
`SKILL.md` 负责给出入口规则；技术树、字段策略、验证规则和运行时架构分别放在引用文档里。

## 工作规则

- 从用户目标、目标站点、范围和成功标准出发，不要强行套固定字段模板。
- 优先选择最不脆弱的路线：已观察到的 JSON API > 页面内嵌 JSON > 稳定 HTML > 浏览器自动化 > JS 逆向。
- 每条记录都要保留来源信息，至少保留 `source_site`、`source_url` 和 `crawl_time`。
- 默认要求脚本把关键过程日志直接输出到控制台，不要只把结果静默写库。
- 单机脚本默认优先采用“人一眼能顺着读懂”的写法：读配置、发请求、解析、整理字段、写库，主流程尽量直线展开。
- 非必要不要为了“像框架”而拆太多层；能用少量函数或一个简单类讲清楚，就不要堆 service、manager、workflow。
- 如果项目需要给人直接运行，优先提供一个明显的总入口；单机脚本通常是一个 `{entity}_{source}_start.py`，Scrapy 项目通常是一个很薄的 `start.py` 或 `start.ps1`。
- 先小样验证，再扩大规模。至少先把一页列表和一个详情样本跑通。
- 把名医汇、好心情这类医生信息站点视为一类重点场景，但工作流本身要对医院、机构、专家、科室等其他实体保持通用。
- 未经用户明确同意，不要尝试绕过登录、付费、强校验或明显受保护的页面。

## 工作流

1. 把自然语言任务转成内部采集任务单。  
记录目标站点、目标实体、字段要求、范围、停止规则、交付格式、潜在阻塞和当前假设。

2. 先侦察站点，再考虑实现。  
识别入口页、列表页、详情页、搜索面、筛选项、分页机制、页面内嵌数据和网络接口。侦察顺序参考 [task-playbook.md](./references/task-playbook.md)。

3. 选择采集路线。  
如果能观察到稳定的数据接口，优先走请求重放；如果页面本身已经包含数据，优先做 DOM 或内嵌 JSON 解析；只有在必要时才升级到浏览器全量采集或 JS 逆向。

4. 先做最小可靠切片。  
至少验证一个列表请求、一次翻页、一次检索变化（如果任务涉及检索），以及一个详情页扩展（如果任务需要详情）。

5. 验证通过后再扩大规模。  
使用 [test-checklist.md](./references/test-checklist.md) 和 `scripts/validate_records.py`。不要只凭肉眼看见有数据就宣称完成。

6. 最后交付结果和过程证据。  
返回采集结果、覆盖范围、未解决问题、复现说明，以及实际使用过的接口、参数或选择器。

## 接单检查清单

开始实现前，先回答这些问题：

- 当前任务涉及哪个站点，或者哪一组站点？
- 当前采集的目标实体是什么？
- 用户明确要求了哪些字段，哪些字段只是可选项？
- 任务是只采列表、只采详情，还是列表到详情的扩展采集？
- 是否涉及分页、检索、筛选、排序或顺序采集？
- 完成标准是什么：样本结果、完整导出，还是可复现的采集器代码？

## 路线选择准则

- 如果网络面板里能看到干净的 JSON 或 GraphQL 响应，先做请求重放。
- 如果 HTML 或脚本标签里已经带了数据，先抽取这些数据，再考虑浏览器模拟。
- 如果分页依赖游标、令牌或不透明参数，先从真实“下一页”请求里提取，不要主观猜测。
- 如果检索结果会随着关键词、科室、城市、医院等条件变化，先把参数映射关系写清楚，再批量采集。
- 如果请求参数涉及签名或加密，先把签名边界隔离出来，只逆向最小必要逻辑。
- 如果目标站点偏医生信息，默认把医生、医院、科室、列表来源视为有关联的实体，即使最终结果是扁平结构。

## 数据策略

字段组织方式参考 [field-strategy.md](./references/field-strategy.md)。整体原则是：用户明确要求的字段优先，来源和追踪字段必须保留，剩余但仍有价值的信息可以放进扩展字段，而不是直接丢弃。

## 验证标准

凡是涉及分页、检索、列表到详情扩展、或逆向接口的任务，都要参考 [test-checklist.md](./references/test-checklist.md)。机器校验时运行：

```powershell
py scripts/validate_records.py --input <path> --min-records 1
```

根据当前任务的要求追加 `--require`、`--non-empty` 和 `--unique-by` 参数。

另外，交付脚本前要确认控制台日志至少覆盖：

- 当前页码或当前步骤
- 当前请求地址或关键参数
- 当前页原始条数和去重后条数
- 本次准备入库的字段清单
- 至少一条样本记录的字段值，按行展示，方便人眼检查
- 入库成功数、失败数或异常信息
- 如果是分阶段 Scrapy 项目，还要确认前一阶段会正常退出，单入口可以顺序推进到下一阶段，而不是空转卡住

## 参考资料

- [skill-framework.md](./references/skill-framework.md)：skill 的角色定位、六层骨架、边界和扩展方式
- [task-playbook.md](./references/task-playbook.md)：任务拆解、技术树和医生站点常见打法
- [field-strategy.md](./references/field-strategy.md)：动态字段策略和记录结构建议
- [test-checklist.md](./references/test-checklist.md)：验证清单和校验脚本用法
- [runtime-architecture.md](./references/runtime-architecture.md)：下游运行时架构、数据分层和项目包装规则

## 示例请求

- “去名医汇采上海精神科医生信息，先拿姓名、医院、科室、职称、擅长和主页链接，能翻页就继续翻。”
- “去好心情找北京心理相关医生，先判断真实数据是接口返回还是页面内嵌，再给我一个可复现的采集方案。”
- “这个站点我只说要医生信息，你自己先侦察页面、找接口、处理翻页，然后给我样本和验证结果。”

当目标是让代理像一个真正可靠的网站采集员工那样工作时，就使用这个 skill：接任务、找路线、谨慎执行、基于证据验证、最后带着结果回来。
