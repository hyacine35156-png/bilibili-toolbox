#!/usr/bin/env python3
"""v4.7.7: 缩小表格列宽，避免操作列被按钮遮挡"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 表头列宽调整
old_col_widths = '        col_widths = [340, 110, 170, 150, 80, 200]'
new_col_widths = '        col_widths = [300, 100, 150, 130, 70, 140]'

if old_col_widths in content:
    content = content.replace(old_col_widths, new_col_widths)
    print("1. 表头列宽已调整（总宽度从1050->890）")
else:
    print("1. 未找到表头列宽代码")

# 2. 数据行列宽也需要同步调整
# 数据行的col_widths是在refresh_scheduled_task_list方法中定义的
# 让我搜索一下
import re
# 查找数据行中的col_widths定义
matches = [(i+1, line.strip()) for i, line in enumerate(content.split('\n')) if 'col_widths' in line]
print(f"\n找到 {len(matches)} 处col_widths定义:")
for lineno, line in matches:
    print(f"  第{lineno}行: {line}")

# 替换所有数据行中的col_widths（如果有的话）
# 数据行中可能直接用硬编码的width，而不是col_widths变量
# 让我检查一下数据行的代码

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
