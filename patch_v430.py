#!/usr/bin/env python3
"""v4.3.0: 去掉复选框，直接用启用/取消按钮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 去掉"选"复选框，改成简洁的启用/取消按钮 ==========
old_checkbox_and_button = '''            # 选择复选框（多选，用于批量删除）
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

            # 启动/取消日程按钮
            if task["enabled"]:
                btn_text = "取消日程"
                btn_bg = COLORS["warning"]
                def toggle_task(t=task):
                    t["enabled"] = False
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"⏸ 已取消日程「{t['name']}」")
            else:
                btn_text = "启动日程"
                btn_bg = COLORS["success"]
                def toggle_task(t=task):
                    t["enabled"] = True
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"✅ 已启动日程「{t['name']}」")
            toggle_btn = DarkButton(row_frame, btn_text, command=toggle_task,
                                     width=65, height=22, bg_color=btn_bg, text_color="#ffffff")
            toggle_btn.pack(side=tk.LEFT, padx=(4, 4), pady=6)'''

new_button_only = '''            # 启用/取消按钮（简洁版）
            if task["enabled"]:
                btn_text = "取消"
                btn_bg = COLORS["warning"]
                def toggle_task(t=task):
                    t["enabled"] = False
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"⏸ 已取消日程「{t['name']}」")
            else:
                btn_text = "启用"
                btn_bg = COLORS["success"]
                def toggle_task(t=task):
                    t["enabled"] = True
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"✅ 已启用日程「{t['name']}」")
            toggle_btn = DarkButton(row_frame, btn_text, command=toggle_task,
                                     width=45, height=22, bg_color=btn_bg, text_color="#ffffff")
            toggle_btn.pack(side=tk.LEFT, padx=(6, 4), pady=6)'''

content = content.replace(old_checkbox_and_button, new_button_only)
print("1. 去掉复选框，改成启用/取消按钮")

# ========== 去掉全选/批量删除按钮（因为没有多选框了） ==========
old_select_buttons = '''        DarkButton(row3, "☑ 全选", command=self.toggle_select_all,
                   width=55, height=26, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT, padx=(0, 6))
        DarkButton(row3, "🗑 批量删除", command=self.delete_selected_tasks,
                   width=75, height=26, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 6))'''

new_no_select_buttons = '''        DarkButton(row3, "🗑 删除选中", command=self.delete_selected_task,
                   width=75, height=26, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 6))'''

content = content.replace(old_select_buttons, new_no_select_buttons)
print("2. 全选/批量删除改成删除选中")

# ========== 添加delete_selected_task方法（删除当前选中的单个任务） ==========
old_delete_selected = '''    def delete_selected_tasks(self):
        """批量删除选中的任务"""
        if not self.selected_ids:
            messagebox.showwarning("提示", "请先勾选要删除的任务", parent=self.app.root)
            return
        count = len(self.selected_ids)
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {count} 个任务吗？", parent=self.app.root):
            return
        self.tasks = [t for t in self.tasks if t["id"] not in self.selected_ids]
        self.selected_ids.clear()
        self.selected_task_id = None
        self.refresh_task_list()
        self.save_schedule()
        self.log(f"🗑 已批量删除 {count} 个任务")'''

new_delete_single = '''    def delete_selected_task(self):
        """删除当前选中的任务"""
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先点击选中要删除的任务", parent=self.app.root)
            return
        task = next((t for t in self.tasks if t["id"] == self.selected_task_id), None)
        if not task:
            return
        if not messagebox.askyesno("确认删除", f"确定要删除任务「{task['name']}」吗？", parent=self.app.root):
            return
        self.tasks = [t for t in self.tasks if t["id"] != self.selected_task_id]
        self.selected_task_id = None
        self.refresh_task_list()
        self.save_schedule()
        self.log(f"🗑 已删除任务「{task['name']}」")'''

content = content.replace(old_delete_selected, new_delete_single)
print("3. 添加删除单个任务方法")

# ========== 列表提示文字更新 ==========
old_list_hint = '''        tk.Label(list_header, text="（勾选「选」可批量删除；点「启动/取消」控制是否执行；双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

new_list_hint = '''        tk.Label(list_header, text="（点击选中，双击编辑；点「启用/取消」控制是否执行）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

content = content.replace(old_list_hint, new_list_hint)
print("4. 列表提示文字更新")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.3.0 patch完成！")
