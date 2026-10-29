#!/usr/bin/env python3
"""v5.0.7: 账户管理独立标签页 + 弹幕工具账户多选"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 标签栏新增"账户管理"标签（在日程任务后面）
# ============================================================
old_tab_schedule = '''        self.tab_schedule = tk.Label(tab_bar, text="📅 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_schedule.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_schedule.bind("<Button-1>", lambda e: self.switch_tab("schedule"))'''

new_tab_schedule = '''        self.tab_schedule = tk.Label(tab_bar, text="📅 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_schedule.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_schedule.bind("<Button-1>", lambda e: self.switch_tab("schedule"))

        self.tab_account = tk.Label(tab_bar, text="👤 账户管理", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_account.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_account.bind("<Button-1>", lambda e: self.switch_tab("account"))'''

if old_tab_schedule in content:
    content = content.replace(old_tab_schedule, new_tab_schedule)
    print("1. 标签栏已新增'账户管理'标签")
else:
    print("1. 未找到标签栏代码")

# ============================================================
# 2. 新增账户管理页面（在日程任务页面后面）
# ============================================================
old_schedule_page = '''        # 日程任务页面
        self.schedule_page = ScheduleFrame(self.tab_container, self.account_mgr, self)
        self.schedule_page.pack(fill=tk.BOTH, expand=True)
        self.schedule_page.pack_forget()

        self.current_tab = "rush"'''

new_schedule_page = '''        # 日程任务页面
        self.schedule_page = ScheduleFrame(self.tab_container, self.account_mgr, self)
        self.schedule_page.pack(fill=tk.BOTH, expand=True)
        self.schedule_page.pack_forget()

        # 账户管理页面
        self.account_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.account_page.pack(fill=tk.BOTH, expand=True)
        self.account_page.pack_forget()
        self.build_account_page()

        self.current_tab = "rush"'''

if old_schedule_page in content:
    content = content.replace(old_schedule_page, new_schedule_page)
    print("2. 已新增账户管理页面容器")
else:
    print("2. 未找到日程任务页面代码")

# ============================================================
# 3. 修改switch_tab方法：隐藏/显示账户管理页面 + 重置标签样式
# ============================================================
old_switch_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()
        self.schedule_page.pack_forget()

        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_schedule.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

new_switch_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()
        self.schedule_page.pack_forget()
        self.account_page.pack_forget()

        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_schedule.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_account.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

if old_switch_hide in content:
    content = content.replace(old_switch_hide, new_switch_hide)
    print("3. switch_tab已添加账户管理页面隐藏/样式重置")
else:
    print("3. 未找到switch_tab隐藏代码")

# 在switch_tab末尾添加account分支
old_switch_end = '''        elif tab_name == "schedule":
            self.schedule_page.pack(fill=tk.BOTH, expand=True)
            self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "schedule"'''

new_switch_end = '''        elif tab_name == "schedule":
            self.schedule_page.pack(fill=tk.BOTH, expand=True)
            self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "schedule"
        elif tab_name == "account":
            self.account_page.pack(fill=tk.BOTH, expand=True)
            self.tab_account.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "account"
            # 切换到账户管理页面时刷新列表
            self.refresh_account_manager_list()'''

if old_switch_end in content:
    content = content.replace(old_switch_end, new_switch_end)
    print("4. switch_tab已添加account分支")
else:
    print("4. 未找到switch_tab末尾代码")

# ============================================================
# 5. 弹幕工具页面：左侧账户管理改为账户多选（参考看播布局）
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

new_danmaku_left = '''        # 左侧：选择发送账户（复选框多选，参考看播布局）
        left_card = tk.Frame(self.danmaku_page, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=280)

        tk.Label(left_card, text="选择发送账户", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（打钩多选，可全选）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))

        # 全选/取消全选按钮
        danmaku_btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        danmaku_btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.danmaku_select_all_btn = tk.Button(danmaku_btn_frame, text="全选", bg=COLORS["bg_input"],
                                                  fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0,
                                                  padx=8, pady=2, cursor="hand2", command=self._danmaku_select_all)
        self.danmaku_select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.danmaku_deselect_all_btn = tk.Button(danmaku_btn_frame, text="取消全选", bg=COLORS["bg_input"],
                                                     fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0,
                                                     padx=8, pady=2, cursor="hand2", command=self._danmaku_deselect_all)
        self.danmaku_deselect_all_btn.pack(side=tk.LEFT)

        # 复选框区域
        self.danmaku_account_frame = tk.Frame(left_card, bg=COLORS["bg_input"])
        self.danmaku_account_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.danmaku_account_vars = {}  # 账户名 -> BooleanVar
        self.danmaku_account_checkbuttons = []

        # 右侧：设置 + 弹幕 + 日志
        right = tk.Frame(self.danmaku_page, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))'''

if old_danmaku_left in content:
    content = content.replace(old_danmaku_left, new_danmaku_left)
    print("5. 弹幕工具页面左侧已改为账户多选（参考看播布局）")
else:
    print("5. 未找到弹幕工具页面左侧代码")

# 版本号
content = content.replace('APP_VERSION = "v5.0.6"', 'APP_VERSION = "v5.0.7"')
print("6. 版本号: v5.0.6 -> v5.0.7")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
