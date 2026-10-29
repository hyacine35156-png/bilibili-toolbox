#!/usr/bin/env python3
"""v4.7.5: 加大表格行间距"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 行之间的间距：row_frame.pack pady=1 -> pady=3
content = content.replace(
    'row_frame.pack(fill=tk.X, pady=1)',
    'row_frame.pack(fill=tk.X, pady=3)'
)
print("1. 行之间间距: pady=1 -> pady=3")

# 2. 数据行Frame高度：height=36 -> height=44（6列）
content = content.replace(
    'col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=36)',
    'col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=44)'
)
content = content.replace(
    'col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=36)',
    'col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=44)'
)
content = content.replace(
    'col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=36)',
    'col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=44)'
)
content = content.replace(
    'col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=36)',
    'col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=44)'
)
content = content.replace(
    'col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=36)',
    'col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=44)'
)
content = content.replace(
    'col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=36)',
    'col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=44)'
)
print("2. 数据行高度: 36 -> 44")

# 3. 数据行内部Label的pady：8 -> 12
content = content.replace(
    'font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=8)',
    'font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)'
)
content = content.replace(
    'font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=8)',
    'font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)'
)
print("3. 数据行内部Label上下边距: pady=8 -> pady=12")

# 4. 操作按钮区域的pady也调整
content = content.replace(
    'btn_frame.pack(side=tk.LEFT, padx=4, pady=2)',
    'btn_frame.pack(side=tk.LEFT, padx=4, pady=6)'
)
print("4. 操作按钮区域上下边距: pady=2 -> pady=6")

# 5. 版本号
content = content.replace('APP_VERSION = "v4.7.4"', 'APP_VERSION = "v4.7.5"')
print("5. 版本号: v4.7.4 -> v4.7.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
