#!/usr/bin/env python3
"""v4.3.1: 恢复全选+批量删除，同时保留启用/取消按钮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 在启用/取消按钮前面加回多选复选框 ==========
old_button_only = '''            # 启用/取消按钮
            if task["enabled"]:'''

new_with_checkbox = '''            # 多选复选框（用于批量删除）
            is_checked = (task["id"] in self.selected_ids)
            check_var = tk.BooleanVar(value=is_checked)
            def toggle_check(var=check_var, tid=task["id"]):
                if var.get():
                    self.selected_ids.add(tid)
                else:
                    self.selected_ids.discard(tid)
            check_chk = tk.Checkbutton(row_frame, text="选", variable=check_var, command=toggle_check,
                                        bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"],
                                        fg=text_color, font=("微软雅黑", 8))
            check_chk.pack(side=tk.LEFT, padx=(4, 2), pady=8)
            check_chk.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 启用/取消按钮
            if task["enabled"]:'''

content = content.replace(old_button_only, new_with_checkbox)
print("1. 加回多选复选框")

# ========== 2. 按钮区域恢复全选+批量删除 ==========
old_delete_only = '''        DarkButton(row3, "🗑 删除选中", command=self.delete_selected_task,
                   width=100, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))'''

new_with_select_all = '''        DarkButton(row3, "☑ 全选", command=self.toggle_select_all,
                   width=70, height=32, bg_color="#9b59b6", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "🗑 批量删除", command=self.delete_selected_tasks,
                   width=100, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))'''

content = content.replace(old_delete_only, new_with_select_all)
print("2. 恢复全选+批量删除按钮")

# ========== 3. 恢复toggle_select_all和delete_selected_tasks方法 ==========
old_delete_single = '''    def delete_selected_task(self):
        """删除当前选中的任务"""'''

new_methods = '''    def toggle_select_all(self):
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
        names = [t["name"] for t in self.schedule_tasks if t["id"] in self.selected_ids]
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {count} 个任务吗？", parent=self.app.root):
            return
        self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] not in self.selected_ids]
        self.selected_ids.clear()
        self.selected_task_id = None
        self.refresh_task_list()
        self.save_schedule()
        self.log(f"🗑 已批量删除 {count} 个任务: {', '.join(names)}")

    def delete_selected_task(self):
        """删除当前选中的任务"""'''

content = content.replace(old_delete_single, new_methods)
print("3. 恢复全选+批量删除方法")

# ========== 4. 列表提示文字更新 ==========
old_hint = '''        tk.Label(list_header, text="（点击选中，双击编辑；点「启用/取消」控制是否执行）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

new_hint = '''        tk.Label(list_header, text="（勾选「选」可批量删除；点「启用/取消」控制是否执行；双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

content = content.replace(old_hint, new_hint)
print("4. 提示文字更新")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.3.1 patch完成！")
