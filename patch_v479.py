#!/usr/bin/env python3
"""v4.7.9: 表头高度增加到50px，文字垂直间距加大"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 表头高度从40px增加到50px
old_height = 'height=40)'
new_height = 'height=50)'
# 只替换表头中的height=40，不替换数据行中的height=44
# 表头代码特征：col_frame = tk.Frame(header_frame, ...
old_header_frame = 'col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=40)'
new_header_frame = 'col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=50)'

if old_header_frame in content:
    content = content.replace(old_header_frame, new_header_frame)
    print("1. 表头高度已增加（40px -> 50px）")
else:
    print("1. 未找到表头Frame代码")

# 2. 表头文字垂直间距从pady=10增加到pady=14
old_pady = 'font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=10)'
new_pady = 'font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=14)'

if old_pady in content:
    content = content.replace(old_pady, new_pady)
    print("2. 表头文字垂直间距已增加（pady=10 -> pady=14）")
else:
    print("2. 未找到表头文字pack代码")

# 3. 版本号
content = content.replace('APP_VERSION = "v4.7.8"', 'APP_VERSION = "v4.7.9"')
print("3. 版本号: v4.7.8 -> v4.7.9")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
