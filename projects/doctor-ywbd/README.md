# doctor-ywbd 医生采集项目

`doctor-ywbd` 用来采集 `https://data.120ask.com/` 的医生数据，项目目录在 `projects/doctor-ywbd`。

当前实现按真实页面链路拆成多阶段 spider，并且把 Redis key 拆到尽量细，方便断点续跑、补采和排查。

## 已确认入口

- 按疾病找医生：`https://data.120ask.com/yisheng/jibing.html`
- 按科室找医生：`https://data.120ask.com/yisheng/keshi.html`
- 按地区找医生：`https://data.120ask.com/yisheng/area.html`
- 按地区找医院：`https://data.120ask.com/yiyuan/area.html`

## 已确认链路

- 疾病索引页：`/yisheng/jibing.html`、`/yisheng/jibing_p*.html`
- 疾病医生列表页：`/yisheng/list_j*.html`
- 科室列表页：`/yisheng/list_d*.html`
- 地区列表页：`/yisheng/list_a*.html`
- 医院地区列表页：`/yiyuan/list_a*.html`
- 医院详情页：`/yiyuan/<hospital_slug>.html`
- 医院专家页：`/yiyuan/yisheng/<hospital_slug>.html`
- 医院专家 ajax：`/public/ajaxyisheng`
- 最终医生详情页：`/yisheng/<doctor_slug>.html`

## 队列和存储

- Redis 连接：复用 `doctor-circle`
- MongoDB 连接：复用 `doctor-circle`
- MongoDB 集合：`doctor_ywbd`

当前 Redis key：

- `doctor_ywbd:disease_index_url`
- `doctor_ywbd:disease_list_url`
- `doctor_ywbd:department_index_url`
- `doctor_ywbd:department_list_url`
- `doctor_ywbd:area_index_url`
- `doctor_ywbd:area_list_url`
- `doctor_ywbd:hospital_area_index_url`
- `doctor_ywbd:hospital_list_url`
- `doctor_ywbd:hospital_detail_url`
- `doctor_ywbd:hospital_expert_url`
- `doctor_ywbd:doctor_info_url`

设计原则：

- 上游入口、索引页、列表页、医院页、专家页、最终详情页都单独分队列
- 最终医生详情统一流入 `doctor_ywbd:doctor_info_url`
- Redis set 去重用于合流多个入口
- 只有第一页负责扩展完整分页，后续页只负责抽详情

## Spider 顺序

全量运行顺序：

1. `entry_seed_spider`
2. `disease_index_spider`
3. `disease_list_spider`
4. `department_index_spider`
5. `department_list_spider`
6. `area_index_spider`
7. `area_list_spider`
8. `hospital_area_index_spider`
9. `hospital_list_spider`
10. `hospital_detail_spider`
11. `hospital_expert_spider`
12. `doctor_detail_spider`

只消费最终详情时只运行：

- `doctor_detail_spider`

## 文件说明

`doctor_ywbd` 目录下主要文件：

- `items.py`：定义最终医生详情 item。
- `middlewares.py`：浏览器请求头注入、521 手工 cookie 提示、代理挂载。
- `pipelines.py`：MongoDB 入库。
- `probe_helpers.py`：入口页、列表页、医院专家页等链路解析工具。
- `redis_requests.py`：统一把请求包装成 scrapy-redis JSON 格式再入队。
- `route_hypotheses.py`：站点入口、Redis key、Mongo 集合名等命名约定。
- `settings.py`：Scrapy、Redis、Mongo、手工 cookie 配置。
- `start.py`：全量阶段式启动入口。
- `start_detail.py`：只消费最终医生详情队列。
- `tools.py`：运行时公共工具、手工 cookie 管理、代理工具。
- `js_bak.py`：知道创宇 JS 解盾备份代码，不参与当前运行时。

`doctor_ywbd/spiders/doctor` 目录下每个 `py` 文件职责：

- `01_entry_seed_spider.py`：把四个确认过的站点入口写入各自的 index 队列。
- `02_disease_index_spider.py`：消费疾病索引页，扩疾病索引翻页和具体疾病医生列表页。
- `03_disease_list_spider.py`：消费具体疾病医生列表页，抽医生详情，并在第一页展开完整分页。
- `04_department_index_spider.py`：消费科室入口页，只投放叶子科室列表页。
- `05_department_list_spider.py`：消费科室列表页，抽医生详情，并在第一页展开完整分页。
- `06_area_index_spider.py`：消费地区入口页，只投放区县级叶子地区列表页。
- `07_area_list_spider.py`：消费地区列表页，抽医生详情，并在第一页展开完整分页。
- `08_hospital_area_index_spider.py`：消费医院地区入口页，只投放区县级医院列表页。
- `09_hospital_list_spider.py`：消费医院地区列表页，拆分出医院翻页、医院详情页、医院专家页。
- `10_hospital_detail_spider.py`：消费医院详情页，补充页面直出的医生详情链接。
- `11_hospital_expert_spider.py`：消费医院专家页，先抓首屏，再请求 ajax 分页，补全医生详情链接。
- `12_doctor_detail_spider.py`：消费最终医生详情页，解析字段并入 MongoDB。

## 当前详情字段

`doctor_detail_spider` 最终落库字段：

- `_id`
- `url`
- `website`
- `doctor_name`
- `title`
- `gender`
- `hospital_name`
- `department_name`
- `good_at`
- `intro`
- `avatar_url`

真实样本见 `sample_doctor_detail_item.json`。

## Cookie 模式

- 项目当前走手工 cookie 模式
- 默认 cookie 放在 `doctor_ywbd/settings.py` 的 `YWBD_INITIAL_COOKIE`
- 运行时会自动把 `YWBD_INITIAL_COOKIE` 转成 `YWBD_INITIAL_COOKIE_HEADER`
- Scrapy 已关闭自带 `CookiesMiddleware`，直接发送手工 `Cookie` 请求头
- 如果返回 `521`，日志只提示手工更新 cookie，不再自动刷新
- 旧的 JS 解盾代码保存在 `doctor_ywbd/js_bak.py`，仅做备份，不参与当前运行

## 运行方式

推荐直接运行：

```powershell
.\start.ps1
```

也可以直接跑全量：

```powershell
python doctor_ywbd/start.py
```

只消费最终详情：

```powershell
python doctor_ywbd/start_detail.py
```

或者在项目根目录运行：

```powershell
scrapy crawl_all
```

## 说明

- 医院专家 ajax 依赖医院专家页返回的站点 cookie 和 Referer
- 521 只做日志提示，cookie 失效后手工替换 `YWBD_INITIAL_COOKIE`
- `findings.md` 里记录了当前真实侦察证据
