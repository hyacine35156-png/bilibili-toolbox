#!/usr/bin/env python3
"""v4.9.5: 送礼账户改下拉单选，选项显示电池数量"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. __init__中添加送礼账户下拉变量
# ============================================================
old_init = '''        self.gift_id_cache = None  # 缓存牛蛙牛蛙的gift_id
        self.gift_account_vars = {}  # 送礼单独账户选择
        self.build_ui()'''

new_init = '''        self.gift_id_cache = None  # 缓存牛蛙牛蛙的gift_id
        self.gift_account_var = tk.StringVar(value="")  # 送礼账户下拉选择
        self.gift_account_battery = {}  # 送礼账户电池余额缓存
        self.build_ui()'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("1. __init__已修改为下拉选择变量")
else:
    print("1. 未找到init位置")

# ============================================================
# 2. 送礼UI：把账户选择行改成下拉框
# ============================================================
old_gift_acc = '''        # 送礼账户选择（单独区域）
        gift_acc_row = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=3)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_acc_container = tk.Frame(gift_acc_row, bg=COLORS["bg_card"])
        self.gift_acc_container.pack(side=tk.LEFT, padx=(8, 0))'''

new_gift_acc = '''        # 送礼账户选择（下拉单选）
        gift_acc_row = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=3)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_account_combo = ttk.Combobox(gift_acc_row, width=30, values=[], state="readonly")
        self.gift_account_combo.pack(side=tk.LEFT, padx=(8, 10))
        self.gift_account_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())
        self.gift_battery_label = tk.Label(gift_acc_row, text="", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 10, "bold"))
        self.gift_battery_label.pack(side=tk.LEFT)'''

if old_gift_acc in content:
    content = content.replace(old_gift_acc, new_gift_acc)
    print("2. 送礼UI已改为下拉选择")
else:
    print("2. 未找到送礼账户UI")

# ============================================================
# 3. _refresh_gift_account_checkboxes改成_refresh_gift_account_combo
# ============================================================
old_refresh_method = '''    def _refresh_gift_account_checkboxes(self):
        """刷新送礼账户复选框列表，电池为0的账户禁用"""
        if not hasattr(self, 'gift_acc_container'):
            return
        for widget in self.gift_acc_container.winfo_children():
            widget.destroy()
        self.gift_account_vars = {}
        self.gift_account_checkbuttons = {}
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            var = tk.BooleanVar(value=False)
            self.gift_account_vars[name] = var
            cb = tk.Checkbutton(self.gift_acc_container, text=name, variable=var,
                                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 10),
                                command=self.save_gift_config)
            cb.pack(side=tk.LEFT, padx=(0, 12))
            self.gift_account_checkbuttons[name] = cb
        # 异步查询电池余额，为0则禁用
        threading.Thread(target=self._check_gift_account_battery, daemon=True).start()

    def _check_gift_account_battery(self):
        """异步查询送礼账户电池余额，为0则禁用复选框"""
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            battery = self.get_battery_balance(acc)
            if battery is not None and battery <= 0:
                # 在UI线程中禁用
                self.after(0, lambda n=name: self._disable_gift_account(n))

    def _disable_gift_account(self, name):
        """禁用指定送礼账户的复选框"""
        if name in self.gift_account_checkbuttons:
            cb = self.gift_account_checkbuttons[name]
            cb.config(state=tk.DISABLED, fg=COLORS["text_muted"])
            # 取消勾选
            if name in self.gift_account_vars:
                self.gift_account_vars[name].set(False)'''

new_refresh_method = '''    def _refresh_gift_account_combo(self):
        """刷新送礼账户下拉框，异步查询电池余额并显示"""
        if not hasattr(self, 'gift_account_combo'):
            return
        # 先显示账户名（不带电池）
        values = []
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(name)
        self.gift_account_combo["values"] = values
        # 异步查询电池余额，更新下拉框选项
        threading.Thread(target=self._update_gift_account_battery, daemon=True).start()

    def _update_gift_account_battery(self):
        """异步查询送礼账户电池余额，更新下拉框选项显示电池数量"""
        battery_info = {}
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            battery = self.get_battery_balance(acc)
            battery_info[name] = battery
        # 在UI线程中更新下拉框
        self.after(0, lambda: self._apply_gift_account_battery(battery_info))

    def _apply_gift_account_battery(self, battery_info):
        """更新送礼账户下拉框选项，显示电池数量"""
        self.gift_account_battery = battery_info
        values = []
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            battery = battery_info.get(name)
            if battery is not None:
                values.append(f"{name} (电池: {battery})")
            else:
                values.append(f"{name} (电池: 未知)")
        # 保存当前选择
        current = self.gift_account_var.get()
        self.gift_account_combo["values"] = values
        # 恢复选择（如果账户名匹配）
        if current:
            for v in values:
                if v.startswith(current + " "):
                    self.gift_account_combo.set(v)
                    break
        # 更新电池标签
        self._update_gift_battery_label()

    def _update_gift_battery_label(self):
        """更新当前选中账户的电池标签"""
        selected = self.gift_account_combo.get()
        if selected and "(" in selected:
            # 提取账户名
            name = selected.split(" (")[0]
            battery = self.gift_account_battery.get(name)
            if battery is not None:
                self.gift_battery_label.config(text=f"电池余额: {battery}")
            else:
                self.gift_battery_label.config(text="")
        else:
            self.gift_battery_label.config(text="")'''

if old_refresh_method in content:
    content = content.replace(old_refresh_method, new_refresh_method)
    print("3. 已改为下拉框刷新方法")
else:
    print("3. 未找到_refresh_gift_account_checkboxes")

# ============================================================
# 4. refresh_account_list中调用新方法
# ============================================================
old_call = '''        self.refresh_status_tree()
        # 同时刷新送礼账户复选框
        self._refresh_gift_account_checkboxes()'''

new_call = '''        self.refresh_status_tree()
        # 同时刷新送礼账户下拉框
        self._refresh_gift_account_combo()'''

if old_call in content:
    content = content.replace(old_call, new_call)
    print("4. refresh_account_list已更新调用")
else:
    print("4. 未找到refresh_account_list调用")

# ============================================================
# 5. save_gift_config：使用下拉选择
# ============================================================
old_save_acc = '''            selected = []
            for name, var in self.gift_account_vars.items():
                if var.get():
                    selected.append(name)
            self.gift_config["selected_accounts"] = selected'''

new_save_acc = '''            # 保存选中的送礼账户（从下拉框提取账户名）
            selected = self.gift_account_combo.get()
            if selected and "(" in selected:
                selected = selected.split(" (")[0]
            self.gift_config["selected_account"] = selected'''

if old_save_acc in content:
    content = content.replace(old_save_acc, new_save_acc)
    print("5. save_gift_config已改为下拉选择")
else:
    print("5. 未找到save_gift_config账户部分")

# ============================================================
# 6. apply_gift_config：使用下拉选择
# ============================================================
old_apply_acc = '''            selected = cfg.get("selected_accounts", [])
            for name, var in self.gift_account_vars.items():
                var.set(name in selected)'''

new_apply_acc = '''            # 恢复选中的送礼账户
            selected = cfg.get("selected_account", "")
            if selected:
                # 在下框中查找匹配项
                for v in self.gift_account_combo["values"]:
                    if v.startswith(selected + " "):
                        self.gift_account_combo.set(v)
                        break
                else:
                    self.gift_account_combo.set(selected)'''

if old_apply_acc in content:
    content = content.replace(old_apply_acc, new_apply_acc)
    print("6. apply_gift_config已改为下拉选择")
else:
    print("6. 未找到apply_gift_config账户部分")

# ============================================================
# 7. start_gift：使用下拉选择获取账户
# ============================================================
old_start_acc = '''        selected_accounts = [acc for acc in self.account_mgr.accounts if self.gift_account_vars.get(acc.get("name", ""), tk.BooleanVar()).get()]
        if not selected_accounts:
            self.log("✗ 请先勾选送礼账户")
            return'''

new_start_acc = '''        # 获取选中的送礼账户
        selected_name = self.gift_account_combo.get()
        if selected_name and "(" in selected_name:
            selected_name = selected_name.split(" (")[0]
        selected_accounts = []
        for acc in self.account_mgr.accounts:
            if acc.get("name") == selected_name:
                selected_accounts.append(acc)
                break
        if not selected_accounts:
            self.log("✗ 请先选择送礼账户")
            return'''

if old_start_acc in content:
    content = content.replace(old_start_acc, new_start_acc)
    print("7. start_gift已改为下拉选择")
else:
    print("7. 未找到start_gift账户部分")

# ============================================================
# 8. 下拉框选择时更新电池标签
# ============================================================
old_combo_bind = '''        self.gift_account_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())'''

new_combo_bind = '''        self.gift_account_combo.bind("<<ComboboxSelected>>", lambda e: (self._update_gift_battery_label(), self.save_gift_config()))'''

if old_combo_bind in content:
    content = content.replace(old_combo_bind, new_combo_bind)
    print("8. 下拉框绑定已更新电池标签")
else:
    print("8. 未找到下拉框绑定")

# ============================================================
# 9. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.4"', 'APP_VERSION = "v4.9.5"')
print("9. 版本号: v4.9.4 -> v4.9.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
