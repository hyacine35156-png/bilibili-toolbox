#!/usr/bin/env python3
"""v4.9.3 fix: 送礼单独账户选择区域"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. __init__中添加gift_account_vars
# ============================================================
old_init = '''        self.gift_id_cache = None  # 缓存牛蛙牛蛙的gift_id
        self.build_ui()'''

new_init = '''        self.gift_id_cache = None  # 缓存牛蛙牛蛙的gift_id
        self.gift_account_vars = {}  # 送礼单独账户选择
        self.build_ui()'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("1. __init__已添加gift_account_vars")
else:
    print("1. 未找到init位置")

# ============================================================
# 2. 送礼UI：在gift_row1之前添加账户选择行
# ============================================================
old_gift_row1 = '''        gift_row1 = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_row1.pack(fill=tk.X, pady=3)
        tk.Label(gift_row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)'''

new_gift_row1 = '''        # 送礼账户选择（单独区域）
        gift_acc_row = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=3)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_acc_container = tk.Frame(gift_acc_row, bg=COLORS["bg_card"])
        self.gift_acc_container.pack(side=tk.LEFT, padx=(8, 0))

        gift_row1 = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_row1.pack(fill=tk.X, pady=3)
        tk.Label(gift_row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)'''

if old_gift_row1 in content:
    content = content.replace(old_gift_row1, new_gift_row1)
    print("2. 送礼UI已添加账户选择行")
else:
    print("2. 未找到gift_row1")

# ============================================================
# 3. refresh_account_list中添加送礼账户刷新
# ============================================================
old_refresh_end = '''            cb.pack(fill=tk.X, anchor="w")
            self.account_checkbuttons.append(cb)
        self.refresh_status_tree()'''

new_refresh_end = '''            cb.pack(fill=tk.X, anchor="w")
            self.account_checkbuttons.append(cb)
        self.refresh_status_tree()
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
            cb = tk.Checkbutton(self.gift_acc_container, text=name, variable=var,
                                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 10),
                                command=self.save_gift_config)
            cb.pack(side=tk.LEFT, padx=(0, 12))'''

if old_refresh_end in content:
    content = content.replace(old_refresh_end, new_refresh_end)
    print("3. refresh_account_list已添加送礼账户刷新")
else:
    print("3. 未找到refresh_account_list结尾")

# ============================================================
# 4. start_gift：使用gift_account_vars
# ============================================================
old_start_acc = '''        selected_accounts = [acc for acc in self.account_mgr.accounts if self.account_vars.get(acc.get("name", ""), tk.BooleanVar()).get()]
        if not selected_accounts:
            self.log("✗ 请先选择送礼账户")
            return'''

new_start_acc = '''        selected_accounts = [acc for acc in self.account_mgr.accounts if self.gift_account_vars.get(acc.get("name", ""), tk.BooleanVar()).get()]
        if not selected_accounts:
            self.log("✗ 请先勾选送礼账户")
            return'''

if old_start_acc in content:
    content = content.replace(old_start_acc, new_start_acc)
    print("4. start_gift已改用gift_account_vars")
else:
    print("4. 未找到start_gift账户部分")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
