# findings

## 站点结论

### 新站主链路

站点：`https://www.169000.net/`

已确认的公开接口：

- `POST /fastGh/1`
  - 返回区域列表
- `POST /fastGh/2-<city_id>`
  - 返回医院列表
- `POST /fastGh/3-<hospital_id>`
  - 返回科室列表
- `POST /fastGh/4-<dept_id>`
  - 返回医生列表

已验证样本：

- `fastGh/2-410100`
  - 可返回郑州市医院
- `fastGh/3-1597528472392306688`
  - 可返回郑州大学第一附属医院河医院区的科室
- `fastGh/4-1773286494975561728`
  - 可返回妇科医生列表

### 新站详情页限制

`/ghplat/doctor/show/<id>.html` 为 SPA 壳子，直接抓 HTML 不能稳定拿到医生详情字段，因此当前项目不从这个页面解析详情正文。

### 旧站桥接

站点：`https://guahao.169000.net/`

已确认：

- 医院搜索需要 `GBK` 表单编码：
  - `POST /index.gl?op=c`
- 医生搜索需要 `GBK` 表单编码：
  - `POST /indexext.gl?op=w`
- 医院详情页：
  - `GET /indexext.gl?op=3&id=...`
- 科室详情页：
  - `GET /indexext.gl?op=4&id=...`
- 医生详情页：
  - `GET /index.gl?op=6&id=...`

桥接优先级：

1. 医院搜索 -> 医院页 -> 科室页 -> 医生详情页
2. 若科室链路没命中，再走医生名搜索兜底

## 当前项目实现约定

- 主链路只负责把新站稳定 ID 扩展完整。
- `hospital_hnyygh` 是 `doctor_hnyygh` 的子链路结果，不单独跑全链路。
- 医院记录只在 `doctor_detail_spider` 中和医生详情一起落库。

## 已知风险

- 院区名和旧站主院名存在命名差异，例如“河医院区”“本部”“东院区”等。
- 当前 `normalize_name_for_match()` 只覆盖了第一版常见院区别名，后续可能还要继续补。
- 旧站桥接目前使用同步请求，若需要大规模并发，后续应进一步治理重试、限速和超时策略。
