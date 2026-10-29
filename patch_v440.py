#!/usr/bin/env python3
"""v4.4.0: 一键执行全部日程 + 不跳转 + 日志同步 + 抢码提前1分钟写日志"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 添加"一键执行全部"按钮（在批量删除后面）
# ============================================================
old_buttons = '''        DarkButton(row3, "🗑 批量删除", command=self.delete_selected_tasks,
                   width=100, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        # 调度器状态'''

new_buttons = '''        DarkButton(row3, "🗑 批量删除", command=self.delete_selected_tasks,
                   width=100, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "⚡ 全部执行", command=self.run_all_tasks,
                   width=100, height=32, bg_color="#e67e22", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        # 调度器状态'''

if old_buttons in content:
    content = content.replace(old_buttons, new_buttons)
    print("1. 已添加「⚡ 全部执行」按钮")
else:
    print("1. 未找到按钮区域代码")

# ============================================================
# 2. 添加 run_all_tasks 方法（在 run_selected_task 后面）
# ============================================================
old_run_selected = '''    def run_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要执行的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task:
            self.execute_task(task, manual=True)

    def execute_task(self, task, manual=False):'''

new_run_selected = '''    def run_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要执行的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task:
            self.execute_task(task, manual=True)

    def run_all_tasks(self):
        """一键执行全部已启用的日程任务"""
        enabled_tasks = [t for t in self.schedule_tasks if t["enabled"]]
        if not enabled_tasks:
            messagebox.showwarning("提示", "没有已启用的日程任务")
            return
        if not messagebox.askyesno("确认", f"确定立即执行全部 {len(enabled_tasks)} 个已启用的日程任务吗？"):
            return
        self.log(f"⚡ 一键执行全部 {len(enabled_tasks)} 个日程任务")
        for idx, task in enumerate(enabled_tasks):
            # 每个任务间隔500ms，避免同时启动冲突
            self.app.root.after(idx * 500, lambda t=task: self.execute_task(t, manual=True))

    def execute_task(self, task, manual=False):'''

if old_run_selected in content:
    content = content.replace(old_run_selected, new_run_selected)
    print("2. 已添加 run_all_tasks 方法")
else:
    print("2. 未找到 run_selected_task 代码")

# ============================================================
# 3. 日程页无需跳转：看播和弹幕任务不再 switch_tab
# ============================================================
old_execute = '''        try:
            if task["type"] == "watch":
                # 切换到看播页面并开始
                self.app.root.after(0, lambda: self.app.switch_tab("watch"))
                self.app.root.after(500, lambda: self._start_watch_safe(task))
            elif task["type"] == "danmaku":
                # 切换到弹幕页面并开始
                self.app.root.after(0, lambda: self.app.switch_tab("danmaku"))
                self.app.root.after(500, lambda: self._start_danmaku_safe(task))
            elif task["type"] == "rush":'''

new_execute = '''        try:
            if task["type"] == "watch":
                # 不跳转，直接后台启动看播
                self.app.root.after(100, lambda: self._start_watch_safe(task))
            elif task["type"] == "danmaku":
                # 不跳转，直接后台启动弹幕
                self.app.root.after(100, lambda: self._start_danmaku_safe(task))
            elif task["type"] == "rush":'''

if old_execute in content:
    content = content.replace(old_execute, new_execute)
    print("3. 看播/弹幕任务不再跳转页面")
else:
    print("3. 未找到 execute_task 中的跳转代码")

# ============================================================
# 4. 完善日志同步：添加 sync_log_to_all 方法
# ============================================================
old_log_method = '''    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\\n"
        self.schedule_log_text.config(state=tk.NORMAL)
        self.schedule_log_text.insert(tk.END, line)
        self.schedule_log_text.see(tk.END)
        self.schedule_log_text.config(state=tk.DISABLED)

    def _on_type_changed(self, *args):'''

new_log_method = '''    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\\n"
        self.schedule_log_text.config(state=tk.NORMAL)
        self.schedule_log_text.insert(tk.END, line)
        self.schedule_log_text.see(tk.END)
        self.schedule_log_text.config(state=tk.DISABLED)

    def sync_log_to_modules(self, msg):
        """将日志同步到所有相关模块页面"""
        try:
            # 同步到抢码页面
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
                self.app.rush_page.log(msg)
        except:
            pass
        try:
            # 同步到看播页面
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
                self.app.watch_page.log(msg)
        except:
            pass
        try:
            # 同步到弹幕页面（主页面日志）
            if hasattr(self.app, 'log'):
                self.app.log(msg)
        except:
            pass

    def _on_type_changed(self, *args):'''

if old_log_method in content:
    content = content.replace(old_log_method, new_log_method)
    print("4. 已添加 sync_log_to_modules 方法")
else:
    print("4. 未找到 log 方法代码")

# ============================================================
# 5. 在 execute_task 中使用 sync_log_to_modules 替代分散的日志同步
# ============================================================
old_log_sync = '''        prefix = "手动执行" if manual else "定时触发"
        msg = f"{'⚡' if manual else '⏰'} [日程] {prefix}任务「{task['name']}」({task['type_name']})"
        self.log(msg)
        # 同时写对应页面日志
        if task["type"] == "rush" and hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
            self.app.rush_page.log(msg)
        elif task["type"] == "watch" and hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
            self.app.watch_page.log(msg)
        elif task["type"] == "danmaku" and hasattr(self.app, 'log'):
            self.app.log(msg)'''

new_log_sync = '''        prefix = "手动执行" if manual else "定时触发"
        msg = f"{'⚡' if manual else '⏰'} [日程] {prefix}任务「{task['name']}」({task['type_name']})"
        self.log(msg)
        # 同步到所有相关模块页面
        self.sync_log_to_modules(msg)'''

if old_log_sync in content:
    content = content.replace(old_log_sync, new_log_sync)
    print("5. execute_task 日志同步已统一")
else:
    print("5. 未找到 execute_task 中的日志同步代码")

# ============================================================
# 6. 抢码任务提前1分钟写日志：修改调度器
# ============================================================
old_scheduler = '''    def _scheduler_loop(self):
        """调度器主循环：每秒检查一次，到点执行任务"""
        last_minute = -1
        while not self.scheduler_stop["stop"]:
            try:
                now = datetime.now()
                current_minute = now.hour * 60 + now.minute

                # 只在分钟变化时检查（避免同一分钟重复执行）
                if current_minute != last_minute:
                    last_minute = current_minute
                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        # 抢码任务是立即执行的，不参与定时检查
                        if task["type"] == "rush" or task.get("hour", -1) == -1:
                            continue
                        task_minute = task["hour"] * 60 + task["minute"]
                        if task_minute == current_minute:
                            # 到点执行
                            self.app.root.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.root.after(5000, lambda t=task: self._reset_task_status(t))

            except Exception as e:
                self.log(f"调度器异常: {e}")

            time.sleep(1)'''

new_scheduler = '''    def _scheduler_loop(self):
        """调度器主循环：每秒检查一次，到点执行任务"""
        last_minute = -1
        warned_tasks = set()  # 已提前1分钟写过日志的任务ID
        while not self.scheduler_stop["stop"]:
            try:
                now = datetime.now()
                current_minute = now.hour * 60 + now.minute

                # 只在分钟变化时检查（避免同一分钟重复执行）
                if current_minute != last_minute:
                    last_minute = current_minute
                    # 新的一分钟，清空已警告集合（用于第二天重复）
                    warned_tasks.clear()

                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        # 抢码任务是立即执行的，不参与定时检查
                        if task["type"] == "rush" or task.get("hour", -1) == -1:
                            continue
                        task_minute = task["hour"] * 60 + task["minute"]

                        # 抢码任务：提前1分钟写日志（如果不足1分钟则立即写）
                        if task["type"] == "rush":
                            time_diff = task_minute - current_minute
                            if time_diff <= 1 and task["id"] not in warned_tasks:
                                warned_tasks.add(task["id"])
                                warn_msg = f"⏳ [日程] 抢码任务「{task['name']}」将在 {task['time_str']} 执行，准备中..."
                                self.log(warn_msg)
                                self.sync_log_to_modules(warn_msg)

                        if task_minute == current_minute:
                            # 到点执行
                            self.app.root.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.root.after(5000, lambda t=task: self._reset_task_status(t))

            except Exception as e:
                self.log(f"调度器异常: {e}")

            time.sleep(1)'''

if old_scheduler in content:
    content = content.replace(old_scheduler, new_scheduler)
    print("6. 调度器已添加抢码任务提前1分钟写日志功能")
else:
    print("6. 未找到调度器循环代码")

# ============================================================
# 7. 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.3.6"', 'APP_VERSION = "v4.4.0"')
print("7. 版本号已更新到 v4.4.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
