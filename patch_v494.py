#!/usr/bin/env python3
"""v4.9.4: 电池为0的账户直接禁用复选框，不跳过"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. _refresh_gift_account_checkboxes：创建后异步查询电池余额，为0则禁用
# ============================================================
old_refresh_gift = '''    def _refresh_gift_account_checkboxes(self):
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

new_refresh_gift = '''    def _refresh_gift_account_checkboxes(self):
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

if old_refresh_gift in content:
    content = content.replace(old_refresh_gift, new_refresh_gift)
    print("1. _refresh_gift_account_checkboxes已修改（异步查询电池，为0禁用）")
else:
    print("1. 未找到_refresh_gift_account_checkboxes")

# ============================================================
# 2. start_gift：移除电池检查和跳过逻辑
# ============================================================
old_start_battery = '''        self.save_gift_config()
        # 检查每个账户的电池余额
        valid_accounts = []
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            battery = self.get_battery_balance(acc)
            if battery is not None and battery <= 0:
                self.log(f"  ⚠ [{name}] 电池余额为0，跳过该账户")
                continue
            if battery is not None:
                self.log(f"  [{name}] 电池余额: {battery}")
            valid_accounts.append(acc)
        if not valid_accounts:
            self.log("✗ 没有可用的账户（所有选中账户电池余额均为0）")
            return
        self.gift_running = True
        self.gift_start_btn.config(state=tk.DISABLED)
        self.gift_stop_btn.config(state=tk.NORMAL)
        self.log(f"▶ 开始送礼: 直播间{room_id}, 牛蛙牛蛙x{gift_num}, 间隔{interval}秒, 次数{max_count}")
        self.log(f"  共 {len(valid_accounts)} 个账户参与送礼")
        selected_accounts = valid_accounts'''

new_start_battery = '''        self.save_gift_config()
        self.gift_running = True
        self.gift_start_btn.config(state=tk.DISABLED)
        self.gift_stop_btn.config(state=tk.NORMAL)
        self.log(f"▶ 开始送礼: 直播间{room_id}, 牛蛙牛蛙x{gift_num}, 间隔{interval}秒, 次数{max_count}")
        self.log(f"  共 {len(selected_accounts)} 个账户参与送礼")'''

if old_start_battery in content:
    content = content.replace(old_start_battery, new_start_battery)
    print("2. start_gift已移除电池检查和跳过逻辑")
else:
    print("2. 未找到start_gift电池检查部分")

# ============================================================
# 3. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.3"', 'APP_VERSION = "v4.9.4"')
print("3. 版本号: v4.9.3 -> v4.9.4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
