#!/usr/bin/env python3
"""v5.0.7: 账户管理独立到日程任务页面右侧"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 修改ScheduleFrame的build_ui底部布局：左侧任务列表+日志，右侧账户管理
# ============================================================
old_bottom = '''        # 底部：任务列表 + 日志
        bottom = tk.Frame(self, bg=COLORS["bg_dark"])
        bottom.pack(fill=tk.BOTH, expand=True)

        # 左侧：任务列表
        list_card = tk.Frame(bottom, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        list_header = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(list_header, text="📋 日程任务列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(list_header, text="（勾选「选」可批量删除；点「启动/取消」控制是否执行；双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))

        self.task_list_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        self.task_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 右侧：日志
        log_card = tk.Frame(bottom, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(log_card, text="📝 执行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 6))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        self.schedule_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                          insertbackground=COLORS["accent"], font=("Consolas", 9),
                                          bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.schedule_log_text.pack(fill=tk.BOTH, expand=True)

        self.selected_task_id = None'''

new_bottom = '''        # 底部：左侧内容（任务列表+日志） + 右侧账户管理
        bottom = tk.Frame(self, bg=COLORS["bg_dark"])
        bottom.pack(fill=tk.BOTH, expand=True)

        # 左侧：任务列表 + 日志（上下布局）
        left_content = tk.Frame(bottom, bg=COLORS["bg_dark"])
        left_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # 任务列表
        list_card = tk.Frame(left_content, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        list_header = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(list_header, text="📋 日程任务列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(list_header, text="（勾选「选」可批量删除；点「启动/取消」控制是否执行；双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))

        self.task_list_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        self.task_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 日志
        log_card = tk.Frame(left_content, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        tk.Label(log_card, text="📝 执行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 6))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        self.schedule_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                          insertbackground=COLORS["accent"], font=("Consolas", 9),
                                          bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.schedule_log_text.pack(fill=tk.BOTH, expand=True)

        # 右侧：账户管理（独立面板）
        account_card = tk.Frame(bottom, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        account_card.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0))
        account_card.pack_propagate(False)
        account_card.configure(width=280)

        tk.Label(account_card, text="账户管理", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        acc_list_frame = tk.Frame(account_card, bg=COLORS["bg_card"])
        acc_list_frame.pack(fill=tk.BOTH, expand=True, padx=12)

        self.account_listbox = tk.Listbox(acc_list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                           selectbackground=COLORS["accent"], selectforeground="#000000",
                                           font=("微软雅黑", 9), bd=0, highlightthickness=0,
                                           activestyle="none", exportselection=False)
        self.account_listbox.pack(fill=tk.BOTH, expand=True)
        self.account_listbox.bind("<<ListboxSelect>>", self.app.on_account_select)

        # 按钮区
        DarkButton(account_card, "+ 添加账户", command=self.app.add_account,
                   width=250, height=36).pack(pady=(10, 6), padx=12)
        DarkButton(account_card, "删除", command=self.app.delete_account,
                   width=250, height=36, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6), padx=12)
        DarkButton(account_card, "验证登录", command=self.app.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 12), padx=12)

        self.selected_task_id = None'''

if old_bottom in content:
    content = content.replace(old_bottom, new_bottom)
    print("1. ScheduleFrame底部布局已修改（左侧任务列表+日志，右侧账户管理）")
else:
    print("1. 未找到ScheduleFrame底部布局代码")

# ============================================================
# 2. 在ScheduleFrame的__init__中同步账户列表引用到主应用
# ============================================================
old_init = '''        self.build_ui()
        self.load_schedule()
        self._load_form_settings()
        self.start_scheduler()'''

new_init = '''        self.build_ui()
        # 同步账户管理控件引用到主应用（账户管理UI已移到此页面）
        self.app.account_listbox = self.account_listbox
        self.load_schedule()
        self._load_form_settings()
        self.start_scheduler()
        # 初始化账户列表
        self.app.refresh_account_list()'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("2. ScheduleFrame __init__已添加账户列表引用同步")
else:
    print("2. 未找到ScheduleFrame __init__代码")

# ============================================================
# 3. 修改弹幕工具页面：删除左侧账户管理，右侧扩展到全宽
# ============================================================
old_danmaku_left = '''        # 左侧：账户管理
        left_card = tk.Frame(self.danmaku_page, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=280)

        tk.Label(left_card, text="账户管理", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)

        self.account_listbox = tk.Listbox(list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                           selectbackground=COLORS["accent"], selectforeground="#000000",
                                           font=("微软雅黑", 9), bd=0, highlightthickness=0,
                                           activestyle="none", exportselection=False)
        self.account_listbox.pack(fill=tk.BOTH, expand=True)
        self.account_listbox.bind("<<ListboxSelect>>", self.on_account_select)

        # 第一排：添加账户
        DarkButton(left_card, "+ 添加账户", command=self.add_account,
                   width=250, height=36).pack(pady=(10, 6), padx=12)

        # 第二排：删除
        DarkButton(left_card, "删除", command=self.delete_account,
                   width=250, height=36, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6), padx=12)

        # 第三排：验证登录
        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 12), padx=12)

        # 右侧：设置 + 弹幕 + 日志
        right = tk.Frame(self.danmaku_page, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))'''

new_danmaku_left = '''        # 右侧：设置 + 弹幕 + 日志（账户管理已移到日程任务页面）
        right = tk.Frame(self.danmaku_page, bg=COLORS["bg_dark"])
        right.pack(fill=tk.BOTH, expand=True)'''

if old_danmaku_left in content:
    content = content.replace(old_danmaku_left, new_danmaku_left)
    print("3. 弹幕工具页面已删除左侧账户管理，右侧扩展到全宽")
else:
    print("3. 未找到弹幕工具页面左侧账户管理代码")

# ============================================================
# 4. 修改switch_tab：切换到日程任务页面时刷新账户列表
# ============================================================
old_switch_schedule = '''        elif tab_name == "schedule":
            self.schedule_page.pack(fill=tk.BOTH, expand=True)
            self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "schedule"'''

new_switch_schedule = '''        elif tab_name == "schedule":
            self.schedule_page.pack(fill=tk.BOTH, expand=True)
            self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "schedule"
            # 切换到日程任务页面时刷新账户列表
            self.refresh_account_list()'''

if old_switch_schedule in content:
    content = content.replace(old_switch_schedule, new_switch_schedule)
    print("4. switch_tab已添加日程页面账户列表刷新")
else:
    print("4. 未找到switch_tab日程页面代码")

# 版本号
content = content.replace('APP_VERSION = "v5.0.6"', 'APP_VERSION = "v5.0.7"')
print("5. 版本号: v5.0.6 -> v5.0.7")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
