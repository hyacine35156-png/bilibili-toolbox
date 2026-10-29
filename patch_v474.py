#!/usr/bin/env python3
"""v4.7.4: 加大列间距 + 调小开始/删除按钮尺寸"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 表头：加大列间距
# ============================================================
old_header = '''            col_frame.pack(side=tk.LEFT, padx=(15 if i == 0 else 10, 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=6)'''

new_header = '''            col_frame.pack(side=tk.LEFT, padx=(25 if i == 0 else 18, 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=6)'''

if old_header in content:
    content = content.replace(old_header, new_header)
    print("1. 表头列间距已加大（首列25，其他18）")
else:
    print("1. 未找到表头代码")

# ============================================================
# 2. 数据行：加大列间距
# ============================================================
content = content.replace(
    'col1.pack(side=tk.LEFT, padx=(15, 0))',
    'col1.pack(side=tk.LEFT, padx=(25, 0))'
)
content = content.replace(
    'col2.pack(side=tk.LEFT, padx=(10, 0))',
    'col2.pack(side=tk.LEFT, padx=(18, 0))'
)
content = content.replace(
    'col3.pack(side=tk.LEFT, padx=(10, 0))',
    'col3.pack(side=tk.LEFT, padx=(18, 0))'
)
content = content.replace(
    'col4.pack(side=tk.LEFT, padx=(10, 0))',
    'col4.pack(side=tk.LEFT, padx=(18, 0))'
)
content = content.replace(
    'col5.pack(side=tk.LEFT, padx=(10, 0))',
    'col5.pack(side=tk.LEFT, padx=(18, 0))'
)
content = content.replace(
    'col6.pack(side=tk.LEFT, padx=(10, 0))',
    'col6.pack(side=tk.LEFT, padx=(18, 0))'
)
print("2. 数据行列间距已加大（首列25，其他18）")

# 数据行内部Label间距也加大
content = content.replace(
    'font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=8)',
    'font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=8)'
)
content = content.replace(
    'font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=8)',
    'font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=8)'
)
print("3. 数据行内部Label间距已加大（padx 6->8）")

# ============================================================
# 3. 开始/删除按钮尺寸调小（90x34 -> 75x28）
# ============================================================
# 开始按钮
content = content.replace(
    'DarkButton(btn_frame, "开始", command=lambda tid=task_id: self.start_scheduled_task(tid),\n                           width=90, height=34, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 2))',
    'DarkButton(btn_frame, "开始", command=lambda tid=task_id: self.start_scheduled_task(tid),\n                           width=75, height=28, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 4))'
)
# 停止按钮
content = content.replace(
    'DarkButton(btn_frame, "停止", command=lambda tid=task_id: self.stop_scheduled_task(tid),\n                           width=90, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 2))',
    'DarkButton(btn_frame, "停止", command=lambda tid=task_id: self.stop_scheduled_task(tid),\n                           width=75, height=28, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 4))'
)
# 删除按钮
content = content.replace(
    'DarkButton(btn_frame, "删除", command=lambda tid=task_id: self.delete_scheduled_task(tid),\n                       width=90, height=34, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)',
    'DarkButton(btn_frame, "删除", command=lambda tid=task_id: self.delete_scheduled_task(tid),\n                       width=75, height=28, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)'
)
print("4. 开始/停止/删除按钮尺寸已调小（90x34 -> 75x28）")

# ============================================================
# 4. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.7.3"', 'APP_VERSION = "v4.7.4"')
print("5. 版本号: v4.7.3 -> v4.7.4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
