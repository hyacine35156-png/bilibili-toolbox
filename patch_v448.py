#!/usr/bin/env python3
"""v4.4.8: 修复v4.4.7下拉框改造后残留的旧属性引用"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. save_rush_config方法中获取值（第947-949行）
# ============================================================
old_save = '''            self.rush_config["schedule_hour"] = self.schedule_hour_entry.get().strip()
            self.rush_config["schedule_minute"] = self.schedule_minute_entry.get().strip()
            self.rush_config["schedule_second"] = self.schedule_second_entry.get().strip()'''

new_save = '''            self.rush_config["schedule_hour"] = self.schedule_hour_var.get().strip()
            self.rush_config["schedule_minute"] = self.schedule_minute_var.get().strip()
            self.rush_config["schedule_second"] = self.schedule_second_var.get().strip()'''

if old_save in content:
    content = content.replace(old_save, new_save)
    print("1. 修复save_rush_config中的旧属性引用")
else:
    print("1. 未找到save_rush_config代码")

# ============================================================
# 2. load_rush_config方法中设置值（第1038-1045行）
# ============================================================
old_load = '''                self.schedule_hour_entry.delete(0, tk.END)
                self.schedule_hour_entry.insert(0, self.rush_config["schedule_hour"])
            except (KeyError, ValueError):
                pass
            try:
                self.schedule_minute_entry.delete(0, tk.END)
                self.schedule_minute_entry.insert(0, self.rush_config["schedule_minute"])
            except (KeyError, ValueError):
                pass
            try:
                self.schedule_second_entry.delete(0, tk.END)
                self.schedule_second_entry.insert(0, self.rush_config["schedule_second"])'''

new_load = '''                self.schedule_hour_var.set(self.rush_config["schedule_hour"])
            except (KeyError, ValueError):
                pass
            try:
                self.schedule_minute_var.set(self.rush_config["schedule_minute"])
            except (KeyError, ValueError):
                pass
            try:
                self.schedule_second_var.set(self.rush_config["schedule_second"])'''

if old_load in content:
    content = content.replace(old_load, new_load)
    print("2. 修复load_rush_config中的旧属性引用")
else:
    print("2. 未找到load_rush_config代码")

# ============================================================
# 3. bind_auto_save方法中绑定事件（第1079-1081行）
# ============================================================
old_bind = '''        self.schedule_hour_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.schedule_minute_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.schedule_second_entry.bind("<FocusOut>", lambda e: self.save_rush_config())'''

new_bind = '''        self.schedule_hour_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())
        self.schedule_minute_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())
        self.schedule_second_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())'''

if old_bind in content:
    content = content.replace(old_bind, new_bind)
    print("3. 修复bind_auto_save中的旧属性引用")
else:
    print("3. 未找到bind_auto_save代码")

# ============================================================
# 4. 另一个获取定时时间的地方（第1456-1458行）
# ============================================================
old_get = '''            h = int(self.schedule_hour_entry.get().strip())
            m = int(self.schedule_minute_entry.get().strip())
            s = int(self.schedule_second_entry.get().strip())'''

new_get = '''            h = int(self.schedule_hour_var.get().strip())
            m = int(self.schedule_minute_var.get().strip())
            s = int(self.schedule_second_var.get().strip())'''

if old_get in content:
    content = content.replace(old_get, new_get)
    print("4. 修复另一处获取定时时间的旧属性引用")
else:
    print("4. 未找到另一处获取定时时间的代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.7"', 'APP_VERSION = "v4.4.8"')
print("5. 版本号已更新到 v4.4.8")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
