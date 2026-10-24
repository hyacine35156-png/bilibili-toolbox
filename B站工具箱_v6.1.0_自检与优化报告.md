# B站工具箱 v6.1.0 自检与优化报告

> 日期：2026-10-25
> 基线：v6.0.4（ed0545e）
> 提交：348973a

---

## 一、本轮需求与完成情况

| # | 需求 | 状态 | 说明 |
|---|------|------|------|
| 1 | 手动添加对话框"显示不完全" | 已修复 | 改为可滚动容器（Canvas+Scrollbar）+ 按内容自适应尺寸，且不超过屏幕 92%x86%；鼠标滚轮可滚动 |
| 2 | 手动任务能加入任务组（如鸣潮3.7） | 已完成 | 对话框"归类版本/期数/类型"三个可编辑下拉框，可直接选 鸣潮3.7 等已有版本 |
| 3 | 也要能自动新建 | 已完成 | 版本下拉框可直接输入新版本名（如 鸣潮3.8）自动新建；任务组同理，填"新建组名"即自动建组 |
| 4 | "解析账户"疑似无用 | 保留并说明 | 见第二章；它只用于查询任务信息，不写账号数据 |
| 5 | exe 必须打包到项目 dist | 已完成 | dist\B站工具箱_v6.1.0.exe（19.30MB），已实测主窗口正常打开 |
| 6 | 报错原因排查 | 已定位 | 根因是 dist\data 数据不完整，不是 exe 位置问题 |
| 7 | 全面自检与优化 | 已完成 | 见第四章 |
| 8 | 提交 git | 已完成 | commit 348973a，5 文件 +780/-15 |

---

## 二、关于"解析账户"到底有没有用（重点）

**结论：有用，必须保留。** 它不是拿来登录或改账号的，而是用来**查询任务详情**。

### 为什么需要
B站的活动任务信息接口 mission/info **必须带登录态 Cookie** 才能返回数据。
手动输入 task_id 时，程序本地并不知道：
- 这个 task_id 对应的任务叫什么名字
- 奖励是什么（菲林*360 / 星声*60 / 播放量任务……）
- 它属于哪个活动（act_id、活动名）

这些都只能靠**某个已登录账户**去调接口查回来。所以"查询账户"的作用是：

| 用途 | 说明 |
|---|---|
| 查任务名 | 否则下拉框里只能显示一串 6ERAcwloghvosw00 |
| 查奖励 | 用于界面展示和抢码日志 |
| 查 act_id | **领取奖励时必须传**，猜错就领不到 |
| 查活动名 | 用于 build_task_info_from_task 正确构造领取参数 |

### 它不会做什么（安全边界）
- 不修改该账户的任何数据
- 不保存该账户的 Cookie 到手动任务里
- 不做登录/登出操作
- 只读：GET /x/activity_components/mission/info

### 如果确实不想选账户
提供两个兜底路径：
1. 勾选 **「查询失败也强制添加」** -> 不解析，任务名暂用 task_id，奖励留空；
2. 手填 **「act_id 兜底」** -> 保证领取时 act_id 不为空。

> 建议：临时抢一两个码，手填 act_id + 强制添加也能用；但要完整功能（显示奖励、批量查询、精准抢码），还是选账户解析更省心。

---

## 三、exe 报错根因（图3）

### 表象
把 exe 放到别处（或数据不全）运行时，程序启动异常 / 卡在卡密页 / 提示数据缺失。

### 真实根因
config.py 第 26-29 行：

    _EXE_DIR = Path(sys.executable).parent if frozen else Path(__file__).parent
    BASE_DIR = _EXE_DIR / "data"

**exe 永远读取"自己所在目录"下的 data\**。所以：

| 问题 | 后果 |
|---|---|
| exe 放到别处，没有配套 data | 读不到 accounts.json / card_auth.json / rush_groups.json，全部功能失效 |
| data 存在但不完整（缺 card_auth.json） | 卡密校验失败，停在验证页 |
| data 存在但不完整（缺 rush_groups.json） | 精准抢码任务组为空 |

### 本次实际遇到的情况
第一次把工作区副本的 data 复制进 dist，那份只有 4 个文件（accounts/config/danmaku/rush_config），
**缺 card_auth.json、rush_groups.json、watch_history.json 等**，这正是"没有把所有数据全部转移"。

### 修复
从项目原有完整 data 恢复（44 个文件，35.55MB），并备份为 dist/data_bak_v610。

### 以后打包的正确姿势（已写入规则）

    cd "C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot"
    Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
    C:\Users\15868\AppData\Local\Programs\Python\Python314\python.exe -m PyInstaller "B站工具箱_v6.1.0.spec" --clean --noconfirm
    Copy-Item -Recurse -Force data dist\     # 必须，且要确认是项目根的完整 data

> 注意：打包前若 exe 正开着会报 PermissionError: [WinError 5] 拒绝访问，
> 先把 B站工具箱_v6.1.0 进程全部结束再打包。

---

## 四、全面自检结果

### 4.1 静态审计（0 错误）
| 检查项 | 结果 |
|---|---|
| AST 重复方法定义 | 0 处 |
| Mixin 方法冲突 | 0 处（NewMode 39 / Scheduled 12 / Manual 9 个方法无重叠） |
| 重复全局函数 | 0 处 |
| 任务表字段完整性 | 103 条全部含 6 个必需字段 |
| 重复 task_id | 0 处 |
| act_id 覆盖 | 全部任务有 act_id 来源 |
| 版本号一致性 | APP_VERSION = spec = v6.1.0 |
| 裸 except | 5 处（storage.py x4、code_export.py x1，均为兜底容错，保留） |
| 未使用导入 | 78 条，多数为转发导出（main.py 导入供子模块使用），未删 |

### 4.2 功能测试（全部 0 失败）
| 测试 | 项数 | 结果 |
|---|---|---|
| 手动任务 v2（归类版本 / 自动新建 / 入组 / 对话框） | 25 | 全过 |
| 回归（模块导入 / 官方任务不变 / 联动） | 15 | 全过 |
| 布局（按钮渲染 / 不溢出 / 控件齐全） | 11 | 全过 |

### 4.3 打包验证
| 项 | 值 |
|---|---|
| exe | dist\B站工具箱_v6.1.0.exe |
| 大小 | 19.30 MB（v6.0.4 为 19.28MB，符合预期） |
| PYZ 模块数 | 567，含 ui.rush_reward.manual_task |
| 主窗口 | 正常打开，标题 B站工具箱 v6.1.0 - ... 剩余360天 |
| 卡密 | 校验通过（365天卡，剩余360天） |

---

## 五、本轮优化清单

| # | 优化 | 收益 |
|---|------|------|
| 1 | 对话框改 Canvas 可滚动 + 自适应尺寸 | 彻底解决高 DPI / 小屏"显示不完全" |
| 2 | 任务下拉框空奖励不再显示 任务名 () | 手动添加无奖励任务时界面干净 |
| 3 | 保存版本失效自动回退 | 游戏版本下线 / 手动任务删空后不再出现空任务列表 |
| 4 | build_task_info_from_task 手动任务优先用实查 act_id | 归类到官方版本后仍能正确领取 |
| 5 | 手动任务删除逻辑改为按集合差集 | 归入官方版本的手动任务也能被彻底删干净 |
| 6 | load_manual_tasks 保留 version/period/type | 归类信息重启不丢失 |
| 7 | 解析节流 0.6s/条 | 批量添加不触发 -702 风控 |
| 8 | 入组自动分配优先级 = 组内最大值+1 | 与官方"添加任务"行为一致 |

---

## 六、Git 提交

    commit 348973a
    v6.1.0: 抢码任务支持手动添加（task_id/活动网址），可归类版本与任务组

     config.py                     |  12 +-
     tasks_config.py               | 119 +++++++-
     ui/rush_reward/__init__.py    |  43 ++-
     ui/rush_reward/manual_task.py | 614 ++++++++++++++++++++++
     ui/rush_reward/new_mode.py    |   7 +-
     5 files changed, 780 insertions(+), 15 deletions(-)

> spec 文件被 .gitignore 的 *.spec 规则忽略（历史上所有 spec 均未入库），故未提交。

---

## 七、遗留事项（未在本轮处理）

1. **Git remote 含明文 token**：origin URL 里带 ghp_ token（交接文档已列为遗留项）。本轮未切换，因为推送需要它；建议后续撤销旧 token 并改用 Git Credential Manager。
2. **未推送**：本地 master 领先远程 3 个提交（4c94f21、ed0545e、348973a），需网络正常时 git push origin master。
3. **桌面快捷方式**：已更新为 B站工具箱_v6.1.0.lnk，旧 v6.0.4 两个快捷方式已删除。
4. **根目录历史脚本**：数百个一次性脚本仍存在，未清理（按交接文档建议，清理前需整目录备份）。
