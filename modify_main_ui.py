file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在定时关机标签按钮后添加看播任务标签按钮
old_tab = '''        self.tab_shutdown = tk.Label(tab_bar, text="⏻ 定时关机", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_shutdown.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_shutdown.bind("<Button-1>", lambda e: self.switch_tab("shutdown"))'''

new_tab = '''        self.tab_shutdown = tk.Label(tab_bar, text="⏻ 定时关机", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_shutdown.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_shutdown.bind("<Button-1>", lambda e: self.switch_tab("shutdown"))

        self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))'''

if old_tab in content:
    content = content.replace(old_tab, new_tab, 1)
    print("✓ 标签按钮已添加")
else:
    print("✗ 未找到标签按钮插入点")

# 2. 在定时关机页面创建后添加看播任务页面
old_page = '''        # 定时关机页面
        self.shutdown_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.shutdown_page.pack(fill=tk.BOTH, expand=True)
        self.shutdown_page.pack_forget()
        self.build_shutdown_page()

        self.current_tab = "rush"'''

new_page = '''        # 定时关机页面
        self.shutdown_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.shutdown_page.pack(fill=tk.BOTH, expand=True)
        self.shutdown_page.pack_forget()
        self.build_shutdown_page()

        # 看播任务页面
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()

        self.current_tab = "rush"'''

if old_page in content:
    content = content.replace(old_page, new_page, 1)
    print("✓ 看播任务页面已添加")
else:
    print("✗ 未找到页面创建插入点")

# 3. 修改switch_tab方法 - 隐藏页面部分
old_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()'''

new_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()'''

if old_hide in content:
    content = content.replace(old_hide, new_hide, 1)
    print("✓ switch_tab隐藏页面已更新")
else:
    print("✗ 未找到switch_tab隐藏页面")

# 4. 修改switch_tab方法 - 重置标签样式部分
old_reset = '''        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

new_reset = '''        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

if old_reset in content:
    content = content.replace(old_reset, new_reset, 1)
    print("✓ switch_tab重置标签样式已更新")
else:
    print("✗ 未找到switch_tab重置标签样式")

# 5. 修改switch_tab方法 - 添加watch分支（在shutdown分支后，保存配置前）
old_shutdown_branch = '''        elif tab_name == "shutdown":
            self.shutdown_page.pack(fill=tk.BOTH, expand=True)
            self.tab_shutdown.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "shutdown"
            # 刷新关机任务列表
            self.refresh_shutdown_task_list()
        # 保存当前标签页'''

new_shutdown_branch = '''        elif tab_name == "shutdown":
            self.shutdown_page.pack(fill=tk.BOTH, expand=True)
            self.tab_shutdown.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "shutdown"
            # 刷新关机任务列表
            self.refresh_shutdown_task_list()
        elif tab_name == "watch":
            self.watch_page.pack(fill=tk.BOTH, expand=True)
            self.tab_watch.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "watch"
            # 切换到看播任务时刷新账户列表
            self.watch_page.refresh_account_list()
        # 保存当前标签页'''

if old_shutdown_branch in content:
    content = content.replace(old_shutdown_branch, new_shutdown_branch, 1)
    print("✓ switch_tab watch分支已添加")
else:
    print("✗ 未找到switch_tab shutdown分支")

# 6. 修改on_closing方法 - 添加watch_page保存
old_close = '''            # 保存抢码工具配置
            if hasattr(self, 'rush_page'):
                self.rush_page.on_close()
            # 取消定时关机'''

new_close = '''            # 保存抢码工具配置
            if hasattr(self, 'rush_page'):
                self.rush_page.on_close()
            # 保存看播任务配置
            if hasattr(self, 'watch_page'):
                self.watch_page.on_close()
            # 取消定时关机'''

if old_close in content:
    content = content.replace(old_close, new_close, 1)
    print("✓ on_closing watch_page保存已添加")
else:
    print("✗ 未找到on_closing抢码保存部分")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 主界面修改完成，文件已保存")
