#!/usr/bin/env python3
"""v4.4.4: 修复抢码日志刷屏 + 弹幕/看播任务状态 + 日志同步"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 抢码监控日志：只在子任务数量变化时写日志
# ============================================================
old_monitor = '''    def _monitor_rush_completion(self, task):
        """监控抢码子任务，等所有子任务结束后标记日程任务完成"""
        def monitor_loop():
            max_wait = 7200  # 最多等2小时
            waited = 0
            check_interval = 5  # 每5秒检查一次
            while waited < max_wait:
                try:
                    if not hasattr(self.app, 'rush_page') or not hasattr(self.app.rush_page, 'scheduled_tasks'):
                        break
                    rush_tasks = self.app.rush_page.scheduled_tasks
                    if not rush_tasks:
                        break
                    # 检查是否还有运行中或等待中的子任务
                    running = [t for t in rush_tasks if t.get("status") in ["运行中", "等待中"]]
                    if not running:
                        # 所有子任务都结束了
                        self.app.root.after(0, lambda: self._mark_rush_done(task))
                        return
                    # 还有子任务在运行，继续等
                    running_names = [t.get("task_name", "?") for t in running]
                    self.log(f"⏳ 抢码任务「{task['name']}」等待中，还有 {len(running)} 个子任务运行中: {', '.join(running_names[:3])}")
                except Exception as e:
                    self.log(f"⚠ 抢码监控异常: {e}")
                time.sleep(check_interval)
                waited += check_interval
            # 超时，标记完成
            self.app.root.after(0, lambda: self._mark_rush_done(task, timeout=True))

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()'''

new_monitor = '''    def _monitor_rush_completion(self, task):
        """监控抢码子任务，等所有子任务结束后标记日程任务完成"""
        def monitor_loop():
            max_wait = 7200  # 最多等2小时
            waited = 0
            check_interval = 5  # 每5秒检查一次
            last_running_count = -1  # 记录上次的运行中数量，只在变化时写日志
            while waited < max_wait:
                try:
                    if not hasattr(self.app, 'rush_page') or not hasattr(self.app.rush_page, 'scheduled_tasks'):
                        break
                    rush_tasks = self.app.rush_page.scheduled_tasks
                    if not rush_tasks:
                        break
                    # 检查是否还有运行中或等待中的子任务
                    running = [t for t in rush_tasks if t.get("status") in ["运行中", "等待中"]]
                    if not running:
                        # 所有子任务都结束了
                        self.app.root.after(0, lambda: self._mark_rush_done(task))
                        return
                    # 只有在数量变化时才写日志，避免刷屏
                    if len(running) != last_running_count:
                        running_names = [t.get("task_name", "?") for t in running]
                        self.log(f"⏳ 抢码任务「{task['name']}」等待中，还有 {len(running)} 个子任务运行中: {', '.join(running_names[:3])}")
                        last_running_count = len(running)
                except Exception as e:
                    self.log(f"⚠ 抢码监控异常: {e}")
                time.sleep(check_interval)
                waited += check_interval
            # 超时，标记完成
            self.app.root.after(0, lambda: self._mark_rush_done(task, timeout=True))

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()'''

if old_monitor in content:
    content = content.replace(old_monitor, new_monitor)
    print("1. 抢码监控日志改为只在数量变化时写")
else:
    print("1. 未找到抢码监控代码")

# ============================================================
# 2. 弹幕和看播任务：不自动标记完成，添加监控线程
# ============================================================
old_execute = '''            # 标记完成（抢码任务由监控线程处理，其他任务2秒后标记）
            if task["type"] != "rush":
                self.app.root.after(2000, lambda: self._mark_task_done(task))'''

new_execute = '''            # 标记完成：
            # - 抢码任务由监控线程处理
            # - 关机任务立即标记
            # - 弹幕和看播任务启动监控线程，等任务实际停止后标记
            if task["type"] == "shutdown":
                self.app.root.after(2000, lambda: self._mark_task_done(task))
            elif task["type"] in ["danmaku", "watch"]:
                self.app.root.after(3000, lambda: self._monitor_long_task(task))'''

if old_execute in content:
    content = content.replace(old_execute, new_execute)
    print("2. 弹幕/看播任务改为监控实际停止状态")
else:
    print("2. 未找到标记完成代码")

# ============================================================
# 3. 添加长任务监控方法（在_mark_task_done之前插入）
# ============================================================
old_mark_done = '''    def _mark_task_done(self, task):
        task["status"] = "已结束"
        self.refresh_task_list()
        self.save_schedule()'''

new_mark_done = '''    def _monitor_long_task(self, task):
        """监控弹幕/看播等长时间运行任务，等任务实际停止后标记完成"""
        def monitor_loop():
            max_wait = 86400  # 最多等24小时
            waited = 0
            check_interval = 10  # 每10秒检查一次
            task_type = task["type"]
            while waited < max_wait:
                try:
                    is_running = False
                    if task_type == "danmaku":
                        # 检查弹幕发送状态
                        if hasattr(self.app, 'running'):
                            is_running = self.app.running
                    elif task_type == "watch":
                        # 检查看播状态
                        if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'running'):
                            is_running = self.app.watch_page.running
                    
                    if not is_running:
                        # 任务已停止，标记完成
                        msg = f"✓ [日程] {task['type_name']}任务「{task['name']}」已完成"
                        self.app.root.after(0, lambda: self._mark_task_done_with_log(task, msg))
                        return
                except Exception as e:
                    pass  # 监控异常不影响任务
                time.sleep(check_interval)
                waited += check_interval
            # 超时，标记完成
            self.app.root.after(0, lambda: self._mark_task_done(task))

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def _mark_task_done_with_log(self, task, msg):
        """标记任务完成并写日志"""
        task["status"] = "已结束"
        self.log(msg)
        self.sync_log_to_modules(msg)
        self.refresh_task_list()
        self.save_schedule()

    def _mark_task_done(self, task):
        task["status"] = "已结束"
        self.refresh_task_list()
        self.save_schedule()'''

if old_mark_done in content:
    content = content.replace(old_mark_done, new_mark_done)
    print("3. 添加长任务监控方法")
else:
    print("3. 未找到_mark_task_done方法")

# ============================================================
# 4. 弹幕/看播启动日志同步到调度器（在_start_watch_safe和_start_danmaku_safe中添加sync_log_to_modules）
# ============================================================
old_watch_safe = '''    def _start_watch_safe(self, task):
        try:
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'start_watch'):
                self.app.watch_page.start_watch()
                msg = f"✓ [日程] 看播任务「{task['name']}」已启动"
                self.log(msg)
                # 同时写看播页面日志
                if hasattr(self.app.watch_page, 'log'):
                    self.app.watch_page.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动看播失败: {e}"
            self.log(msg)
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
                self.app.watch_page.log(msg)'''

new_watch_safe = '''    def _start_watch_safe(self, task):
        try:
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'start_watch'):
                self.app.watch_page.start_watch()
                msg = f"✓ [日程] 看播任务「{task['name']}」已启动"
                self.log(msg)
                self.sync_log_to_modules(msg)
                # 同时写看播页面日志
                if hasattr(self.app.watch_page, 'log'):
                    self.app.watch_page.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动看播失败: {e}"
            self.log(msg)
            self.sync_log_to_modules(msg)
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
                self.app.watch_page.log(msg)'''

if old_watch_safe in content:
    content = content.replace(old_watch_safe, new_watch_safe)
    print("4. 看播启动日志添加同步")
else:
    print("4. 未找到_start_watch_safe方法")

old_danmaku_safe = '''    def _start_danmaku_safe(self, task):
        try:
            if hasattr(self.app, 'start_sending'):
                self.app.start_sending()
                msg = f"✓ [日程] 弹幕任务「{task['name']}」已启动"
                self.log(msg)
                # 同时写主页面日志（弹幕工具的日志）
                if hasattr(self.app, 'log'):
                    self.app.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动弹幕失败: {e}"
            self.log(msg)
            if hasattr(self.app, 'log'):
                self.app.log(msg)'''

new_danmaku_safe = '''    def _start_danmaku_safe(self, task):
        try:
            if hasattr(self.app, 'start_sending'):
                self.app.start_sending()
                msg = f"✓ [日程] 弹幕任务「{task['name']}」已启动"
                self.log(msg)
                self.sync_log_to_modules(msg)
                # 同时写主页面日志（弹幕工具的日志）
                if hasattr(self.app, 'log'):
                    self.app.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动弹幕失败: {e}"
            self.log(msg)
            self.sync_log_to_modules(msg)
            if hasattr(self.app, 'log'):
                self.app.log(msg)'''

if old_danmaku_safe in content:
    content = content.replace(old_danmaku_safe, new_danmaku_safe)
    print("5. 弹幕启动日志添加同步")
else:
    print("5. 未找到_start_danmaku_safe方法")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.3"', 'APP_VERSION = "v4.4.4"')
print("6. 版本号已更新到 v4.4.4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
