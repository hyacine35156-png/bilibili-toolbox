#!/usr/bin/env python3
"""v4.7.1: 统一表格列宽对齐，删除多账户轮流模式"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 统一表头列宽（和数据行一致）
# ============================================================
old_header = '''        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=36, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0), pady=6)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=22, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''

new_header = '''        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=38, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0), pady=6)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=14, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=22, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''

if old_header in content:
    content = content.replace(old_header, new_header)
    print("1. 表头列宽已统一（任务名称38, 领取时间14, 时长/间隔18）")
else:
    print("1. 未找到表头代码")

# ============================================================
# 2. 删除多账户轮流模式，只保留单账户
# ============================================================
old_account_row = '''        # 第二行：账户选择
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="抢码账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.rush_account_mode = tk.StringVar(value="single")
        ttk.Radiobutton(row2, text="单账户", variable=self.rush_account_mode, value="single",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row2, text="多账户轮流", variable=self.rush_account_mode, value="rotate",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)

        self.rush_account_list = tk.Listbox(row2, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                             selectbackground=COLORS["accent"], selectforeground="#000000",
                                             font=("微软雅黑", 10), bd=0, highlightthickness=0,
                                             height=3, exportselection=False, selectmode=tk.EXTENDED)
        self.rush_account_list.pack(side=tk.LEFT, padx=(15, 0), fill=tk.X, expand=True)'''

new_account_row = '''        # 第二行：账户选择
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="抢码账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        self.rush_account_list = tk.Listbox(row2, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                             selectbackground=COLORS["accent"], selectforeground="#000000",
                                             font=("微软雅黑", 10), bd=0, highlightthickness=0,
                                             height=3, exportselection=False, selectmode=tk.EXTENDED)
        self.rush_account_list.pack(side=tk.LEFT, padx=(15, 0), fill=tk.X, expand=True)'''

if old_account_row in content:
    content = content.replace(old_account_row, new_account_row)
    print("2. 已删除多账户轮流单选按钮，只保留账户列表")
else:
    print("2. 未找到账户选择行代码")

# ============================================================
# 3. 删除rush_account_mode相关的保存和加载逻辑
# ============================================================
# 删除配置保存中的rush_account_mode
content = content.replace('            "rush_account_mode": "single",\n', '')
content = content.replace('            self.rush_config["rush_account_mode"] = self.rush_account_mode.get()\n', '')

# 删除配置加载中的rush_account_mode
old_load = '''            if self.rush_config.get("rush_account_mode"):
                self.rush_account_mode.set(self.rush_config["rush_account_mode"])
'''
if old_load in content:
    content = content.replace(old_load, '')
    print("3. 已删除rush_account_mode的保存和加载逻辑")
else:
    print("3. 未找到rush_account_mode加载代码")

# 删除trace_add
content = content.replace('        self.rush_account_mode.trace_add("write", lambda *a: self.save_rush_config())\n', '')

# ============================================================
# 4. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.7.0"', 'APP_VERSION = "v4.7.1"')
print("4. 版本号: v4.7.0 -> v4.7.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
