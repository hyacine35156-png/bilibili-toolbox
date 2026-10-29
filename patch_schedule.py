#!/usr/bin/env python3
"""添加日程任务功能：定时执行抢码/看播/发弹幕"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== ScheduleFrame类代码 ==========
schedule_class_code = '''

# ========== 日程任务 ==========
class ScheduleFrame(tk.Frame):
    """日程任务：定时执行抢码/看播/发弹幕"""
    def __init__(self, parent, account_mgr, app):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.app = app  # DanmakuApp实例，用于访问其他页面
        self.account_mgr = account_mgr
        self.schedule_tasks = []
        self.scheduler_running = False
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = None
        self.build_ui()
        self.load_schedule()
        self.start_scheduler()

    def build_ui(self):
        # 顶部：添加任务卡片
        add_card = tk.Frame(self, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        add_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(add_card, text="➕ 添加日程任务", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))

        add_inner = tk.Frame(add_card, bg=COLORS["bg_card"])
        add_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行：任务名称 + 类型
        row1 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)

        tk.Label(row1, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.task_name_entry = DarkEntry(row1, width=20)
        self.task_name_entry.pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row1, text="任务类型:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.task_type_var = tk.StringVar(value="watch")
        ttk.Radiobutton(row1, text="📺 看播", variable=self.task_type_var, value="watch",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="💬 弹幕", variable=self.task_type_var, value="danmaku",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⚡ 抢码", variable=self.task_type_var, value="rush",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)

        # 第二行：执行时间
        row2 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)

        tk.Label(row2, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.schedule_hour = DarkEntry(row2, width=5)
        self.schedule_hour.insert(0, "20")
        self.schedule_hour.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row2, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.schedule_minute = DarkEntry(row2, width=5)
        self.schedule_minute.insert(0, "00")
        self.schedule_minute.pack(side=tk.LEFT, padx=(2, 10))
        tk.Label(row2, text="（每天自动执行，使用各页面当前已设置的参数）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT)

        # 第三行：添加按钮
        row3 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=(8, 0))

        DarkButton(row3, "+ 添加任务", command=self.add_schedule_task,
                   width=120, height=32, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(row3, "▶ 立即执行选中", command=self.run_selected_task,
                   width=130, height=32, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))
        DarkButton(row3, "🗑 删除选中", command=self.delete_selected_task,
                   width=110, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))

        # 调度器状态
        self.scheduler_status_label = tk.Label(row3, text="● 调度器运行中", bg=COLORS["bg_card"],
                                                fg=COLORS["success"], font=("微软雅黑", 10, "bold"))
        self.scheduler_status_label.pack(side=tk.RIGHT)

        # 底部：任务列表 + 日志
        bottom = tk.Frame(self, bg=COLORS["bg_dark"])
        bottom.pack(fill=tk.BOTH, expand=True)

        # 左侧：任务列表
        list_card = tk.Frame(bottom, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        list_header = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(list_header, text="📋 日程任务列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(list_header, text="（点击选中，可启用/禁用/立即执行/删除）", bg=COLORS["bg_card"],
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
        self.schedule_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.schedule_log_text.yview,
                                    style="Dark.Horizontal.TScrollbar")
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.schedule_log_text.config(yscrollcommand=log_scroll.set)

        self.selected_task_id = None

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\\n"
        self.schedule_log_text.config(state=tk.NORMAL)
        self.schedule_log_text.insert(tk.END, line)
        self.schedule_log_text.see(tk.END)
        self.schedule_log_text.config(state=tk.DISABLED)

    def add_schedule_task(self):
        name = self.task_name_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入任务名称")
            return
        try:
            hour = int(self.schedule_hour.get().strip())
            minute = int(self.schedule_minute.get().strip())
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）")
            return

        task_type = self.task_type_var.get()
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码"}

        task = {
            "id": f"schedule_{int(time.time()*1000)}",
            "name": name,
            "type": task_type,
            "type_name": type_names[task_type],
            "hour": hour,
            "minute": minute,
            "time_str": f"{hour:02d}:{minute:02d}",
            "enabled": True,
            "last_run": "",
            "status": "等待中",
        }
        self.schedule_tasks.append(task)
        self.refresh_task_list()
        self.save_schedule()
        self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天 {task['time_str']} 执行")

    def refresh_task_list(self):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        if not self.schedule_tasks:
            tk.Label(self.task_list_frame, text="暂无日程任务，设置好参数后点击「+ 添加任务」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(pady=30)
            return

        for idx, task in enumerate(self.schedule_tasks):
            is_selected = (task["id"] == self.selected_task_id)
            bg_color = COLORS["accent"] if is_selected else (COLORS["bg_input"] if idx % 2 == 0 else COLORS["bg_card"])
            text_color = "#000000" if is_selected else COLORS["text_primary"]

            row_frame = tk.Frame(self.task_list_frame, bg=bg_color)
            row_frame.pack(fill=tk.X, pady=1)
            row_frame.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 启用/禁用复选框
            enabled_var = tk.BooleanVar(value=task["enabled"])
            def toggle_enabled(var=enabled_var, t=task):
                t["enabled"] = var.get()
                self.save_schedule()
                self.refresh_task_list()
                self.log(f"{'✅ 启用' if var.get() else '⏸ 禁用'}任务「{t['name']}」")
            chk = tk.Checkbutton(row_frame, variable=enabled_var, command=toggle_enabled,
                                 bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"])
            chk.pack(side=tk.LEFT, padx=(8, 4), pady=8)
            chk.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 任务名称
            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=18, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)
            name_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 类型
            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=10, anchor=tk.W)
            type_label.pack(side=tk.LEFT, padx=(10, 0))
            type_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 时间
            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=8, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(10, 0))
            time_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 状态
            status_text = task.get("status", "等待中")
            if status_text == "执行中":
                status_fg = COLORS["danger"]
            elif status_text == "已完成":
                status_fg = COLORS["success"]
            elif status_text == "失败":
                status_fg = COLORS["warning"]
            else:
                status_fg = COLORS["text_muted"]
            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=10, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(10, 0))
            status_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 上次执行
            last_run = task.get("last_run", "-")
            last_label = tk.Label(row_frame, text=f"上次: {last_run}", bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=18, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(10, 0))
            last_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

    def select_task(self, task_id):
        self.selected_task_id = task_id
        self.refresh_task_list()

    def delete_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要删除的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task and messagebox.askyesno("确认", f"确定删除任务「{task['name']}」吗？"):
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] != self.selected_task_id]
            self.selected_task_id = None
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已删除任务「{task['name']}」")

    def run_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要执行的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task:
            self.execute_task(task, manual=True)

    def execute_task(self, task, manual=False):
        """执行指定任务"""
        task["status"] = "执行中"
        task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.refresh_task_list()

        prefix = "手动执行" if manual else "定时触发"
        self.log(f"{'⚡' if manual else '⏰'} {prefix}任务「{task['name']}」({task['type_name']})")

        try:
            if task["type"] == "watch":
                # 切换到看播页面并开始
                self.app.after(0, lambda: self.app.switch_tab("watch"))
                self.app.after(500, lambda: self._start_watch_safe(task))
            elif task["type"] == "danmaku":
                # 切换到弹幕页面并开始
                self.app.after(0, lambda: self.app.switch_tab("danmaku"))
                self.app.after(500, lambda: self._start_danmaku_safe(task))
            elif task["type"] == "rush":
                # 切换到抢码页面并开始
                self.app.after(0, lambda: self.app.switch_tab("rush"))
                self.app.after(500, lambda: self._start_rush_safe(task))

            # 标记完成（实际执行在页面线程中进行）
            self.app.after(2000, lambda: self._mark_task_done(task))

        except Exception as e:
            task["status"] = "失败"
            self.refresh_task_list()
            self.log(f"✗ 任务「{task['name']}」执行失败: {e}")

    def _start_watch_safe(self, task):
        try:
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'start_watch'):
                self.app.watch_page.start_watch()
                self.log(f"✓ 看播任务已启动")
        except Exception as e:
            self.log(f"✗ 启动看播失败: {e}")

    def _start_danmaku_safe(self, task):
        try:
            if hasattr(self.app, 'start_sending'):
                self.app.start_sending()
                self.log(f"✓ 弹幕任务已启动")
        except Exception as e:
            self.log(f"✗ 启动弹幕失败: {e}")

    def _start_rush_safe(self, task):
        try:
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_rush'):
                self.app.rush_page.start_rush()
                self.log(f"✓ 抢码任务已启动")
        except Exception as e:
            self.log(f"✗ 启动抢码失败: {e}")

    def _mark_task_done(self, task):
        task["status"] = "已完成"
        self.refresh_task_list()
        self.save_schedule()

    def start_scheduler(self):
        """启动调度器"""
        if self.scheduler_running:
            return
        self.scheduler_running = True
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.scheduler_status_label.config(text="● 调度器运行中", fg=COLORS["success"])
        self.log("⏰ 日程调度器已启动")

    def _scheduler_loop(self):
        """调度器主循环：每秒检查一次，到点执行任务"""
        last_minute = -1
        while not self.scheduler_stop["stop"]:
            try:
                now = datetime.now()
                current_minute = now.hour * 60 + now.minute

                # 只在分钟变化时检查（避免同一分钟重复执行）
                if current_minute != last_minute:
                    last_minute = current_minute
                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        task_minute = task["hour"] * 60 + task["minute"]
                        if task_minute == current_minute:
                            # 到点执行
                            self.app.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.after(5000, lambda t=task: self._reset_task_status(t))

            except Exception as e:
                self.log(f"调度器异常: {e}")

            time.sleep(1)

    def _reset_task_status(self, task):
        """重置任务状态为等待中（用于每天重复执行）"""
        if task.get("status") == "已完成":
            task["status"] = "等待中"
            self.refresh_task_list()

    def stop_scheduler(self):
        """停止调度器"""
        self.scheduler_stop["stop"] = True
        self.scheduler_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=2)
        self.scheduler_status_label.config(text="● 调度器已停止", fg=COLORS["text_muted"])
        self.log("⏰ 日程调度器已停止")

    def save_schedule(self):
        """保存日程配置"""
        try:
            config_file = BASE_DIR / "schedule_config.json"
            # 只保存可序列化的字段
            save_data = []
            for task in self.schedule_tasks:
                save_data.append({
                    "id": task["id"],
                    "name": task["name"],
                    "type": task["type"],
                    "type_name": task["type_name"],
                    "hour": task["hour"],
                    "minute": task["minute"],
                    "time_str": task["time_str"],
                    "enabled": task["enabled"],
                    "last_run": task.get("last_run", ""),
                })
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_schedule(self):
        """加载日程配置"""
        try:
            config_file = BASE_DIR / "schedule_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    saved_tasks = json.load(f)
                for task in saved_tasks:
                    task["status"] = "等待中"
                    self.schedule_tasks.append(task)
                self.refresh_task_list()
                self.log(f"已加载 {len(saved_tasks)} 个日程任务")
        except Exception as e:
            self.log(f"加载日程配置失败: {e}")

    def on_close(self):
        """关闭时保存配置并停止调度器"""
        self.save_schedule()
        self.stop_scheduler()

'''

# 在DanmakuApp类之前插入ScheduleFrame类
insert_marker = "class DanmakuApp:"
content = content.replace(insert_marker, schedule_class_code + "\n" + insert_marker)
print("1. 插入ScheduleFrame类")

# ========== 2. 在build_ui中添加日程任务标签 ==========
old_tab_watch = '''        self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))'''

new_tab_watch = '''        self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))

        self.tab_schedule = tk.Label(tab_bar, text="📅 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_schedule.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_schedule.bind("<Button-1>", lambda e: self.switch_tab("schedule"))'''

content = content.replace(old_tab_watch, new_tab_watch)
print("2. 添加日程任务标签按钮")

# ========== 3. 在主内容区添加日程任务页面 ==========
old_watch_page = '''        # 看播任务页面
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()

        self.current_tab = "rush"'''

new_watch_page = '''        # 看播任务页面
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()

        # 日程任务页面
        self.schedule_page = ScheduleFrame(self.tab_container, self.account_mgr, self)
        self.schedule_page.pack(fill=tk.BOTH, expand=True)
        self.schedule_page.pack_forget()

        self.current_tab = "rush"'''

content = content.replace(old_watch_page, new_watch_page)
print("3. 添加日程任务页面实例")

# ========== 4. 在switch_tab中添加日程任务切换逻辑 ==========
old_switch_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()'''

new_switch_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()
        self.schedule_page.pack_forget()'''

content = content.replace(old_switch_hide, new_switch_hide)
print("4. switch_tab隐藏日程任务页面")

# ========== 5. 在switch_tab中重置标签样式 ==========
old_reset_tabs = '''        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

new_reset_tabs = '''        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_schedule.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

content = content.replace(old_reset_tabs, new_reset_tabs)
print("5. switch_tab重置日程任务标签样式")

# ========== 6. 在switch_tab中添加日程任务显示逻辑 ==========
old_watch_switch = '''        elif tab_name == "watch":
            self.watch_page.pack(fill=tk.BOTH, expand=True)
            self.tab_watch.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "watch"
            # 切换到看播任务时刷新账户列表
            self.watch_page.refresh_account_list()
        # 保存当前标签页'''

new_watch_switch = '''        elif tab_name == "watch":
            self.watch_page.pack(fill=tk.BOTH, expand=True)
            self.tab_watch.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "watch"
            # 切换到看播任务时刷新账户列表
            self.watch_page.refresh_account_list()
        elif tab_name == "schedule":
            self.schedule_page.pack(fill=tk.BOTH, expand=True)
            self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "schedule"
        # 保存当前标签页'''

content = content.replace(old_watch_switch, new_watch_switch)
print("6. switch_tab添加日程任务显示逻辑")

# ========== 7. 在__init__中恢复标签页时添加schedule ==========
old_restore_tab = '''        # 恢复上次选中的标签页
        saved_tab = self.config.get("current_tab", "rush")
        if saved_tab == "danmaku":
            self.switch_tab("danmaku")
        elif saved_tab == "shutdown":
            self.switch_tab("shutdown")'''

new_restore_tab = '''        # 恢复上次选中的标签页
        saved_tab = self.config.get("current_tab", "rush")
        if saved_tab == "danmaku":
            self.switch_tab("danmaku")
        elif saved_tab == "shutdown":
            self.switch_tab("shutdown")
        elif saved_tab == "schedule":
            self.switch_tab("schedule")'''

content = content.replace(old_restore_tab, new_restore_tab)
print("7. __init__恢复schedule标签页")

# ========== 8. 在on_closing中保存日程配置 ==========
old_on_closing = '''    def on_closing(self):
        """窗口关闭时保存所有配置"""
        try:
            self.save_config()
            self.save_danmaku_silent()
            # 保存抢码工具配置
            if hasattr(self, 'rush_page'):
                self.rush_page.on_close()
            # 保存看播任务配置
            if hasattr(self, 'watch_page'):
                self.watch_page.on_close()
            # 取消定时关机
            self.cancel_shutdown()
            # 保存关机配置
            self.save_shutdown_config()
        except Exception:
            pass
        self.root.destroy()'''

new_on_closing = '''    def on_closing(self):
        """窗口关闭时保存所有配置"""
        try:
            self.save_config()
            self.save_danmaku_silent()
            # 保存抢码工具配置
            if hasattr(self, 'rush_page'):
                self.rush_page.on_close()
            # 保存看播任务配置
            if hasattr(self, 'watch_page'):
                self.watch_page.on_close()
            # 保存日程任务配置并停止调度器
            if hasattr(self, 'schedule_page'):
                self.schedule_page.on_close()
            # 取消定时关机
            self.cancel_shutdown()
            # 保存关机配置
            self.save_shutdown_config()
        except Exception:
            pass
        self.root.destroy()'''

content = content.replace(old_on_closing, new_on_closing)
print("8. on_closing保存日程配置")

# ========== 9. 更新窗口标题 ==========
old_title = '''        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务(X25Kn观看心跳)")'''
new_title = '''        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务+日程任务")'''
content = content.replace(old_title, new_title)
print("9. 更新窗口标题")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n日程任务功能添加完成！")
