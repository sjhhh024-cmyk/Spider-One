# 好心情医生单机脚本

## 项目定位

这是一个单机脚本项目，专门针对好心情 `allSearch` 接口做医生数据采集，并直接写入 MongoDB。

当前实现特点：

- 直接请求接口，不依赖浏览器
- 自动按页推进
- 遇到 `code=4998` / `系统错误` 自动重试
- 遇到“请求第 N 页但响应回了别的页”自动重试
- 按 `doctor.id` 去重
- 每页数据按顺序直接写入 MongoDB
- 头像地址自动拼成完整 URL
- 控制台直接打印页码、请求地址、条数、字段名、样本记录和入库结果
- 入口只有一个主脚本，读下来就是直线流程

## 目录说明

- `profile.yml`：你要改的配置文件
- `doctor_hxq_start.py`：主脚本，读配置、请求、解析、去重、入库都在这里
- `start.ps1`：最薄启动入口，等价于执行一次 Python 主脚本
- `profile.example.yml`：参考配置
- `sample_all_search_p1_ps3.json`：接口样本，方便你看字段

如果你只想快速定位：

- 改配置：`profile.yml`
- 看逻辑：`doctor_hxq_start.py`
- 真正启动：`start.ps1`

## 配置

你只需要改 `profile.yml`。

先复制一份配置：

```powershell
Copy-Item profile.example.yml profile.yml
```

当前配置项：

- `source.base_url`：接口地址
- `source.page_size`：分页大小，当前接口建议 `1000`
- `source.start_page`：起始页，默认 `1`
- `source.max_pages`：最大探测页数
- `source.timeout_seconds`：单次请求超时
- `source.max_retries`：单页失败最大重试次数
- `mongodb.uri`：如果你已经有完整连接串，就填这里；留空则走下面的账号密码字段
- `mongodb.host`：MongoDB 主机
- `mongodb.port`：MongoDB 端口
- `mongodb.username`：MongoDB 用户名
- `mongodb.password`：MongoDB 密码
- `mongodb.auth_source`：MongoDB 认证库，常见是 `admin`
- `mongodb.database`：数据库名
- `mongodb.collection`：集合名
- `mongodb.upsert_key`：upsert 键，当前默认 `doctor_id`

## 运行方式

推荐直接运行：

```powershell
pwsh -File .\start.ps1 -ProfilePath profile.yml
```

也可以直接运行：

```powershell
py doctor_hxq_start.py --profile profile.yml
```

## 当前落库字段

当前主脚本直接按单层结构入库，字段包括：

- `_id`
- `doctor_id`
- `name`
- `hospital_name`
- `department_name`
- `title`
- `avatar_url`
- `profile_url`
- `territory`
- `intro`
- `disease_names`
- `city_id`
- `province_id`
- `hospital_id_hxq`
- `department_id_hxq`
- `evaluation_score`
- `source_site`
- `source_url`
- `grab_data`

## 当前已知接口规律

- `pn=50d` 会被服务端容错成第一页，不是真正的第 50 页
- 当前真实分页边界曾观察到 `35` 页，`36` 页为空
- 服务端会间歇性返回 `系统错误 / code=4998`
- 服务端也可能返回页码错位响应，所以不能只看列表里有没有数据

## 下一步建议

- 如果后面要采详情页，再补详情接口
- 如果后面要采医院或科室，再单独写对应启动脚本
- 如果后面变成多站点大规模任务，再升级到 Scrapy 或分布式结构
