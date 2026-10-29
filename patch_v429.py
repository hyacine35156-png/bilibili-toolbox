#!/usr/bin/env python3
"""v4.2.9: 启用/禁用复选框改成启动/取消日程按钮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 把启用/禁用复选框改成按钮 ==========
old_enabled_checkbox = '''            # 启用/禁用复选框（控制是否参与定时执行）
            enabled_var = tk.BooleanVar(value=task["enabled"])
            def toggle_enabled(var=enabled_var, t=task):
                t["enabled"] = var.get()
                self.save_schedule()
                self.refresh_task_list()
                self.log(f"{'✅ 启用' if var.get() else '⏸ 禁用'}任务「{t['name']}」")
            chk = tk.Checkbutton(row_frame, text="用", variable=enabled_var, command=toggle_enabled,
                                 bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"],
                                 fg=text_color, font=("微软雅黑", 8))
            chk.pack(side=tk.LEFT, padx=(2, 4), pady=8)
            chk.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))'''

new_enabled_button = '''            # 启动/取消日程按钮
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

content = content.replace(old_enabled_checkbox, new_enabled_button)
print("1. 启用/禁用复选框改成启动/取消按钮")

# ========== 状态显示：已禁用的任务显示"已取消" ==========
old_status_display = '''            # 状态
            status_text = task.get("status", "等待中")
            if status_text == "执行中":
                status_fg = COLORS["danger"]
            elif status_text in ["已完成", "已结束"]:
                status_fg = COLORS["success"]
            elif "已结束" in status_text:
                status_fg = COLORS["success"]
            elif status_text == "失败":
                status_fg = COLORS["warning"]
            else:
                status_fg = COLORS["text_muted"]'''

new_status_display = '''            # 状态
            if not task["enabled"]:
                status_text = "已取消"
                status_fg = COLORS["text_muted"]
            else:
                status_text = task.get("status", "等待中")
                if status_text == "执行中":
                    status_fg = COLORS["danger"]
                elif status_text in ["已完成", "已结束"]:
                    status_fg = COLORS["success"]
                elif "已结束" in status_text:
                    status_fg = COLORS["success"]
                elif status_text == "失败":
                    status_fg = COLORS["warning"]
                else:
                    status_fg = COLORS["text_muted"]'''

content = content.replace(old_status_display, new_status_display)
print("2. 已禁用任务状态显示已取消")

# ========== 列表提示文字更新 ==========
old_list_hint = '''        tk.Label(list_header, text="（勾选左侧框可多选批量删除；点击选中，双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

new_list_hint = '''        tk.Label(list_header, text="（勾选「选」可批量删除；点「启动/取消」控制是否执行；双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))'''

content = content.replace(old_list_hint, new_list_hint)
print("3. 列表提示文字更新")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.2.9 patch完成！")
