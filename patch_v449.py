#!/usr/bin/env python3
"""v4.4.9: 启动所有定时任务时每隔5秒启动一个，避免请求频率过高"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 修改start_all_scheduled_tasks方法，用后台线程循序启动
# ============================================================
old_start_all = '''    def start_all_scheduled_tasks(self):
        """启动所有定时任务"""
        count = 0
        for task in self.scheduled_tasks:
            if task.get("status") != "运行中":
                self.start_scheduled_task(task["id"])
                count += 1
        self.log(f"▶ 已启动 {count} 个定时任务")'''

new_start_all = '''    def start_all_scheduled_tasks(self):
        """启动所有定时任务（每隔5秒启动一个，避免请求频率过高）"""
        tasks_to_start = []
        for task in self.scheduled_tasks:
            if task.get("status") != "运行中":
                tasks_to_start.append(task["id"])

        if not tasks_to_start:
            self.log("⚠ 没有需要启动的定时任务")
            return

        self.log(f"▶ 即将循序启动 {len(tasks_to_start)} 个定时任务（每个间隔5秒）")

        # 用后台线程循序启动
        def _start_sequentially():
            for i, task_id in enumerate(tasks_to_start):
                if i > 0:
                    self.log(f"  ⏳ 等待5秒后启动下一个任务...")
                    time.sleep(5)
                self.start_scheduled_task(task_id)
            self.log(f"✓ 全部 {len(tasks_to_start)} 个定时任务已启动完成")

        threading.Thread(target=_start_sequentially, daemon=True).start()'''

if old_start_all in content:
    content = content.replace(old_start_all, new_start_all)
    print("1. 修改start_all_scheduled_tasks为循序启动（间隔5秒）")
else:
    print("1. 未找到start_all_scheduled_tasks代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.8"', 'APP_VERSION = "v4.4.9"')
print("2. 版本号已更新到 v4.4.9")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
