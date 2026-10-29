#!/usr/bin/env python3
"""v4.5.4: 删除无用滚动条，修复文字被挡住的布局问题"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 看播任务页面：删除账户列表滚动条，改用普通Frame
# ============================================================
old_account_scroll = '''        # 复选框滚动区域
        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.account_canvas = tk.Canvas(list_frame, bg=COLORS["bg_input"], bd=0, highlightthickness=0)
        self.account_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.account_canvas.yview)
        self.account_scrollable_frame = tk.Frame(self.account_canvas, bg=COLORS["bg_input"])
        self.account_scrollable_frame.bind("<Configure>", lambda e: self.account_canvas.configure(scrollregion=self.account_canvas.bbox("all")))
        self.account_canvas.create_window((0, 0), window=self.account_scrollable_frame, anchor="nw")
        self.account_canvas.configure(yscrollcommand=self.account_scrollbar.set)
        self.account_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.account_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)'''

new_account_scroll = '''        # 复选框区域（无滚动条，账户数量少直接显示）
        list_frame = tk.Frame(left_card, bg=COLORS["bg_input"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.account_scrollable_frame = list_frame'''

if old_account_scroll in content:
    content = content.replace(old_account_scroll, new_account_scroll)
    print("1. 看播任务：删除账户列表滚动条，改用普通Frame")
else:
    print("1. 未找到看播任务账户滚动条代码")

# ============================================================
# 2. 看播任务页面：调大左侧账户卡片宽度 220 -> 280
# ============================================================
old_left_width = '''        left_card.pack_propagate(False)
        left_card.configure(width=220)'''

new_left_width = '''        left_card.pack_propagate(False)
        left_card.configure(width=280)'''

if old_left_width in content:
    content = content.replace(old_left_width, new_left_width)
    print("2. 看播任务：左侧账户卡片宽度 220 -> 280")
else:
    print("2. 未找到左侧账户卡片宽度设置")

# ============================================================
# 3. 抢码页面：定时任务列表列宽调整，避免文字被挡住
# ============================================================
old_rush_header = '''        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=30, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=4)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=14, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''

new_rush_header = '''        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=28, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=4)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=8, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''

if old_rush_header in content:
    content = content.replace(old_rush_header, new_rush_header)
    print("3. 抢码页面：定时任务列表列宽调整")
else:
    print("3. 未找到抢码页面定时任务表头代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.3"', 'APP_VERSION = "v4.5.4"')
print("4. 版本号已更新到 v4.5.4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
