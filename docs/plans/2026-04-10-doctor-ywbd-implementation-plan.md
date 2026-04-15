# doctor-ywbd Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 建一个放在 `projects` 下的 YWBD 医生采集项目，复用 doctor-circle 的 Redis/Mongo 运行方式，但把 Redis key、Mongo 集合、项目命名全部切到 `doctor_ywbd` 规范，并先固化“按医院、按地区、按疾病、按科室”四类入口和“列表页 -> 详情页”的链路骨架。

**Architecture:** 采用与 `projects/doctor-circle` 一致的 Scrapy + `scrapy_redis` 结构，先落一个能顺着读的三阶段链路：入口种子、列表页扩展、医生详情入库。由于 `data.120ask.com` 当前被 Knownsec CloudWAF 按 `foregin_ip` 拦截，所有尚未被实测证实的 URL 规律统一收口到单独的路由模块，避免散落硬编码。

**Tech Stack:** Python, Scrapy, scrapy-redis, pymongo, pytest

---

### Task 1: 固化已知侦察结论

**Files:**
- Create: `projects/doctor-ywbd/README.md`
- Create: `projects/doctor-ywbd/findings.md`

**Step 1: 写最小文档骨架**

记录下面这些已证实事实：
- `www.120ask.com` 首页存在 `//data.120ask.com/` 的“医院库”入口
- 当前访问 `https://data.120ask.com/` 返回 Knownsec CloudWAF `403`
- 拦截原因里明确出现 `error_403_type=foregin_ip`
- 公开搜索结果出现过 `data.120ask.com/keshi/yisheng/<slug>.html` 历史存档痕迹

**Step 2: 在 README 里说明当前阶段**

说明当前项目定位：
- 已完成入口/链路骨架
- 尚待真实网络放行后补全接口和解析细节

### Task 2: 为路由假设和命名规则写失败测试

**Files:**
- Create: `projects/doctor-ywbd/tests/test_route_hypotheses.py`

**Step 1: 写失败测试**

测试覆盖：
- 四类入口常量必须齐全：`hospital`、`region`、`disease`、`department`
- 医生详情 URL 模板必须输出 `https://data.120ask.com/<category>/yisheng/<slug>.html`
- Redis key 必须是 `doctor_ywbd:list_url`、`doctor_ywbd:info_url`
- Mongo 集合名必须是 `doctor_ywbd`

**Step 2: 运行测试并确认失败**

Run:

```powershell
pytest projects/doctor-ywbd/tests/test_route_hypotheses.py -q
```

Expected:
- 失败，原因是模块和函数还不存在

### Task 3: 实现最小路由与命名模块

**Files:**
- Create: `projects/doctor-ywbd/doctor_ywbd/route_hypotheses.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/__init__.py`

**Step 1: 写最小实现**

提供：
- 四类入口映射
- 生成详情 URL 的函数
- Redis key 命名函数
- Mongo 集合名常量

**Step 2: 重新运行测试**

Run:

```powershell
pytest projects/doctor-ywbd/tests/test_route_hypotheses.py -q
```

Expected:
- 全绿

### Task 4: 建 Scrapy 项目骨架并接入 YWBD 命名

**Files:**
- Create: `projects/doctor-ywbd/scrapy.cfg`
- Create: `projects/doctor-ywbd/start.ps1`
- Create: `projects/doctor-ywbd/doctor_ywbd/settings.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/items.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/pipelines.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/middlewares.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/start.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/commands/crawl_all.py`

**Step 1: 复用 doctor-circle 的运行时结构**

但把以下内容改成 YWBD 命名：
- BOT_NAME
- Mongo 集合
- Redis key
- spider 名称

**Step 2: 保持配置可直接读懂**

不要过度抽象；把“当前是探测版项目”的说明写进注释和 README。

### Task 5: 建三阶段 spider 骨架

**Files:**
- Create: `projects/doctor-ywbd/doctor_ywbd/spiders/__init__.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/spiders/doctor/__init__.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/spiders/doctor/1_entry_seed_spider.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/spiders/doctor/2_list_page_spider.py`
- Create: `projects/doctor-ywbd/doctor_ywbd/spiders/doctor/3_doctor_detail_spider.py`

**Step 1: 入口种子 spider**

职责：
- 生成四类入口 URL
- 直接把入口 URL 放入 `doctor_ywbd:list_url`
- 记录当前种子写入结果

**Step 2: 列表页 spider**

职责：
- 读取 Redis 里的入口或列表 URL
- 输出当前页的探测记录
- 为后续详情扩展保留 `doctor_detail_candidates`
- 为翻页保留 `next_page_candidates`

**Step 3: 详情页 spider**

职责：
- 从 Redis 读取医生详情 URL
- 先按通用 HTML 结构提取最基础字段
- 当前提取不到时也要保留原始页面来源和状态信息

### Task 6: 验证与交付

**Files:**
- Modify: `projects/doctor-ywbd/README.md`

**Step 1: 运行测试**

Run:

```powershell
pytest projects/doctor-ywbd/tests -q
```

**Step 2: 做基础语法校验**

Run:

```powershell
python -m py_compile projects/doctor-ywbd/doctor_ywbd/route_hypotheses.py
python -m py_compile projects/doctor-ywbd/doctor_ywbd/settings.py
```

**Step 3: 在 README 里写清楚当前风险**

必须说明：
- 当前实时站点仍被 IP 级别拦截
- 路由里只有 `keshi/yisheng` 详情模式有公开旁证
- 其余类目入口与列表规则已做成可配置假设，等待放行后二次验证
