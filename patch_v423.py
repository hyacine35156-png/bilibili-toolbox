#!/usr/bin/env python3
"""v4.2.3: 修复_on_type_changed缺失 + 添加编辑日程功能"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 在add_schedule_task之前插入缺失的方法 ==========
old_add_task = '''    def add_schedule_task(self):
        name = self.task_name_entry.get().strip()'''

new_add_task = '''    def _on_type_changed(self, *args):
        """类型切换时：自动填名称 + 控制时间输入框"""
        task_type = self.task_type_var.get()
        self._auto_fill_name(task_type)

        if task_type == "rush":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（添加后立即启动抢码任务列表，各任务按自身领取时间运行）",
                                         fg=COLORS["warning"])
        else:
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
        count = sum(1 for t in self.schedule_tasks if t["type"] == task_type)
        auto_name = f"{prefix}{count + 1}"
        current = self.task_name_entry.get().strip()
        if not current or current in [f"{prefix}{i}" for i in range(1, count + 2)]:
            self.task_name_entry.delete(0, tk.END)
            self.task_name_entry.insert(0, auto_name)

    def add_schedule_task(self):
        name = self.task_name_entry.get().strip()'''

content = content.replace(old_add_task, new_add_task)
print("1. 插入_on_type_changed和_auto_fill_name方法")

# ========== 2. 在任务列表的操作列添加"编辑"按钮 ==========
# 先找到refresh_task_list中操作按钮的部分
old_task_buttons = '''            # 操作按钮
            btn_frame = tk.Frame(row_frame, bg=bg_color)
            btn_frame.pack(side=tk.LEFT, padx=(8, 0))

            task_id = task.get("id")
            if status in ["等待中", "已完成", "已领取", "失败"]:
                DarkButton(btn_frame, "开始", command=lambda tid=task_id: self.start_scheduled_task(tid),
                           width=45, height=22, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 2))
            else:
                DarkButton(btn_frame, "停止", command=lambda tid=task_id: self.stop_scheduled_task(tid),
                           width=45, height=22, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 2))

            DarkButton(btn_frame, "删除", command=lambda tid=task_id: self.delete_scheduled_task(tid),
                       width=45, height=22, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)'''

# 这个是抢码页面的，不是日程页面的。让我找日程页面的任务列表。
# 日程页面的refresh_task_list在3855行，让我看看它的结构。

# 实际上日程页面的任务列表结构不同，让我先读取确认
print("2. 跳过（需要先确认日程任务列表结构）")

# ========== 3. 添加编辑日程方法（在delete_selected_task之后） ==========
old_delete_selected = '''    def delete_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要删除的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task and messagebox.askyesno("确认", f"确定删除任务「{task['name']}」吗？"):
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] != self.selected_task_id]
            self.selected_task_id = None
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已删除任务「{task['name']}」")'''

new_delete_selected = '''    def delete_selected_task(self):
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

    def edit_selected_task(self):
        """编辑选中的日程任务"""
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要编辑的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if not task:
            return

        # 创建编辑窗口
        edit_win = tk.Toplevel(self.app.root)
        edit_win.title(f"编辑任务 - {task['name']}")
        edit_win.geometry("380x280")
        edit_win.configure(bg=COLORS["bg_card"])
        edit_win.resizable(False, False)
        edit_win.attributes("-topmost", True)
        edit_win.grab_set()
        edit_win.update_idletasks()
        x = (edit_win.winfo_screenwidth() // 2) - 190
        y = (edit_win.winfo_screenheight() // 2) - 140
        edit_win.geometry(f"380x280+{x}+{y}")

        tk.Label(edit_win, text="✏ 编辑日程任务", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 14, "bold")).pack(pady=(15, 10))

        # 任务名称
        name_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(name_frame, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        name_entry = DarkEntry(name_frame, width=22)
        name_entry.insert(0, task["name"])
        name_entry.pack(side=tk.LEFT, padx=(10, 0))

        # 任务类型
        type_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        type_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(type_frame, text="任务类型:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        edit_type_var = tk.StringVar(value=task["type"])
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}
        for val, label in type_names.items():
            ttk.Radiobutton(type_frame, text=label, variable=edit_type_var, value=val,
                            style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(6, 0))

        # 执行时间
        time_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        time_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(time_frame, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        hour_entry = DarkEntry(time_frame, width=5)
        hour_entry.insert(0, f"{task.get('hour', 20):02d}" if task.get("hour", -1) >= 0 else "20")
        hour_entry.pack(side=tk.LEFT, padx=(10, 2))
        tk.Label(time_frame, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        minute_entry = DarkEntry(time_frame, width=5)
        minute_entry.insert(0, f"{task.get('minute', 0):02d}" if task.get("minute", -1) >= 0 else "00")
        minute_entry.pack(side=tk.LEFT, padx=(2, 0))
        time_hint = tk.Label(time_frame, text="", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                             font=("微软雅黑", 8))
        time_hint.pack(side=tk.LEFT, padx=(10, 0))

        def on_type_change(*args):
            if edit_type_var.get() == "rush":
                hour_entry.config(state=tk.DISABLED)
                minute_entry.config(state=tk.DISABLED)
                time_hint.config(text="（立即执行）", fg=COLORS["warning"])
            else:
                hour_entry.config(state=tk.NORMAL)
                minute_entry.config(state=tk.NORMAL)
                time_hint.config(text="")
        edit_type_var.trace_add("write", on_type_change)
        on_type_change()

        # 按钮
        btn_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        btn_frame.pack(pady=(15, 10))

        def save_edit():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("提示", "请输入任务名称", parent=edit_win)
                return
            new_type = edit_type_var.get()
            if new_type == "rush":
                new_hour = -1
                new_minute = -1
                new_time_str = "立即执行"
            else:
                try:
                    new_hour = int(hour_entry.get().strip())
                    new_minute = int(minute_entry.get().strip())
                    if not (0 <= new_hour <= 23 and 0 <= new_minute <= 59):
                        raise ValueError
                except ValueError:
                    messagebox.showwarning("提示", "请输入有效的时间", parent=edit_win)
                    return
                new_time_str = f"{new_hour:02d}:{new_minute:02d}"

            task["name"] = new_name
            task["type"] = new_type
            task["type_name"] = type_names[new_type]
            task["hour"] = new_hour
            task["minute"] = new_minute
            task["time_str"] = new_time_str
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"✏ 已修改任务「{new_name}」({type_names[new_type]})，{new_time_str}")
            edit_win.destroy()

        DarkButton(btn_frame, "保存", command=save_edit,
                   width=80, height=30, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
        DarkButton(btn_frame, "取消", command=edit_win.destroy,
                   width=80, height=30, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)'''

content = content.replace(old_delete_selected, new_delete_selected)
print("3. 添加edit_selected_task方法")

# ========== 4. 在添加任务按钮行添加"编辑"按钮 ==========
old_btn_row = '''        DarkButton(row3, "+ 添加任务", command=self.add_schedule_task,
                   width=120, height=32, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(row3, "▶ 立即执行选中", command=self.run_selected_task,
                   width=130, height=32, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))
        DarkButton(row3, "🗑 删除选中", command=self.delete_selected_task,
                   width=110, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))'''

new_btn_row = '''        DarkButton(row3, "+ 添加任务", command=self.add_schedule_task,
                   width=120, height=32, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(row3, "✏ 编辑选中", command=self.edit_selected_task,
                   width=110, height=32, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))
        DarkButton(row3, "▶ 立即执行选中", command=self.run_selected_task,
                   width=130, height=32, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))
        DarkButton(row3, "🗑 删除选中", command=self.delete_selected_task,
                   width=110, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))'''

content = content.replace(old_btn_row, new_btn_row)
print("4. 添加编辑选中按钮")

# ========== 5. 在任务列表每行添加双击编辑和操作按钮 ==========
# 先找到日程页面refresh_task_list中任务行的结构
old_task_row_name = '''            # 任务名称
            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=18, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)
            name_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))'''

new_task_row_name = '''            # 任务名称（双击编辑）
            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=18, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)
            name_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))
            name_label.bind("<Double-Button-1>", lambda e, tid=task["id"]: self._edit_task_by_id(tid))'''

content = content.replace(old_task_row_name, new_task_row_name)
print("5. 任务名称添加双击编辑")

# ========== 6. 添加_edit_task_by_id辅助方法 ==========
old_run_selected = '''    def run_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要执行的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task:
            self.execute_task(task, manual=True)'''

new_run_selected = '''    def _edit_task_by_id(self, task_id):
        """根据ID编辑任务（双击调用）"""
        self.selected_task_id = task_id
        self.refresh_task_list()
        self.edit_selected_task()

    def run_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要执行的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task:
            self.execute_task(task, manual=True)'''

content = content.replace(old_run_selected, new_run_selected)
print("6. 添加_edit_task_by_id方法")

# ========== 7. 更新任务列表提示文字 ==========
old_list_hint = '''        tk.Label(list_header, text="（点击选中，可启用/禁用/立即执行/删除）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

new_list_hint = '''        tk.Label(list_header, text="（点击选中，双击编辑；可启用/禁用/编辑/立即执行/删除）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

content = content.replace(old_list_hint, new_list_hint)
print("7. 更新列表提示文字")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.2.3 patch完成！")
