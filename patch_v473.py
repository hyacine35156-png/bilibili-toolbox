#!/usr/bin/env python3
"""v4.7.3: 加大表格列之间的间距"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 表头：加大列间距
old_header_padx = '''        for i, (name, w) in enumerate(zip(col_names, col_widths)):
            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=32)
            col_frame.pack(side=tk.LEFT, padx=(8 if i == 0 else 4, 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=6)'''

new_header_padx = '''        for i, (name, w) in enumerate(zip(col_names, col_widths)):
            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=32)
            col_frame.pack(side=tk.LEFT, padx=(15 if i == 0 else 10, 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=6)'''

if old_header_padx in content:
    content = content.replace(old_header_padx, new_header_padx)
    print("1. 表头列间距已加大（首列15，其他10）")
else:
    print("1. 未找到表头代码")

# 2. 数据行：加大列间距（6列）
# 任务名称列
content = content.replace(
    'col1.pack(side=tk.LEFT, padx=(8, 0))',
    'col1.pack(side=tk.LEFT, padx=(15, 0))'
)
# 领取时间列
content = content.replace(
    'col2.pack(side=tk.LEFT, padx=(4, 0))',
    'col2.pack(side=tk.LEFT, padx=(10, 0))'
)
# 时长/间隔列
content = content.replace(
    'col3.pack(side=tk.LEFT, padx=(4, 0))',
    'col3.pack(side=tk.LEFT, padx=(10, 0))'
)
# 账户列
content = content.replace(
    'col4.pack(side=tk.LEFT, padx=(4, 0))',
    'col4.pack(side=tk.LEFT, padx=(10, 0))'
)
# 状态列
content = content.replace(
    'col5.pack(side=tk.LEFT, padx=(4, 0))',
    'col5.pack(side=tk.LEFT, padx=(10, 0))'
)
# 操作列
content = content.replace(
    'col6.pack(side=tk.LEFT, padx=(4, 0))',
    'col6.pack(side=tk.LEFT, padx=(10, 0))'
)
print("2. 数据行列间距已加大（首列15，其他10）")

# 3. 数据行内部Label的padx也加大
content = content.replace(
    'font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=8)',
    'font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=8)'
)
content = content.replace(
    'font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=4, pady=8)',
    'font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=8)'
)
print("3. 数据行内部Label间距已加大（padx 4->6）")

# 4. 版本号
content = content.replace('APP_VERSION = "v4.7.2"', 'APP_VERSION = "v4.7.3"')
print("4. 版本号: v4.7.2 -> v4.7.3")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
