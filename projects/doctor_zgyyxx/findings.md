# doctor_zgyyxx 当前观察结论

目标站点：

- `https://www.dayi.org.cn/list/3`

目标实体：

- 医生

当前阶段：

- 只做站点观察
- 暂不启动采集实现

## 已确认页面

以下页面在当前环境下已经实际访问成功：

1. `https://www.dayi.org.cn/list/3`
2. `https://www.dayi.org.cn/doctor/1120165.html`

同时已对照访问：

1. `https://www.dayi.org.cn/list/1`
2. `https://www.dayi.org.cn/list/2`
3. `https://www.dayi.org.cn/list/100`
4. `https://www.dayi.org.cn/list/3/2`
5. `https://www.dayi.org.cn/list/3/3`
6. `https://www.dayi.org.cn/list/2/2`

其中：

- `/list/1` 是症状栏目
- `/list/2` 是医院栏目
- `/list/3` 是医生栏目
- `/list/100` 返回 404 页面

## 当前已确认的站点形态

这个站点不是纯前端空壳页，首屏数据已经直接渲染在 HTML / Nuxt 状态里。

当前从医生列表页首屏 HTML 中已经确认：

- 当前页码：`pageNo: 1`
- 每页条数：`pageSize: 10`
- 总量字段：`totalCount: 1000`
- 列表页详情前缀：`detailPath: "/doctor"`
- 分页前缀：`paginationPathPrefix: "/list"`

当前已经实际验证的医生栏目分页规则：

- 第 1 页：`/list/3`
- 第 2 页：`/list/3/2`
- 第 3 页：`/list/3/3`

并且样本页已经确认：

- `/list/3/2` 返回 `pageNo: 2`
- `/list/3/3` 返回 `pageNo: 3`
- 不同分页页面的医生详情链接确实发生变化

列表首屏内嵌数据样本已确认包含：

- `id`
- `title`
- `thumbnail`
- `introduction`
- `clinicProfessional`
- `departmentName`
- `institutionName`
- `classType`

这说明医生列表首屏至少可以稳定拿到：

- 医生 ID
- 医生姓名
- 头像
- 简介摘要
- 医院名
- 科室名
- 职称

## 已确认的详情字段

样本详情页：

- `https://www.dayi.org.cn/doctor/1120165.html`

当前已从详情页 HTML 中确认能拿到的字段组包括：

- `mapHospital`
- `mapDepartment`
- `visitInfo`
- `education`
- `workExperience`
- `researchArea`
- `academic`
- `production`
- `science`
- `bookmaking`
- `thesis`
- `honorary`

从页面文本也已确认能直接看到：

- 医生姓名
- 医院
- 科室
- 职称
- 诊治范围 / 擅长方向
- 教育经历
- 工作经历
- 研究方向
- 学术成果相关信息
- 出诊信息

结论：

- 详情页信息密度高
- 首选路线仍然是公开 HTML / 页面内嵌状态解析
- 目前暂时没有必须上浏览器自动化的迹象

## 已确认的医院补医生链路

医院列表样本页：

- `https://www.dayi.org.cn/list/2`

医院详情样本页：

- `https://www.dayi.org.cn/hospital/1125632.html`

当前已确认：

- 医院列表首屏同样是 SSR / Nuxt 状态直出
- 医院列表首屏字段包含：
  - `id`
  - `title`
  - `thumbnail`
  - `introduction`
  - `secondType`
  - `secondTitle`
  - `classType`
- 医院详情页首屏状态里暴露了医院详情数据结构

医院详情页前端字典中已经明确存在：

- `专家团队`
- 对应字段键：`doctors`

并且当前样本页已经实际确认 `doctors` 数据存在于首屏内嵌状态，样本结构包含：

- `url`
- `name`
- `job`
- `zl`

从样本内容可直接看出，这组字段已经能覆盖：

- 医生姓名
- 医生头像
- 医生职务 / 职称 / 任职描述
- 诊疗专长

同时医院详情页内还可拿到：

- 医院名称
- 医院等级
- 医院地址
- 科室设置 `offices`
- 特色专科 `special`

结论：

- “医院列表 -> 医院详情 -> doctors 专家团队” 这条链路已经被样本证实可行
- 它比当前直接依赖医生栏目分页更稳
- 很适合作为医生抓取的主补充链路，甚至可以优先于医生栏目分页侦察

## 当前最大的风险点

### 1. 暂未在首屏 HTML 中直接观察到清晰公开医生列表接口

目前只在 HTML / Nuxt 状态里确认到了：

- `doctorDetail`
- `institutionName`

但还没有直接定位到一个可复用的医生列表 JSON 接口地址。

这意味着如果后续还要走“医生栏目全量采集”，仍然需要先补一轮：

- 浏览器网络面板侦察
- 或 Nuxt / bundle 代码里继续追真实取数口

但如果先走医院链路，这个风险会明显下降。

### 2. `totalCount=1000` 仍需二次确认

当前医生栏目和医院栏目样本页都出现了：

- `totalCount: 1000`

这可能是：

- 真实总量
- 当前列表的封顶展示量
- 或站点统一对外暴露的上限值

这个值在后续实现前仍然值得单独核实。

## 当前推荐路线

按稳定性从高到低，建议这样推进：

1. 医生栏目主链路已可按 `/list/3`、`/list/3/<page>` 继续扩页
2. 同时保留“医院列表 -> 医院详情 -> doctors”作为补充扩源链路
3. 医生列表拿到基础字段后，再回流到标准医生详情页做字段补全
4. 如果后面能找到公开 JSON 接口，再升级成请求重放
5. 只有在前几条都不成立时，才考虑浏览器自动化

## 当前阶段建议

这个项目目前适合定义为：

- `可做`
- `但先停在观察阶段`

原因是：

- 首屏列表和详情都能拿到有效医生信息
- 详情字段覆盖已经足够做医生项目
- 医院详情页已确认存在 `doctors` 专家团队补充链路
- 医生栏目分页规则已经实测成立
- 真正的不确定点主要集中在“总量是否封顶”和“医院补充链路的覆盖率”

因此下一步最值得做的不是继续停留在纯观察，而是带着这两条已证实链路做最小实现验证，重点确认：

1. 医生栏目是否能稳定顺序翻到更深页
2. `totalCount=1000` 是否为真实总量，还是站点统一封顶值
3. 医院详情里的 `doctors` 是否所有医院都稳定存在
4. `doctors` 里的专家是否都能映射到独立医生详情页
5. 医生详情页字段是否全部来自 SSR，还是有部分依赖二次请求

## 当前结论

`doctor_zgyyxx` 已确认属于可采集医生站点，而且“从医院页补充医生”是当前更稳的方向。

现阶段最稳的判断是：

- 列表首屏：可解析
- 医生栏目分页：已证实可用，规则为 `/list/3/<page>`
- 医生详情：可解析
- 医院详情专家团队：已证实可解析
- 推荐状态：可以进入最小实现，医生主链路加医院补充链路并行
