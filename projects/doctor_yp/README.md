# doctor_yp 医谱医生采集项目

`doctor_yp` 用来采集 `https://docbook.com.cn/doctorList` 的医生数据，项目目录在 `projects/doctor_yp`。

当前实现定位为轻量单机脚本：

- 列表页走 SSR 路由分页：`/doctorList/<page>`
- 详情页走公开医生主页：`/doctorDetail/<doctor_id>`
- 默认先抓列表，再补详情字段，然后直接写入 MongoDB
- 默认配置直接写在 `doctor_yp.py`
- 控制台直接打印页码、条数、样本记录和入库结果

## 已确认链路

- 医生列表页：`https://docbook.com.cn/doctorList`
- 分页规则：`https://docbook.com.cn/doctorList/<page>`
- 医生详情页：`https://docbook.com.cn/doctorDetail/<doctor_id>`

前端页面证据已经确认：

- 列表页前端路由翻页使用 `/doctorList/<page>`
- 每页 `15` 条
- 样本首页总量 `27432`
- 样本首页总页数 `1829`

## 当前落库字段

- `_id`
- `doctor_id`
- `doctor_name`
- `doctor_hospital`
- `doctor_department`
- `doctor_titile`
- `doctor_other_title`
- `intro`
- `doctor_avatar_url`
- `source_url`
- `crawl_time`

如果关闭详情抓取，基础列表字段仍会入库。

## 默认配置

默认配置已经直接写在 [doctor_yp.py](C:\Users\lenovo\Desktop\Spider%20One\projects\doctor_yp\doctor_yp.py) 里的 `DEFAULT_PROFILE`：

- 站点：`https://docbook.com.cn`
- 页码：`0`
- 采集模式：`全量采集`
- 详情并发数：`20`
- 详情抓取：`true`
- MongoDB：
  `101.200.125.240:27017`
  用户名：`admin`
  数据库：`Doctor_Database`
  集合：`doctor_yp`

上面这套 Mongo 默认值直接参考了之前的 `doctor-ywbd` / `doctor_wygk` 项目。

## 运行方式

直接运行：

```powershell
py .\doctor_yp.py
```

或者：

```powershell
python .\doctor_yp.py
```

## 当前实现说明

- 第一版优先保证医生列表和详情稳定可复现
- `start_page=0` 表示从第一页开始全量采集；`start_page=数字` 表示从该页开始一直采到最后一页
- 详情页默认使用线程池并发抓取，可通过 `DEFAULT_PROFILE["source"]["detail_max_workers"]` 调整并发数
- `profile_url`、访问量、粉丝数均不入库
- `doctor_titile` 字段只放标准医疗职称，例如主任医师 / 副主任医师 / 药师 / 技师 / 护师
- `doctor_other_title` 字段放其它头衔，例如院士 / 副教授 / 硕士研究生导师
- 目前没有接医院、科室订阅、作品列表等旁链
- 如果后面要补课程、手术、会议等内容，再单独扩展详情页接口链路
