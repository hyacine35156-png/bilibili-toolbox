#!/usr/bin/env python3
"""v4.9.3: 送礼单独账户选择区域，电池检测送礼账户"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. __init__中添加送礼账户变量
# ============================================================
old_init_gift = '''        # 送礼相关
        self.gift_running = False
        self.gift_stop = {}
        self.gift_threads = []
        self.gift_id_cache = {}'''

new_init_gift = '''        # 送礼相关
        self.gift_running = False
        self.gift_stop = {}
        self.gift_threads = []
        self.gift_id_cache = {}
        self.gift_account_vars = {}  # 送礼单独账户选择'''

if old_init_gift in content:
    content = content.replace(old_init_gift, new_init_gift)
    print("1. __init__已添加gift_account_vars")
else:
    print("1. 未找到送礼init变量")

# ============================================================
# 2. 送礼UI：在gift_row1之前添加账户选择行
# ============================================================
old_gift_ui_start = '''        # 送礼设置
        gift_frame = tk.Frame(watch_card, bg=COLORS["bg_card"])
        gift_frame.pack(fill=tk.X, pady=(15, 0))
        tk.Label(gift_frame, text="送礼设置（牛蛙牛蛙）", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, pady=(0, 8))

        gift_row1 = tk.Frame(gift_frame, bg=COLORS["bg_card"])
        gift_row1.pack(fill=tk.X, pady=4)'''

new_gift_ui_start = '''        # 送礼设置
        gift_frame = tk.Frame(watch_card, bg=COLORS["bg_card"])
        gift_frame.pack(fill=tk.X, pady=(15, 0))
        tk.Label(gift_frame, text="送礼设置（牛蛙牛蛙）", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, pady=(0, 8))

        # 送礼账户选择（单独区域）
        gift_acc_row = tk.Frame(gift_frame, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=4)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_acc_container = tk.Frame(gift_acc_row, bg=COLORS["bg_card"])
        self.gift_acc_container.pack(side=tk.LEFT, padx=(8, 0))
        # 账户复选框在_refresh_gift_account_checkboxes中创建

        gift_row1 = tk.Frame(gift_frame, bg=COLORS["bg_card"])
        gift_row1.pack(fill=tk.X, pady=4)'''

if old_gift_ui_start in content:
    content = content.replace(old_gift_ui_start, new_gift_ui_start)
    print("2. 送礼UI已添加账户选择行")
else:
    print("2. 未找到送礼UI起始")

# ============================================================
# 3. 添加_refresh_gift_account_checkboxes方法
# ============================================================
old_refresh_accounts = '''    def refresh_account_checkboxes(self):
        """刷新左侧账户复选框列表"""
        # 清空现有
        for widget in self.account_container.winfo_children():
            widget.destroy()
        self.account_vars = {}
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            var = tk.BooleanVar(value=False)
            self.account_vars[name] = var
            cb = tk.Checkbutton(self.account_container, text=name, variable=var, bg=COLORS["bg_card"], fg=COLORS["text_primary"], font=("微软雅黑", 10), selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"], command=self._on_account_check)
            cb.pack(anchor=tk.W, pady=2)'''

new_refresh_accounts = '''    def refresh_account_checkboxes(self):
        """刷新左侧账户复选框列表"""
        # 清空现有
        for widget in self.account_container.winfo_children():
            widget.destroy()
        self.account_vars = {}
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            var = tk.BooleanVar(value=False)
            self.account_vars[name] = var
            cb = tk.Checkbutton(self.account_container, text=name, variable=var, bg=COLORS["bg_card"], fg=COLORS["text_primary"], font=("微软雅黑", 10), selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"], command=self._on_account_check)
            cb.pack(anchor=tk.W, pady=2)
        # 同时刷新送礼账户复选框
        self._refresh_gift_account_checkboxes()

    def _refresh_gift_account_checkboxes(self):
        """刷新送礼账户复选框列表"""
        if not hasattr(self, 'gift_acc_container'):
            return
        for widget in self.gift_acc_container.winfo_children():
            widget.destroy()
        self.gift_account_vars = {}
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            var = tk.BooleanVar(value=False)
            self.gift_account_vars[name] = var
            cb = tk.Checkbutton(self.gift_acc_container, text=name, variable=var, bg=COLORS["bg_card"], fg=COLORS["text_primary"], font=("微软雅黑", 10), selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"], command=self.save_gift_config)
            cb.pack(side=tk.LEFT, padx=(0, 12))'''

if old_refresh_accounts in content:
    content = content.replace(old_refresh_accounts, new_refresh_accounts)
    print("3. 已添加_refresh_gift_account_checkboxes方法")
else:
    print("3. 未找到refresh_account_checkboxes")

# ============================================================
# 4. save_gift_config：使用gift_account_vars
# ============================================================
old_save_gift_acc = '''            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.gift_config["selected_accounts"] = selected'''

new_save_gift_acc = '''            selected = []
            for name, var in self.gift_account_vars.items():
                if var.get():
                    selected.append(name)
            self.gift_config["selected_accounts"] = selected'''

if old_save_gift_acc in content:
    content = content.replace(old_save_gift_acc, new_save_gift_acc)
    print("4. save_gift_config已改用gift_account_vars")
else:
    print("4. 未找到save_gift_config账户部分")

# ============================================================
# 5. apply_gift_config：使用gift_account_vars
# ============================================================
old_apply_gift_acc = '''            selected = cfg.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected)'''

new_apply_gift_acc = '''            selected = cfg.get("selected_accounts", [])
            for name, var in self.gift_account_vars.items():
                var.set(name in selected)'''

if old_apply_gift_acc in content:
    content = content.replace(old_apply_gift_acc, new_apply_gift_acc)
    print("5. apply_gift_config已改用gift_account_vars")
else:
    print("5. 未找到apply_gift_config账户部分")

# ============================================================
# 6. start_gift：使用gift_account_vars获取选中账户
# ============================================================
old_start_gift_acc = '''        # 获取选中的账户
        selected_accounts = []
        for name, var in self.account_vars.items():
            if var.get():
                for acc in self.account_mgr.accounts:
                    if acc.get("name") == name:
                        selected_accounts.append(acc)
                        break
        if not selected_accounts:
            self.log("✗ 请先勾选至少一个账户")
            return'''

new_start_gift_acc = '''        # 获取选中的送礼账户
        selected_accounts = []
        for name, var in self.gift_account_vars.items():
            if var.get():
                for acc in self.account_mgr.accounts:
                    if acc.get("name") == name:
                        selected_accounts.append(acc)
                        break
        if not selected_accounts:
            self.log("✗ 请先勾选至少一个送礼账户")
            return'''

if old_start_gift_acc in content:
    content = content.replace(old_start_gift_acc, new_start_gift_acc)
    print("6. start_gift已改用gift_account_vars")
else:
    print("6. 未找到start_gift账户部分")

# ============================================================
# 7. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.2"', 'APP_VERSION = "v4.9.3"')
print("7. 版本号: v4.9.2 -> v4.9.3")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
