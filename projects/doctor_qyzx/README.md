# doctor_qyzx 七元网医生采集项目

`doctor_qyzx` 用来采集 `https://www.qypxw.net/zxxmjg/` 的医生数据，项目目录在 `projects/doctor_qyzx`。

当前实现定位为轻量单机脚本：

- 列表页走公开 HTML 分页：`/zxxmjg/`、`/zxxmjg/pageN/`
- 详情页走公开医生页面：`/zxxmjg/<category>_<id>/`
- 默认先抓列表，再补详情字段，然后直接写入 MongoDB
- 默认配置直接写在 `doctor_qyzx.py`
- 控制台直接打印页码、条数、样本记录和入库结果

## 已确认链路

- 医生列表页：`https://www.qypxw.net/zxxmjg/`
- 分页规则：`https://www.qypxw.net/zxxmjg/page2/`
- 医生详情页：`https://www.qypxw.net/zxxmjg/yk_2566/`

当前样本页证据已经确认：

- 首页当前卡片数：`21`
- 当前分页末页：`401`
- 列表卡可直接拿到姓名、医院、简介摘要、头像、详情链接
- 详情页可直接拿到科室、职称、诊疗项目、所属医院、正文简介

## 当前落库字段

- `_id`
- `doctor_id`
- `doctor_name`
- `doctor_department`
- `doctor_hospital`
- `doctor_title`
- `doctor_specialties`
- `intro`
- `doctor_avatar_url`
- `source_site`
- `source_url`
- `crawl_time`

## 默认配置

默认配置已经直接写在 [doctor_qyzx.py](C:\Users\lenovo\Desktop\Spider%20One\projects\doctor_qyzx\doctor_qyzx.py) 里的 `DEFAULT_PROFILE`：

- 站点：`https://www.qypxw.net/zxxmjg/`
- 页码：`0`
- 采集模式：`全量采集`
- 详情并发数：`20`
- 详情抓取：`true`
- MongoDB：
  `101.200.125.240:27017`
  用户名：`admin`
  数据库：`Doctor_Database`
  集合：`doctor_qyzx`

## 运行方式

直接运行：

```powershell
py .\doctor_qyzx.py
```

或者：

```powershell
python .\doctor_qyzx.py
```

## 当前实现说明

- `start_page=0` 表示从第一页开始全量采集；`start_page=数字` 表示从该页开始一直采到最后一页
- 详情页默认使用线程池并发抓取，可通过 `DEFAULT_PROFILE["source"]["detail_max_workers"]` 调整并发数
- 当前站点列表页没有公开总条数字段，脚本按真实分页链路递进到最后一页
- 列表页已经带详情链接，所以详情抓取不需要额外拼装接口签名
- 当前项目只覆盖医生主链路，不扩医院、项目、问答等旁链
