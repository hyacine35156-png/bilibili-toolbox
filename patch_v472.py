#!/usr/bin/env python3
"""v4.7.2: 抢码账户改下拉框 + 表格固定像素宽度严格对齐"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 抢码账户从Listbox改成Combobox下拉框
# ============================================================
old_account = '''        # 第二行：账户选择
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="抢码账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        self.rush_account_list = tk.Listbox(row2, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                             selectbackground=COLORS["accent"], selectforeground="#000000",
                                             font=("微软雅黑", 10), bd=0, highlightthickness=0,
                                             height=3, exportselection=False, selectmode=tk.EXTENDED)
        self.rush_account_list.pack(side=tk.LEFT, padx=(15, 0), fill=tk.X, expand=True)'''

new_account = '''        # 第二行：账户选择（下拉框）
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="抢码账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        self.rush_account_var = tk.StringVar()
        self.rush_account_combo = ttk.Combobox(row2, textvariable=self.rush_account_var,
                                                 values=[], state="readonly",
                                                 font=("微软雅黑", 10), width=25)
        self.rush_account_combo.pack(side=tk.LEFT, padx=(15, 0))'''

if old_account in content:
    content = content.replace(old_account, new_account)
    print("1. 抢码账户已从Listbox改成Combobox下拉框")
else:
    print("1. 未找到抢码账户代码")

# ============================================================
# 2. 修改refresh_account_list方法，更新Combobox选项
# ============================================================
old_refresh = '''    def refresh_account_list(self):
        self.rush_account_list.delete(0, tk.END)
        default_index = -1
        for i, acc in enumerate(self.account_mgr.accounts):
            display = f"  {acc['name']}"
            self.rush_account_list.insert(tk.END, display)
            if acc["name"] == "灵砂是无敌的":
                default_index = i
        # 默认选中"灵砂是无敌的"账户
        if default_index >= 0:
            self.rush_account_list.selection_set(default_index)
            self.rush_account_list.see(default_index)'''

new_refresh = '''    def refresh_account_list(self):
        account_names = [acc["name"] for acc in self.account_mgr.accounts]
        self.rush_account_combo["values"] = account_names
        # 默认选中"灵砂是无敌的"账户，否则选第一个
        default_name = "灵砂是无敌的"
        if default_name in account_names:
            self.rush_account_var.set(default_name)
        elif account_names:
            self.rush_account_var.set(account_names[0])'''

if old_refresh in content:
    content = content.replace(old_refresh, new_refresh)
    print("2. refresh_account_list方法已更新为Combobox模式")
else:
    print("2. 未找到refresh_account_list方法")

# ============================================================
# 3. 修改get_selected_accounts方法，从Combobox获取选中账户
# ============================================================
old_get_selected = '''    def get_selected_accounts(self):
        selection = self.rush_account_list.curselection()
        if not selection:
            return []
        return [self.account_mgr.accounts[i] for i in selection]'''

new_get_selected = '''    def get_selected_accounts(self):
        selected_name = self.rush_account_var.get()
        if not selected_name:
            return []
        for acc in self.account_mgr.accounts:
            if acc["name"] == selected_name:
                return [acc]
        return []'''

if old_get_selected in content:
    content = content.replace(old_get_selected, new_get_selected)
    print("3. get_selected_accounts方法已更新为Combobox模式")
else:
    print("3. 未找到get_selected_accounts方法")

# ============================================================
# 4. 表格表头：用固定像素宽度的Frame容器，严格对齐
# ============================================================
old_header = '''        header_frame = tk.Frame(list_frame, bg=COLORS["bg_input"])
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=38, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0), pady=6)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=14, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=22, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''

new_header = '''        header_frame = tk.Frame(list_frame, bg=COLORS["bg_input"])
        header_frame.pack(fill=tk.X)
        # 用固定像素宽度的Frame容器，确保表头和数据行严格对齐
        col_widths = [340, 110, 170, 150, 80, 200]
        col_names = ["任务名称", "领取时间", "时长/间隔", "账户", "状态", "操作"]
        for i, (name, w) in enumerate(zip(col_names, col_widths)):
            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=32)
            col_frame.pack(side=tk.LEFT, padx=(8 if i == 0 else 4, 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=6)'''

if old_header in content:
    content = content.replace(old_header, new_header)
    print("4. 表格表头已改为固定像素宽度Frame容器")
else:
    print("4. 未找到表头代码")

# ============================================================
# 5. 表格数据行：用固定像素宽度的Frame容器，严格对齐
# ============================================================
old_data_row = '''            # 任务名称
            name_text = task.get("task_name", "未知任务")[:36]
            tk.Label(row_frame, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), width=38, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0), pady=6)

            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            tk.Label(row_frame, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), width=14, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            tk.Label(row_frame, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:12] if accounts else "未设置"
            tk.Label(row_frame, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            tk.Label(row_frame, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))

            # 操作按钮
            btn_frame = tk.Frame(row_frame, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=(12, 0))'''

new_data_row = '''            # 用固定像素宽度的Frame容器，确保和表头严格对齐
            col_widths = [340, 110, 170, 150, 80, 200]

            # 任务名称
            name_text = task.get("task_name", "未知任务")[:30]
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=36)
            col1.pack(side=tk.LEFT, padx=(8, 0))
            col1.pack_propagate(False)
            tk.Label(col1, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=8)

            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=36)
            col2.pack(side=tk.LEFT, padx=(4, 0))
            col2.pack_propagate(False)
            tk.Label(col2, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=8)

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=36)
            col3.pack(side=tk.LEFT, padx=(4, 0))
            col3.pack_propagate(False)
            tk.Label(col3, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=8)

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:10] if accounts else "未设置"
            col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=36)
            col4.pack(side=tk.LEFT, padx=(4, 0))
            col4.pack_propagate(False)
            tk.Label(col4, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=8)

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=36)
            col5.pack(side=tk.LEFT, padx=(4, 0))
            col5.pack_propagate(False)
            tk.Label(col5, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=8)

            # 操作按钮
            col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=36)
            col6.pack(side=tk.LEFT, padx=(4, 0))
            col6.pack_propagate(False)
            btn_frame = tk.Frame(col6, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=4, pady=2)'''

if old_data_row in content:
    content = content.replace(old_data_row, new_data_row)
    print("5. 表格数据行已改为固定像素宽度Frame容器")
else:
    print("5. 未找到数据行代码")

# ============================================================
# 6. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.7.1"', 'APP_VERSION = "v4.7.2"')
print("6. 版本号: v4.7.1 -> v4.7.2")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
