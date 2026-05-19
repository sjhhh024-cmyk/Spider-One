# ytggzy

烟台市公共资源交易网采集脚本。

当前口径：

- 只采集、整理字段、打印字典
- 模型字段直接用模型结果，站点侧不做二次处理
- 候选人按当前 `zbggzy` 候选人口径处理
- 支持 `招标公告`、`中标公告`、`候选人公告`、`采购意向`

## 运行

```powershell
F:\Anaconda3\envs\spider\python.exe .\ytggzy_zhaobiao.py
F:\Anaconda3\envs\spider\python.exe .\ytggzy_zhongbiao.py
F:\Anaconda3\envs\spider\python.exe .\ytggzy_houxuanren.py
F:\Anaconda3\envs\spider\python.exe .\ytggzy_caigouyixiang.py
```

## 默认参数

- `module_name = 全部模块`
- `start_page = 1`
- `max_pages = 1`
- `page_size = 10`

## 站点链路

- 列表接口：`/inteligentsearch/rest/esinteligentsearch/getFullTextDataNew`
- 详情页：列表返回的 `linkurl`
- 正文：` .txt-content `
- 附件：` .com-files a `
