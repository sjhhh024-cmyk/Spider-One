# doctor-ywbd 当前侦察结论

## 真实可访问页面

以下页面在当前环境下已经实际请求成功：

1. `https://data.120ask.com/yisheng/jibing.html`
2. `https://data.120ask.com/yisheng/keshi.html`
3. `https://data.120ask.com/yisheng/area.html`
4. `https://data.120ask.com/yiyuan/area.html`
5. `https://data.120ask.com/yiyuan/yisheng/0387pltyawkim7pa.html`
6. `https://data.120ask.com/yisheng/f06faia2nlwg3h0f.html`

## 已确认路由规则

- 疾病入口页包含：`/yisheng/jibing_d*.html`
- 疾病中间页包含：`/yisheng/list_j*.html`
- 疾病分页示例：`/yisheng/list_j1072p2.html`
- 科室分页示例：`/yisheng/list_d1p2.html`
- 地区分页示例：`/yisheng/list_a110000p2.html`
- 医院列表分页示例：`/yiyuan/list_a110000p2.html`
- 医院详情示例：`/yiyuan/0387pltyawkim7pa.html`
- 医院专家页示例：`/yiyuan/yisheng/0387pltyawkim7pa.html`
- 最终医生详情统一为：`/yisheng/<doctor_slug>.html`

## 已确认接口

医院专家页内嵌：

```text
$.getJSON('/public/ajaxyisheng', {'hid':hid,'pid':pid,'did':did,'zid':zid,'sid':sid,'wid':wid,'tid':tid,'kid':kid,'limit':limit}, ...)
```

当前已实际验证：

- 专家页首屏 HTML 可访问
- 首屏返回站点 cookie 后，请求 `/public/ajaxyisheng` 可返回 JSON
- 请求至少需要：
  - 页面 cookie
  - `Referer: 医院专家页 URL`
  - `X-Requested-With: XMLHttpRequest`

验证成功的示例参数：

```text
hid=125
pid=2
did=0
zid=0
sid=0
wid=0
tid=0
kid=0
limit=8
```

返回 JSON 中包含：

- `rsList`
- `tjList`
- `pageCount`

其中医生链接字段为：

```text
rsList[].url
```

## 当前项目实现策略

1. 疾病、科室、地区入口分别独立投递各自的 Redis key
2. 医院入口先扩到医院列表和医院详情，再扩医院专家页
3. 医院专家页优先抓首屏 HTML，再继续请求 `/public/ajaxyisheng`
4. 所有来源最终统一汇总到 `doctor_ywbd:doctor_info_url`
5. 医生详情统一写入 MongoDB `doctor_ywbd`
