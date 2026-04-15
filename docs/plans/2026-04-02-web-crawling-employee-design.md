# 网站采集员工 Skill 总纲设计

## 目标

把 `web-crawling-employee` 设计成一个真正的“网站采集员工 skill”，而不是一个固定字段、固定站点、固定脚本套路的采集模板。

它要能接收自然语言任务，理解用户想拿什么数据，侦察网站真实结构，选择采集路线，组织分页、检索、顺序采集和详情扩展，必要时处理 JS 逆向，并在交付前完成验证。

## 当前总原则

- skill 先解决“怎么思考和怎么接活”，再解决“代码怎么跑”。
- 医生信息网站是当前重点场景，但 skill 本体不能被写死成医生采集器。
- skill 和 runtime 分层明确：skill 负责上层判断，runtime 负责下层运行。
- 大框架先定骨架，不提前锁死站点级实现细节。

## Skill 主骨架

当前把这个 skill 固定成六层：

1. `任务理解层`
   把用户自然语言要求转成内部任务单，明确目标站点、实体、字段、范围、停止规则和交付形式。

2. `站点侦察层`
   识别列表页、详情页、搜索面、筛选项、分页机制、接口来源、内嵌 JSON 和潜在逆向边界。

3. `路线决策层`
   以“便宜且稳定优先”为原则，在接口重放、内嵌数据解析、HTML 解析、浏览器辅助、浏览器提取和最小必要逆向之间做选择。

4. `执行编排层`
   把任务拆成列表、详情、检索、翻页、顺序采集、失败重试和样本验证等动作，可以对接 runtime，也能指导单项目独立执行。

5. `验收交付层`
   负责字段完整性、分页正确性、检索有效性、去重、来源追踪和最终交付说明。

6. `经验沉淀层`
   沉淀字段经验、站点规律、失败样例、分页规则、去重键和复现方式。

## Skill 与下游体系的关系

```text
用户任务
  -> Skill
  -> Runtime
  -> Project Package
  -> Redis / SQLite / MongoDB
```

含义固定如下：

- `Skill`：网站采集员工的大脑
- `Runtime`：统一调度和恢复中控
- `Project Package`：具体项目的站点实现
- `Redis`：运行时调度窗口
- `SQLite`：项目账本
- `MongoDB`：最终业务结果

## Skill 包内文件职责

- `web-crawling-employee/SKILL.md`
  入口说明，定义接单规则、工作流和使用顺序。
- `web-crawling-employee/references/skill-framework.md`
  大框架总纲，定义角色、分层、边界和扩展原则。
- `web-crawling-employee/references/task-playbook.md`
  技术树、侦察方法和常见站点打法。
- `web-crawling-employee/references/field-strategy.md`
  动态字段组织策略。
- `web-crawling-employee/references/test-checklist.md`
  验证和交付标准。
- `web-crawling-employee/references/runtime-architecture.md`
  进入平台化、长期运行、百万级任务阶段时再看的运行时架构参考。

## 当前不展开的细节

当前这份总纲先不锁死：

- MongoDB 具体 collection 设计
- 项目级任务表字段
- 代理池产品方案
- 每个网站的独立字段全集
- 复杂反爬对抗的逐站实现

## 当前结论

这次设计收口后，`web-crawling-employee` 的定位已经明确：

它首先是一个“会接任务、会判断路线、会安排执行、会验收结果、会沉淀经验”的 skill；  
runtime、Redis、SQLite、MongoDB 和项目代码，都是它下游要协作的体系，而不是它本身。
