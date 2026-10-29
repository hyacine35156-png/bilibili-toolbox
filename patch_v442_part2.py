#!/usr/bin/env python3
"""v4.4.2 part2: 修复日志卡片布局 - 去掉expand，固定高度"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 修复日志卡片：去掉expand=True，改为固定高度180px
old_log = '''        # 日志卡片（设置最小高度200px，确保能显示多行日志）
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        log_card.pack_propagate(False)
        log_card.configure(height=220)'''

new_log = '''        # 日志卡片（固定高度180px，确保能显示多行日志）
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(6, 0))
        log_card.pack_propagate(False)
        log_card.configure(height=180)'''

if old_log in content:
    content = content.replace(old_log, new_log)
    print("1. 日志卡片改为固定高度180px，去掉expand")
else:
    print("1. 未找到日志卡片代码")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
