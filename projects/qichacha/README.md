# qichacha A 表项目

这个项目当前只实现 `A表：泰州每日新增企业主表`。

## 官方来源

- `20266` 市场主体登记信息
- `20277` 合伙企业设立登记信息
- `20330` 个人独资企业设立登记信息

来源站点：
`https://opendata.taizhou.gov.cn/oportal`

## 当前口径

- 以 `成立日期（CLRQ）` 作为“新增日期”
- 三个目录合并后，按 `统一社会信用代码` 去重
- 导出字段：
  - 企业名称
  - 统一社会信用代码
  - 法定代表人/负责人/经营者
  - 住所
  - 注册资本（万）
  - 生产经营地/经营场所
  - 成立日期
  - 核准日期
  - 业务类型
  - 来源目录
  - 目录ID

## 已知限制

- 这三个官方目录当前是 `按季度更新`，不是日更接口。
- 所以“每日新增企业主表”可以按天过滤生成，但是否有数据，取决于开放平台当季是否已经同步到该日期。
- 例如 `2026-04-30` 这次生成结果为 `0` 条，不是脚本失败，而是官方当前公开口径下没有该日期记录。

## 运行

```powershell
py projects/qichacha/daily_new_enterprises.py --date 2026-04-30 --output-dir projects/qichacha/outputs
```

## 输出

- `taizhou_daily_new_enterprises_<date>.json`
- `taizhou_daily_new_enterprises_<date>.xlsx`
