#!/usr/bin/env python3
"""v4.2.6: 1.已完成显示已结束 2.抢码不跳转 3.日志两边显示"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 抢码任务不跳转页面 ==========
old_rush_exec = '''            elif task["type"] == "rush":
                # 切换到抢码页面并开始
                self.app.root.after(0, lambda: self.app.switch_tab("rush"))
                self.app.root.after(500, lambda: self._start_rush_safe(task))'''

new_rush_exec = '''            elif task["type"] == "rush":
                # 抢码任务不跳转，直接后台执行
                self.app.root.after(100, lambda: self._start_rush_safe(task))'''

content = content.replace(old_rush_exec, new_rush_exec)
print("1. 抢码任务不跳转页面")

# ========== 2. 日志两边都显示 ==========
# _start_watch_safe: 同时写看播页面日志
old_watch_safe = '''    def _start_watch_safe(self, task):
        try:
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'start_watch'):
                self.app.watch_page.start_watch()
                self.log(f"✓ 看播任务已启动")
        except Exception as e:
            self.log(f"✗ 启动看播失败: {e}")'''

new_watch_safe = '''    def _start_watch_safe(self, task):
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

content = content.replace(old_watch_safe, new_watch_safe)
print("2a. 看播日志两边显示")

# _start_danmaku_safe: 同时写弹幕页面日志
old_danmaku_safe = '''    def _start_danmaku_safe(self, task):
        try:
            if hasattr(self.app, 'start_sending'):
                self.app.start_sending()
                self.log(f"✓ 弹幕任务已启动")
        except Exception as e:
            self.log(f"✗ 启动弹幕失败: {e}")'''

new_danmaku_safe = '''    def _start_danmaku_safe(self, task):
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

content = content.replace(old_danmaku_safe, new_danmaku_safe)
print("2b. 弹幕日志两边显示")

# _start_rush_safe: 同时写抢码页面日志
old_rush_safe = '''    def _start_rush_safe(self, task):
        try:
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_all_scheduled_tasks'):
                self.app.rush_page.start_all_scheduled_tasks()
                self.log(f"✓ 抢码定时任务已全部启动")
            elif hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_rush'):
                self.app.rush_page.start_rush()
                self.log(f"✓ 抢码监控已启动")
        except Exception as e:
            self.log(f"✗ 启动抢码失败: {e}")'''

new_rush_safe = '''    def _start_rush_safe(self, task):
        try:
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_all_scheduled_tasks'):
                self.app.rush_page.start_all_scheduled_tasks()
                msg = f"✓ [日程] 抢码任务「{task['name']}」已全部启动"
                self.log(msg)
                # 同时写抢码页面日志
                if hasattr(self.app.rush_page, 'log'):
                    self.app.rush_page.log(msg)
            elif hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_rush'):
                self.app.rush_page.start_rush()
                msg = f"✓ [日程] 抢码监控「{task['name']}」已启动"
                self.log(msg)
                if hasattr(self.app.rush_page, 'log'):
                    self.app.rush_page.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动抢码失败: {e}"
            self.log(msg)
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
                self.app.rush_page.log(msg)'''

content = content.replace(old_rush_safe, new_rush_safe)
print("2c. 抢码日志两边显示")

# ========== 3. 已完成任务显示"已结束" ==========
# _mark_task_done: 状态改为"已结束"
old_mark_done = '''    def _mark_task_done(self, task):
        task["status"] = "已完成"
        self.refresh_task_list()
        self.save_schedule()'''

new_mark_done = '''    def _mark_task_done(self, task):
        task["status"] = "已结束"
        self.refresh_task_list()
        self.save_schedule()'''

content = content.replace(old_mark_done, new_mark_done)
print("3a. 状态文字改为已结束")

# _reset_task_status: 匹配"已结束"
old_reset = '''    def _reset_task_status(self, task):
        """重置任务状态为等待中（用于每天重复执行）"""
        if task.get("status") == "已完成":
            task["status"] = "等待中"
            self.refresh_task_list()'''

new_reset = '''    def _reset_task_status(self, task):
        """重置任务状态为等待中（用于每天重复执行）"""
        if task.get("status") == "已结束":
            task["status"] = "等待中"
            self.refresh_task_list()'''

content = content.replace(old_reset, new_reset)
print("3b. 重置状态匹配已结束")

# 任务列表状态颜色判断: 添加"已结束"
old_status_color = '''            if status_text == "执行中":
                status_fg = COLORS["danger"]
            elif status_text == "已完成":
                status_fg = COLORS["success"]
            elif status_text == "失败":
                status_fg = COLORS["warning"]
            else:
                status_fg = COLORS["text_muted"]'''

new_status_color = '''            if status_text == "执行中":
                status_fg = COLORS["danger"]
            elif status_text in ["已完成", "已结束"]:
                status_fg = COLORS["success"]
            elif status_text == "失败":
                status_fg = COLORS["warning"]
            else:
                status_fg = COLORS["text_muted"]'''

content = content.replace(old_status_color, new_status_color)
print("3c. 状态颜色添加已结束")

# ========== 4. execute_task中的日志也加[日程]标记 ==========
old_exec_log = '''        prefix = "手动执行" if manual else "定时触发"
        self.log(f"{'⚡' if manual else '⏰'} {prefix}任务「{task['name']}」({task['type_name']})")'''

new_exec_log = '''        prefix = "手动执行" if manual else "定时触发"
        msg = f"{'⚡' if manual else '⏰'} [日程] {prefix}任务「{task['name']}」({task['type_name']})"
        self.log(msg)
        # 同时写对应页面日志
        if task["type"] == "rush" and hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
            self.app.rush_page.log(msg)
        elif task["type"] == "watch" and hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
            self.app.watch_page.log(msg)
        elif task["type"] == "danmaku" and hasattr(self.app, 'log'):
            self.app.log(msg)'''

content = content.replace(old_exec_log, new_exec_log)
print("4. 执行日志两边显示")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.2.6 patch完成！")
