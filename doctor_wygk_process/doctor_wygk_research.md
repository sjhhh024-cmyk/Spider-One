# doctor_wygk 调研记录

## 目标站点

- 首页: `https://www.allinmd.cn/edu/home?ch=1642644453342UeW`
- 患者端: `https://patient.allinmd.cn`

## 已确认的医生采集入口

### 1. 医院医生列表入口

- 页面路由: `https://patient.allinmd.cn/interrogation/hospitalHome`
- 前端 chunk: `__patient_chunk_38.js`
- 列表接口:
  `GET https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getFrontDoctorList`

已验证参数:

- `visitSiteId=27`
- `deptId=` 可空
- `deptName=全部`

已验证返回字段:

- `doctorId`
- `doctorName`
- `medicalTitle`
- `expertise`
- `deptNameList`
- `doctorUrl`

已验证样例:

- `https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getFrontDoctorList?visitSiteId=27&deptId=&deptName=%E5%85%A8%E9%83%A8`

### 2. 科室列表入口

- 接口:
  `GET https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/dept/getDeptList`

已验证参数:

- `visitSiteId=27`
- `hospitalId=1`
- `firstResult=0`
- `maxResult=100`

用途:

- 先拿医院下的科室
- 再把 `deptId` / `deptName` 带入 `getFrontDoctorList` 细分采集

### 3. 医生详情入口

#### 3.1 personalInfo 详情页

- 页面路由:
  `https://www.allinmd.cn/edu/personalInfo?doctorId=<doctorId>`
- 前端 chunk:
  `30.8f6dea6919aff9851504.js`

前端已确认调用 3 个公开接口：

1. `GET /base-customer-platform/customer/auth/v1/getCustomerAuth`
2. `GET /allin-api-platform/services/customer/patent/v3/getMapList`
3. `GET /base-customer-platform/customer/event/v4/getMapList`

已验证参数:

- `queryJson={"customerId":"<doctorId>"}`

`getCustomerAuth` 已验证返回字段:

- `customerId`
- `fullName`
- `medicalTitleShow`
- `company`
- `department`
- `summary`
- `expertise`
- `illnessNameList`
- `logoUrl`

`getMapList` 已验证返回字段:

- `occupationList`
- `socialList`
- `educationList`
- `continuingEducationList`
- `honorList`
- `fundList`
- `opusList`
- `patentList`

`getBigEvent` 已验证返回字段:

- `dataList[].event_name`

结论:

- `personalInfo` 确实比旧详情页更全
- 适合作为当前统一医生详情主口径
- `source_url` 应统一落到 `personalInfo` 页

#### 3.2 旧详情接口兜底

- 旧页面路由:
  `https://patient.allinmd.cn/interrogation/doctor/detail?doctorId=<doctorId>&doctorCustomerId=<doctorId>&from=find`
- 旧详情接口:
  `GET https://api-gateway.allinmd.cn/tocure-api-platform/services/tocure/customer/auth/chongqing/procedure/getMapById`

已验证参数:

- `doctorId`
- `visitSiteId=27`

已验证返回字段:

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
- `settingInfo`

结论:

- 旧接口仍然有价值
- 当前更适合作为统一详情的兜底补充，而不是主来源

### 4. 医生文章扩展入口

- 接口:
  `GET https://api-gateway.allinmd.cn/base_patienteducation_platform/cms/patient/education/api/getDoctorArticle`

已验证参数:

- `refCustomerIdSetIn=<doctorId>`
- `sortType=8`
- `firstResult=0`
- `maxResult=3`
- `isValid=1`
- `educationContentTypeNotIn=5`
- `status=1`
- `attUseFlag=15`
- `visitSiteId=27`

已验证返回字段:

- `educationId`
- `educationName`
- `webStoragePath`

## 页面和接口来源

### consult_online 路由

来源文件:

- `__patient_chunk_46.js`

确认到:

- 页面路由: `/interrogation/consult_online`
- 接口: `/base-search-service/search/tocure/customer/searchCustomer`
- 默认参数:
  - `firstResult`
  - `maxResult`
  - `logoUseFlag=5`
  - `searchName`
  - `specialty`
  - `region`
  - `searchCustomerQuality=1`
  - `miniAppType=1`

备注:

- 该接口在当前环境下直接请求多次返回 `504 Gateway Timeout`
- 代码层面它仍然是一个公开医生搜索入口，但当前更稳的入口是 `hospitalHome -> getFrontDoctorList`

## 当前推荐采集路线

1. 先用 `getDeptList` 拉科室
2. 对每个科室调用 `getFrontDoctorList`
3. 拿到 `doctorId` 后调用 `personalInfo` 多接口合流
4. 需要扩展内容时，再调 `getDoctorArticle`

## 2026-04-14 追加侦察

本轮重点继续验证 `https://www.allinmd.cn/edu/organization` 相关模块，以及课程 / 直播 / 手术几个模块里，是否存在更适合做“全量医生补入口”的公开接口。

### 5. 协会 / 组织模块

#### 5.1 组织资源总列表

- 接口:
  `GET https://api-gateway.allinmd.cn/base-resource-platform/organization/resource/getResourceColumnList`

已验证参数样例:

- `maxResult=4`
- `opUsr=`

已验证结论:

- 返回 `data.orgResourceCount=30380`
- 资源条目内存在 `resCustomerList`
- `resCustomerList` 内稳定返回:
  - `authorId`
  - `customerId`
  - `name`
  - `company`
  - `medicalTitle`
  - `customerActionUrl`

判断:

- 这是一个很强的“医生候选池”入口
- 键不是 `doctorId`，但 `customerId` 已足够作为医生身份键使用

#### 5.2 组织首页栏目

- 接口:
  `GET https://api-gateway.allinmd.cn/ccos-training/pcd/organization/homepage/getOrganizationColumnList`

已验证参数样例:

- `organizationId=14`
- `opUsr=`

已验证结论:

- `videoList` 等栏目资源内同样有 `resCustomerList[].customerId`
- 可作为组织专题内的医生补充来源

### 6. 直播模块

#### 6.1 近期直播列表

- 接口:
  `GET https://api-gateway.allinmd.cn/live-service/pcd/live/activity/v2/getLiveActivityPage`

已验证参数样例:

- `opUsr=`
- `customerId=`
- `visitSiteId=1`
- `pageNum=1`
- `pageSize=5`
- `statusList=20,40,50,60,70`

已验证返回字段:

- `activityId`
- `activityTitle`
- `professionList`
- `doctorList`

`doctorList` 已验证字段:

- `doctorId`
- `doctorName`
- `medicalTitle`
- `company`

判断:

- 这是直播模块里最强的医生入口
- 列表页就直接回 `doctorList[].doctorId`
- 但按 `2026-04-14` 实测，总量只有 `total=7`
- 更像“近期直播医生直出列表”，不够覆盖历史全量

#### 6.2 历史直播全量列表 + 详情补医生

- 历史列表接口:
  `GET https://api-gateway.allinmd.cn/live-service/pcd/live/activity/getAllActivityPageInfo`
- 详情接口:
  `GET https://api-gateway.allinmd.cn/live-service/meeting/activity/getActivityDetail`

历史列表已验证参数样例:

- `opUsr=`
- `customerId=`
- `visitSiteId=1`
- `pageNum=1`
- `pageSize=10`

详情接口已验证参数样例:

- `activityId=3533`
- `bizType=2`
- `pageSize=5`
- `userId=`
- `userType=`

来源确认:

- `liveDetail` 页面 chunk: `__live_detail_chunk_47.js`
- store 逻辑文件: `__allinmd_main.js`
- 已确认页面调用 `getLiveDetailData -> /live-service/meeting/activity/getActivityDetail`
- 返回 `doctorList` 后直接写入页面右侧 `teacherData`

已验证结论:

- `getAllActivityPageInfo` 在 `2026-04-14` 实测:
  - `totalCount=2365`
  - `totalPageCount=237`
  - 列表层 `doctorList=null`
- `getActivityDetail` 可对单个 `activityId` 补出:
  - `doctorList[].doctorId`
  - `doctorList[].doctorName`
  - `doctorList[].medicalTitle`
  - `doctorList[].company`
  - `doctorList[].headUrl`

历史样本实测:

- 第 `1` 页首条 `activityId=3533`:
  - `detail doctorList=4`
- 第 `20` 页首条 `activityId=3344`:
  - `detail doctorList=3`
- 第 `80` 页首条 `activityId=2613`:
  - `detail doctorList=0`
- 第 `160` 页首条 `activityId=1531`:
  - `detail doctorList=5`
- 第 `237` 页首条 `activityId=380`:
  - `detail doctorList=0`
- 按每 `10` 页抽 `1` 条、共抽 `24` 条样本:
  - `doctorList > 0` 的有 `21` 条
  - `doctorList = 0` 的有 `3` 条

判断:

- 直播模块已经确认存在“历史全量 activityId 列表 -> 详情补 `doctorId`”的正式链路
- 这条链路比近期列表更适合做全量直播医生采集
- 从抽样看覆盖率很高，但不是 100% 每场历史直播都有讲师列表，极老活动里存在 `doctorList=0` 的情况
- 适合并入主架构，作为医院科室链路之外的强补充来源

#### 6.3 全部会议列表

- 接口:
  `GET https://api-gateway.allinmd.cn/allinmd-integration-service/find/getMeetingPage`

已验证参数样例:

- `pageNum=1`
- `pageSize=5`
- `classificationId=0`
- `visitSiteId=1`

已验证结论:

- 返回量大，示例 `total=1464`
- 但样本里 `doctorList` 为空
- 更偏会议资源列表，不适合单独作为医生主入口

#### 6.4 会议搜索接口

- 接口:
  `GET https://api-gateway.allinmd.cn/allinmd-integration-service/global/search/partSearch`

会议搜索已验证参数样例:

- `visitSiteId=1`
- `pageNum=1`
- `pageSize=5`
- `partSearchChannel=0`
- `partSearchType=8`
- `keyWord=骨`

已验证结论:

- 搜索结果能拿到会议资源
- 但样本中没有直接稳定的医生主键字段
- 仍然只适合作为搜索探测，不建议并入主链路

### 7. 手术模块

#### 7.1 手术视频列表

- 接口:
  `GET https://api-gateway.allinmd.cn/base-video-platform/cms/video/getFeedVideoList`

已验证参数样例:

- `professionId=`
- `propertyId=`
- `queryType=1`
- `pageSize=5`
- `pageNum=1`
- `includeInternation=0`
- `visitSiteId=1`

已验证返回字段:

- `resId`
- `resName`
- `resTwoTypeName`
- `resCustomerList`

`resCustomerList` 已验证字段:

- `authorId`
- `customerId`
- `name`
- `company`
- `medicalTitle`
- `customerActionUrl`

判断:

- 这是手术模块里的强入口
- 量大，示例 `total=3606`
- 列表页直接可拿医生 `customerId`

#### 7.2 手术搜索接口

- 接口:
  `GET https://api-gateway.allinmd.cn/allinmd-integration-service/global/search/partSearch`

手术搜索已验证参数样例:

- `visitSiteId=1`
- `pageNum=1`
- `pageSize=5`
- `partSearchChannel=0`
- `partSearchType=5`
- `keyWord=膝`

已验证结论:

- 搜索结果样本中有两种情况:
  - 有 `authors[].id`
  - 仅资源基础字段，没有稳定作者
- 结果结构不如 `getFeedVideoList` 稳定
- 适合作为补充，不适合做主链路

### 8. 课程模块

#### 8.1 课程导航列表

- 接口:
  `GET https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getNavigationList`

已验证参数样例:

- `customerId=`
- `visitSiteId=1`

用途:

- 获取课程导航树
- 产出 `channel/propertyId`，供后续项目列表使用

#### 8.2 课程项目列表

- 接口:
  `POST https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getProjectList`

已验证请求体样例:

- `channelId=406`
- `propertyOneList=[]`
- `propertySecList=[]`
- `courseTagList=[]`
- `sortType=1`
- `pageNum=1`
- `pageSize=5`
- `customerId=`
- `distinctId=doctor_wygk_probe`

已验证结论:

- 示例 `total=103`
- 只返回课程项目基础信息，如:
  - `projectId`
  - `projectName`
  - `courseCount`
  - `courseDuration`
- 不直接带医生信息

判断:

- 课程模块不能只停在列表
- 需要进入项目详情课表接口

#### 8.3 课程项目详情

- 接口:
  `GET https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/getProductDetail`

已验证参数样例:

- `projectId=550`
- `customerId=`
- `visitSiteId=1`

已验证结论:

- 能拿到:
  - `projectId`
  - `projectName`
  - `videoAllCount`
  - `updateVideoCount`
  - `channelList`
- 但 `doctorList` 样本为空
- `channelList` 中课程栏目 `channelType=5`

#### 8.4 课程介绍模块

- 接口:
  `GET https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getIntroModuleList`

已验证参数样例:

- `courseId=550`
- `customerId=`
- `visitSiteId=1`

用途:

- 拿课程简介
- 不产出医生键

#### 8.5 课程课表筛选

- 接口:
  `GET https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getSystemCourseTimetableFilter`

已验证参数样例:

- `courseId=550`
- `customerId=`
- `channelId=1524`
- `visitSiteId=1`

用途:

- 先拿排序和筛选项
- 再请求课表列表

#### 8.6 课程课表列表

- 接口:
  `POST https://api-gateway.allinmd.cn/ccos-training/mpd/credit/project/course/getSystemCourseTimetable`

已验证请求体样例:

- `projectId=550`
- `customerId=`
- `channelId=1524`
- `sortTypeId=1`

已验证返回字段:

- `courseGroupResultList[].courseGroupList[].resourceId`
- `courseGroupResultList[].courseGroupList[].resourceName`
- `courseGroupResultList[].courseGroupList[].resCustomerList`

`resCustomerList` 已验证字段:

- `authorId`
- `customerId`
- `name`
- `company`
- `medicalTitle`
- `customerActionUrl`

判断:

- 这是课程模块里真正可落地的医生入口
- 结构是:
  `课程导航 -> 项目列表 -> 项目详情(getProductDetail) -> 课表(getSystemCourseTimetable)`
- 每节课程视频都能稳定回流讲者 `customerId`

#### 8.7 国际课程

- 接口:
  `GET https://api-gateway.allinmd.cn/base-video-platform/cms/video/getInternationalVideoList`

已验证参数样例:

- `opUsr=`
- `pageNum=1`
- `pageSize=5`
- `videoSource=`
- `professionId=`
- `propertyId=`
- `queryType=2`
- `visitSiteId=1`

已验证结论:

- 量很大，示例 `total=78548`
- 但样本 `resCustomerList` 多为空
- 可作为国际资源池，但医生覆盖不稳定

### 9. 当前结论

按“医生主键稳定性 + 可扩展成全量”的强弱排序:

1. 患者端医院科室链路:
   `getDeptList -> getFrontDoctorList -> doctorId -> getMapById`
2. 直播模块:
   `getAllActivityPageInfo -> activityId -> getActivityDetail -> doctorList[].doctorId`
3. 课程模块:
   `getNavigationList -> getProjectList -> getProductDetail -> getSystemCourseTimetable -> resCustomerList[].customerId`
4. 手术模块:
   `getFeedVideoList -> resCustomerList[].customerId`
5. 协会 / 组织模块:
   `getResourceColumnList / getOrganizationColumnList -> resCustomerList[].customerId`
6. 医生主页粉丝模块:
   `getDoctorInfo -> getFansList -> customer_auth.customerId`

不建议先并入主链路的接口:

- `getMeetingPage`
- `partSearch` 会议搜索
- `partSearch` 手术搜索
- `getInternationalVideoList`

原因:

- 要么医生字段不稳定
- 要么天然是搜索口
- 要么更适合作为补充资源池而不是正式采集主链路

### 10. 医生主页粉丝扩散补口

目标页样例:

- `https://www.allinmd.cn/edu/doctorHome?doctorId=1424958335567`

已验证公开接口:

#### 10.1 医生主页主信息

- 接口:
  `GET https://api-gateway.allinmd.cn/landing-resource/mpd/doctor/mainpage/getDoctorInfo`

已验证参数:

- `customerId=<doctorId>`

已验证字段:

- `customerId`
- `name`
- `company`
- `medicalTitle`
- `logoUrl`
- `fansCount`

#### 10.2 粉丝列表

- 接口:
  `GET https://api-gateway.allinmd.cn/allin-api-platform/services/customer/follow/fans/v2/getMapList`

已验证参数:

- `queryJson={"sortType":2,"followTypeFlag":31,"followType":1,"logoUseFlag":4,"customerId":"<doctorId>","firstResult":0,"maxResult":20}`

已验证字段:

- `customer_auth.customerId`
- `customer_auth.fullName`
- `customer_auth.company`
- `customer_auth.medicalTitleShow`
- `customer_att.logoUrl`

`2026-04-14` 实测样例:

- 对 `doctorId=1424958335567`
  - `getDoctorInfo.fansCount=18`
  - 粉丝列表第 `1` 页原始返回 `18` 条
  - 按 `company` 包含“医院”过滤后保留 `17` 条

当前项目实现策略:

- 新增 spider:
  `doctor_home_fans_spider`
- 新增 Redis key:
  `doctor_home_task`
  `doctor_home_done`
- `doctor_home_task` 只存最小任务:
  `{"doctor_id":"..."}`
- 所有来源发现医生时，同时写入：
  `doctor_info_url`
  `doctor_home_task`
- `doctor_home_done` 记录已展开过的主页 id，防止互相关注反复扩散
- 粉丝链路只补入口，最终详情仍统一走 `personalInfo` 多接口合流

## 过程文件目录

本次侦察产物已集中在:

- `C:\Users\lenovo\Desktop\Spider One\doctor_wygk_process`
