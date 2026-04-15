# doctor_wygk 调研结论

## 已证实接口

### 1. 科室接口

- 地址：
  `GET https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getDeptList`
- 已证实参数：
  - `visitSiteId=27`
  - `hospitalId=1`
  - `firstResult=0`
  - `maxResult=100`

### 2. 科室医生列表接口

- 地址：
  `GET https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getFrontDoctorList`
- 已证实参数：
  - `visitSiteId=27`
  - `deptId`
  - `deptName`

已确认能直接返回：

- `doctorId`
- `doctorName`
- `medicalTitle`
- `expertise`
- `deptNameList`
- `doctorUrl`

### 3. 医生详情接口

当前统一详情主口径已经切到 `personalInfo` 页背后的多接口合流。

#### 3.1 personalInfo 详情页

- 地址：
  `GET https://www.allinmd.cn/edu/personalInfo?doctorId=<doctorId>`

#### 3.2 personalInfo 基础信息接口

- 地址：
  `GET https://api-gateway.allinmd.cn/base-customer-platform/customer/auth/v1/getCustomerAuth`
- 已证实参数：
  - `queryJson={"customerId":"<doctorId>"}`

已确认能返回：

- `customerId`
- `fullName`
- `medicalTitleShow`
- `company`
- `department`
- `summary`
- `expertise`
- `illnessNameList`
- `logoUrl`

#### 3.3 personalInfo 扩展履历接口

- 地址：
  `GET https://api-gateway.allinmd.cn/allin-api-platform/services/customer/patent/v3/getMapList`
- 已证实参数：
  - `queryJson={"customerId":"<doctorId>"}`

已确认能返回：

- `occupationList`
- `socialList`
- `educationList`
- `continuingEducationList`
- `honorList`
- `fundList`
- `opusList`
- `patentList`

#### 3.4 personalInfo 大事记接口

- 地址：
  `GET https://api-gateway.allinmd.cn/base-customer-platform/customer/event/v4/getMapList`
- 已证实参数：
  - `queryJson={"customerId":"<doctorId>"}`

已确认能返回：

- `dataList[].event_name`

#### 3.5 旧详情兜底接口

- 地址：
  `GET https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/customer/auth/chongqing/procedure/getMapById`
- 已证实参数：
  - `doctorId`
  - `visitSiteId=27`

已确认能返回：

- `doctorId`
- `fullName`
- `medicalTitle`
- `hospitalName`
- `logoUrl`
- `expertise`
- `practiceIntroduction`
- `socialList`
- `abilityAcademicList`
- `abilityPracticeList`
- `honorList`

当前项目里的统一详情策略：

- 主字段优先取 `getCustomerAuth`
- 履历卡片优先取 `getMapList`
- 学术/执业成就和高清头像用 `getMapById` 做补充
- `source_url` 统一使用医生自己的 `personalInfo` 地址
- 最终入库时强制要求：
  `doctor_name`
  `hospital_name`
  `department_name`
  三项都非空

### 4. 医生文章接口

- 地址：
  `GET https://api-gateway.allinmd.cn/base_patienteducation_platform/cms/patient/education/api/getDoctorArticle`
- 已证实参数：
  - `refCustomerIdSetIn`
  - `sortType=8`
  - `firstResult`
  - `maxResult`
  - `isValid=1`
  - `educationContentTypeNotIn=5`
  - `status=1`
  - `attUseFlag=15`
  - `visitSiteId=27`

## 当前主结论

- 正式主链路采用医院科室接口
- 浏览器缓存态不进入正式主链路
- 所有来源最终都应该回流到统一 `doctor_info_url`

## 已验证的扩源链路

### 1. 直播历史链路

- 历史列表：
  `GET /live-service/pcd/live/activity/getAllActivityPageInfo`
- 详情补讲师：
  `GET /live-service/meeting/activity/getActivityDetail`

结论：

- 历史列表可拿全量 `activityId`
- 详情接口可稳定补出 `doctorList[].doctorId`
- 抽样 `24` 条历史活动，有 `21` 条带讲师医生

### 2. 课程链路

- 导航：
  `GET /ccos-training/mpd/credit/project/course/getNavigationList`
- 项目列表：
  `POST /ccos-training/mpd/credit/project/course/getProjectList`
- 项目详情：
  `GET /ccos-training/mpd/credit/project/getProductDetail`
- 课表：
  `POST /ccos-training/mpd/credit/project/course/getSystemCourseTimetable`

结论：

- 列表层不直接带医生
- 课表层稳定返回 `resCustomerList[].customerId`

### 3. 手术链路

- 列表：
  `GET /base-video-platform/cms/video/getFeedVideoList`

结论：

- 列表层直接返回 `resCustomerList[].customerId`

### 4. 协会 / 组织链路

- 组织资源：
  `GET /base-resource-platform/organization/resource/getResourceColumnList`
- 组织首页栏目：
  `GET /ccos-training/pcd/organization/homepage/getOrganizationColumnList`

结论：

- 列表层稳定返回 `resCustomerList[].customerId`
- `2026-04-14` 复核前端代码后，当前公开页固定请求：
  `getResourceColumnList?maxResult=4`
- 当前没有在前端代码里发现稳定公开分页口
- 因此项目里把它实现为“组织资源池 + organizationId=14 首页专题补口”，作为强补充来源接入，而不是宣称严格全量

### 5. 医生主页粉丝链路

- 主页主信息：
  `GET /landing-resource/mpd/doctor/mainpage/getDoctorInfo`
- 粉丝列表：
  `GET /allin-api-platform/services/customer/follow/fans/v2/getMapList`

已证实参数：

- `customerId=<doctorId>`
- `queryJson={"sortType":2,"followTypeFlag":31,"followType":1,"logoUseFlag":4,"customerId":"<doctorId>","firstResult":0,"maxResult":20}`

已确认能返回：

- 主页主信息中的：
  `customerId`
  `name`
  `company`
  `medicalTitle`
  `logoUrl`
  `fansCount`
- 粉丝列表中的：
  `customer_auth.customerId`
  `customer_auth.fullName`
  `customer_auth.company`
  `customer_auth.medicalTitleShow`
  `customer_att.logoUrl`

当前项目里的接入策略：

- 只用粉丝列表补医生入口，不直接作为最终详情
- 只保留 `company` 包含“医院”的粉丝账号
- 粉丝医生一律回流到统一 `doctor_info_url`
- 同时新增两组 Redis 状态：
  `doctor_home_task`
  `doctor_home_done`
- `doctor_home_task` 只存最小 `doctor_id`
- `doctor_home_done` 记录已经展开过粉丝页的医生 id，用来防止 A/B 互关导致循环
