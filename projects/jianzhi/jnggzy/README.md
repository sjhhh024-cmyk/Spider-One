# jnggzy

济南公共资源交易中心采集脚本使用说明。

本项目用于采集 `https://jnggzy.jinan.gov.cn/` 的公告数据。
当前脚本只负责采集、整理字段、打印结果，不接数据库，也不做上传。

## 1. 项目作用

运行脚本后，会按栏目抓取列表页，再进入详情页整理字段。

每条结果最终会构造成一个 `dict`，并直接在控制台 `print` 出来。

当前交付口径：

- 不接 MongoDB / MySQL / Redis
- 不做上传接口
- 不落库存储
- 只输出采集后的字典结果

## 2. 目录说明

- `jnggzy.py`：主脚本
- `profile.yml`：运行配置文件
- `需求.jpg`：模块截图
- `tests/`：测试代码

## 3. 运行前准备

请使用当前机器上的 Python 环境运行：

```powershell
F:\Anaconda3\envs\spider\python.exe
```

进入当前目录后执行：

```powershell
F:\Anaconda3\envs\spider\python.exe .\jnggzy.py --profile .\profile.yml
```

## 4. 配置文件怎么改

配置文件是 [profile.yml](C:/Users/lenovo/Desktop/Spider%20One/projects/jianzhi/jnggzy/profile.yml)。

当前默认配置如下：

```yml
enable_model_enrichment: true

source:
  base_url: https://jnggzy.jinan.gov.cn/jnggzyztb/front
  module_name: 全部模块
  notice_type: 招标公告
  type: "0"
  area: ""
  subheading: ""
  start_page: 1
  max_pages: 1
  timeout_seconds: 30
  detail_delay_seconds: 0
```

各参数说明如下。

### 顶层参数

`enable_model_enrichment`

- `false`：只走规则提取
- `true`：开启客户提供的模型补全

说明：

- 当前默认开启
- 开启后，模型能返回的对应字段优先使用模型结果
- 当前脚本里，部分模型字段会先清空，再写模型结果
- 如果模型没返回对应字段，该字段会保持为空

### source 下的参数

`base_url`

- 站点接口基础地址
- 正常不用修改

`module_name`

- 要采集的一级模块
- 可以写单个模块，也可以写 `全部模块`

当前支持的一级模块有：

- `建设工程`
- `政府采购`
- `土地矿产`
- `产权交易`
- `水利工程`
- `铁路工程`
- `交通工程`
- `园林绿化工程`
- `排污权交易`
- `国有企业采购`
- `农村产权`
- `其他项目`
- `电力、新能源工程`
- `全部模块`

`notice_type`

- 只有在你想自定义单模块任务时才有意义
- 当前默认跑 `全部模块` 时，这个参数不会控制全部栏目

`type`

- 站点原始分类编号
- 正常不用手改
- 脚本内部已经按模块配置好了

`area`

- 区域参数
- 当前默认空字符串即可

`subheading`

- 子分类参数
- 正常不用手改
- 脚本内部会根据当前任务自动带对应值

`start_page`

- 从第几页开始采
- 测试时可以改成 `1`

`max_pages`

- 最大采集页数
- `0` 表示不手动限制，自动采到接口最后一页
- `1` 表示每个栏目只采 1 页
- `2` 表示每个栏目只采 2 页

建议：

- 日常测试：改成 `1` 或 `2`
- 正式全量：保持 `0`

`timeout_seconds`

- 单次请求超时时间
- 默认 `30`

`detail_delay_seconds`

- 详情页之间的等待时间
- 默认 `0`
- 如果后面需要放慢采集速度，可以改大一点

## 5. 推荐的测试方式

### 方式一：看全部模块的顺序输出

这是当前默认方式。

配置：

- `module_name: 全部模块`
- `max_pages: 1` 或 `2`

这样运行时会按一级模块分组打印，比较适合人工检查。

输出效果大概如下：

```text
========== 一级模块: 建设工程 ==========
当前二级栏目: 招标公告
[招标公告][第 1 页 / 共 1474 页] 列表条数: 15
...
二级栏目结束: 招标公告，本栏记录数: 15
一级模块结束: 建设工程，本组记录数: 42
```

### 方式二：只测单个一级模块

例如只测试 `政府采购`，可以把 `profile.yml` 改成：

```yml
source:
  base_url: https://jnggzy.jinan.gov.cn/jnggzyztb/front
  module_name: 政府采购
  notice_type: 招标公告
  type: "1"
  area: ""
  subheading: ""
  start_page: 1
  max_pages: 1
  timeout_seconds: 30
  detail_delay_seconds: 0
```

这样脚本只会跑 `政府采购` 下面配置好的栏目。

## 6. 脚本整体流程

脚本主流程如下：

1. 读取 `profile.yml`
2. 根据 `module_name` 找到当前要跑的任务列表
3. 按一级模块分组顺序执行
4. 先请求列表页
5. 从列表页拿到详情链接或详情标识
6. 进入详情页提取字段
7. 组装成标准 `dict`
8. 如果开启模型，再用客户模型覆盖对应字段
9. 最后直接把结果打印出来

## 7. 当前列表页接口说明

当前不是所有模块都走同一个接口，脚本里已经按站点真实情况分开处理。

### 7.1 常规模块

大部分模块走：

```text
/front/search.do
```

分页参数：

- `pagenum`

### 7.2 国有企业采购

走：

```text
/front/assets/querySoaList.do
```

分页参数：

- `index`
- `pageSize=15`
- `type`

其中：

- `采购公告`：`type=2`
- `中标公告`：`type=1`

### 7.3 农村产权

走：

```text
/front/getAgricultureList.do
```

分页参数：

- `index`
- `pageSize=15`
- `type`

其中：

- `挂牌项目`：`type=1`
- `成交公告`：`type=2`

## 8. 当前做过的真实参数映射

有些栏目在页面展示名和接口查询名不一致，脚本里已经做过映射，不需要手工处理。

例如：

- `建设工程 - 中标候选人` -> `中标候选人公示`
- `铁路工程 - 预中标公告` -> `中标公告`
- `土地矿产 - 结果公示` -> `中标公告`
- `产权交易 - 项目信息` -> `招标公告`
- `其他项目 - 预中标公告` -> `search_type=7 + 中标候选人公示`
- `其他项目 - 中标公告` -> `search_type=7 + 中标公告`

说明：

- 这些映射已经写在代码里
- 正常运行时不需要额外配置

## 9. 字段输出说明

当前输出字段严格按客户 Excel 模板来，不额外添加便捷字段、调试字段、别名字段。

也就是说：

- 中标公告只输出“中标”sheet 对应字段
- 招标公告只输出“招标”sheet 对应字段
- 采购意向只输出“采购意向”sheet 对应字段
- 候选人公告只输出“候选人公告”sheet 对应字段

四套模板如下。

### 9.1 中标公告字段

```text
tenderTitle
tenderNumber
cityId
cityName
renderMoney
renderDate
renderType
procurementUnit
relationCompanyName
uploadFileUrl
provinceCode
announcementType
originalWebsiteAddress
projectClassification
tenderAdditionalInfoStr
htmlContent
contentType
isUnion
contactName
contactTelephone
parentType
```

### 9.2 招标公告字段

```text
provinceCode
regionCode
regionName
bidType
announcementTitle
originalWebsiteAddress
procurementMethod
parentType
announcementType
projectNum
projectName
budgetAmount
releaseSource
releaseTime
consultationInfo
fileInfo
contentType
htmlContent
webSource
```

其中：

- `consultationInfo` 内部结构为 `purchasingInfor`、`projectInfo`
- `fileInfo` 内部结构为 `fileUrl`、`fileType`、`fileName`

### 9.3 采购意向字段

```text
provinceCode
cityId
cityName
procurementTitle
releaseSource
releaseDatetime
releaseContentMix
fileInfo
originalWebsiteAddress
extra
parentType
bidType
webSource
```

其中：

- `fileInfo` 内部结构为 `fileUrl`、`fileType`、`fileName`

### 9.4 候选人公告字段

```text
tenderTitle
renderDate
renderType
procurementUnit
relationCompanyName
uploadFileUrl
provinceCode
provinceName
cityId
cityName
announcementType
originalWebsiteAddress
htmlContent
contentType
parentType
extra
webSource
```

说明：

- `uploadFileUrl` 本身就是模板字段
- `uploadFileUrl` 内部对象字段为 `fileUrl`、`fileType`、`fileName`
- `extra` 当前用于放候选人模型返回的补充信息
- 只有 Excel 模板里存在的字段才会保留

## 10. 模型怎么开

客户提供的模型文件已经接入为可选增强。

如果要开启，把 `profile.yml` 顶层改成：

```yml
enable_model_enrichment: true
```

模型使用规则：

- 当前默认开启
- 开启后，模型涉及到的字段优先使用模型结果
- 当前脚本里，部分字段会先清空再写模型结果
- 模型没有结果的字段，可能保持为空

## 11. 测试命令

运行测试：

```powershell
F:\Anaconda3\envs\spider\python.exe -m pytest .\tests\test_jnggzy_templates.py -q
```

语法检查：

```powershell
F:\Anaconda3\envs\spider\python.exe -m py_compile .\jnggzy.py
```

## 12. 当前建议

如果是客户验收或人工查看，建议这样操作：

1. 先把 `max_pages` 改成 `1`
2. 跑一次 `全部模块`
3. 看每个一级模块下的字典字段是否符合预期
4. 没问题后，再把 `max_pages` 改回 `0` 跑全量
