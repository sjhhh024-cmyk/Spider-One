# doctor_wygk 医生采集项目

`doctor_wygk` 用来采集唯医骨科公开链路里的医生数据，项目目录在 `projects/doctor_wygk`。

当前阶段已经把“医院 -> 科室 -> 医生列表 -> 医生详情”主链路，以及直播、课程、手术、组织、医生主页粉丝五个公开来源一起并入项目。医生详情已经切到 `personalInfo` 页背后的公开接口合流，字段比旧版 `getMapById` 更完整。

## 当前定位

- 主架构：分层多 spider
- 主链路：公开接口优先
- 详情口径：统一合流到一个详情 spider
- 浏览器缓存态：只用于后续侦察，不进入正式采集主链路

## 当前已确认主链路

- 医院页：`https://patient.allinmd.cn/interrogation/hospitalHome`
- 科室接口：`/tocure-api-platform/services/tocure/dept/getDeptList`
- 科室医生列表接口：`/tocure-api-platform/services/tocure/dept/getFrontDoctorList`
- 医生详情页：`https://www.allinmd.cn/edu/personalInfo?doctorId=<doctorId>`
- 医生详情基础接口：`/base-customer-platform/customer/auth/v1/getCustomerAuth`
- 医生详情扩展卡片接口：`/allin-api-platform/services/customer/patent/v3/getMapList`
- 医生详情大事记接口：`/base-customer-platform/customer/event/v4/getMapList`
- 医生详情兜底接口：`/tocure-api-platform/services/tocure/customer/auth/chongqing/procedure/getMapById`

## 当前已接入来源

- 医院科室链路：
  `getDeptList -> getFrontDoctorList -> personalInfo 多接口合流`
- 直播历史链路：
  `getAllActivityPageInfo -> getActivityDetail -> doctorList[].doctorId`
- 课程链路：
  `getNavigationList -> getProjectList -> getProductDetail -> getSystemCourseTimetable -> resCustomerList[].customerId`
- 手术链路：
  `getFeedVideoList -> resCustomerList[].customerId`
- 组织链路：
  `getResourceColumnList / getOrganizationColumnList -> resCustomerList[].customerId`
- 医生主页粉丝链路：
  `getDoctorInfo -> getFansList -> customer_auth.customerId`

当前确认过的关键参数：

- `visitSiteId=27`
- `hospitalId=1`

## 当前 Redis 任务链

- `hospital_home_url`
  医院入口种子和入口追踪
- `dept_task`
  医院级科室扩展任务
- `doctor_list_task`
  科室医生列表扩展任务
- `doctor_info_url`
  统一医生详情任务
- `doctor_home_task`
  待展开的医生主页任务，只存最小 `doctor_id`，专门用于粉丝扩散，避免同一个医生因为来源不同反复入队
- `doctor_home_done`
  已经展开过粉丝列表的医生 id 集合，用来截断互相关注导致的循环

## 当前设计原则

- 主链路只做稳定接口
- Redis key 按任务语义拆清楚
- 所有医生最终统一进入 `doctor_info_url`
- 医生主页粉丝扩散只负责补入口，不直接入库
- Mongo 只落最终医生结果，不落中间任务状态
- 最终入库硬门槛：
  `doctor_name`
  `hospital_name`
  `department_name`
  这三个字段缺任意一个，都不入库

## 当前阶段说明

这版项目优先保证：

1. 结构清楚
2. 主链路稳定
3. 后续补入口容易接入

额外说明：

- `doctor_detail_spider` 现在既处理医院主链路详情，也处理四个公开来源的直接合流任务。
- 统一详情顺序是：
  `getCustomerAuth -> getMapList(履历卡片) -> getMapById(兜底补充) -> getBigEvent`
- `source_url` 统一落医生自己的 `personalInfo` 地址。
- `personalInfo` 属于详情增强来源，不会降低主链路对“姓名 / 医院 / 科室”三项必填的要求。
- 当前最终文档除基础字段外，还会补：
  `doctor_illnesses`
  `doctor_social_titles`
  `doctor_honors`
  `doctor_academic_achievements`
  `doctor_practice_achievements`
  `doctor_work_experiences`
  `doctor_educations`
  `doctor_continuing_educations`
  `doctor_funds`
  `doctor_opuses`
  `doctor_patents`
  `doctor_big_events`
- 组织模块当前走“组织资源池 + CAOS 首页专题补口”。
- 医生主页粉丝模块当前走：
  `getDoctorInfo(customerId) -> getMapList(queryJson)`，
  只保留 `company` 包含“医院”的粉丝账号，再回流到统一详情链路。
- `doctor_home_task` 故意只存 `{"doctor_id":"..."}`，不是为了省几字节，而是为了让 Redis set 真正按医生去重；如果把来源页、姓名、头像都塞进去，同一个医生从不同入口回流时会生成很多份不同 JSON，主页扩散就会反复展开。
- 截至 `2026-04-14`，组织首页前端仍只固定请求 `maxResult=4` 的资源池接口，没有发现稳定的公开分页口，所以这一块目前是强补充来源，不宣称严格全量。
