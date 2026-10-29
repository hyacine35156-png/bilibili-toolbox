#!/usr/bin/env python3
"""v4.5.1: 关机任务时间从关机页面读取，不在日程页面设置"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 修改_on_type_changed方法，关机类型时禁用时间输入框
# ============================================================
old_type_changed = '''        if task_type == "rush":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（添加后立即启动抢码任务列表，各任务按自身领取时间运行）",
                                         fg=COLORS["warning"])
        else:
            self.schedule_hour.config(state=tk.NORMAL)
            self.schedule_minute.config(state=tk.NORMAL)
            self.time_hint_label.config(text="（每天自动执行，使用各页面当前已设置的参数）",
                                         fg=COLORS["text_muted"])'''

new_type_changed = '''        if task_type == "rush":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（添加后立即启动抢码任务列表，各任务按自身领取时间运行）",
                                         fg=COLORS["warning"])
        elif task_type == "shutdown":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（关机时间在「定时关机」页面设置，此处无需填写）",
                                         fg=COLORS["warning"])
        else:
            self.schedule_hour.config(state=tk.NORMAL)
            self.schedule_minute.config(state=tk.NORMAL)
            self.time_hint_label.config(text="（每天自动执行，使用各页面当前已设置的参数）",
                                         fg=COLORS["text_muted"])'''

if old_type_changed in content:
    content = content.replace(old_type_changed, new_type_changed)
    print("1. 修改_on_type_changed，关机类型禁用时间输入框")
else:
    print("1. 未找到_on_type_changed代码")

# ============================================================
# 2. 修改add_schedule_task方法，关机类型时设置特殊标记
# ============================================================
old_add_task = '''        if task_type == "rush":
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
            time_str = f"{hour:02d}:{minute:02d}"'''

new_add_task = '''        if task_type == "rush":
            # 抢码不需要时间，添加后立即执行
            hour = -1
            minute = -1
            time_str = "立即执行"
        elif task_type == "shutdown":
            # 关机任务时间从关机页面读取，不在日程页面设置
            hour = -2
            minute = -2
            time_str = "关机页面设置"
        else:
            try:
                hour = int(self.schedule_hour.get().strip())
                minute = int(self.schedule_minute.get().strip())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）")
                return
            time_str = f"{hour:02d}:{minute:02d}"'''

if old_add_task in content:
    content = content.replace(old_add_task, new_add_task)
    print("2. 修改add_schedule_task，关机类型设置特殊标记")
else:
    print("2. 未找到add_schedule_task代码")

# ============================================================
# 3. 修改_scheduler_loop方法，关机任务动态读取关机页面时间
# ============================================================
old_scheduler_check = '''                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        # 抢码任务是立即执行的，不参与定时检查
                        if task["type"] == "rush" or task.get("hour", -1) == -1:
                            continue
                        task_minute = task["hour"] * 60 + task["minute"]'''

new_scheduler_check = '''                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        # 抢码任务是立即执行的，不参与定时检查
                        if task["type"] == "rush" or task.get("hour", -1) == -1:
                            continue
                        # 关机任务：动态从关机页面读取时间
                        if task["type"] == "shutdown" and task.get("hour", -1) == -2:
                            try:
                                if hasattr(self.app, 'shutdown_page') and self.app.shutdown_page:
                                    shutdown_hour = int(self.app.shutdown_page.shutdown_hour.get().strip())
                                    shutdown_minute = int(self.app.shutdown_page.shutdown_minute.get().strip())
                                    task_minute = shutdown_hour * 60 + shutdown_minute
                                else:
                                    continue
                            except (ValueError, AttributeError):
                                continue
                        else:
                            task_minute = task["hour"] * 60 + task["minute"]'''

if old_scheduler_check in content:
    content = content.replace(old_scheduler_check, new_scheduler_check)
    print("3. 修改_scheduler_loop，关机任务动态读取关机页面时间")
else:
    print("3. 未找到_scheduler_loop代码")

# ============================================================
# 4. 修改添加任务后的日志提示
# ============================================================
old_add_log = '''        if task_type == "rush":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，立即执行")
            # 抢码任务添加后立即执行
            self.after(100, lambda t=task: self.execute_task(t))
        else:
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天 {time_str} 执行")'''

new_add_log = '''        if task_type == "rush":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，立即执行")
            # 抢码任务添加后立即执行
            self.after(100, lambda t=task: self.execute_task(t))
        elif task_type == "shutdown":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天按关机页面设置的时间执行")
        else:
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天 {time_str} 执行")'''

if old_add_log in content:
    content = content.replace(old_add_log, new_add_log)
    print("4. 修改添加任务后的日志提示")
else:
    print("4. 未找到添加任务日志代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.0"', 'APP_VERSION = "v4.5.1"')
print("5. 版本号已更新到 v4.5.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
