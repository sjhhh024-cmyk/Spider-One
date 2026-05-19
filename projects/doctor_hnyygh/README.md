# doctor_hnyygh

基于 `Scrapy + scrapy-redis` 的河南省预约挂号服务平台医生采集项目，主站使用 [https://www.169000.net/](https://www.169000.net/) 的 `fastGh` 接口扩展 `区域 -> 医院 -> 科室 -> 医生` 主链路，旧站使用 [https://guahao.169000.net/](https://guahao.169000.net/) 的服务端渲染页面补齐医生和医院详情字段。

当前实现遵循两个固定约束：

1. 医生是主链路，最终写入 `doctor_hnyygh`。
2. 医院不是独立主采集流，而是在医生详情桥接阶段顺手写入 `hospital_hnyygh`。

## 链路说明

当前 spider 顺序如下：

1. `entry_seed_spider`
   - 写入 `fastGh/1` 到 `doctor_hnyygh:area_index_url`
2. `area_hospital_spider`
   - 消费区域入口
   - 解析城市列表
   - 为每个城市写入 `fastGh/2-<city_id>` 到 `doctor_hnyygh:hospital_list_url`
3. `hospital_spider`
   - 消费医院列表入口
   - 解析医院列表
   - 为每家医院写入 `fastGh/3-<hospital_id>` 到 `doctor_hnyygh:department_list_url`
4. `department_spider`
   - 消费科室列表入口
   - 解析科室列表
   - 为每个科室写入 `fastGh/4-<dept_id>` 到 `doctor_hnyygh:doctor_list_url`
5. `doctor_list_spider`
   - 消费医生列表入口
   - 解析医生 ID 与姓名
   - 写入统一医生详情任务到 `doctor_hnyygh:doctor_info_url`
6. `doctor_detail_spider`
   - 不依赖新站 SPA 详情
   - 使用旧站 HTML 桥接补齐医生详情
   - 同时生成医院记录并写入 `hospital_hnyygh`

## 关键事实

- 新站 `fastGh` 已确认可用：
  - `POST /fastGh/1` 区域
  - `POST /fastGh/2-<city_id>` 医院
  - `POST /fastGh/3-<hospital_id>` 科室
  - `POST /fastGh/4-<dept_id>` 医生
- 新站 `/ghplat/doctor/show/<id>.html` 是 SPA 壳子，不能直接靠 HTML 拿详情字段。
- 旧站搜索提交必须使用 `GBK` 表单编码。
- 旧站医生详情页可直接抽取：
  - `doctor_name`
  - `doctor_hospital`
  - `doctor_department`
  - `doctor_title`
  - `doctor_avatar_url`
  - `doctor_specialties`
  - `intro`
- 旧站医院详情页可直接抽取：
  - `hospital_name`
  - `hospital_phone`
  - `hospital_address`
  - `hospital_website`
  - `hospital_intro`

## 已知限制

- 新站部分院区名和旧站医院主名不完全一致，当前版本依赖轻量名称归一规则做桥接匹配。
- `doctor_detail_spider` 目前在 spider 内部用同步 `requests.Session()` 访问旧站桥接页，适合先完成项目落地，后续如果要放大并发可以再抽成 downloader / service 层。

## 启动

项目根目录运行：

```powershell
py -3 doctor_hnyygh/start.py
```

或：

```powershell
scrapy crawl_all
```
