# AI投顾值班室使用说明

AI投顾值班室是本项目里的主动分析工作台，用来把“题材主线识别、个股八维+紫苏叶+缠论复核、风控纪律、飞书/微信推送”组合成一个日内值班流程。当前版本是 MVP：它负责生成研究快照和操作纪律提示，不做自动下单，也不承诺收益。

## 1. 启动项目

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe main.py --webui-only
```

启动后打开：

```text
http://127.0.0.1:8000/advisor
```

如果左侧菜单可见，点击 `AI投顾` 也可以进入。

## 2. 页面怎么用

进入页面后主要看四块：

| 区域 | 用途 |
| --- | --- |
| 顶部状态卡 | 查看当前阶段、通知是否可用、最新快照时间、是否需要人工确认 |
| 值班控制台 | 选择阶段、是否生成后立即推送、手动运行、发送推送测试 |
| 最新快照 | 查看主线判断、候选分层、观察点、风险纪律和下一步动作 |
| 历史快照 | 回看最近生成的分析记录，方便复盘和后续迭代 |

建议你的日常使用节奏：

| 时间 | 阶段 | 重点 |
| --- | --- | --- |
| 09:20 | 竞价题材雷达 | 看隔夜催化、竞价异动、疑似启动题材，先不急着买 |
| 10:00 | 开盘主线确认 | 判断题材是真启动、短拉升还是试探，分层龙头/中军/补涨 |
| 11:30 | 午盘策略校准 | 看上午持续性、量价承接、下午是否还能参与 |
| 14:30 | 尾盘风控 | 检查高位分歧、隔夜风险、是否降仓或只保留核心观察 |
| 15:30 | 收盘复盘 | 沉淀次日观察清单、纪律清单、候选池变化 |

## 3. 一键生成快照

页面里可以选择：

- `自动匹配当前阶段`：系统按当前时间选择最接近的值班阶段。
- 指定某个阶段：适合复盘或补跑，比如下午补一份开盘确认。
- `生成后立即推送`：生成快照后同步发到已配置的通知渠道。

生成结果会保存到本地：

```text
data/advisor_copilot_snapshots.json
```

这个文件是运行数据，不建议提交到 Git。

## 4. 配置飞书/微信推送

当前按钮已经接入项目原有通知服务。要真正推送，需要在 `.env` 或系统环境变量里配置至少一个通知渠道。

飞书机器人：

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxx
FEISHU_WEBHOOK_SECRET=可选，如果机器人开启了签名校验再填
```

企业微信机器人：

```env
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx
```

配置后重启项目，再进入 `AI投顾` 页面。如果顶部显示通知已就绪，就可以使用：

- `发送推送测试`
- 勾选 `生成后立即推送`

## 5. API 调用方式

查看状态：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/advisor/status -Method Get
```

生成当前阶段快照：

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/v1/advisor/run `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"stage":"auto","send_notification":false}'
```

生成并推送开盘确认：

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/v1/advisor/run `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"stage":"open_confirm","send_notification":true}'
```

查看最近快照：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/advisor/snapshots?limit=5" -Method Get
```

发送推送测试：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/advisor/notify-test -Method Post
```

## 6. 当前版本的边界

当前 MVP 已经把“投顾团队工作台”的壳搭好，但真正变成可持续盈利系统，还需要继续接数据和规则：

- 题材强度：接入板块涨幅、涨停家数、连板高度、成交额集中度、资金回流。
- 持续性判断：区分一日游、试探启动、主升、高潮、退潮。
- 个股复核：把候选股自动送入八维、紫苏叶、缠论组合分析。
- 持仓联动：接入你的真实或模拟持仓，生成止盈、止损、加仓、减仓条件。
- 主动推送：后续可加定时任务，让系统在 09:20、10:00、11:30、14:30、15:30 自动跑并推送。
- 复盘闭环：把每次建议、实际走势、执行结果沉淀成交易日志，用来优化规则。

## 7. 后续改造入口

核心后端文件：

```text
src/services/advisor_copilot_service.py
api/v1/endpoints/advisor.py
```

核心前端文件：

```text
apps/dsa-web/src/pages/AdvisorPage.tsx
apps/dsa-web/src/api/advisor.ts
apps/dsa-web/src/types/advisor.ts
```

测试文件：

```text
tests/test_advisor_copilot_service.py
tests/test_advisor_api.py
apps/dsa-web/src/pages/__tests__/AdvisorPage.test.tsx
```

优先建议下一步做两件事：

1. 把真实题材/板块/涨停/成交额数据接进 `AdvisorCopilotService.run_stage()`。
2. 加一个定时任务，让值班室按交易日时间表自动生成并推送。
