# qdggzy

青岛市公共资源交易电子服务系统采集脚本。

目标站点：

`https://ggzy.qingdao.gov.cn/PortalQDManage/`

当前项目只负责采集、整理字段、构造字典并直接打印，不接数据库、不上传、不落库。
当前已按 `zbggzy` 同口径接入 Redis 运行状态监控。
`BizType` 规则为：
- 站点存在真实二级分类时，使用 `一级类型-二级类型`
- 站点没有真实二级分类时，只保留一级类型本身

## 目录说明

- `qdggzy_core.py`：总启动脚本，顺序启动招标 / 中标 / 候选人三个脚本
- `qdggzy_zhaobiao.py`：招标脚本
- `qdggzy_zhongbiao.py`：中标脚本
- `qdggzy_houxuanren.py`：候选人脚本
- `monitoring.py`：Redis 健康状态上报
- `tests/`：测试代码

说明：

- 当前正式目录只保留 4 个采集脚本
- `qdggzy_core.py` 负责公共抓取、解析、模型接入和总入口
- 其余 3 个脚本分别固定运行各自板块

当前实现范围：

- 首页任务发现：从首页解析一级模块和二级栏目配置
- 已覆盖主链路模块：`建设工程`、`政府采购`、`国企采购`、`其他项目`、`无形资产`、`环境权`
- 已并入特殊模块首版：`资源交易`、`产权交易`
- 列表接口：默认走 `PartialZTBNew`，合同类栏目自动切 `PartialHTZTBNew`
- `资源交易`、`产权交易` 当前改走 `Tradeinfo-GGGSList/...` 静态列表页直抓
- 详情解析：提取正文主容器、字段、附件，并输出标准字典
- 输出类型：`招标公告`、`中标公告`、`候选人公告`、`采购意向`

模型接入说明：

- `招标公告`：统一走 `projects/jianzhi/general_model/GetBidModel.py`
- `中标公告`：统一走 `projects/jianzhi/general_model/GetTenderModel.py`
- `候选人公告`：统一走 `projects/jianzhi/general_model/GetCandidateModel.py`
- 金额统一走 `projects/jianzhi/general_model/AmountConverter.py`
- 上述三个板块固定使用模型，站点侧不再做二次处理
- 候选人结果按当前 `zbggzy` 候选人口径处理
- `采购意向` 当前未提供对应通用模型，仍按基础解析结果构造

命令示例：

```bash
F:\Anaconda3\envs\spider\python.exe projects\jianzhi\qdggzy\qdggzy_core.py --module-name 建设工程 --max-pages 1
F:\Anaconda3\envs\spider\python.exe projects\jianzhi\qdggzy\qdggzy_zhaobiao.py --module-name 政府采购 --max-pages 1
F:\Anaconda3\envs\spider\python.exe projects\jianzhi\qdggzy\qdggzy_zhongbiao.py --module-name 政府采购 --max-pages 1
F:\Anaconda3\envs\spider\python.exe projects\jianzhi\qdggzy\qdggzy_houxuanren.py --module-name 建设工程 --max-pages 1
```

支持参数：

- `--module-name`：一级模块名称
- `--output-board`：输出板块，可选 `招标公告` / `中标公告` / `候选人公告` / `采购意向`
- `--start-page`：起始页，默认 `1`
- `--max-pages`：最多抓取页数，默认 `1`
- `--page-size`：每页条数，默认 `10`
- `--timeout-seconds`：请求超时秒数，默认 `20`
- `--detail-delay-seconds`：详情请求间隔，默认 `0`

说明：

- `htmlContent` 会清洗掉附件下载链接后再做 `base64`
- 字段严格按标准模板构造，不做接库逻辑
- 每个“一级模块-二级类型/公告类型”会作为一条独立监控状态上报，核心字段包括 `WasSuccessful`、`WebsiteError`、`HasContent`、`HasNewData`、`IsValidData`、`WebName`、`BizType`
- `产权交易` 详情可能跳转到 `cqjy.qdcq.net` 外站，当前已支持无 `htmlTable` 时用标题/正文兜底
- 国企采购、资源交易、产权交易等静态列表分页按 `?pageIndex=` 组织
- 当前环境在线请求可能受代理影响；离线样本测试已覆盖基础解析链路
