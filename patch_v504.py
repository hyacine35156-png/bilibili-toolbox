#!/usr/bin/env python3
"""v5.0.4: 定时任务名称后加版本信息括号"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 修改任务名称显示，加上版本信息括号
old_name = '''            # 任务名称
            name_text = task.get("task_name", "未知任务")[:30]
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=44)'''

new_name = '''            # 任务名称（加版本信息括号）
            task_name = task.get("task_name", "未知任务")
            version = task.get("version", "")
            period = task.get("period", "")
            if version or period:
                version_info = f"{version}{period}" if version and period else (version or period)
                name_text = f"{task_name}（{version_info}）"[:40]
            else:
                name_text = task_name[:30]
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=44)'''

if old_name in content:
    content = content.replace(old_name, new_name)
    print("1. 任务名称显示已修改（加版本信息括号）")
else:
    print("1. 未找到目标代码")

# 加宽任务名称列（从340到420）
old_width = '''            col_widths = [340, 110, 260, 150, 80, 200]'''
new_width = '''            col_widths = [420, 110, 260, 150, 80, 200]'''

if old_width in content:
    content = content.replace(old_width, new_width)
    print("2. 任务名称列宽度已加宽（340 -> 420）")
else:
    print("2. 未找到列宽度代码")

# 版本号
content = content.replace('APP_VERSION = "v5.0.3"', 'APP_VERSION = "v5.0.4"')
print("3. 版本号: v5.0.3 -> v5.0.4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
