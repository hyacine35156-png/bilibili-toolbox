# B站工具箱 项目交接文档

> 编写日期：2026-10-25
> 当前版本：**v6.0.4**
> 文档性质：完整交接文档，供新接手者独立开发、打包、排错使用。
> 所有路径、版本号、命令均为 2026-10-25 实测核对结果。

---

## 目录

1. [项目概览](#一项目概览)
2. [项目文件位置与目录结构](#二项目文件位置与目录结构)
3. [项目架构](#三项目架构)
4. [技术实现要点](#四技术实现要点)
5. [卡密授权系统（重点）](#五卡密授权系统重点)
6. [数据存储与备份](#六数据存储与备份)
7. [打包发布流程（重点）](#七打包发布流程重点)
8. [Git 与 GitHub 仓库](#八git-与-github-仓库)
9. [外部服务与依赖](#九外部服务与依赖)
10. [日常维护操作手册](#十日常维护操作手册)
11. [已知问题、历史教训与注意事项](#十一已知问题历史教训与注意事项)
12. [遗留事项清单](#十二遗留事项清单)

---

## 一、项目概览

**B站工具箱**是一个 Windows 桌面应用（Python + Tkinter，PyInstaller 打包成单文件 exe），用于 B 站直播/创作激励的多账号自动化运营。

**八大功能模块（顶部 Tab）：**

| Tab | 功能 | 主要代码位置 |
|---|---|---|
| ⚡ 抢码工具（默认页） | 监控并领取 B 站创作激励任务奖励，含「旧模式」与「新模式·精准抢码」两套抢码逻辑 | `ui/rush_reward/` |
| 💬 弹幕工具 | 多账号向指定直播间自动发弹幕 | `main.py`（弹幕页内联） |
| ⏻ 定时关机 | 定时/延时关闭电脑 | `main.py`（关机页内联） |
| 📺 看播任务 | 多账号模拟真实看播（进房、心跳、x25Kn 上报、弹幕 WS、送礼） | `ui/watch_live.py` |
| 🎁 兑换码 | 领取后提取/导出/管理兑换码 | `ui/code_export.py` |
| 📅 日程任务 | 定时执行抢码/看播/弹幕/送礼/关机，支持方案保存 | `ui/schedule.py` |
| 👤 账户管理 | B 站账号 Cookie 增删改查、直播间管理 | `main.py` + `managers/` |
| 📖 使用说明 | 内置帮助文本 | `config.py` 中 `TASK_GUIDE_TEXT` |

**技术栈：**
- 语言：Python 3.14.7（系统解释器路径见下）
- GUI：标准库 Tkinter / ttk（暗色主题，无任何第三方 GUI 框架）
- 网络：`requests`（HTTP / WBI 签名）、`websocket-client`（直播弹幕长连接）
- 加密：PyArmor 9.2.7 (trial) 加密卡密验证模块
- 打包：PyInstaller 6.22.2（spec 配置，单文件 exe，无控制台窗口）
- 授权后端：Netlify Functions + Supabase（卡密数据库）
- 无数据库：账号、配置、任务全部用本地 JSON 文件存储

---

## 二、项目文件位置与目录结构

### 2.1 项目根目录（最重要）

```
C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\
```

- 系统 Python 解释器：`C:\Users\15868\AppData\Local\Programs\Python\Python314\python.exe`
- 桌面实际路径（系统重定向后）：`E:\虚拟c盘\`（创建桌面快捷方式时 WScript 返回的就是这个路径）

### 2.2 核心源码结构（v6.0.3 起已从单文件拆分为 19 个模块）

```
bilibili-danmaku-bot/
├── main.py                      # 程序入口（1991行）：主窗口、8个Tab骨架、弹幕页/关机页/账户页/说明页
├── config.py                    # 全局常量（120行）：路径、版本号、配色、API地址、WBI混淆表、请求头
├── tasks_config.py              # 游戏活动任务表（167行）：ALL_TASKS + 各版本 act_id 映射
├── storage.py                   # 持久化（180行）：原子写JSON、安全加载、兑换码记录
├── bili_api.py                  # B站接口（506行）：登录校验、发弹幕、WBI签名、任务查询/库存/领取
├── widgets.py                   # 自定义Tk组件（177行）：DarkButton/DarkEntry/ToolTip等
├── dialogs.py                   # 账户添加/编辑对话框（151行）
├── card_auth.py                 # 卡密验证转发层（18行，明文；card_verify缺失时给占位）
├── card_verify.py               # 卡密验证核心（PyArmor加密，仅3行密文，不可手改）
├── app_icon.ico                 # 应用图标
├── managers/
│   ├── __init__.py
│   ├── account.py               # 账户管理器（76行）：增删改查、Cookie组装
│   └── room.py                  # 直播间管理器（108行）：增删改查、从账户导入
├── ui/
│   ├── __init__.py
│   ├── watch_live.py            # 看播任务页（2101行）：进房/心跳/x25Kn/弹幕WS/送礼
│   ├── schedule.py              # 日程任务页（1009行）：定时执行各类任务
│   ├── code_export.py           # 兑换码页（542行）
│   ├── card_auth_page.py        # 卡密认证页（254行）
│   └── rush_reward/
│       ├── __init__.py          # 抢码主框架（2046行）：旧模式UI+逻辑、任务过滤、领取
│       ├── new_mode.py          # 精准抢码新模式（1469行，Mixin）：任务组/调度器/NTP/首帧/风控退避
│       └── scheduled.py         # 旧版定时领取（667行，Mixin）：定时任务列表与工作线程
├── pyarmor_runtime_000000/      # PyArmor运行时（__init__.py + pyarmor_runtime.pyd）
├── B站工具箱_v6.0.4.spec        # 当前打包配置（每个版本一个spec，旧spec全部保留）
├── requirements.txt             # 仅 requests、websocket-client
├── build.py                     # ⚠ 已过时的旧打包脚本（引用 main_gui_pro.py），实际打包用 spec，勿用
├── 一键打包.bat                 # 旧打包批处理（同样过时，以 spec 为准）
├── README.md                    # 早期弹幕工具的说明，已不能反映当前完整功能
├── agent.md                     # 项目开发规则/用户偏好（部分内容如 main_gui_pro.py 已过时）
├── 项目完整档案.md               # v4.6.5~v6.0.3 历史档案
├── 单文件拆分计划.md             # A1 拆分方案文档
├── LICENSE                      # MIT
├── data/                        # 运行时数据（见第六章，git 已忽略）
├── dist/                        # 打包输出（git 已忽略）
├── build/                       # PyInstaller 中间产物（可随时删除）
├── versions/                    # 版本备份（当前仅 main_gui_pro_v6.0.3.py）
└── card-system/                 # 卡密授权服务（Netlify 后端 + 下载页，见第五章）
```

核心模块合计约 **11,585 行** Python 代码。

### 2.3 根目录大量历史脚本（重要提醒）

根目录存在数百个一次性开发脚本，命名前缀包括 `patch_*.py`、`fix_*.py`、`add_*.py`、`test_*.py`、`analyze_*.py`、`update_v*.py`、`verify_*.py`、`check_*.py`、`probe_*.py` 等，还有大量 `screenshot*.png`、`main_gui_pro_v*_backup.py` 备份文件、`backup_*/` 目录。

- 这些是历次迭代用的临时补丁/探针/测试脚本，**不属于运行程序**，程序运行和打包完全不依赖它们。
- 其中大部分已被 `.gitignore` 忽略（`fix_*`、`check_*`、`gen_test*` 等），但仍有大量未被忽略、显示为 git 未跟踪（`??`）。
- 真正的运行入口只有 `main.py`，由 spec 的 `hiddenimports` 决定哪些模块被打包（见第七章）。
- 历史单文件备份：`main_gui_pro_v3.5.1_backup.py` ~ `main_gui_pro_v6.0.3_backup_before_optimization.py`，是拆分前的老版本快照，留作考古/回滚参考。

**建议：交接后不要急于删除这些脚本；若要清理，先整体备份项目目录再动手。**

---

## 三、项目架构

### 3.1 启动流程

入口 `main.py` 末尾的 `main()`：

1. （Windows）调用 `ctypes.windll.user32.SetProcessDPIAware()` 做高 DPI 适配。
2. 创建第一个 `tk.Tk()` 根窗口，调用 `show_card_auth(root)` 显示**卡密验证页**。
3. 验证不通过 → 销毁窗口直接退出；验证通过 → 销毁验证窗口。
4. 重新创建 `tk.Tk()`，实例化 `DanmakuApp(root)`（主窗口），进入 `mainloop()`。
5. `DanmakuApp.__init__` 中：
   - 加载配置、初始化 `AccountManager` / `RoomManager`；
   - `_migrate_old_files()`：把 exe 同目录的旧配置文件迁移到 `data/` 子目录；
   - 构建顶部标题栏、Tab 栏、底部状态栏（版本号、授权剩余天数、设备码）；
   - 实例化各功能 Frame；
   - 恢复上次停留的 Tab。

### 3.2 模块依赖关系

```
main.py
 ├─ config.py        （常量，无外部依赖）
 ├─ tasks_config.py  → config.py, storage.py
 ├─ storage.py       → config.py
 ├─ bili_api.py      → config.py, tasks_config.py
 ├─ widgets.py / dialogs.py
 ├─ card_auth.py     → card_verify.py（PyArmor，导入失败时有占位兜底）
 ├─ managers/        → config.py（账户/直播间）
 └─ ui/
     ├─ rush_reward/__init__.py（RushRewardFrame）
     │    ├─ new_mode.py   （NewModeMixin，精准抢码）
     │    └─ scheduled.py  （ScheduledMixin，旧定时领取）
     ├─ watch_live.py   （WatchLiveFrame）
     ├─ schedule.py     （ScheduleFrame）
     ├─ code_export.py  （CodeExportFrame）
     └─ card_auth_page.py（CardAuthFrame）
```

- 抢码模块采用 **Mixin 组合**：`RushRewardFrame` 同时继承 `NewModeMixin` 和 `ScheduledMixin`，新模式/旧定时逻辑分别在两个 mixin 文件里，由宿主类提供共享 UI 和工具方法。
- 循环导入已验证无环；17 个子模块均可单独导入（拆分时做过自检）。

### 3.3 抢码任务数据模型

所有游戏激励任务都在 `tasks_config.py` 的 `ALL_TASKS` 列表中，每条结构：

```python
{"version": "绝区零3.3", "period": "全版本", "type": "直播里程碑",
 "name": "累计3天完成开播及互动任务", "task_id": "18ERA1wloghvcrj00",
 "award": "菲林*360"}
```

当前（2026-10-25）共 **103 个任务**：
- 鸣潮3.7：29 个
- 原神7.1：17 个
- 崩坏星穹铁道4.6：30 个
- 绝区零3.3：27 个（观看互动3、投稿12、直播5、直播里程碑7）

`VERSION_DEFAULT_ACT_ID` 字典把版本名映射到 B 站活动 `act_id`（同一版本所有任务共享一个 act_id）。

**UI 下拉框联动（v6.0.4 已改为动态）：**
- 版本下拉框：从 `ALL_TASKS` 动态去重生成（旧模式 `version_combo`、新模式 `nm_version_combo` 都是动态）。
- 期数下拉框：根据所选版本从 `ALL_TASKS` 过滤。
- 类型下拉框：根据版本+期数过滤。
- 任务下拉框：根据版本+期数+类型过滤。
- 因此**更新游戏版本只需改 `tasks_config.py`，UI 会自动出现新版本**（这是 3.2→3.3 踩过硬编码坑后修的）。

---

## 四、技术实现要点

### 4.1 B 站接口（bili_api.py）

- **登录校验**：`GET https://api.bilibili.com/x/web-interface/nav`，带 Cookie，判断 `code==0 && data.isLogin`。
- **发弹幕**：`POST https://api.live.bilibili.com/msg/send`，参数含 csrf(bili_jct)、roomid、msg。
- **任务三件套**（创作激励）：
  - `MISSION_INFO_API = https://api.bilibili.com/x/activity_components/mission/info`（查库存/资格）
  - `MISSION_RECEIVE_API = .../mission/receive`（领取）
  - `MISSION_MYLIST_API = .../mission/mylist`（我的任务列表）
- **WBI 签名**：B 站接口签名，用 `MIXIN_KEY_ENC_TAB`（0–63 合法置换表，config.py 里）对 img_key+sub_key 重排，再对参数做 md5 得到 `w_rid` + `wts`。拆分时与官方公式独立复算比对，`w_rid` 逐字节一致。
- 带 WBI 密钥缓存（`_WBI_KEY_CACHE`，1 小时 TTL）和任务信息缓存（`_mission_info_cache`，24 小时 TTL）。

### 4.2 看播/直播（ui/watch_live.py）

- **进房**：进入直播间获取 token。
- **心跳**：定时上报（默认 60 秒），模拟在线；心跳上报失败不影响弹幕连接和视频流。
- **x25Kn 参数**：B站风控参数，代码中有专门的上报逻辑（历史上有 `patch_x25kn.py`、`test_x25kn.py` 探针）。
- **弹幕 WebSocket**：用 `websocket-client` 建立直播弹幕长连接。
- **视频流**：下载直播视频流以模拟真实观看。
- **送礼**：调用送礼接口，消耗真实电池；无电池时禁用按钮，送礼次数默认 0。

### 4.3 精准抢码（new_mode.py，技术含量最高）

- **任务组（group）**：可把多个任务+账户+目标准点时间编成一组统一调度。
- **NTP 毫秒级对时**：抢码前向 NTP 服务器校准本地时间，降低本机时钟偏差。
- **首帧/预热**：提前建立连接、预热请求。
- **调度器（scheduler）**：Treeview 展示定时任务（早期是 Frame，UI 重构过，曾因残留 `nm_scheduler_frame` 引用报错，已修为调用 `nm_update_scheduler()`）。
- **风控退避**：随机间隔、请求频率退避重试；抢码间隔历史经验值 600–800ms（见 agent.md）。
- 多线程独立运行，每个任务独立工作线程。

### 4.4 多线程与状态

- 大量网络任务用 `threading.Thread` 跑后台，避免阻塞 Tk 主线程。
- 全局锁 `_GLOBAL_LOCK`（config.py）。
- 跨线程更新 UI 一律用 `self.after(0, lambda: ...)` 投递到 Tk 主线程。
- 运行中保护：删除账户前检查该账户是否有任务在跑（v6.0.4 修过 `watch_frame`/`gift_frame`/`rush_frame` 属性名拼错导致保护失效的 bug，正确属性名是 `watch_page` / `rush_page`）。

### 4.5 持久化（storage.py）

- `atomic_write_json`：先写 `.tmp` → `flush` + `fsync` → `os.replace`，断电不损坏。
- `safe_load_json`：JSON 解析失败时把坏文件备份为 `.corrupt`，返回默认值，**不会静默清空数据**。

---

## 五、卡密授权系统（重点）

### 5.1 客户端

- `card_verify.py`：卡密验证核心，**已用 PyArmor 9.2.7 (trial) 加密**（文件头 `# Pyarmor 9.2.7 (trial)...`），源码不可见、不可手改。
- `pyarmor_runtime_000000/`：PyArmor 运行时（`__init__.py` + `pyarmor_runtime.pyd`），**打包必须包含**，否则卡密系统失效（v5.9.3 踩过这个坑）。
- `card_auth.py`：明文转发层，从 `card_verify` 导入 `get_machine_code / verify_card_online / load_saved_card / is_card_expired / save_card_info / clear_saved_card / get_card_remaining_text` 等；若导入失败给占位函数，保证开发环境能启动。
- `ui/card_auth_page.py`：卡密输入/验证界面。
- 业务规则（来自 agent.md）：
  - 离线宽限期 **1 天**；
  - 卡密剩余时间精确到**分钟**；
  - 验证通过后本地保存授权信息，下次可直接进入直到过期；
  - 设备码在主窗口底部状态栏显示（脱敏后带"复制"按钮）。

### 5.2 授权后端（card-system/，Netlify + Supabase）

```
card-system/
├── netlify.toml                    # publish=public, functions=netlify/functions, /api/* 重定向到函数
├── package.json
├── netlify/functions/
│   ├── lib/supabase.js             # Supabase 访问封装
│   ├── verify-card.js              # 卡密验证（exe调用）：限流(每IP每分钟20次)+CORS
│   ├── update-card.js              # 更新卡密（绑定/状态）
│   ├── generate-cards.js           # 生成卡密
│   ├── list-cards.js               # 卡密列表
│   └── stats.js                    # 统计
├── .netlify/functions/             # 已构建的函数产物（*.zip + manifest.json）
└── public/
    ├── index.html                  # 卡密管理后台（41KB）
    ├── download.html               # 软件下载页
    ├── app_icon.png
    └── B站工具箱_v6.0.0.zip         # 下载页提供的旧版安装包（约40GB列表里的41,564KB≈40.6MB）
```

- 卡密服务地址（config.py 内 `CARD_API_BASE`）：`https://precious-tanuki-c4b16d.netlify.app/api`
- 验证接口：`POST {CARD_API_BASE}/verify-card`
- 数据库：**Supabase**，项目 ID `ongvfaxymdrhiblxxsbb`（连接凭据在 Netlify 环境变量 / supabase.js 中，不在本仓库明文）。
- 安全加固历史（commit `f600c3b`）：删除了 admin123 兜底密码、改用 `crypto.randomInt` 生成、verify 加限流、CORS 收窄、500 错误不泄露细节、`lib/supabase.js` 入库。
- 管理后台：`https://precious-tanuki-c4b16d.netlify.app/`（卡密的绑定设备数、封禁、备注、延长有效期都在这里维护）。

### 5.3 下载中心（与卡密后台不同的另一个站点）

- 下载中心是一个**豆包 app_builder 托管的全栈网页应用**，app id `app_17dveqh3b1h`，访问地址形如 `https://4kvm1sjadmf8p.aiforce.cloud/app/app_17dveqh3b1h`。
- 下载软件**不需要卡密**，所有人可下载；历史版本只保留 v5.9.1（页面规则）。
- 当前站点显示版本可能仍是 **v6.0.3**（v6.0.4 尚未更新上去）。
- **重要边界**：该应用的源码/数据库与豆包账号绑定，**不能跨豆包账号迁移读写**。若换账号，需在新账号用 app_builder 重建，数据未必能导出。

---

## 六、数据存储与备份

### 6.1 运行时数据目录 data/

程序所有数据都在 exe 同目录的 `data/` 子目录（开发时即项目根的 `data/`），`config.py` 启动时自动创建。

**当前实际存在（2026-10-25 实测）：**

```
data/
├── accounts.json        # B站账号（当前7个），字段：name/SESSDATA/bili_jct/DedeUserID/username
├── config.json          # 弹幕默认配置（cookie占位、房间号、间隔、模式）
├── danmaku_list.txt     # 弹幕内容词库（每行一条）
├── logs/                # 抢码日志（当前3个 抢码日志_时间戳.txt）
└── backup/              # 程序内置旧exe备份（v5.3.0.exe、v2.0.0.exe，约16~20MB）
```

**运行后按需生成（当前不存在，属正常）：**

```
data/
├── card_auth.json       # 卡密授权缓存（验证通过后生成）
├── 兑换码记录.json       # 领取到兑换码后生成（CODE_EXPORT_FILE）
├── act_id_cache.json    # act_id 缓存
├── watch_config.json    # 看播页配置
├── rush_config.json     # 抢码页配置
├── scheduled_tasks.json # 旧定时任务
└── shutdown_config.json # 定时关机配置
```

这些文件名由 `config.py` 中的常量（`ACCOUNTS_FILE`、`CONFIG_FILE`、`DANMAKU_FILE`、`CARD_FILE`、`CODE_EXPORT_FILE`、`ACT_ID_CACHE_FILE`、`LOG_DIR`、`BACKUP_DIR` 等）定义，具体以 config.py 为准。

- `data/` 已被 `.gitignore` 忽略，**账号 Cookie 不会进 Git**（这是硬性安全要求）。
- 账号上限：**8 个**（agent.md 规则）。
- Cookie 三要素：`SESSDATA`、`bili_jct`（csrf）、`DedeUserID`（可选）。SESSDATA 等于账号密码，切勿外泄。
- 当前 7 个账号中有 1 个（"灵砂是无敌的"）Cookie 曾报告过期，需用户重新提供。

### 6.2 备份目录（项目根，均未纳入 git）

- `data_backup_20261020_172417/`：2026-10-20 的 data 整目录备份。
- `backup_*/`、`backup_v5.9.31_*/`：多个历史整目录备份。
- `versions/`：源码版本备份（当前 `main_gui_pro_v6.0.3.py`）。
- `data/backup/`：两个超大旧 exe（v5.3.0 约 20MB、v2.0.0 约 16MB）。

### 6.3 ⚠ 数据安全血泪教训

- 历史上曾有一次用 `Remove-Item -Recurse -Force dist` 误删了用户数据，**回收站无法找回**。
- 打包时的**铁律**：
  - 只删 `build/` 和目标 exe；
  - 打包后**必须手动 `Copy-Item -Recurse -Force data dist\`**（spec 不打包 data，data 是运行时外挂目录）；
  - **禁止**整目录 `Remove-Item -Recurse -Force dist`。

---

## 七、打包发布流程（重点）

### 7.1 环境

- Python：`C:\Users\15868\AppData\Local\Programs\Python\Python314\python.exe`（3.14.7）
- 依赖：`pip install requests websocket-client pyinstaller`（requirements.txt 只列前两个，PyInstaller 已装 6.22.2）

### 7.2 标准打包步骤（以当前版本为例，PowerShell）

在项目根目录执行：

```powershell
cd "C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot"

# 1) 清理中间产物（只删 build 和目标 exe，绝不整删 dist）
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Force "dist\B站工具箱_v6.0.4.exe" -ErrorAction SilentlyContinue

# 2) 用 spec 打包（--clean 清缓存，--noconfirm 覆盖输出）
C:\Users\15868\AppData\Local\Programs\Python\Python314\python.exe -m PyInstaller "B站工具箱_v6.0.4.spec" --clean --noconfirm

# 3) 关键：复制 data 数据目录到 dist
Copy-Item -Recurse -Force data dist\

# 4) 启动冒烟测试（启动后等几秒，不自动退出即成功，再关掉）
$p = Start-Process "dist\B站工具箱_v6.0.4.exe" -PassThru -WorkingDirectory "dist"
Start-Sleep -Seconds 6
if (-not $p.HasExited) { "启动成功"; Stop-Process -Id $p.Id -Force } else { "启动失败，退出码 $($p.ExitCode)" }
```

打包输出：`dist\B站工具箱_v6.0.4.exe`（约 19.3 MB，单文件，无控制台）。

### 7.3 spec 文件要点（B站工具箱_v6.0.4.spec）

- `Analysis(['main.py'])`：入口是 main.py。
- `datas=[('pyarmor_runtime_000000', 'pyarmor_runtime_000000')]`：**必须带上 PyArmor 运行时**。
- `hiddenimports`：**必须列全拆分后的 19 个模块**，否则打包后报 ModuleNotFoundError：
  ```
  websocket, requests, pyarmor_runtime_000000, card_verify,
  config, tasks_config, storage, bili_api, widgets, dialogs, card_auth,
  managers, managers.account, managers.room,
  ui, ui.rush_reward, ui.rush_reward.new_mode, ui.rush_reward.scheduled,
  ui.watch_live, ui.schedule, ui.code_export, ui.card_auth_page
  ```
- `excludes`：排除 numpy/scipy/pandas/matplotlib/PIL 等大库以减小体积。
- `console=False`：无黑框；`name="B站工具箱_v6.0.4"`；`icon=['app_icon.ico']`；`upx=True`。

### 7.4 升级版本号的完整改动清单

1. `config.py`：`APP_VERSION = "vX.Y.Z"`（界面底部版本号取自这里）。
2. 复制旧 spec 为 `B站工具箱_vX.Y.Z.spec`，改里面的 `name=`。
3. 若有游戏版本更新：改 `tasks_config.py`（`ALL_TASKS` + `VERSION_DEFAULT_ACT_ID`），UI 已动态加载无需改。
4. 按 7.2 打包、复制 data、冒烟测试。
5. **更新桌面快捷方式**（用户固定偏好）：
   - 名称：`B站工具箱_vX.Y.Z.lnk`；
   - 目标指向新 exe；工作目录设为 dist；图标取 exe 自身；
   - 桌面实际路径为 `E:\虚拟c盘\`（用 `[Environment]::GetFolderPath("Desktop")` 获取，不要写死）。
   - 同时删除旧版本桌面快捷方式，只留最新。
6. 打包完成后自动打开新 exe 让用户立即测试（用户偏好）。

PowerShell 创建快捷方式示例：

```powershell
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "B站工具箱_v6.0.4.lnk"
$target = "C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\B站工具箱_v6.0.4.exe"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $target
$s.WorkingDirectory = Split-Path $target
$s.IconLocation = $target
$s.Save()
```

### 7.5 发布到下载中心（仅在用户明确要求时）

- 用户偏好：**无明确"上传网站"指令时，不生成 zip**，只出 exe + 更新桌面快捷方式。
- 需要上传时：把 exe 打包为 zip 发布到下载中心（app `app_17dveqh3b1h`），并按 agent.md 规则把"网站当前显示的最新版"移入历史版本，新版放首页（注意是按网站现状挪，不是按代码上一版挪）。
- 该应用为豆包托管，需通过 app_builder 编辑，不能用本地文件直接改。

---

## 八、Git 与 GitHub 仓库

### 8.1 仓库信息

- 远程仓库：`https://github.com/hyacine35156-png/bilibili-toolbox`
- GitHub 用户名：`hyacine35156-png`
- 分支：`master`（唯一主分支，远程 `origin/master`）
- License：MIT

### 8.2 最近提交（截至 2026-10-25）

```
ed0545e 修复版本下拉框硬编码：改为从ALL_TASKS动态加载，旧模式/精准抢码均支持绝区零3.3
4c94f21 任务更新：删除绝区零3.2，新增绝区零3.3（27个任务）
c9f6fbc v6.0.4: 修复属性名拼写错误导致运行中保护失效
466370d v6.0.4: 修复config.py注释乱码和重复代码，删除抢码页死分支
cb62ea7 v6.0.4: 修复config编码、导入直播间bug、添加刷新按钮
1b6d7c3 A1单文件拆分: 12763行拆分为19个模块，逻辑零改动，AST 329/329方法逐字节等价
17abceb 添加MIT LICENSE
f600c3b 可优化点修复-卡密安全
b68cb6a 可优化点修复-功能Bug
224de74 添加项目完整档案
...
```

### 8.3 提交与推送

- 已跟踪文件（`git ls-files`）：核心源码、`card-system/` 后端、文档与图标，共 **49 个**文件。
- 工作区有**大量未跟踪文件**（历史脚本/截图/备份，见 2.3），提交时**只 `git add` 本次改动的具体文件，不要 `git add .`**，避免把临时脚本和 data 误提交。
- 推送（网络正常时）：

```powershell
git add <具体文件>
git commit -m "简明中文说明"
git push origin master
```

### 8.4 ⚠ Token 安全（重要，当前存在隐患）

- 历史上为了免密推送，曾把 GitHub Personal Access Token 拼进 remote URL，形如 `https://<用户名>:<ghp_xxx>@github.com/...`。**Token 会明文保存在 `.git/config` 里**，任何能读该文件的人都能拿到，不应长期保留。
- **当前 `.git/config` 的 origin URL 里仍带 token（2026-10-25 实测确认存在）。** 请尽快处理：
  1. 到 GitHub → Settings → Developer settings → Personal access tokens **撤销（Revoke）旧 token**；
  2. 重新生成一个最小权限（只勾 `repo`）、有过期时间的新 token；
  3. 把 remote 改回不含 token 的干净地址：
     ```powershell
     git remote set-url origin https://github.com/hyacine35156-png/bilibili-toolbox.git
     ```
  4. 推送时若要临时用 token，推送完立即改回干净 URL；更推荐用 Git Credential Manager 缓存。
- 撤销 token 不影响已推送的代码和仓库。
- 历史障碍：删除 token 时 GitHub 要求邮箱验证，而 Gmail 当时收不到验证邮件，导致旧 token 尚未撤销——恢复邮箱访问后第一件事处理它。
- 网络注意：本机对 `github.com:443` 曾间歇性连接失败（`Test-NetConnection` 返回 False），推送会卡在 "Send header"，需等网络恢复重试；PowerShell 里 `curl` 是 `Invoke-WebRequest` 别名，要用真 curl 需写 `curl.exe`。

### 8.5 未推送的提交

2026-10-25 实测：本地 `master` 指向 `ed0545e`，本地缓存的 `origin/master` 指向 `c9f6fbc`，即**本地领先远程 2 个提交尚未推送**：

```
4c94f21 任务更新：删除绝区零3.2，新增绝区零3.3（27个任务）
ed0545e 修复版本下拉框硬编码：改为从ALL_TASKS动态加载
```

（注：`c9f6fbc` 属性名修复已在远程。）网络恢复后执行 `git push origin master` 即可；推送后用 `git status` 确认 "up to date"，并把 remote URL 改回无 token 形式。若长期无法 fetch，`origin/master` 只是本地缓存，GitHub 上的真实状态以实际推送结果为准。

---

## 九、外部服务与依赖

| 服务 | 地址 / 标识 | 用途 | 凭据位置 |
|---|---|---|---|
| B站开放接口 | api.bilibili.com / api.live.bilibili.com | 登录、弹幕、任务、看播 | 用用户 Cookie，无需 Key |
| 卡密/管理后台 | https://precious-tanuki-c4b16d.netlify.app/ | 卡密验证、卡密管理 | Netlify 环境变量 + Supabase |
| Supabase | 项目 ID `ongvfaxymdrhiblxxsbb` | 卡密数据库 | `card-system/netlify/functions/lib/supabase.js` / Netlify 环境变量 |
| 下载中心（豆包托管） | app id `app_17dveqh3b1h` | 软件分发与更新说明 | 与豆包账号绑定，不可跨账号迁移 |
| 另有豆包全栈应用 | app id `app_17e9ym01nvf` | 与本项目相关、用途待确认的另一个托管应用 | 同上，绑定豆包账号 |

Python 依赖（requirements.txt）：

```
requests>=2.31.0
websocket-client>=1.8.0
```

打包期工具：PyInstaller 6.22.2、PyArmor 9.2.7 (trial)。

---

## 十、日常维护操作手册

### 10.1 更新游戏版本任务（最高频，以绝区零为例）

1. 拿到新活动的 `task_id` 汇总（官方活动页或既有提取脚本）。
2. 编辑 `tasks_config.py`：
   - 删除旧版本的所有条目；
   - 新增新版本条目，字段严格用 `version/period/type/name/task_id/award`；
   - `period` 统一按实际（绝区零3.3 为 "全版本"）；
   - 更新 `VERSION_DEFAULT_ACT_ID` 里的版本名→act_id。
3. 检查 `ui/rush_reward/__init__.py` 的 `build_task_info_from_task()`：给新游戏/新版本确认正确的 `act_name` 分支（否则会落到 else 显示错误的"鸣潮3.7…"名称）。
4. 验证：
   ```powershell
   python -m py_compile tasks_config.py
   python -c "from tasks_config import ALL_TASKS; ..."  # 数任务数、查重ID
   ```
5. 旧模式与精准抢码的版本下拉框已动态化，无需改 UI。
6. 打包 → 复制 data → 冒烟测试 → 更新桌面快捷方式。
7. commit（只 add 改动文件）。

### 10.2 更新 B 站账号

1. 让用户提供每个账号的 `SESSDATA` 与 `bili_jct`（`DedeUserID` 可选）。
2. 编辑 `data/accounts.json`（或在 exe 的账户管理页添加，更安全）。
3. 用 `verify_login` 或 exe 内"添加账户"逐个验证有效性。
4. 账号上限 8 个；Cookie 不会进 git。
5. 改完把 `data/` 复制到 `dist/` 再测试打包版。

### 10.3 修改 UI / 逻辑

- 抢码旧模式：`ui/rush_reward/__init__.py`
- 精准抢码：`ui/rush_reward/new_mode.py`
- 旧定时领取：`ui/rush_reward/scheduled.py`
- 看播/送礼：`ui/watch_live.py`
- 日程：`ui/schedule.py`
- 兑换码：`ui/code_export.py`
- 弹幕/关机/账户页/说明页：`main.py`
- 全局常量/配色/API：`config.py`
- 自定义控件：`widgets.py`

注意 Mixin 方法归属：`new_mode.py`、`scheduled.py` 里的方法依赖宿主 `RushRewardFrame` 提供的属性，改动时不要把宿主属性误提为模块级。

### 10.4 验证手段（改动后）

- 语法：`python -m py_compile <文件>`。
- 模块独立导入：`python -c "import ui.rush_reward.new_mode"`（17 个模块逐一试）。
- 文本级/AST 比对：大规模重构后对比拆分前后方法集合、模块级常量（参考《单文件拆分计划.md》3.11 自检方法）。
- 真实启动 exe 冒烟，手动切换各 Tab、版本下拉框，确认无报错。
- 不要只信 exit code 0；要实际看界面层。

---

## 十一、已知问题、历史教训与注意事项

### 11.1 已修复但需警惕复发的问题

- **重复定义 / 死代码**：单文件时代曾出现 `toggle_select_all`、`delete_selected_tasks` 重复两份、`ToolTip` 未定义、5 份 log 实现不一致。拆分后大幅缓解，但改同名方法时仍要全局搜确认只有一份。
- **属性名拼写**：`watch_frame`/`gift_frame`/`rush_frame` 曾拼错（正确 `watch_page`/`rush_page`），导致运行中保护失效。
- **UI 残留引用**：调度器从 Frame 改 Treeview 后，残留 `nm_scheduler_frame` 引用，正确是调用 `nm_update_scheduler()`。
- **硬编码下拉框**：版本列表曾硬编码，3.2→3.3 时新版本不出现，已改动态加载；新增期数/类型时确认不要再写死。
- **config.py 乱码与重复赋值**：曾有 18 行注释乱码、12 处常量重复赋值，v6.0.4 已重写清理。
- **死分支**：main.py 曾有 `hasattr` 双重保护但实际不生效的刷新死分支，已删。

### 11.2 环境/操作坑

- 打包必须带 `pyarmor_runtime_000000` 和完整 `hiddenimports`，否则卡密或某个模块在打包后失效（源码运行正常、打包后报错，几乎都是漏 hiddenimport）。
- 打包后必须复制 `data/` 到 `dist/`，否则打包版读不到账号。
- spec 的 `console=False`，若要排查打包后闪退，可临时把 `console=True` 重新打包看报错。
- 证书：main.py 在 import requests 前用 certifi 设置 `REQUESTS_CA_BUNDLE`/`CURL_CA_BUNDLE`，解决打包后 HTTPS 证书问题，勿删。
- PowerShell 5.1 与 7 的编码差异：读写含中文的源码用 UTF-8；本机是 pwsh 7，`-Encoding utf8` 无 BOM。
- 不要用 `build.py` / `一键打包.bat`（旧脚本，引用已不存在的 `main_gui_pro.py` 和"B站弹幕工具.exe"）。
- 根目录历史脚本可删但建议先整目录备份；删除任何用户文件前必须确认路径、且默认不删。

### 11.3 合规与风控

- 自动弹幕/看播/送礼/抢码违反 B 站使用规则，存在封号、禁言、风控风险；发送间隔建议 ≥5 秒（抢码 600–800ms 是特殊场景），送礼消耗真实电池。
- 工具仅供学习研究，使用者自担风险（README 有免责声明）。
- 卡密系统涉及商业化，Supabase 服务密钥、Netlify 环境变量切勿写进前端或公开仓库。

### 11.4 文档现状（避免被过期文档误导）

- `README.md`：只描述早期"弹幕工具"，**不含**抢码/看播/卡密等新功能，仅作历史参考。
- `agent.md`：开发规则仍有价值，但里面的"主程序 main_gui_pro.py""当前版本 v5.9.8"等已过时（现为 main.py 拆分结构、v6.0.4）。
- `项目完整档案.md`：覆盖 v4.6.5~v6.0.3 历史，可查沿革。
- 以**本交接文档 + 实际代码**为准。

---

## 十二、遗留事项清单

1. **GitHub Token 安全**：撤销 remote URL 中泄露的旧 token、换发新 token、把 origin 改回干净 URL（依赖能收到 GitHub 验证邮件）。
2. **未推送提交**：本地领先远程 2 个提交（4c94f21 绝区零3.3、ed0545e 下拉框动态化），网络恢复后 `git push origin master`，确认本地与远程一致。
3. **下载中心版本**：站点仍显示 v6.0.3，需要时更新到 v6.0.4（用户明确要求时才做，走 app_builder）。
4. **过期账号**："灵砂是无敌的" Cookie 过期，等用户提供新 SESSDATA/bili_jct。
5. **PyArmor 试用版限制**：trial 版单文件加密上限约 40KB，所以只加密了 `card_verify.py`，主体明文；若需全量加密要购买正版。
6. **根目录清理**：数百个历史脚本/截图/备份未纳入 git 且占用空间，可在整目录备份后做一次归档清理。
7. **build.py / 一键打包.bat / README / agent.md 已部分过时**：可按本文件更新或标注"已废弃"，避免新人误用。
8. **另一个豆包应用 `app_17e9ym01nvf`** 的具体用途与是否需要迁移/维护，待与用户确认。
9. 交接后如要继续在豆包内维护下载中心等托管应用，注意它们与豆包账号绑定，换账号无法直接读写，需提前规划迁移。

---

## 附：关键命令速查

```powershell
# 进入项目
cd "C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot"

# 语法检查
C:\Users\15868\AppData\Local\Programs\Python\Python314\python.exe -m py_compile main.py

# 打包（版本号随实际改）
C:\Users\15868\AppData\Local\Programs\Python\Python314\python.exe -m PyInstaller "B站工具箱_v6.0.4.spec" --clean --noconfirm

# 复制数据
Copy-Item -Recurse -Force data dist\

# Git（只提交具体文件）
git status
git add <文件>
git commit -m "说明"
git push origin master
git remote set-url origin https://github.com/hyacine35156-png/bilibili-toolbox.git
```

---

*文档完。本文件所有路径、模块行数、任务数、提交号、命令均已在 2026-10-25 现场核对；如后续代码变更，请同步更新本文件。*
