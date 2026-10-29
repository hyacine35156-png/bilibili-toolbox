#!/usr/bin/env python3
"""v4.8.0: 增大时长/间隔列宽度，避免内容被截断"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 表头列宽：时长/间隔从170px增大到210px
old_col_widths = '        col_widths = [340, 110, 170, 150, 80, 200]'
new_col_widths = '        col_widths = [340, 110, 210, 150, 80, 200]'

count = content.count(old_col_widths)
content = content.replace(old_col_widths, new_col_widths)
print(f"1. 时长/间隔列宽度已增大（170px -> 210px，替换了{count}处）")

# 2. 版本号
content = content.replace('APP_VERSION = "v4.7.9"', 'APP_VERSION = "v4.8.0"')
print("2. 版本号: v4.7.9 -> v4.8.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
