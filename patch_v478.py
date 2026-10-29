#!/usr/bin/env python3
"""v4.7.8: 回退列宽到v4.7.6，增加表头高度避免文字被遮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 回退列宽到v4.7.6
old_col_widths = '        col_widths = [300, 100, 150, 130, 70, 140]'
new_col_widths = '        col_widths = [340, 110, 170, 150, 80, 200]'

count = content.count(old_col_widths)
content = content.replace(old_col_widths, new_col_widths)
print(f"1. 列宽已回退到v4.7.6（替换了{count}处）")

# 2. 增加表头高度：从32px增加到40px
old_header_height = '            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=32)'
new_header_height = '            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=40)'

if old_header_height in content:
    content = content.replace(old_header_height, new_header_height)
    print("2. 表头高度已增加（32px -> 40px）")
else:
    print("2. 未找到表头高度代码")

# 3. 表头文字垂直居中：增加pady
old_header_label_pady = 'font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=6)'
new_header_label_pady = 'font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=10)'

if old_header_label_pady in content:
    content = content.replace(old_header_label_pady, new_header_label_pady)
    print("3. 表头文字垂直间距已增加（pady=6 -> pady=10）")
else:
    print("3. 未找到表头文字pack代码")

# 4. 版本号
content = content.replace('APP_VERSION = "v4.7.6"', 'APP_VERSION = "v4.7.8"')
print("4. 版本号: v4.7.6 -> v4.7.8")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
