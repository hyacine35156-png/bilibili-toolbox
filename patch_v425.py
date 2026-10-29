#!/usr/bin/env python3
"""v4.2.5: 修复切换类型名称不更新 + self.app.after报错"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 修复_auto_fill_name：切换类型时强制更新名称 ==========
old_auto_fill = '''    def _auto_fill_name(self, task_type):
        """根据类型自动填写任务名称（看播1、看播2...）"""
        type_prefix = {
            "watch": "看播",
            "danmaku": "弹幕",
            "rush": "抢码",
            "shutdown": "关机",
        }
        prefix = type_prefix.get(task_type, "任务")
        count = sum(1 for t in self.schedule_tasks if t["type"] == task_type)
        auto_name = f"{prefix}{count + 1}"
        current = self.task_name_entry.get().strip()
        if not current or current in [f"{prefix}{i}" for i in range(1, count + 2)]:
            self.task_name_entry.delete(0, tk.END)
            self.task_name_entry.insert(0, auto_name)'''

new_auto_fill = '''    def _auto_fill_name(self, task_type):
        """根据类型自动填写任务名称（看播1、看播2...）"""
        type_prefix = {
            "watch": "看播",
            "danmaku": "弹幕",
            "rush": "抢码",
            "shutdown": "关机",
        }
        prefix = type_prefix.get(task_type, "任务")
        count = sum(1 for t in self.schedule_tasks if t["type"] == task_type)
        auto_name = f"{prefix}{count + 1}"
        # 切换类型时强制更新名称（不管当前是什么）
        self.task_name_entry.delete(0, tk.END)
        self.task_name_entry.insert(0, auto_name)'''

content = content.replace(old_auto_fill, new_auto_fill)
print("1. 修复切换类型名称自动更新")

# ========== 2. 修复self.app.after → self.app.root.after ==========
# execute_task中的所有self.app.after都要改
old_after_1 = '''                self.app.after(0, lambda: self.app.switch_tab("watch"))
                self.app.after(500, lambda: self._start_watch_safe(task))'''
new_after_1 = '''                self.app.root.after(0, lambda: self.app.switch_tab("watch"))
                self.app.root.after(500, lambda: self._start_watch_safe(task))'''
content = content.replace(old_after_1, new_after_1)

old_after_2 = '''                self.app.after(0, lambda: self.app.switch_tab("danmaku"))
                self.app.after(500, lambda: self._start_danmaku_safe(task))'''
new_after_2 = '''                self.app.root.after(0, lambda: self.app.switch_tab("danmaku"))
                self.app.root.after(500, lambda: self._start_danmaku_safe(task))'''
content = content.replace(old_after_2, new_after_2)

old_after_3 = '''                self.app.after(0, lambda: self.app.switch_tab("rush"))
                self.app.after(500, lambda: self._start_rush_safe(task))'''
new_after_3 = '''                self.app.root.after(0, lambda: self.app.switch_tab("rush"))
                self.app.root.after(500, lambda: self._start_rush_safe(task))'''
content = content.replace(old_after_3, new_after_3)

old_after_4 = '''                self.app.after(0, lambda: self._execute_shutdown_safe(task))'''
new_after_4 = '''                self.app.root.after(0, lambda: self._execute_shutdown_safe(task))'''
content = content.replace(old_after_4, new_after_4)

old_after_5 = '''            self.app.after(2000, lambda: self._mark_task_done(task))'''
new_after_5 = '''            self.app.root.after(2000, lambda: self._mark_task_done(task))'''
content = content.replace(old_after_5, new_after_5)

print("2. 修复self.app.after → self.app.root.after（5处）")

# ========== 3. 调度器中的self.app.after也要改 ==========
old_scheduler_after = '''                            self.app.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.after(5000, lambda t=task: self._reset_task_status(t))'''
new_scheduler_after = '''                            self.app.root.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.root.after(5000, lambda t=task: self._reset_task_status(t))'''
content = content.replace(old_scheduler_after, new_scheduler_after)
print("3. 修复调度器中的after")

# ========== 4. shutdown_task_worker中的self.after也要检查 ==========
# 这个是DanmakuApp类的方法，self就是DanmakuApp，self.after也不对
# 应该是self.root.after
old_shutdown_after_1 = '''                    task["status"] = "已取消"
                    self.after(0, self.refresh_shutdown_task_list)
                    self.after(0, self.update_shutdown_status)
                    return'''
new_shutdown_after_1 = '''                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.root.after(0, self.update_shutdown_status)
                    return'''
content = content.replace(old_shutdown_after_1, new_shutdown_after_1)

old_shutdown_after_2 = '''                task["status"] = "倒计时中"
                self.after(0, self.refresh_shutdown_task_list)
                self.after(0, self.update_shutdown_status)
                time.sleep(1)'''
new_shutdown_after_2 = '''                task["status"] = "倒计时中"
                self.root.after(0, self.refresh_shutdown_task_list)
                self.root.after(0, self.update_shutdown_status)
                time.sleep(1)'''
content = content.replace(old_shutdown_after_2, new_shutdown_after_2)

old_shutdown_after_3 = '''                task["status"] = "待确认"
                self.after(0, self.refresh_shutdown_task_list)'''
new_shutdown_after_3 = '''                task["status"] = "待确认"
                self.root.after(0, self.refresh_shutdown_task_list)'''
content = content.replace(old_shutdown_after_3, new_shutdown_after_3)

old_shutdown_after_4 = '''                    task["status"] = "执行中"
                    self.after(0, self.refresh_shutdown_task_list)'''
new_shutdown_after_4 = '''                    task["status"] = "执行中"
                    self.root.after(0, self.refresh_shutdown_task_list)'''
content = content.replace(old_shutdown_after_4, new_shutdown_after_4)

old_shutdown_after_5 = '''                    task["status"] = "已取消"
                    self.after(0, self.refresh_shutdown_task_list)
                    self.after(0, self.update_shutdown_status)
                    self.log(f"■ 关机任务「{task['name']}」已取消")'''
new_shutdown_after_5 = '''                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.root.after(0, self.update_shutdown_status)
                    self.log(f"■ 关机任务「{task['name']}」已取消")'''
content = content.replace(old_shutdown_after_5, new_shutdown_after_5)

old_shutdown_after_6 = '''            task["status"] = "异常"
            self.log(f"✗ 关机任务「{task['name']}」异常: {e}")
            self.after(0, self.refresh_shutdown_task_list)
            self.after(0, self.update_shutdown_status)'''
new_shutdown_after_6 = '''            task["status"] = "异常"
            self.log(f"✗ 关机任务「{task['name']}」异常: {e}")
            self.root.after(0, self.refresh_shutdown_task_list)
            self.root.after(0, self.update_shutdown_status)'''
content = content.replace(old_shutdown_after_6, new_shutdown_after_6)

print("4. 修复关机任务中的after（7处）")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nv4.2.5 patch完成！")
