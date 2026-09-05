# B站直播间自动发弹幕工具

一个轻量级的B站直播自动发弹幕模板程序，无需打开浏览器，后台静默运行。

## 项目结构

```
bilibili-danmaku-bot/
├── config.json          # 配置文件（cookie、房间号、发送间隔等）
├── main.py              # 主程序
├── danmaku_list.txt     # 弹幕内容列表（每行一条）
├── requirements.txt     # Python依赖
├── README.md            # 使用说明
└── danmaku_bot.log      # 运行日志（自动生成）
```

## 环境要求

- Python 3.8+
- 一个B站账号（需要登录凭证）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 Cookie

1. 浏览器登录 [B站](https://www.bilibili.com)
2. 按 F12 打开开发者工具 → Application（应用）→ Cookies
3. 找到并复制以下三个值：
   - `SESSDATA`
   - `bili_jct`（即 csrf token）
   - `DedeUserID`（可选）

### 3. 配置 config.json

```json
{
  "cookie": {
    "SESSDATA": "你的SESSDATA",
    "bili_jct": "你的bili_jct",
    "DedeUserID": "你的DedeUserID"
  },
  "room_id": 123456,
  "send_interval_min": 5,
  "send_interval_max": 10,
  "send_mode": "random",
  "max_retry": 3,
  "log_level": "INFO"
}
```

### 4. 编辑弹幕内容

打开 `danmaku_list.txt`，每行写一条弹幕，程序会随机或顺序选取发送。

### 5. 运行

```bash
python main.py
```

按 `Ctrl+C` 停止程序。

## 配置项说明

| 配置项 | 说明 | 默认值 |
|---|---|---|
| cookie.SESSDATA | 登录凭证，必填 | - |
| cookie.bili_jct | csrf token，必填 | - |
| cookie.DedeUserID | 用户ID，可选 | - |
| room_id | 目标直播间房间号 | 0 |
| send_interval_min | 发送间隔最小值（秒） | 5 |
| send_interval_max | 发送间隔最大值（秒） | 10 |
| send_mode | 发送模式：random（随机）/ sequence（顺序） | random |
| max_retry | 单条弹幕最大重试次数 | 3 |
| log_level | 日志级别：DEBUG/INFO/WARNING/ERROR | INFO |

## 功能特性

- 无需浏览器，纯网络请求发送
- 登录状态自动验证
- 随机/顺序两种弹幕选取模式
- 可配置发送间隔（随机区间，降低风控风险）
- 失败自动重试
- 连续失败5次自动停止（防止账号被封）
- 完整日志记录（控制台 + 文件）

## 风险提示

1. **账号风险**：自动发弹幕违反B站社区规则，可能导致禁言或封号，建议使用小号
2. **频率控制**：发送间隔不要低于3秒，高频发送极易触发风控
3. **Cookie安全**：SESSDATA 等于账号密码，不要泄露给他人
4. **内容合规**：弹幕内容不要包含违规词、广告、刷屏内容
5. **本工具仅供学习研究使用，使用者需自行承担一切后果**

## 常见问题

**Q: 提示"登录验证失败"怎么办？**
A: Cookie已过期或填写错误，重新登录B站获取最新的SESSDATA和bili_jct。

**Q: 弹幕发送失败，code=-101？**
A: 账号被风控或Cookie无效，检查账号状态。

**Q: 弹幕发出去了但直播间看不到？**
A: 可能被B站审核拦截（吞弹幕），降低发送频率或更换弹幕内容。

**Q: 可以同时给多个直播间发吗？**
A: 当前模板只支持单个房间，如需多房间可复制多份配置分别运行。

## 免责声明

本项目仅供技术学习和研究使用，请勿用于商业用途或违反B站用户协议。使用本工具产生的一切后果由使用者自行承担。
