#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加组内任务修改功能"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改表头，添加修改按钮说明
content = content.replace(
    'headers = [("优先级", 5), ("任务名称", 28), ("奖励", 14), ("窗口期", 6), ("账户", 12), ("操作(↑上移↓下移×删除)", 22)]',
    'headers = [("优先级", 5), ("任务名称", 28), ("奖励", 14), ("窗口期", 6), ("账户", 12), ("操作(↑↓✎×)", 22)]'
)

# 2. 在操作按钮中添加修改按钮（在×删除按钮之前）
old_buttons = '''            tk.Button(btn_frame, text="×", bg="#c0392b", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_remove_task(tid)).pack(side=tk.LEFT, padx=1)'''

new_buttons = '''            tk.Button(btn_frame, text="✎", bg="#3498db", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda t=task: self.nm_edit_task(t)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="×", bg="#c0392b", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_remove_task(tid)).pack(side=tk.LEFT, padx=1)'''

content = content.replace(old_buttons, new_buttons)

# 3. 在nm_remove_task方法之前添加nm_edit_task方法
old_remove_method = '    def nm_remove_task(self, task_id):'
new_edit_method = '''    def nm_edit_task(self, task):
        """编辑组内任务"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return

        # 创建编辑对话框
        edit_win = tk.Toplevel(self)
        edit_win.title(f"编辑任务 - {task.get('name', '')[:20]}")
        edit_win.geometry("420x280")
        edit_win.configure(bg=COLORS["bg_card"])
        edit_win.transient(self)
        edit_win.grab_set()

        # 任务信息显示
        info_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        info_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        tk.Label(info_frame, text="任务:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(anchor=tk.W)
        tk.Label(info_frame, text=task.get("name", ""), bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 10, "bold"), wraplength=380, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 5))
        tk.Label(info_frame, text=f"奖励: {task.get('award', '')}", bg=COLORS["bg_card"], fg=COLORS["success"],
                 font=("微软雅黑", 10)).pack(anchor=tk.W)

        # 编辑区域
        edit_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        edit_frame.pack(fill=tk.X, padx=15, pady=10)

        # 窗口期
        row1 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=5)
        tk.Label(row1, text="窗口期(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
        window_var = tk.StringVar(value=str(task.get("window_seconds", 15)))
        window_entry = tk.Entry(row1, textvariable=window_var, width=10, font=("微软雅黑", 10),
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"])
        window_entry.pack(side=tk.LEFT, padx=5)

        # 账户选择
        row2 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=5)
        tk.Label(row2, text="账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
        account_var = tk.StringVar(value=task.get("account_name", ""))
        # 获取所有账户
        account_names = []
        try:
            if hasattr(self, 'account_mgr') and self.account_mgr:
                accounts = self.account_mgr.get_all_accounts()
                account_names = [a.get("name", "") for a in accounts]
        except Exception:
            pass
        if not account_names:
            account_names = [task.get("account_name", "")]
        account_combo = ttk.Combobox(row2, textvariable=account_var, values=account_names,
                                     state="readonly", width=20, font=("微软雅黑", 10))
        account_combo.pack(side=tk.LEFT, padx=5)

        # 基础间隔
        row3 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=5)
        tk.Label(row3, text="基础间隔(ms):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
        interval_var = tk.StringVar(value=str(task.get("base_interval", 900)))
        interval_entry = tk.Entry(row3, textvariable=interval_var, width=10, font=("微软雅黑", 10),
                                  bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"])
        interval_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(row3, text="(风控后自动+20~40ms)", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)

        # 按钮区域
        btn_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=15, pady=15)

        def save_edit():
            """保存修改"""
            try:
                window_val = int(window_var.get())
                interval_val = int(interval_var.get())
            except ValueError:
                messagebox.showerror("错误", "窗口期和基础间隔必须是数字", parent=edit_win)
                return

            # 找到任务并更新
            for t in group.get("tasks", []):
                if t.get("task_id") == task.get("task_id"):
                    t["window_seconds"] = window_val
                    t["account_name"] = account_var.get()
                    t["base_interval"] = interval_val
                    # 同时更新account_id（如果能找到）
                    try:
                        if hasattr(self, 'account_mgr') and self.account_mgr:
                            accounts = self.account_mgr.get_all_accounts()
                            for a in accounts:
                                if a.get("name") == account_var.get():
                                    t["account_id"] = a.get("id", a.get("account_id", ""))
                                    break
                    except Exception:
                        pass
                    break

            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"[编辑] 任务「{task.get('name', '')}」已更新: 窗口期={window_val}秒, 账户={account_var.get()}, 间隔={interval_val}ms")
            edit_win.destroy()

        tk.Button(btn_frame, text="保存", bg=COLORS["success"], fg="#ffffff",
                  font=("微软雅黑", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  command=save_edit).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)
        tk.Button(btn_frame, text="取消", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                  font=("微软雅黑", 10), relief=tk.FLAT, cursor="hand2",
                  command=edit_win.destroy).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)

    def nm_remove_task(self, task_id):'''

content = content.replace(old_remove_method, new_edit_method)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("组内任务修改功能添加完成！")
print("1. 操作按钮中添加了✎修改按钮")
print("2. 点击后弹出编辑对话框，可修改窗口期、账户、基础间隔")
print("3. 保存后自动更新任务列表和配置文件")
