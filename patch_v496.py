#!/usr/bin/env python3
"""v4.9.6: 库存判断只用每日剩余，不用max(每日剩余, 剩余总量)"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 替换所有 max(day_s, total_s) 为 day_s
count = content.count("max(day_s, total_s)")
content = content.replace("max(day_s, total_s)", "day_s")
print(f"已替换 {count} 处 max(day_s, total_s) -> day_s")

# 版本号
content = content.replace('APP_VERSION = "v4.9.5"', 'APP_VERSION = "v4.9.6"')
print("版本号: v4.9.5 -> v4.9.6")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
