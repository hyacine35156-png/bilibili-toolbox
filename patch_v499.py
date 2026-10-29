#!/usr/bin/env python3
"""v4.9.9: 修复电池查询(myWallet接口)，下拉框只显示账户名，增加查询电池按钮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 修复get_battery_balance方法，用myWallet接口
# ============================================================
old_method = '''    def get_battery_balance(self, account):
        """查询账户电池余额（gold字段，后两位为小数，100=1电池）"""
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = "https://api.live.bilibili.com/User/getUserInfo"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                user_info = data.get("data", {})
                # gold字段是电池数，后两位为小数，如100=1电池
                gold_raw = user_info.get("gold", 0)
                battery = gold_raw / 100.0 if gold_raw else 0
                return battery
            return None
        except Exception:
            return None'''

new_method = '''    def get_battery_balance(self, account):
        """查询账户电池余额（gold字段，后两位为小数，100=1电池）"""
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = "https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                wallet = data.get("data", {})
                # gold字段是电池数，后两位为小数，如100=1电池
                gold_raw = wallet.get("gold", 0)
                battery = gold_raw / 100.0 if gold_raw else 0
                return battery
            return None
        except Exception:
            return None'''

if old_method in content:
    content = content.replace(old_method, new_method)
    print("1. get_battery_balance已修复（改用myWallet接口）")
else:
    print("1. 未找到get_battery_balance方法")

# ============================================================
# 2. 送礼UI：下拉框只显示账户名，增加查询电池按钮
# ============================================================
old_gift_acc_ui = '''        # 送礼账户选择（下拉单选）
        gift_acc_row = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=3)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_account_combo = ttk.Combobox(gift_acc_row, width=30, values=[], state="readonly")
        self.gift_account_combo.pack(side=tk.LEFT, padx=(8, 10))
        self.gift_account_combo.bind("<<ComboboxSelected>>", lambda e: (self._update_gift_battery_label(), self.save_gift_config()))
        self.gift_battery_label = tk.Label(gift_acc_row, text="", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 10, "bold"))
        self.gift_battery_label.pack(side=tk.LEFT)'''

new_gift_acc_ui = '''        # 送礼账户选择（下拉单选）
        gift_acc_row = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=3)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_account_combo = ttk.Combobox(gift_acc_row, width=25, values=[], state="readonly")
        self.gift_account_combo.pack(side=tk.LEFT, padx=(8, 10))
        self.gift_account_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())
        # 查询电池按钮
        self.gift_query_battery_btn = tk.Button(gift_acc_row, text="查询电池", bg=COLORS["accent"], fg="white", font=("微软雅黑", 10), bd=0, padx=12, pady=3, cursor="hand2", command=self._query_gift_battery)
        self.gift_query_battery_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.gift_battery_label = tk.Label(gift_acc_row, text="", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 10, "bold"))
        self.gift_battery_label.pack(side=tk.LEFT)'''

if old_gift_acc_ui in content:
    content = content.replace(old_gift_acc_ui, new_gift_acc_ui)
    print("2. 送礼UI已修改（下拉框只显示账户名+查询电池按钮）")
else:
    print("2. 未找到送礼账户UI")

# ============================================================
# 3. _refresh_gift_account_combo：下拉框只显示账户名
# ============================================================
old_refresh_combo = '''    def _refresh_gift_account_combo(self):
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
        threading.Thread(target=self._update_gift_account_battery, daemon=True).start()'''

new_refresh_combo = '''    def _refresh_gift_account_combo(self):
        """刷新送礼账户下拉框，只显示账户名"""
        if not hasattr(self, 'gift_account_combo'):
            return
        values = []
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(name)
        # 保存当前选择
        current = self.gift_account_combo.get()
        self.gift_account_combo["values"] = values
        # 恢复选择
        if current and current in values:
            self.gift_account_combo.set(current)
        elif values:
            self.gift_account_combo.set(values[0])'''

if old_refresh_combo in content:
    content = content.replace(old_refresh_combo, new_refresh_combo)
    print("3. _refresh_gift_account_combo已修改（只显示账户名）")
else:
    print("3. 未找到_refresh_gift_account_combo")

# ============================================================
# 4. 删除_update_gift_account_battery和_apply_gift_account_battery方法，增加_query_gift_battery
# ============================================================
old_update_methods = '''    def _update_gift_account_battery(self):
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

new_query_method = '''    def _query_gift_battery(self):
        """查询当前选中送礼账户的电池余额"""
        selected_name = self.gift_account_combo.get()
        if not selected_name:
            self.gift_battery_label.config(text="请先选择账户")
            return
        self.gift_battery_label.config(text="查询中...")
        self.gift_query_battery_btn.config(state=tk.DISABLED)
        # 异步查询
        def query():
            battery = None
            for acc in self.account_mgr.accounts:
                if acc.get("name") == selected_name:
                    battery = self.get_battery_balance(acc)
                    break
            # 在UI线程更新
            def update():
                if battery is not None:
                    self.gift_battery_label.config(text=f"电池余额: {battery}")
                else:
                    self.gift_battery_label.config(text="查询失败")
                self.gift_query_battery_btn.config(state=tk.NORMAL)
            self.after(0, update)
        threading.Thread(target=query, daemon=True).start()'''

if old_update_methods in content:
    content = content.replace(old_update_methods, new_query_method)
    print("4. 已替换为_query_gift_battery方法")
else:
    print("4. 未找到旧的电池更新方法")

# ============================================================
# 5. save_gift_config：下拉框只存账户名
# ============================================================
old_save_acc = '''            # 保存选中的送礼账户（从下拉框提取账户名）
            selected = self.gift_account_combo.get()
            if selected and "(" in selected:
                selected = selected.split(" (")[0]
            self.gift_config["selected_account"] = selected'''

new_save_acc = '''            # 保存选中的送礼账户
            selected = self.gift_account_combo.get()
            self.gift_config["selected_account"] = selected'''

if old_save_acc in content:
    content = content.replace(old_save_acc, new_save_acc)
    print("5. save_gift_config已修改（只存账户名）")
else:
    print("5. 未找到save_gift_config账户部分")

# ============================================================
# 6. apply_gift_config：恢复选择
# ============================================================
old_apply_acc = '''            # 恢复选中的送礼账户
            selected = cfg.get("selected_account", "")
            if selected:
                # 在下框中查找匹配项
                for v in self.gift_account_combo["values"]:
                    if v.startswith(selected + " "):
                        self.gift_account_combo.set(v)
                        break
                else:
                    self.gift_account_combo.set(selected)'''

new_apply_acc = '''            # 恢复选中的送礼账户
            selected = cfg.get("selected_account", "")
            if selected and selected in self.gift_account_combo["values"]:
                self.gift_account_combo.set(selected)'''

if old_apply_acc in content:
    content = content.replace(old_apply_acc, new_apply_acc)
    print("6. apply_gift_config已修改")
else:
    print("6. 未找到apply_gift_config账户部分")

# ============================================================
# 7. start_gift：获取账户
# ============================================================
old_start_acc = '''        # 获取选中的送礼账户
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

new_start_acc = '''        # 获取选中的送礼账户
        selected_name = self.gift_account_combo.get()
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
    print("7. start_gift已修改")
else:
    print("7. 未找到start_gift账户部分")

# ============================================================
# 8. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.8"', 'APP_VERSION = "v4.9.9"')
print("8. 版本号: v4.9.8 -> v4.9.9")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
