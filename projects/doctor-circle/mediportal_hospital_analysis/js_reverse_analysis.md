# 医生圈医院接口侦察记录

## 目标

确认医生圈项目是否存在可复用的医院详情接口，以及该接口是否需要登录态。

## 已确认入口

- Web 版入口: `https://api.mediportal.com.cn/health/web/`
- 前端配置: `https://api.mediportal.com.cn/health/web/src/config.js?rev=9dd3bcd7ca349bc7fbbb6cab92313fbc`
- 登录控制器: `https://api.mediportal.com.cn/health/web/src/js/controllers/signin.js`

## 已确认的医院相关接口

### 1. 公开可访问的医院基础信息接口

`POST/GET https://api.mediportal.com.cn/health/base/findHospitalByCondition`

实测可返回字段:

- `id`
- `name`
- `address`
- `level`
- `provinceName`
- `cityName`
- `countryName`

备注:

- 当前参数行为不稳定
- 直接传 `name` / `hospitalName` / `keyword` 时，返回结果更像默认医院池，不像精确搜索

### 2. 登录态医院详情接口

`POST https://api.mediportal.com.cn/health/group/hospital/getDetailByGroupId`

结论:

- 前端配置里明确存在该接口
- 直接请求返回 `缺少访问令牌`
- 当前项目里的公开 token 不能调用这条接口

## 鉴权链路

从 `signin.js` 可确认:

1. 登录接口为 `app.url.login`
2. 登录成功后返回 `response.data.data.access_token`
3. 前端会把该值写入:
   - Cookie `a`
   - `app.url.access_token`
   - `localStorage['access_token']`

关键代码逻辑:

- `utils.setCookie('a', response.data.data.access_token);`
- `app.url.access_token = response.data.data.access_token;`
- `utils.localData('access_token', app.url.access_token);`

因此，医院详情接口依赖的是登录后用户 token，不是当前医生圈抓取链路里的公开接口 token。

## 当前判断

1. `doctor-circle` 现有医生接口只能拿到医院名，拿不到医院详情
2. 医生圈 Web 管理端存在医院详情接口，但需要登录态
3. 如果没有医生圈账号登录态，就无法继续验证详情字段

## 下一步建议

### 方案 A

获取一个已登录浏览器里的 `localStorage.access_token`，直接验证:

- `group/hospital/getDetailByGroupId`
- `group/hospital/groupHospitalList`

### 方案 B

如果没有账号，只能先基于 `findHospitalByCondition` 做医院基础信息补全，而不是完整详情采集。
