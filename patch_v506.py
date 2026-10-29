#!/usr/bin/env python3
"""v5.0.6: 加宽定时任务列表所有列，留足空间"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 表头列宽度加宽
old_header_width = '''        col_widths = [550, 110, 220, 130, 80, 180]
        col_names = ["任务名称", "领取时间", "时长/间隔", "账户", "状态", "操作"]'''

new_header_width = '''        col_widths = [550, 140, 300, 160, 110, 240]
        col_names = ["任务名称", "领取时间", "时长/间隔", "账户", "状态", "操作"]'''

if old_header_width in content:
    content = content.replace(old_header_width, new_header_width)
    print("1. 表头列宽度已加宽（领取时间140, 时长/间隔300, 账户160, 状态110, 操作240）")
else:
    print("1. 未找到表头列宽度代码")

# 2. 数据行列宽度加宽
old_row_width = '''            col_widths = [550, 110, 220, 130, 80, 180]'''
new_row_width = '''            col_widths = [550, 140, 300, 160, 110, 240]'''

if old_row_width in content:
    content = content.replace(old_row_width, new_row_width)
    print("2. 数据行列宽度已加宽")
else:
    print("2. 未找到数据行列宽度代码")

# 版本号
content = content.replace('APP_VERSION = "v5.0.5"', 'APP_VERSION = "v5.0.6"')
print("3. 版本号: v5.0.5 -> v5.0.6")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
