# 江苏 GSXT 侦察结论

目标：

- 站点：`https://js.gsxt.gov.cn`
- 地域：`泰州`
- 日期口径：`企业注册日期 = 成立日期 / CLRQ`
- 样本日：`2026-04-30`

## 当前侦察结果

当前访问链路不是单层反爬，而是至少两层：

1. `521` 第一层挑战  
   页面返回 `document.cookie=...__jsl_clearance_s...; location.href=...`

2. `412 Environment Checking` 第二层环境校验  
   页面标题为 `Environment Checking`，会加载：
   - `/1eeb27c_268ab095d.js`
   - `/ctct_bundle_c8c12415.js`

3. 第二层脚本会发起：
   - `POST /ctct/nwaf/waf.log`

4. 当前环境下该请求返回：
   - `405`
   - 返回体为 `NWAF页面`
   - 页面文案明确提示：`当前IP请求异常，请更换IP地址进行访问，或访问 https://shiming.gsxt.gov.cn 实名注册/登录后再进行访问`

## 已确认的 cookie / 现象

- 第一层可拿到：
  - `__jsluid_s`
  - `__jsl_clearance_s`
- 第二层可拿到：
  - `CT_1rqu7ab01`
  - `CT_16eadf26c`
  - `CT_1f7ba0eb8`
  - `CT_1g9aa1ec2`

但仅复用 cookie 做纯请求仍会停留在：

- `412 Environment Checking`

说明第二层不只是看 cookie，还会看浏览器环境或风控结果。

## 代理验证新增结论

用户提供的 `GoProxy` 面板：

- `http://117.50.131.232:7778/`

已确认 guest 模式可直接读取：

- `/api/proxies`
- `/api/pool/status`
- `/api/custom/status`

并且当前 `localhost:7776 / 7777 / 7779` 并没有在本机监听；这次可用的是面板返回的远端出口地址，不是本地转发端口。

### 2026-04-30 实测结果

1. 用新增脚本 `goproxy_gsxt_probe.py` 抽样测试低延迟亚洲 `HTTP` 出口后，绝大多数公开代理本身不可用或超时。
2. 但至少有两个远端 `HTTP` 出口可以实际连到 `js.gsxt.gov.cn`：
   - `1.231.81.166:3128`（KR）
   - `8.219.97.248:80`（SG）
3. 这两个出口在纯请求下返回 `521` 第一层挑战，而不再是本机直连时观察到的 `412 / 405 NWAF页面`。
4. 再用本机 Chrome + `1.231.81.166:3128` 做 Playwright 验证后：
   - `response_status = 521`
   - 页面标题已经是 `Environment Checking`
   - 已拿到：
     - `__jsluid_s`
     - `__jsl_clearance_s`
     - `CT_1rqu7ab01`
     - `CT_16eadf26c`
     - `CT_1f7ba0eb8`
     - `CT_1g9aa1ec2`

### 这说明什么

- 更换出口是有效的。
- 代理后，链路已经从“本机直连直接被 NWAF 第二层拦截”推进到了“可稳定进入第一层挑战，并在浏览器里落到 `Environment Checking` 页面”。
- 但截至本次验证，还没有穿过第二层进入真实查询页，所以 `泰州 + 2026-04-30 + 成立日期` 的正式检索参数仍未拿到。

## 当前判断

截至 `2026-04-30`，本机当前公网出口/IP 已被 `js.gsxt.gov.cn` 的 NWAF 风控拦截。  
问题不在“没找到查询接口”，而在“还没穿过风控进入真实首页/查询页”。

## 下一步建议

优先级从高到低：

1. 基于已可连通的 `KR/SG` 代理，继续做“代理 + 浏览器环境”的第二层验证，重点盯 `waf.log` 是否仍返回 `405 NWAF页面`
2. 如果代理浏览器环境下仍无法越过第二层，再考虑 `https://shiming.gsxt.gov.cn` 登录态
3. 最后才是继续做第二层环境校验脚本的最小逆向，这条线成本更高，且不保证能绕过当前 IP 风控
