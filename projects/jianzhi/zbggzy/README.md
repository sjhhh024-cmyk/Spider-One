# zbggzy

淄博市公共资源交易网采集脚本使用说明。

本项目用于采集 `http://ggzyjy.zibo.gov.cn:8082/` 的公告数据。
脚本只负责采集、整理字段、构造字典并直接打印，不接数据库、不上传、不落库。
当前已按 `file/监控埋点案例` 中的 `WebsiteRedisStorage` 文档接入运行状态监控。`BizType` 规则为：
- 站点存在真实二级分类时，使用 `一级类型-二级类型`
- 当前站点没有真实二级分类时，只保留一级类型本身，不把 `招标公告 / 中标公告 / 候选人公告` 当成二级类型

## 1. 目录说明

- `zbggzy_core.py`：薄总入口，顺序启动招标 / 中标 / 候选人三个脚本
- `zbggzy_zhaobiao.py`：只输出招标公告
- `zbggzy_zhongbiao.py`：只输出中标公告
- `zbggzy_houxuanren.py`：只输出候选人公告
- `tests/`：测试代码

## 2. 运行方式

本项目不再使用 `profile.yml`。
运行参数直接写在脚本顶部的 `RUN_CONFIG` 里，测试时改配置后直接运行脚本。

示例：

```powershell
E:\python3.12.2\python.exe .\zbggzy_core.py
```

只跑招标公告：

```powershell
E:\python3.12.2\python.exe .\zbggzy_zhaobiao.py
```

只跑中标公告：

```powershell
E:\python3.12.2\python.exe .\zbggzy_zhongbiao.py
```

只跑候选人公告：

```powershell
E:\python3.12.2\python.exe .\zbggzy_houxuanren.py
```

先改脚本顶部配置，例如：

```powershell
$env:PYTHONIOENCODING='utf-8'
```

```python
RUN_CONFIG = {
    "module_name": "建设工程",
    "notice_type": "招标公告",
    "start_page": 1,
    "max_pages": 1,
    "page_size": 15,
    "timeout_seconds": 30,
    "detail_delay_seconds": 0,
}
```

然后直接运行对应脚本。

只跑“建设工程 -> 招标公告”：

```powershell
E:\python3.12.2\python.exe .\zbggzy_zhaobiao.py
```

只跑“建设工程 -> 中标候选人公示”：

```powershell
E:\python3.12.2\python.exe .\zbggzy_houxuanren.py
```

只跑“政府采购 -> 中标（成交）公告”：

```powershell
E:\python3.12.2\python.exe .\zbggzy_zhongbiao.py
```

## 3. 当前默认参数

- `module_name = "全部模块"`
- `notice_type = ""`
- `start_page = 1`
- `max_pages = 1`
- `page_size = 15`
- `timeout_seconds = 30`
- `detail_delay_seconds = 0`

## 4. 采集范围

脚本会动态读取各一级模块页面上的“公告类型”筛选项，再按分类号采集。

当前覆盖：

- 建设工程
- 政府采购
- 国企采购
- 药械采购
- 其他交易
- 农村工程
- 农村采购
- 土地流转
- 集体资产
- 农业设施
- 其他交易(农村产权)

以下一级模块当前直接跳过，不采集：

- 自然资源
- 产权交易
- 供需信息

## 5. 输出板块映射

- 含 `候选人` / `评标结果` / `预中标` -> `候选人公告`
- 含 `结果` / `成交` / `合同` / `中标` -> `中标公告`
- 其他默认 -> `招标公告`

以下公告类型当前直接跳过，不采集、不输出：

- `变更公告`
- `澄清公告`
- `更正公告`
- `终止公告`
- `废标公告`
- `流标公告`
- `异常公告`
- `异议回复`
- `验收公告`
- `需求（意向）公示`
- `招标项目计划`
- `合同公告`
- `合同公示`
- `合同公示及变更`
- `土地信息`

## 6. 站点链路

- 列表接口：`/EpointWebBuilder_zbggzy/rest/frontAppCustomAction/getPageInfoListNew`
- 详情页：直接访问列表返回的 `infourl`
- 附件：从详情页里的 `downloadztbattach` 链接提取

脚本会先获取匿名 token，再带 `Authorization: Bearer ...` 调列表接口。

## 7. 字段口径

字段以 `字段汇总及数据示例.xlsx` 为准，按三套模板输出：

- 招标公告
- 中标公告
- 候选人公告

其中：

- `htmlContent` 使用清洗后的详情 HTML，再做 base64
- 会去掉 `viewGuid`、`iframetitle`、`助农易贷`、区块链壳层、附件下载链接、裸露下载地址
- `中标.uploadFileUrl` 输出 `list[str]`
- `候选人公告.uploadFileUrl` 输出 `list[dict]`
- `招标.fileInfo` 输出 `list[dict]`
- `招标.procurementMethod` 当前只认表格/模型结果，不再从正文规则兜底
- `政府采购`、`国企采购`、`药械采购`、`其他交易` 的 `合同公告` 按中标公告采集
- `农村工程`、`农村采购`、`土地流转`、`集体资产`、`农业设施`、`其他交易(农村产权)` 的 `合同公示` 按中标公告采集

## 8. 测试命令

```powershell
E:\python3.12.2\python.exe -m pytest .\tests -q
E:\python3.12.2\python.exe -m py_compile .\zbggzy_core.py .\zbggzy_zhaobiao.py .\zbggzy_zhongbiao.py .\zbggzy_houxuanren.py
```

## 9. 已知说明

- 深页不走页面验证码，直接使用匿名 token 请求列表接口。
- 模型增强失败时不会中断，保留当前基础结果。
- `zbggzy_core.py` 只做总启动，不承载采集解析实现。
- 三个独立脚本各自持有自己的采集、解析、字段组装和模型增强逻辑，并可单独启动。
- 候选人公告固定使用 `general/GetCandidateModel.py`，站点侧不再重组客户模型已返回的字段。
- 当前口径下 `需求（意向）公示` 继续排除，因此不再提供 `采购意向` 独立入口脚本。
- 每个“一级模块-二级公告类型”会作为一条独立监控状态上报，核心字段包括 `WasSuccessful`、`WebsiteError`、`HasContent`、`HasNewData`、`IsValidData`、`WebName`、`BizType`。
