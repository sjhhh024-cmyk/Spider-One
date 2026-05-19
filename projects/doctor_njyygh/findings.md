# doctor_njyygh 站点侦察

目标站点：`https://www.nj12320.org/njres/reservation/hos_search.do`

站点名称：南京市预约挂号服务平台

侦察日期：2026-05-19

## 任务单

- `target_site`: `www.nj12320.org`
- `entity_type`: 医生为主，医院和科室作为链路实体
- `requested_fields`: 用户暂未指定，按医生通用模板优先保留姓名、医院、科室、职称、简介/擅长、头像、来源
- `scope`: 南京市预约挂号平台公开页面
- `expansion_mode`: 医院列表 -> 科室页 -> 医生详情
- `delivery_format`: 当前阶段先收集信息，后续可落 Scrapy 项目
- `stopping_rule`: 医院列表页码结束；科室页无医生链接时跳过；医生详情按 `docid + hoscode` 去重
- `risk_notes`: 页面带有安全脚本和动态 `jsessionid`，但主链路 HTML 请求当前可直接访问；不要尝试预约提交、登录或绕过强校验

## 已验证主链路

### 1. 医院列表

入口：

```text
GET https://www.nj12320.org/njres/reservation/hos_search.do
```

已验证返回：

- 状态码 200
- HTML 内直接包含医院列表
- 首屏统计：`找到 47 家医院`
- 分页统计：`共47条数据 页次:1/6页`

分页：

```text
POST https://www.nj12320.org/njres/reservation/hos_search.do
Content-Type: application/x-www-form-urlencoded

currentpage=2&hoslevel=&hosname=&hostype=
```

已验证第 2 页可返回真实不同医院列表，分页文案为 `页次:2/6页`。

筛选参数：

- `hoslevel`: 医院类型
  - `0`: 省部医院
  - `1`: 市属医院
  - `2`: 区属医院
  - `3`: 部队医院
  - `4`: 其他医院
- `hostype`: 医院等级
  - `3`: 三级医院
  - `2`: 二级医院
  - `1`: 一级医院
  - `0`: 其他医院
- `hosname`: 医院名关键词

样例：

```text
GET /njres/reservation/hos_search.do?hosname=%E9%BC%93%E6%A5%BC
```

已验证可返回 `找到 4 家医院`。

列表页可解析字段：

- `hospital_id`: `hoscode`
- `hospital_name`
- `hospital_level`
- `hospital_type`
- `hospital_intro_summary`
- `hospital_avatar_url`: `/njres/images/hospic/<hoscode>.jpg`
- 科室链接：`/njres/reservation/dep_detail.do?depid=<depid>`
- 医院详情：`/njres/hospital/hos_showHosDetail.do?hoscode=<hoscode>`
- 查看医生/预约页：`/njres/reservation/hos_showReservation.do?hoscode=<hoscode>`

### 2. 医院详情

样例：

```text
GET https://www.nj12320.org/njres/hospital/hos_showHosDetail.do?hoscode=32010100
```

已验证可返回南京鼓楼医院详情 HTML。

可解析字段：

- `hospital_name`: 南京鼓楼医院
- `hospital_level`: 三级甲等
- `hospital_address`: 南京市中山路321号
- `hospital_phone`: 025-83304616
- `hospital_website`: http://www.njglyy.com/
- `hospital_intro`
- 开放预约科室列表及 `depid`

注意：

- 部分请求偶发 404/空响应，建议后续实现中加浏览器常见请求头、重试和限速。
- 链接中经常出现 `;jsessionid=...`，解析时应移除该段，保留 query 参数。

### 3. 科室详情 / 医生列表

样例：

```text
GET https://www.nj12320.org/njres/reservation/dep_detail.do?depid=1501118
```

已验证返回：

- 科室：`1型糖尿病专病`
- 医院：`南京鼓楼医院`
- 医院等级：`三级甲等`
- 科室简介：`内分泌专业`
- 医生列表区域标题：`可预约专家`

医生链接样例：

```text
/njres/reservation/doc_detail.do?docid=441295&hoscode=32010100
```

科室页可解析医生摘要字段：

- `doctor_id`: `docid`
- `hospital_id`: `hoscode`
- `doctor_name`: 陆婧
- `doctor_title`: 副主任医师
- `doctor_avatar_url`: `/njres/images/ys.jpg`
- `doctor_intro_summary`
- `doctor_department`: 当前科室名
- `doctor_hospital`: 当前医院名

注意：

- `dep_detail.do?depid=1501118&hoscode=32010100` 曾返回 500；只带 `depid` 的 URL 当前更稳定。
- 科室到医院的关系可从列表页或医院详情页继承，不必强行把 `hoscode` 拼回科室详情 URL。

### 4. 医生详情

样例：

```text
GET https://www.nj12320.org/njres/reservation/doc_detail.do?docid=441295&hoscode=32010100
```

已验证可直接访问，不需要登录。

可解析字段：

- `doctor_id`: `441295`
- `hospital_id`: `32010100`
- `doctor_name`: 陆婧
- `doctor_hospital`: 南京鼓楼医院
- `doctor_hospital_grade`: 三级甲等
- `doctor_department`: 1型糖尿病专病
- `doctor_title`: 副主任医师
- `doctor_avatar_url`: `/njres/images/ys.jpg`
- `intro`: 页面 `简介` 的完整文本
- `doctor_specialties`: 页面未单独结构化，简介中包含“擅长...”句，可后处理切分
- `schedule_raw`: 可选，`toShowSchedule('32010100',55665962,'pm',441295)` 和 title 中包含门诊类型、出诊时间、挂号费

## 搜索链路验证

页面搜索脚本 `submitSearch()` 映射如下：

- 医院搜索：
  - action: `/njres/reservation/hos_search.do`
  - 参数：`hosname`
  - 已验证 GET 查询可用
- 科室搜索：
  - action: `/njres/reservation/depsearch_searchDept.do`
  - 参数：`depName`, `changeFlay=1`
  - 曾验证 POST `depName=糖尿病` 可返回 `找到 30 个科室`
  - 该页看起来偏科室名索引，不建议作为主链路
- 医生搜索：
  - action: `/njres/reservation/hos_showReservation.do`
  - 参数：`docname`
  - 直接 POST `docname=陆婧` 返回 `非法的请求`
  - 不建议作为主链路

不要使用这些猜测接口：

- `/njres/reservation/doc_search.do?docname=...`：已返回 500
- `/njres/reservation/dep_search.do?depName=...`：已返回 500

## 推荐实现路线

优先做 HTML 请求重放，不需要浏览器常驻。

1. `entry_seed_spider`
   - 写入医院列表入口第 1 页
2. `hospital_list_spider`
   - 请求 `hos_search.do`
   - 解析总页数、医院摘要、医院详情 URL、科室 URL
   - 生成后续分页任务和医院详情/科室详情任务
3. `hospital_detail_spider`
   - 请求 `hos_showHosDetail.do?hoscode=<hoscode>`
   - 写入 `hospital_njyygh`
   - 补充更多科室链接
4. `department_detail_spider`
   - 请求 `dep_detail.do?depid=<depid>`
   - 解析科室信息和医生详情链接
   - 生成医生详情任务
5. `doctor_detail_spider`
   - 请求 `doc_detail.do?docid=<docid>&hoscode=<hoscode>`
   - 写入 `doctor_njyygh`

## 去重键建议

医生：

```text
doctor_njyygh:<docid>:<hoscode>
```

医院：

```text
hospital_njyygh:<hoscode>
```

科室：

```text
department_njyygh:<depid>
```

## 请求与解析注意点

- 统一删除 URL 中的 `;jsessionid=<...>`，避免同一资源重复入队。
- 请求头建议至少带：
  - `User-Agent`
  - `Accept`
  - `Accept-Language: zh-CN,zh;q=0.9`
- 遇到 404、500、空 body 时不要立即判定结构错误，应重试并记录样本 URL。
- 页面包含 `$_ts`、动态 meta 和 `/XPyVjfO3RPd7/...js` 安全脚本；当前主链路可直接请求，后续若批量受限再考虑浏览器或 Cookie 维持。
- 不采集预约提交接口，不访问登录后接口。

## 字段口径建议

医生核心字段：

```json
{
  "_id": "441295:32010100",
  "doctor_id": "441295",
  "doctor_name": "陆婧",
  "doctor_hospital": "南京鼓楼医院",
  "doctor_department": "1型糖尿病专病",
  "doctor_title": "副主任医师",
  "doctor_avatar_url": "https://www.nj12320.org/njres/images/ys.jpg",
  "doctor_specialties": "从简介中按“擅长”切分，无法切分则留空",
  "intro": "医生详情页简介全文",
  "doctor_hospital_grade": "三级甲等",
  "hospital_id": "32010100",
  "source_site": "南京市预约挂号服务平台",
  "source_url": "https://www.nj12320.org/njres/reservation/doc_detail.do?docid=441295&hoscode=32010100",
  "crawl_time": "运行时生成"
}
```

医院核心字段：

```json
{
  "_id": "32010100",
  "hospital_id": "32010100",
  "hospital_name": "南京鼓楼医院",
  "hospital_address": "南京市中山路321号",
  "hospital_phone": "025-83304616",
  "hospital_intro": "医院详情页简介全文",
  "hospital_level": "三级甲等",
  "hospital_type": "市属医院",
  "hospital_website": "http://www.njglyy.com/",
  "hospital_offices": "开放预约科室列表",
  "source_site": "南京市预约挂号服务平台",
  "source_url": "https://www.nj12320.org/njres/hospital/hos_showHosDetail.do?hoscode=32010100",
  "crawl_time": "运行时生成"
}
```

## 最小验证样本

已验证样本链路：

```text
医院列表第 1 页
  -> 南京鼓楼医院 hoscode=32010100
  -> 科室 1型糖尿病专病 depid=1501118
  -> 医生 陆婧 docid=441295
  -> 医生详情 doc_detail.do?docid=441295&hoscode=32010100
```

后续实现完成后，建议最小验证：

- 医院列表第 1 页解析不少于 1 家医院
- 第 2 页分页结果与第 1 页不同
- 医院详情解析出地址、电话、简介
- 科室页解析出至少 1 条医生详情链接
- 医生详情解析出姓名、医院、科室、职称、简介
- 对 `doctor_id + hospital_id` 去重后不重复入库
