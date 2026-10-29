#!/usr/bin/env python3
"""v4.2.2: 1.任务名自动填写 2.表单自动记忆 3.抢码不需要时间"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 添加类型切换时自动填名称+禁用时间的回调 ==========
# 在build_ui的类型单选按钮后添加回调绑定
old_type_radio_end = '''        ttk.Radiobutton(row1, text="⏻ 关机", variable=self.task_type_var, value="shutdown",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)'''

new_type_radio_end = '''        ttk.Radiobutton(row1, text="⏻ 关机", variable=self.task_type_var, value="shutdown",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)

        # 类型切换时自动填名称+控制时间输入框
        self.task_type_var.trace_add("write", self._on_type_changed)'''

content = content.replace(old_type_radio_end, new_type_radio_end)
print("1. 添加类型切换回调")

# ========== 2. 在时间输入行添加提示标签（抢码时显示） ==========
old_time_row = '''        tk.Label(row2, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
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
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT)'''

new_time_row = '''        tk.Label(row2, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.schedule_hour = DarkEntry(row2, width=5)
        self.schedule_hour.insert(0, "20")
        self.schedule_hour.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row2, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.schedule_minute = DarkEntry(row2, width=5)
        self.schedule_minute.insert(0, "00")
        self.schedule_minute.pack(side=tk.LEFT, padx=(2, 10))
        self.time_hint_label = tk.Label(row2, text="（每天自动执行，使用各页面当前已设置的参数）", bg=COLORS["bg_card"],
                                         fg=COLORS["text_muted"], font=("微软雅黑", 8))
        self.time_hint_label.pack(side=tk.LEFT)'''

content = content.replace(old_time_row, new_time_row)
print("2. 时间行添加提示标签引用")

# ========== 3. 添加_on_type_changed方法和_auto_fill_name方法 ==========
# 在add_schedule_task方法之前插入
old_add_task_def = '''    def add_schedule_task(self):
        """添加日程任务"""'''

new_helper_methods = '''    def _on_type_changed(self, *args):
        """类型切换时：自动填名称 + 控制时间输入框"""
        task_type = self.task_type_var.get()
        self._auto_fill_name(task_type)

        if task_type == "rush":
            # 抢码不需要时间，禁用输入框
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（添加后立即启动抢码任务列表，各任务按自身领取时间运行）",
                                         fg=COLORS["warning"])
        else:
            # 其他类型需要时间
            self.schedule_hour.config(state=tk.NORMAL)
            self.schedule_minute.config(state=tk.NORMAL)
            self.time_hint_label.config(text="（每天自动执行，使用各页面当前已设置的参数）",
                                         fg=COLORS["text_muted"])

    def _auto_fill_name(self, task_type):
        """根据类型自动填写任务名称（看播1、看播2...）"""
        type_prefix = {
            "watch": "看播",
            "danmaku": "弹幕",
            "rush": "抢码",
            "shutdown": "关机",
        }
        prefix = type_prefix.get(task_type, "任务")
        # 统计同类型任务数量
        count = sum(1 for t in self.schedule_tasks if t["type"] == task_type)
        auto_name = f"{prefix}{count + 1}"
        # 只有当输入框为空或已是自动生成的名称时才替换
        current = self.task_name_entry.get().strip()
        if not current or current in [f"{prefix}{i}" for i in range(1, count + 2)]:
            self.task_name_entry.delete(0, tk.END)
            self.task_name_entry.insert(0, auto_name)

    def add_schedule_task(self):
        """添加日程任务"""'''

content = content.replace(old_add_task_def, new_helper_methods)
print("3. 添加类型切换和自动填名称方法")

# ========== 4. 修改add_schedule_task：抢码不需要验证时间，添加后立即执行 ==========
old_add_task_logic = '''        name = self.task_name_entry.get().strip()
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
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}

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
        self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天 {task['time_str']} 执行")'''

new_add_task_logic = '''        name = self.task_name_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入任务名称")
            return

        task_type = self.task_type_var.get()
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}

        if task_type == "rush":
            # 抢码不需要时间，添加后立即执行
            hour = -1
            minute = -1
            time_str = "立即执行"
        else:
            try:
                hour = int(self.schedule_hour.get().strip())
                minute = int(self.schedule_minute.get().strip())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）")
                return
            time_str = f"{hour:02d}:{minute:02d}"

        task = {
            "id": f"schedule_{int(time.time()*1000)}",
            "name": name,
            "type": task_type,
            "type_name": type_names[task_type],
            "hour": hour,
            "minute": minute,
            "time_str": time_str,
            "enabled": True,
            "last_run": "",
            "status": "等待中",
        }
        self.schedule_tasks.append(task)
        self.refresh_task_list()
        self.save_schedule()
        # 保存表单设置
        self._save_form_settings()

        if task_type == "rush":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，立即执行")
            # 抢码任务添加后立即执行
            self.after(100, lambda t=task: self.execute_task(t))
        else:
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天 {time_str} 执行")

        # 添加后自动填下一个名称
        self._auto_fill_name(task_type)'''

content = content.replace(old_add_task_logic, new_add_task_logic)
print("4. 修改添加任务逻辑（抢码立即执行）")

# ========== 5. 修改调度器：抢码任务不参与定时检查 ==========
old_scheduler_check = '''                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        task_minute = task["hour"] * 60 + task["minute"]
                        if task_minute == current_minute:
                            # 到点执行
                            self.app.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.after(5000, lambda t=task: self._reset_task_status(t))'''

new_scheduler_check = '''                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        # 抢码任务是立即执行的，不参与定时检查
                        if task["type"] == "rush" or task.get("hour", -1) == -1:
                            continue
                        task_minute = task["hour"] * 60 + task["minute"]
                        if task_minute == current_minute:
                            # 到点执行
                            self.app.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.after(5000, lambda t=task: self._reset_task_status(t))'''

content = content.replace(old_scheduler_check, new_scheduler_check)
print("5. 调度器跳过抢码任务")

# ========== 6. 添加表单设置保存/加载方法 ==========
old_load_schedule_def = '''    def load_schedule(self):
        """加载日程配置"""'''

new_form_settings = '''    def _save_form_settings(self):
        """保存表单设置（类型、时间）"""
        try:
            config_file = BASE_DIR / "schedule_form_settings.json"
            settings = {
                "task_type": self.task_type_var.get(),
                "hour": self.schedule_hour.get(),
                "minute": self.schedule_minute.get(),
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_form_settings(self):
        """加载表单设置"""
        try:
            config_file = BASE_DIR / "schedule_form_settings.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.task_type_var.set(settings.get("task_type", "watch"))
                h = settings.get("hour", "20")
                m = settings.get("minute", "00")
                self.schedule_hour.delete(0, tk.END)
                self.schedule_hour.insert(0, h)
                self.schedule_minute.delete(0, tk.END)
                self.schedule_minute.insert(0, m)
                # 触发类型切换回调
                self._on_type_changed()
        except Exception:
            pass

    def load_schedule(self):
        """加载日程配置"""'''

content = content.replace(old_load_schedule_def, new_form_settings)
print("6. 添加表单设置保存/加载")

# ========== 7. 在__init__中加载表单设置 ==========
old_schedule_init = '''        self.build_ui()
        self.load_schedule()
        self.start_scheduler()'''

new_schedule_init = '''        self.build_ui()
        self.load_schedule()
        self._load_form_settings()
        self.start_scheduler()'''

content = content.replace(old_schedule_init, new_schedule_init)
print("7. init中加载表单设置")

# ========== 8. 任务列表中抢码任务的时间显示"立即执行" ==========
# refresh_task_list中已经用task["time_str"]，抢码任务的time_str是"立即执行"，所以已经正确显示
# 但需要确保状态显示正确，抢码任务执行后状态应该是"已完成"而不是"等待中"
# 这个在execute_task和_mark_task_done中已经处理

# ========== 9. on_close中保存表单设置 ==========
old_on_close = '''    def on_close(self):
        """关闭时保存配置并停止调度器"""
        self.save_schedule()
        self.stop_scheduler()'''

new_on_close = '''    def on_close(self):
        """关闭时保存配置并停止调度器"""
        self.save_schedule()
        self._save_form_settings()
        self.stop_scheduler()'''

content = content.replace(old_on_close, new_on_close)
print("8. on_close保存表单设置")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.2.2 patch完成！")
