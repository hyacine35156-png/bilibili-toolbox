#!/usr/bin/env python3
"""v4.9.8: 修复电池查询，SESSDATA字段名是大写的"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 替换get_battery_balance中的sessdata为SESSDATA
old_code = '''            sessdata = account.get("sessdata", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}'''

new_code = '''            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("1. 已修复SESSDATA字段名（小写->大写）")
else:
    print("1. 未找到目标代码")

# 版本号
content = content.replace('APP_VERSION = "v4.9.7"', 'APP_VERSION = "v4.9.8"')
print("2. 版本号: v4.9.7 -> v4.9.8")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
