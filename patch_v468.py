#!/usr/bin/env python3
"""v4.6.8: 加大定时任务列表头部按钮尺寸"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''DarkButton(schedule_header, "+ 添加当前设置", command=self.add_scheduled_task,
                   width=150, height=34, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "▶ 全部开始", command=self.start_all_scheduled_tasks,
                   width=120, height=34, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "■ 全部停止", command=self.stop_all_scheduled_tasks,
                   width=120, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.RIGHT)'''

new = '''DarkButton(schedule_header, "+ 添加当前设置", command=self.add_scheduled_task,
                   width=200, height=38, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "▶ 全部开始", command=self.start_all_scheduled_tasks,
                   width=140, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "■ 全部停止", command=self.stop_all_scheduled_tasks,
                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.RIGHT)'''

if old in content:
    content = content.replace(old, new)
    print("按钮尺寸已修改: 添加当前设置150x34->200x38, 全部开始/停止120x34->140x38")
else:
    print("未找到按钮代码，尝试单独替换...")
    # 单独替换每个按钮
    content = content.replace('width=150, height=34, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))',
                              'width=200, height=38, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))')
    content = content.replace('width=120, height=34, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(4, 0))',
                              'width=140, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(4, 0))')
    content = content.replace('width=120, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.RIGHT)',
                              'width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.RIGHT)')
    print("单独替换完成")

# 版本号
content = content.replace('APP_VERSION = "v4.6.7"', 'APP_VERSION = "v4.6.8"')
print("版本号: v4.6.7 -> v4.6.8")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
