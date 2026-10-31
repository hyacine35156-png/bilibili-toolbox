# B站工具箱 优化执行报告

> 执行日期：2026-10-25
> 基线：v6.1.0（83c193b）
> 当前：v6.1.0（09216ed）
> 备份：分支 v6.1.0-stable、tag v6.1.0-pre-optimize

---

## 一、执行结果总览

| 编号 | 主题 | 状态 | 说明 |
|------|------|------|------|
| O1 | 卡密/Token 安全收口 | **跳过** | 按用户要求暂不处理 |
| O2 | data 自动备份与自愈 | 完成 | data_guard.py，已接入启动流程 |
| O3 | 兑换码改 SQLite | **跳过** | 按用户要求暂不处理 |
| O4 | 抢码结果结构化落库 | 完成 | rush_stats.py + UI 统计面板 |
| O5 | 统一日志系统 | 完成 | logging_util.py 基础设施 |
| O6 | 网络层统一封装 | 完成 | http_client.py 基础设施 |
| O7 | 界面配置化(DPI) | 完成 | ui/theme.py + 手动任务对话框已迁移 |
| O8 | 单元测试补齐 | 完成 | tests/test_core.py 22 个用例 |
| O9 | 任务表外置 JSON | 完成 | data/tasks_official.json + 回退机制 |
| O10 | 自动更新机制 | 完成(保守) | updater.py，仅提示不自动替换 |

---

## 二、额外修复：对话框抖动

用户反馈手动添加界面会抖动。定位到两个叠加根因：

1. **滚动条布局死循环**：滚动条用 `pack()` 显示/隐藏会改变 canvas 宽度，
   触发 `<Configure>` 事件，再次调整滚动条 → 自我触发的布局循环。
   修复：改用 `place()` 绝对定位，完全不参与布局计算。

2. **按钮文字撑开布局**：保存按钮文字在「保存到任务库」和
   「保存到任务库（N）」之间切换，宽度变化导致整行重排。
   修复：所有动文字按钮固定 `width`。

验证：9 次连续采样，窗口尺寸 780x898、按钮宽度/位置全部恒定。

---

## 三、各模块说明

### O2 data_guard.py（数据自动备份与自愈）

解决历史事故：曾误删 dist 丢数据；dist/data 不全导致卡密失效。

| 能力 | 说明 |
|------|------|
| `check_integrity()` | 启动校验 6 个关键文件，缺失/损坏自动从最近备份恢复 |
| `daily_backup()` | 每天首次启动打包 data/，滚动保留 7 份 |
| `list_backups()` | 备份浏览 |
| `verify_dist_data()` | 打包后比对源码 data 与 dist/data 完整性 |
| `startup_maintenance()` | 启动统一入口，已接入 main.py |

关键文件清单：accounts.json / card_auth.json / rush_groups.json /
rush_config.json / rooms_config.json / watch_config.json

### O4 rush_stats.py（抢码结果结构化）

解决：抢码结果只写文本日志，无法统计成功率。

- 存储：`data/rush_results.jsonl`（追加写，多线程安全，不会并发丢数据）
- 字段：ts/task_id/task_name/account/act_id/result/code/message/latency_ms
- 埋点位置：`do_receive_fast` 和 `do_receive_once` 两个统一入口
- UI：抢码页新增「📊 抢码统计（今日）」面板
- 统计内容：成功率、失败码 Top3、平均延迟、最活跃任务、高峰时段

### O5 logging_util.py（统一日志）

项目历史上存在 4 份独立 log 实现。本模块提供：

- `get_logger(name)`：命名 logger，写文件 + 控制台
- `attach_ui(logger, widget)`：绑定 Tk 控件，跨线程用 `root.after` 安全投递
- 文件按天切分、10MB 滚动、7 天清理
- `read_recent(name, n)`：排障时读最近日志

### O6 http_client.py（统一 HTTP）

| 能力 | 说明 |
|------|------|
| 连接池 | pool_connections=32, pool_maxsize=64 |
| 超时 | 默认 (5,10)s；抢码用 FAST_TIMEOUT (3,5)s |
| 重试 | 指数退避+抖动，3 次；可重试 429/5xx 与网络异常 |
| 代理 | `set_proxy()` / `load_proxy_from_config()` |
| 统计 | `recent_stats()` / `stats_summary()` 记录耗时 |

### O7 ui/theme.py（DPI 自适应）

解决反复出现的「显示不完全」——根因是硬编码像素。

- `get_scale()`：DPI 系数（96dpi=1.0，夹在 1.0~2.5）
- `sz(n)` / `font(size, bold)`：按 DPI 换算尺寸与字号
- `create_dialog()`：统一弹窗工厂，自动测内容/居中/封顶、滚动条 place 定位
- 手动任务对话框已完整迁移（字号、滚动条、边距、最小尺寸全部走 sz()）

### O8 tests/test_core.py（单元测试）

22 个用例，覆盖纯函数层：

- task_id 解析（完整网址/纯id/批量/去重/&param/JSON片段/垃圾输入）
- 字段提取（完整/嵌套/act_id兜底）
- WBI 签名（mixin key 长度/w_rid 字段/确定性）
- 库存解析（总量+每日限量/空/仅总量）
- 常量一致性（任务字段/无重复ID/版本act_id/版本号格式）

运行：`python -m unittest discover tests -v`

### O9 任务表外置

- `data/tasks_official.json`：103 条任务 + 4 个版本 act_id
- `load_official_tasks()`：优先读 JSON，失败回退内置 `ALL_TASKS`
- `TASKS_SOURCE`：记录来源（json/builtin），便于排障
- 以后更新游戏活动只需替换 JSON，**无需改代码重打包**

> 注：JSON 本身被 `.gitignore` 的 `*.json` 规则忽略，属运行时数据。
> 内置任务表仍保留在 tasks_config.py 作为回退，不会丢失。

### O10 updater.py（更新检查，保守实现）

**设计取舍**：原方案是自动下载替换 exe 重启，风险中高——自更新失败会导致
程序再也打不开。改为只做安全提示：

- 后台请求 `latest.json` 比对版本号
- 有新版本弹窗提示 + 下载链接
- **不做任何自动替换**
- 未配置 `UPDATE_INDEX_URL` 时直接跳过

---

## 四、验证结果

| 项目 | 结果 |
|------|------|
| 全模块编译 | 通过 |
| 单元测试 | 22/22 通过 |
| 新模块导入 | 6/6 通过 |
| 打包 | 19.36MB，成功 |
| PYZ 模块数 | 575，含全部 6 个新模块 |
| exe 启动 | 正常，标题「v6.1.0 ... 剩余359天」 |
| 自动备份 | 已生成 data_20261025_121644.zip (10.9KB) |
| JSON 回退 | 删除 JSON 后正确回退 103 条内置任务 |
| 对话框抖动 | 9 次采样尺寸恒定 |

---

## 五、Git 记录

```
09216ed feat: O10 更新检查（保守实现）
4c33af6 feat: O7界面DPI自适应 + O8单元测试 + O9任务表外置
737f0b4 feat: 新增数据自愈/统一日志/HTTP客户端/抢码统计四个基础模块 (O2/O4/O5/O6)
ad65385 fix: 修复手动添加对话框抖动
83c193b v6.1.0: 手动任务改为解析预览->点击保存两步式；官方任务删除持久化
```

备份分支：`v6.1.0-stable`　备份 tag：`v6.1.0-pre-optimize`

**未推送 GitHub**（按用户要求）。

---

## 六、尚未接入的部分（后续可选）

以下基础设施已建好但尚未全面替换现有代码，属于渐进式改造：

1. **O5 logging_util**：目前只有 API 就绪，各 Frame 的 `log()` 仍是原实现。
   下一步可逐模块替换，统一日志格式与滚动策略。
2. **O6 http_client**：`bili_api.py` 仍用原生 `requests`。
   下一步可替换以启用统一重试/代理/耗时统计。
3. **O7 theme**：仅手动任务对话框已迁移，其余页面仍用硬编码字号。
   下一步可逐页迁移。

> 这些替换都涉及较大改动面，按渐进原则分批做更安全。