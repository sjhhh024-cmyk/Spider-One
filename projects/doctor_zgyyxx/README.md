# doctor_zgyyxx

`doctor_zgyyxx` 是中国医药信息查询平台医生项目的单脚本实现。

当前实现口径：

- 医生主链路：`/list/3` -> `/list/3/<page>` -> `/doctor/<doctor_id>.html`
- 医院主链路：`/list/2` -> `/hospital/<hospital_id>.html`
- 医生写入 `doctor_zgyyxx`
- 医院写入 `hospital_zgyyxx`
- Redis 只保留 3 条任务队列：
  - `doctor_zgyyxx:doctor_list_task`
  - `doctor_zgyyxx:doctor_detail_task`
  - `doctor_zgyyxx:hospital_detail_task`

## 当前设计

- 不使用 Scrapy
- 使用 Redis set 做任务去重和断点续跑
- 医生和医院是两条平行线
- 不做 `doctor_done` / `hospital_done` / `failures`
- 医院详情不会反向补投医生详情，避免循环

## 已实现字段

医生侧：

- 核心字段固定输出
- 补充字段按页面实际出现写入
- 详情字段优先覆盖列表字段

医院侧：

- 统一使用 `hospital_*` 命名
- 先落列表最小文档
- 再用详情页完整字段覆盖

## 运行说明

直接运行 [doctor_zgyyxx.py](C:/Users/lenovo/Desktop/Spider%20One/projects/doctor_zgyyxx/doctor_zgyyxx.py) 里的 `DoctorZgyyxxSpider` 即可。

Redis 默认沿用仓库现有共享配置：

- host: `117.50.131.232`
- port: `6379`
- db: `1`

也支持通过环境变量覆盖：

- `SPIDER_ONE_REDIS_HOST`
- `SPIDER_ONE_REDIS_PORT`
- `SPIDER_ONE_REDIS_DB`
- `SPIDER_ONE_REDIS_PASSWORD`

## 当前边界

- 医院详情页里的 `doctors` 目前只作为观察到的辅助信息保留，不作为稳定医生详情任务来源
- 当前测试样本已覆盖列表、详情、Redis 队列和医院覆盖逻辑
