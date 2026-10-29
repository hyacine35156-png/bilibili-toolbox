#!/usr/bin/env python3
"""v4.2.4: 多选日程 + 批量删除"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 在__init__中添加selected_ids集合 ==========
old_init = '''        self.schedule_tasks = []
        self.scheduler_running = False
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = None
        self.build_ui()'''

new_init = '''        self.schedule_tasks = []
        self.scheduler_running = False
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = None
        self.selected_ids = set()  # 多选的任务ID集合
        self.build_ui()'''

content = content.replace(old_init, new_init)
print("1. 添加selected_ids集合")

# ========== 2. 按钮栏添加全选和批量删除按钮 ==========
old_btn_row = '''        DarkButton(row3, "+ 添加任务", command=self.add_schedule_task,
                   width=120, height=32, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(row3, "✏ 编辑选中", command=self.edit_selected_task,
                   width=110, height=32, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))
        DarkButton(row3, "▶ 立即执行选中", command=self.run_selected_task,
                   width=130, height=32, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))
        DarkButton(row3, "🗑 删除选中", command=self.delete_selected_task,
                   width=110, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(10, 0))'''

new_btn_row = '''        DarkButton(row3, "+ 添加任务", command=self.add_schedule_task,
                   width=120, height=32, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(row3, "✏ 编辑", command=self.edit_selected_task,
                   width=70, height=32, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "▶ 执行", command=self.run_selected_task,
                   width=70, height=32, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "☑ 全选", command=self.toggle_select_all,
                   width=70, height=32, bg_color="#9b59b6", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "🗑 批量删除", command=self.delete_selected_tasks,
                   width=100, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))'''

content = content.replace(old_btn_row, new_btn_row)
print("2. 按钮栏添加全选和批量删除")

# ========== 3. 在任务列表每行开头添加选择复选框 ==========
old_row_start = '''        for idx, task in enumerate(self.schedule_tasks):
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
            chk.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))'''

new_row_start = '''        for idx, task in enumerate(self.schedule_tasks):
            is_selected = (task["id"] == self.selected_task_id)
            is_checked = (task["id"] in self.selected_ids)
            bg_color = COLORS["accent"] if is_selected else (COLORS["bg_input"] if idx % 2 == 0 else COLORS["bg_card"])
            text_color = "#000000" if is_selected else COLORS["text_primary"]

            row_frame = tk.Frame(self.task_list_frame, bg=bg_color)
            row_frame.pack(fill=tk.X, pady=1)
            row_frame.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 选择复选框（多选）
            check_var = tk.BooleanVar(value=is_checked)
            def toggle_check(var=check_var, tid=task["id"]):
                if var.get():
                    self.selected_ids.add(tid)
                else:
                    self.selected_ids.discard(tid)
            check_chk = tk.Checkbutton(row_frame, variable=check_var, command=toggle_check,
                                        bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"])
            check_chk.pack(side=tk.LEFT, padx=(4, 2), pady=8)

            # 启用/禁用复选框
            enabled_var = tk.BooleanVar(value=task["enabled"])
            def toggle_enabled(var=enabled_var, t=task):
                t["enabled"] = var.get()
                self.save_schedule()
                self.refresh_task_list()
                self.log(f"{'✅ 启用' if var.get() else '⏸ 禁用'}任务「{t['name']}」")
            chk = tk.Checkbutton(row_frame, variable=enabled_var, command=toggle_enabled,
                                 bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"])
            chk.pack(side=tk.LEFT, padx=(2, 4), pady=8)
            chk.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))'''

content = content.replace(old_row_start, new_row_start)
print("3. 每行添加选择复选框")

# ========== 4. 添加toggle_select_all和delete_selected_tasks方法 ==========
old_select_task = '''    def select_task(self, task_id):
        self.selected_task_id = task_id
        self.refresh_task_list()'''

new_select_task = '''    def select_task(self, task_id):
        self.selected_task_id = task_id
        self.refresh_task_list()

    def toggle_select_all(self):
        """全选/取消全选"""
        if len(self.selected_ids) == len(self.schedule_tasks):
            # 已全选，取消全选
            self.selected_ids.clear()
            self.log("☐ 已取消全选")
        else:
            # 全选
            self.selected_ids = {t["id"] for t in self.schedule_tasks}
            self.log(f"☑ 已全选 {len(self.schedule_tasks)} 个任务")
        self.refresh_task_list()

    def delete_selected_tasks(self):
        """批量删除勾选的任务"""
        if not self.selected_ids:
            messagebox.showwarning("提示", "请先勾选要删除的任务（每行左侧复选框）")
            return
        count = len(self.selected_ids)
        if messagebox.askyesno("确认", f"确定删除选中的 {count} 个任务吗？"):
            names = [t["name"] for t in self.schedule_tasks if t["id"] in self.selected_ids]
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] not in self.selected_ids]
            if self.selected_task_id in self.selected_ids:
                self.selected_task_id = None
            self.selected_ids.clear()
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已批量删除 {count} 个任务: {', '.join(names)}")'''

content = content.replace(old_select_task, new_select_task)
print("4. 添加全选和批量删除方法")

# ========== 5. 更新列表提示文字 ==========
old_list_hint = '''        tk.Label(list_header, text="（点击选中，双击编辑；可启用/禁用/编辑/立即执行/删除）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

new_list_hint = '''        tk.Label(list_header, text="（勾选左侧框可多选批量删除；点击选中，双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

content = content.replace(old_list_hint, new_list_hint)
print("5. 更新列表提示文字")

# ========== 6. 编辑/执行按钮提示改为单选操作 ==========
# edit_selected_task和run_selected_task已经是基于selected_task_id的单选，不需要改
# 但需要确保用户知道"编辑"和"执行"是针对点击选中的那个任务

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.2.4 patch完成！")
