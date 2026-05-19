# doctor_dzys 大众网医生采集项目

`doctor_dzys` 用来采集 `https://www.dazhong.com/hospital/sitemap_doctor` 下的大众网医生详情。

## 已确认链路

- 医生种子页：`https://www.dazhong.com/hospital/sitemap_doctor`
- 医生详情页：`https://www.dazhong.com/hospital/doctor_home/<doctor_id>.html`

## 当前字段

按通用模板落库：

- `_id`
- `doctor_id`
- `doctor_name`
- `doctor_hospital`
- `doctor_department`
- `doctor_title`
- `doctor_avatar_url`
- `doctor_specialties`
- `intro`
- `source_site`
- `source_url`
- `crawl_time`

## 过滤规则

- 过滤姓名里包含 `医生` 的占位记录
- 过滤明显不像真实医院的可疑医院名
- 仅保留 `doctor_hospital` 可识别为医院机构的记录

## Redis 中间层

- 默认 Redis：`117.50.131.232:6379/1`
- `doctor_dzys:doctor_info_url`：本次待处理的医生详情任务
- `doctor_dzys:doctor_info_done`：本次已处理完成的医生 ID
- 详情链接会先入 Redis，再从 Redis 取回处理

## 运行方式

```powershell
py .\doctor_dzys.py --dry-run --limit 5
```

去掉 `--dry-run` 后写入 MongoDB。

## 说明

- 站点是静态 HTML，不需要 JS 逆向
- `sitemap_doctor` 当前实测包含 `7749` 条医生链接
- 详情页主字段都在 `div.det_doctor` 内
- 头像从详情页内的医生图像节点解析

## 头像上传七牛

`upload_avatars_to_qiniu.py` 会从 `Doctor_Database.doctor_dzys` 读取已有医生记录：

- 只处理 `doctor_avatar_url` 非空的记录
- 下载头像时自动带 `Referer: source_url`
- 跳过默认头像 `doctor-0.jpg`
- 上传到七牛后回写：
  - `doctor_avatar_url`：改成七牛地址
  - `doctor_avatar_origin_url`：保留原始大众网头像地址
- 脚本启动时会自动清理历史遗留的：
  - `doctor_avatar_qiniu_key`
  - `doctor_avatar_qiniu_url`

运行前打开 [upload_avatars_to_qiniu.py](/C:/Users/lenovo/Desktop/Spider%20One/projects/doctor_dzys/upload_avatars_to_qiniu.py)，把顶部这几项填上：

```powershell
QINIU_ACCESS_KEY = "你的AK"
QINIU_SECRET_KEY = "你的SK"
QINIU_BUCKET = "你的bucket"
QINIU_DOMAIN = "https://你的CDN域名"
```

然后直接执行：

```powershell
py .\upload_avatars_to_qiniu.py
```

或者直接运行：

```powershell
.\start_upload_avatars.ps1
```

如果你确实需要限制范围，再改脚本顶部这些开关：

- `RUN_LIMIT = 0`
- `RUN_FORCE = False`
- `RUN_DRY_RUN = False`
- `RUN_DOCTOR_ID = ""`
