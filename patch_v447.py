#!/usr/bin/env python3
"""v4.4.7: 定时时间从输入框改成下拉选择框"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 把定时时间的三个输入框改成下拉选择框
# ============================================================
old_time_inputs = '''        self.schedule_hour_entry = DarkEntry(row5, width=4)
        self.schedule_hour_entry.insert(0, "00")
        self.schedule_hour_entry.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="时", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.schedule_minute_entry = DarkEntry(row5, width=4)
        self.schedule_minute_entry.insert(0, "59")
        self.schedule_minute_entry.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="分", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.schedule_second_entry = DarkEntry(row5, width=4)
        self.schedule_second_entry.insert(0, "54")
        self.schedule_second_entry.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)'''

new_time_inputs = '''        # 时：00-23
        hour_values = [f"{h:02d}" for h in range(24)]
        self.schedule_hour_var = tk.StringVar(value="00")
        self.schedule_hour_combo = ttk.Combobox(row5, textvariable=self.schedule_hour_var,
                                                   values=hour_values, state="readonly", width=4,
                                                   font=("微软雅黑", 9))
        self.schedule_hour_combo.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="时", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        # 分：00-59
        minute_values = [f"{m:02d}" for m in range(60)]
        self.schedule_minute_var = tk.StringVar(value="59")
        self.schedule_minute_combo = ttk.Combobox(row5, textvariable=self.schedule_minute_var,
                                                     values=minute_values, state="readonly", width=4,
                                                     font=("微软雅黑", 9))
        self.schedule_minute_combo.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="分", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        # 秒：00-59
        second_values = [f"{s:02d}" for s in range(60)]
        self.schedule_second_var = tk.StringVar(value="54")
        self.schedule_second_combo = ttk.Combobox(row5, textvariable=self.schedule_second_var,
                                                     values=second_values, state="readonly", width=4,
                                                     font=("微软雅黑", 9))
        self.schedule_second_combo.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)'''

if old_time_inputs in content:
    content = content.replace(old_time_inputs, new_time_inputs)
    print("1. 定时时间输入框改成下拉选择框")
else:
    print("1. 未找到定时时间输入框代码")

# ============================================================
# 修改获取定时时间的代码，从entry.get()改成var.get()
# ============================================================
old_get_time = '''        try:
            h = int(self.schedule_hour_entry.get().strip())
            m = int(self.schedule_minute_entry.get().strip())
            s = int(self.schedule_second_entry.get().strip())
            if h < 0 or h > 23 or m < 0 or m > 59 or s < 0 or s > 59:
                raise ValueError
            target_seconds = h * 3600 + m * 60 + s
        except ValueError:
            messagebox.showwarning("提示", "定时时间格式错误，时(0-23) 分(0-59) 秒(0-59)")
            return'''

new_get_time = '''        try:
            h = int(self.schedule_hour_var.get().strip())
            m = int(self.schedule_minute_var.get().strip())
            s = int(self.schedule_second_var.get().strip())
            if h < 0 or h > 23 or m < 0 or m > 59 or s < 0 or s > 59:
                raise ValueError
            target_seconds = h * 3600 + m * 60 + s
        except ValueError:
            messagebox.showwarning("提示", "定时时间格式错误，时(0-23) 分(0-59) 秒(0-59)")
            return'''

if old_get_time in content:
    content = content.replace(old_get_time, new_get_time)
    print("2. 修改获取定时时间的代码")
else:
    print("2. 未找到获取定时时间的代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.6"', 'APP_VERSION = "v4.4.7"')
print("3. 版本号已更新到 v4.4.7")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
