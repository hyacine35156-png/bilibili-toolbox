# B站工具箱 — 安装与运行说明

> 版本：v6.7.13　｜　更新日期：2026-11-01

---

## 一、系统要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11（64 位） |
| Python | 3.10 及以上（实测 3.14.7） |
| 网络 | 需能访问 api.bilibili.com（卡密验证还需访问验证服务器） |
| 磁盘 | 至少 200 MB 可用空间 |

---

## 二、安装步骤

### 1. 获取代码

    git clone https://github.com/hyacine35156-png/bilibili-toolbox.git
    cd bilibili-toolbox

### 2. 安装依赖

    pip install -r requirements.txt

requirements.txt 内容：

    requests>=2.31.0
    websocket-client>=1.8.0

### 3. 首次运行

    python main.py

程序会自动完成以下初始化：

- 创建 data/ 数据目录（config.py 中 BASE_DIR.mkdir）
- 生成空的配置文件（storage.safe_load_json 缺文件时用默认值）
- 弹出卡密验证窗口

---

## 三、卡密验证

### 为什么需要卡密

程序启动时强制验证卡密，未通过无法进入主界面。
验证逻辑封装在 card_verify.py（PyArmor 加密模块，不可直接阅读）。

### 设备绑定机制

卡密与【机器码】绑定。机器码由本机硬件信息（CPU/主板/磁盘）哈希生成。

    换一台电脑 -> 机器码变化 -> 原卡密报「该卡密已绑定其他设备」(code -5)

### 如何查看本机机器码

1. 启动程序，卡密窗口会显示设备码
2. 或运行：

    python -c "import card_verify; print(card_verify.get_machine_code())"

### 如何处理换机

1. 在新电脑首次运行时记下新的机器码
2. 登录卡密管理后台，将卡密重新绑定到新机器码
3. 重启程序，联网验证一次即可

**或者**直接在后台生成一张新卡密给新机器用。

### 验证服务器

    CARD_API_BASE   = https://precious-tanuki-c4b16d.netlify.app/api
    CARD_VERIFY_URL = https://precious-tanuki-c4b16d.netlify.app/api/verify-card

服务不可用时无法完成验证（不支持离线验证）。

---

## 四、数据文件位置

### 源码运行（python main.py）

    项目根目录/data/

### 打包 exe 运行

    dist/data/

### 关键数据文件

| 文件 | 内容 |
|---|---|
| accounts.json | B站账户（SESSDATA / bili_jct / UID） |
| rooms_config.json | 直播间列表 |
| schedule_config.json | 日程任务 |
| rush_groups.json | 抢码任务组 |
| app_settings.json | 全局设置 |
| card_auth.json | 卡密授权信息 |
| rush_results.jsonl | 抢码历史记录 |
| task_status_cache.json | 任务状态缓存 |

---

## 五、首次使用流程

1. **验证卡密** → 通过后进入主界面
2. **进入「⚙ 设置」页**
   - 点「＋ 添加账户」→ 填入 B站 SESSDATA 和 bili_jct
   - 点「⚡ 全部验证」确认所有账户有效
3. **添加直播间** → 点「从账户导入」可自动获取各账户的房间号
4. **配置功能**（按需）
   - 「枪码工具」：抢码任务（旧模式 / 新模式·精准抢码）
   - 「弹幕工具」：自动发送弹幕
   - 「看播任务」：自动挂机看播
   - 「兑换码」：领取兑换码
   - 「日程任务」：定时执行以上任务
5. **验证配置** → 等待下一个整点/半点，看日志是否正常执行

---

## 六、如何获取 SESSDATA 与 bili_jct

1. 浏览器登录 B站
2. 按 F12 打开开发者工具
3. 切换到「Application（应用）」→「Cookies」→ https://www.bilibili.com
4. 找到：
   - SESSDATA — 登录凭证（长字符串）
   - bili_jct — CSRF 令牌（32 位十六进制）
   - DedeUserID — 用户 UID（数字）
5. 复制粘贴到程序的「添加账户」窗口

---

## 七、打包成 exe

    pip install pyinstaller
    python -m PyInstaller "B站工具箱_v6.7.13.spec" --clean --noconfirm

产物在 dist/ 目录。

**注意**：打包前需关闭正在运行的程序（否则 exe 被锁定报 WinError 5）。

---

## 八、常见问题

### Q: 启动报 Could not create temporary directory!

**原因**：%TEMP% 目录下积累了太多 PyInstaller 残留的 _MEI* 目录。

说明：PyInstaller 单文件 exe 每次运行会解压到 %TEMP%/_MEIxxxxxx（约 37MB），
正常退出会自动删除，但被强杀（任务管理器结束 / 崩溃）时会残留。

**解决**（关闭所有正在运行的程序后执行）：

    Get-ChildItem $env:TEMP -Filter "_MEI*" -Directory | Remove-Item -Recurse -Force

v6.7.7 起程序已内置启动时自动清理（只删 1 小时以上未修改的目录）。

### Q: 弹出「账号登录已失效」

v6.7.9 起已修复网络误报。如仍出现：

- 确认 SESSDATA 没有过期（浏览器登录状态是否正常）
- 单独点该账户的「验证登录」看具体错误

### Q: 抢码总是晚到

检查日志中这几行：

    [提前量] 半RTT ... 超过上限 150ms，已下调（防提早）
    [提前量] 防提早保护: 提前量 ... 超过安全上限 ...，已下调
    [精准首发] 真实到达偏差 +XXXms（晚到，自旋精度 +X.Xms）

- 自旋精度应在 <10ms
- 真实到达偏差在 +50~+200ms 属正常（故意晚到以避开「未到时间」判定）

### Q: 系统时钟偏差很大

需管理员权限执行：

    w32tm /resync

或在程序「枪码工具」页点「同步系统时间」。
程序会自动补偿 NTP 偏差，但建议定期校准。

---

## 九、目录结构说明

    bilibili-toolbox/
    ├── main.py                  主程序入口
    ├── config.py                常量 / 路径 / 颜色 / API 地址
    ├── storage.py               原子写 / 安全读
    ├── bili_api.py              B站接口封装
    ├── widgets.py               自定义 Tk 组件
    ├── dialogs.py               对话框
    ├── app_settings.py          全局设置读写
    ├── schedule_params.py       日程参数校验
    ├── rush_stats.py            抢码统计
    ├── tasks_config.py          任务表 + act_id 缓存
    ├── card_auth.py             卡密验证转发层
    ├── card_verify.py           PyArmor 加密的验证实现
    ├── pyarmor_runtime_000000/  PyArmor 运行时（必需）
    ├── ui/                      各功能页面
    │   ├── theme.py             字体与主题
    │   ├── schedule.py          日程任务页
    │   ├── watch_live.py        看播页
    │   ├── code_export.py       兑换码页
    │   ├── card_auth_page.py    卡密验证页
    │   └── rush_reward/         抢码页（拆分模块）
    ├── managers/                账户与直播间管理器
    ├── tests/                   单元测试
    ├── data/                    源码运行时的数据目录
    └── dist/                    打包产物目录
        └── data/                exe 运行时的数据目录

---

## 十、卸载

删除程序目录即可。如需彻底清理，同时删除 %TEMP% 下的 _MEI* 残留。

---

## 附：版本记录

| 版本 | 主要变更 |
|---|---|
| v6.7.13 | 仓库瘦身（112MB → 3.5MB），移除 ffmpeg/node_modules/backup 等 316 个无用文件 |
| v6.7.12 | 顶部标题栏改用思源宋体 Heavy900 |
| v6.7.11 | 删除副标题，修复 tab 文字截断 |
| v6.7.10 | 修复任务完成状态显示为「已完成」，缩小日志字号 |
| v6.7.9 | 移除设置页滚动条，修复账号失效误报 |
| v6.7.7 | 修复 Could not create temporary directory |
| v6.7.3 | 抢码提前量双重保护（保证一定晚到） |
