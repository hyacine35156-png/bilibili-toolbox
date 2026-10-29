#!/usr/bin/env python3
"""v4.7.6: 表头与数据行间距 + 时长/账户列间距加大"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 表头底部增加间距（表头和第一行数据之间）
# ============================================================
old_header_pack = '        header_frame.pack(fill=tk.X)'
new_header_pack = '        header_frame.pack(fill=tk.X, pady=(0, 8))'

if old_header_pack in content:
    content = content.replace(old_header_pack, new_header_pack)
    print("1. 表头底部间距已增加（pady=8）")
else:
    print("1. 未找到表头pack代码")

# ============================================================
# 2. 时长/间隔列（col3）和账户列（col4）之间间距加大
# ============================================================
# 表头：第3列（时长/间隔，index=2）和第4列（账户，index=3）之间
# 当前表头用的是统一的 padx=(25 if i == 0 else 18, 0)
# 需要改成单独控制每列的间距
old_header_loop = '''        for i, (name, w) in enumerate(zip(col_names, col_widths)):
            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=32)
            col_frame.pack(side=tk.LEFT, padx=(25 if i == 0 else 18, 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=6)'''

new_header_loop = '''        # 每列左边距：首列25，时长/间隔列后加大到35
        col_paddings = [25, 18, 18, 35, 18, 18]
        for i, (name, w) in enumerate(zip(col_names, col_widths)):
            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=32)
            col_frame.pack(side=tk.LEFT, padx=(col_paddings[i], 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=6)'''

if old_header_loop in content:
    content = content.replace(old_header_loop, new_header_loop)
    print("2. 表头列间距已调整（时长/间隔后加大到35）")
else:
    print("2. 未找到表头循环代码")

# 数据行：col4（账户）的左边距从18加大到35
content = content.replace(
    'col4.pack(side=tk.LEFT, padx=(18, 0))',
    'col4.pack(side=tk.LEFT, padx=(35, 0))'
)
print("3. 数据行账户列左边距已加大（18 -> 35）")

# ============================================================
# 4. 今日剩余数据加百分号
# ============================================================
# 日志输出：初始库存
content = content.replace(
    'self.log(f"  初始库存: 今日剩余={day_s}, 剩余总量={total_s}%")',
    'self.log(f"  初始库存: 今日剩余={day_s}%, 剩余总量={total_s}%")'
)
# 库存调试输出
content = content.replace(
    'self.log(f"[库存调试] 解析结果: 今日剩余={day_stock}, 活动剩余={total_stock}, 来源={stock_source}")',
    'self.log(f"[库存调试] 解析结果: 今日剩余={day_stock}%, 活动剩余={total_stock}%, 来源={stock_source}")'
)
# 库存状态显示：今日剩余
content = content.replace(
    'stock_parts_final.append(f"今日剩余{day_stock}")',
    'stock_parts_final.append(f"今日剩余{day_stock}%")'
)
# 抢码循环中的库存显示：今日
content = content.replace(
    'stock_parts.append(f"今日{day_stock}")',
    'stock_parts.append(f"今日{day_stock}%")'
)
print("4. 今日剩余数据已加百分号（4处）")

# ============================================================
# 5. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.7.5"', 'APP_VERSION = "v4.7.6"')
print("5. 版本号: v4.7.5 -> v4.7.6")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
