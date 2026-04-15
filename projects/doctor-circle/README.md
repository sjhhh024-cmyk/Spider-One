# 医生圈采集项目

这是一个按 Scrapy 原生结构整理的“医生圈”项目。

## 先看哪里

- 入口文件：`doctor_circle/start.py`
- 配置文件：`doctor_circle/settings.py`
- 批量启动顺序：`doctor_circle/commands/crawl_all.py`
- 采集主逻辑：`doctor_circle/spiders/doctor/`
- 手工补 Redis 的辅助脚本：`txt_into_redis.py`

## 采集顺序

1. `1_circle_list_spider.py`
   拉圈子列表，并把圈子详情地址写入 Redis。
2. `2_circle_doctor_list_spider.py`
   从 Redis 读取圈子地址，生成医生列表地址。
3. `3_doctor_detail_url_spider.py`
   从 Redis 读取医生列表地址，生成医生详情地址。
4. `4_doctor_detail_spider.py`
   从 Redis 读取医生详情地址，解析医生详情并写入 MongoDB。

## 运行方式

推荐直接运行：

```powershell
.\start.ps1
```

这个脚本会先执行下面这条 SSH 隧道命令，再启动 Scrapy：

```powershell
ssh -L 6379:localhost:6379 root@8.140.197.200
```

如果你只想手工跑 Python，也可以直接运行：

```powershell
python doctor_circle/start.py
```

或者在项目根目录运行：

```powershell
scrapy crawl_all
```

## 主要配置

全部放在 `doctor_circle/settings.py` 里，重点看这些：

- MongoDB 连接
- Redis 连接
- Redis key
- 医生圈接口 token
- 并发、重试、下载间隔
- 本地 Redis 走 SSH 隧道时，默认就是 `127.0.0.1:6379`

## 说明

- 这个项目刻意保持“能顺着读”的写法，没有额外套 service / manager / workflow。
- `_id` 默认优先使用业务主键。
- `start.ps1` 里可以直接改 SSH 隧道命令和 Python 解释器路径。
