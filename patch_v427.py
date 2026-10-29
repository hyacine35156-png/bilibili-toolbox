#!/usr/bin/env python3
"""v4.2.7: 1.抢码等最后子任务结束 2.抢码放选择框第一个"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 类型选择框抢码放第一个 ==========
old_type_radio = '''        ttk.Radiobutton(row1, text="📺 看播", variable=self.task_type_var, value="watch",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="💬 弹幕", variable=self.task_type_var, value="danmaku",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⚡ 抢码", variable=self.task_type_var, value="rush",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⏻ 关机", variable=self.task_type_var, value="shutdown",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)'''

new_type_radio = '''        ttk.Radiobutton(row1, text="⚡ 抢码", variable=self.task_type_var, value="rush",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="📺 看播", variable=self.task_type_var, value="watch",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="💬 弹幕", variable=self.task_type_var, value="danmaku",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⏻ 关机", variable=self.task_type_var, value="shutdown",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)'''

content = content.replace(old_type_radio, new_type_radio)
print("1. 类型选择框抢码放第一个")

# ========== 2. 默认类型改为rush ==========
old_default_type = '''        self.task_type_var = tk.StringVar(value="watch")'''
new_default_type = '''        self.task_type_var = tk.StringVar(value="rush")'''
content = content.replace(old_default_type, new_default_type)
print("2. 默认类型改为抢码")

# ========== 3. 抢码任务不立即标记已结束，改为监控子任务 ==========
# 修改execute_task中抢码部分：不调用_mark_task_done，而是调用_monitor_rush_tasks
old_rush_exec = '''            elif task["type"] == "rush":
                # 抢码任务不跳转，直接后台执行
                self.app.root.after(100, lambda: self._start_rush_safe(task))'''

new_rush_exec = '''            elif task["type"] == "rush":
                # 抢码任务不跳转，直接后台执行，等所有子任务结束才标记完成
                self.app.root.after(100, lambda: self._start_rush_safe(task))
                self.app.root.after(3000, lambda: self._monitor_rush_completion(task))'''

content = content.replace(old_rush_exec, new_rush_exec)
print("3. 抢码任务添加完成监控")

# ========== 4. 修改_mark_task_done：抢码任务不在这里标记（由监控线程处理） ==========
old_mark_done = '''            # 标记完成（实际执行在页面线程中进行）
            self.app.root.after(2000, lambda: self._mark_task_done(task))'''

new_mark_done = '''            # 标记完成（抢码任务由监控线程处理，其他任务2秒后标记）
            if task["type"] != "rush":
                self.app.root.after(2000, lambda: self._mark_task_done(task))'''

content = content.replace(old_mark_done, new_mark_done)
print("4. 抢码任务跳过自动标记完成")

# ========== 5. 添加_monitor_rush_completion方法 ==========
old_mark_done_def = '''    def _mark_task_done(self, task):
        task["status"] = "已结束"
        self.refresh_task_list()
        self.save_schedule()'''

new_monitor_method = '''    def _monitor_rush_completion(self, task):
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
        monitor_thread.start()

    def _mark_rush_done(self, task, timeout=False):
        """标记抢码任务完成"""
        if timeout:
            task["status"] = "已结束(超时)"
            self.log(f"⏰ 抢码任务「{task['name']}」监控超时(2小时)，标记为已结束")
        else:
            task["status"] = "已结束"
            self.log(f"✓ 抢码任务「{task['name']}」所有子任务已完成")
        self.refresh_task_list()
        self.save_schedule()

    def _mark_task_done(self, task):
        task["status"] = "已结束"
        self.refresh_task_list()
        self.save_schedule()'''

content = content.replace(old_mark_done_def, new_monitor_method)
print("5. 添加抢码完成监控方法")

# ========== 6. 任务列表状态颜色：添加"已结束(超时)" ==========
old_status_color = '''            if status_text == "执行中":
                status_fg = COLORS["danger"]
            elif status_text in ["已完成", "已结束"]:
                status_fg = COLORS["success"]
            elif status_text == "失败":
                status_fg = COLORS["warning"]
            else:
                status_fg = COLORS["text_muted"]'''

new_status_color = '''            if status_text == "执行中":
                status_fg = COLORS["danger"]
            elif status_text in ["已完成", "已结束"]:
                status_fg = COLORS["success"]
            elif "已结束" in status_text:
                status_fg = COLORS["success"]
            elif status_text == "失败":
                status_fg = COLORS["warning"]
            else:
                status_fg = COLORS["text_muted"]'''

content = content.replace(old_status_color, new_status_color)
print("6. 状态颜色添加超时已结束")

# ========== 7. _reset_task_status也匹配"已结束(超时)" ==========
old_reset = '''    def _reset_task_status(self, task):
        """重置任务状态为等待中（用于每天重复执行）"""
        if task.get("status") == "已结束":
            task["status"] = "等待中"
            self.refresh_task_list()'''

new_reset = '''    def _reset_task_status(self, task):
        """重置任务状态为等待中（用于每天重复执行）"""
        if "已结束" in task.get("status", ""):
            task["status"] = "等待中"
            self.refresh_task_list()'''

content = content.replace(old_reset, new_reset)
print("7. 重置状态匹配超时已结束")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.2.7 patch完成！")
