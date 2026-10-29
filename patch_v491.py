#!/usr/bin/env python3
"""v4.9.1: 送礼直播间号改下拉选择（用户名+历史记录+手动输入）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 修改送礼UI：把Entry改成Combobox
# ============================================================
old_gift_room = '''        tk.Label(gift_row1, text="直播间号:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_room_entry = tk.Entry(gift_row1, width=20, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("微软雅黑", 10), bd=0, insertbackground=COLORS["accent"])
        self.gift_room_entry.pack(side=tk.LEFT, padx=(8, 20))'''

new_gift_room = '''        tk.Label(gift_row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_room_combo = ttk.Combobox(gift_row1, width=24, values=[])
        self.gift_room_combo.pack(side=tk.LEFT, padx=(8, 20))'''

if old_gift_room in content:
    content = content.replace(old_gift_room, new_gift_room)
    print("1. 送礼直播间UI已改为下拉选择")
else:
    print("1. 未找到送礼直播间UI")

# ============================================================
# 2. 修改load_gift_config：添加room_history
# ============================================================
old_gift_default = '''        default = {
            "room_id": "",
            "gift_name": "牛蛙牛蛙",
            "gift_num": 1,
            "interval": 10,
            "max_count": 0,
            "selected_accounts": []
        }'''

new_gift_default = '''        default = {
            "room_id": "",
            "gift_name": "牛蛙牛蛙",
            "gift_num": 1,
            "interval": 10,
            "max_count": 0,
            "selected_accounts": [],
            "room_history": []
        }'''

if old_gift_default in content:
    content = content.replace(old_gift_default, new_gift_default)
    print("2. load_gift_config已添加room_history")
else:
    print("2. 未找到load_gift_config")

# ============================================================
# 3. 修改save_gift_config：保存历史记录，用combo代替entry
# ============================================================
old_save_gift = '''    def save_gift_config(self):
        try:
            self.gift_config["room_id"] = self.gift_room_entry.get().strip()
            self.gift_config["gift_num"] = self.gift_num_var.get()
            self.gift_config["interval"] = self.gift_interval_var.get()
            self.gift_config["max_count"] = self.gift_count_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.gift_config["selected_accounts"] = selected
            config_file = BASE_DIR / "gift_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.gift_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass'''

new_save_gift = '''    def save_gift_config(self):
        try:
            current_room = self.gift_room_combo.get().strip()
            # 如果是纯数字直播间号，保存到历史记录
            if current_room and current_room.isdigit() and current_room not in self.gift_config.get("room_history", []):
                history = self.gift_config.get("room_history", [])
                history.insert(0, current_room)
                self.gift_config["room_history"] = history[:20]
                self._refresh_gift_room_combo_values()
            self.gift_config["room_id"] = current_room
            self.gift_config["gift_num"] = self.gift_num_var.get()
            self.gift_config["interval"] = self.gift_interval_var.get()
            self.gift_config["max_count"] = self.gift_count_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.gift_config["selected_accounts"] = selected
            config_file = BASE_DIR / "gift_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.gift_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass'''

if old_save_gift in content:
    content = content.replace(old_save_gift, new_save_gift)
    print("3. save_gift_config已修改（历史记录+combo）")
else:
    print("3. 未找到save_gift_config")

# ============================================================
# 4. 修改apply_gift_config：用combo代替entry，刷新下拉框
# ============================================================
old_apply_gift = '''    def apply_gift_config(self):
        try:
            cfg = self.gift_config
            self.gift_room_entry.delete(0, tk.END)
            self.gift_room_entry.insert(0, cfg.get("room_id", ""))
            self.gift_num_var.set(cfg.get("gift_num", 1))
            self.gift_interval_var.set(cfg.get("interval", 10))
            self.gift_count_var.set(cfg.get("max_count", 0))
            selected = cfg.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected)
        except Exception:
            pass'''

new_apply_gift = '''    def apply_gift_config(self):
        try:
            cfg = self.gift_config
            self._refresh_gift_room_combo_values()
            self.gift_room_combo.set(cfg.get("room_id", ""))
            self.gift_num_var.set(cfg.get("gift_num", 1))
            self.gift_interval_var.set(cfg.get("interval", 10))
            self.gift_count_var.set(cfg.get("max_count", 0))
            selected = cfg.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected)
        except Exception:
            pass

    def _refresh_gift_room_combo_values(self):
        """刷新送礼直播间下拉框选项：用户直播间 + 历史记录"""
        values = []
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(f"【{name}】直播间")
        if self.gift_config.get("room_history"):
            values.append("--- 历史记录 ---")
            values.extend(self.gift_config["room_history"])
        self.gift_room_combo["values"] = values

    def _on_gift_room_selected(self, event=None):
        """选择送礼直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.gift_room_combo.get().strip()
        if selected.startswith("【") and "】直播间" in selected:
            name = selected[1:selected.index("】")]
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", "")
                    if mid:
                        room_id = self.get_user_room_id(mid)
                        if room_id:
                            self.gift_room_combo.set(str(room_id))
                            self.log(f"已获取「{name}」的直播间号: {room_id}")
                        else:
                            self.log(f"获取「{name}」直播间号失败，请手动输入")
                    break
        elif selected == "--- 历史记录 ---":
            self.gift_room_combo.set("")
        self.save_gift_config()'''

if old_apply_gift in content:
    content = content.replace(old_apply_gift, new_apply_gift)
    print("4. apply_gift_config已修改，已添加下拉框方法")
else:
    print("4. 未找到apply_gift_config")

# ============================================================
# 5. 修改start_gift：用combo代替entry
# ============================================================
old_start_gift_room = '''        room_id = self.gift_room_entry.get().strip()
        if not room_id:
            self.log("✗ 请先输入送礼直播间号")
            return'''

new_start_gift_room = '''        room_id = self.gift_room_combo.get().strip()
        if not room_id:
            self.log("✗ 请先选择或输入送礼直播间号")
            return'''

if old_start_gift_room in content:
    content = content.replace(old_start_gift_room, new_start_gift_room)
    print("5. start_gift已修改（combo）")
else:
    print("5. 未找到start_gift")

# ============================================================
# 6. 在bind_auto_save中添加送礼下拉框绑定
# ============================================================
old_bind = '''    def bind_auto_save(self):
        try:
            self.room_combo.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
        except Exception:
            pass'''

new_bind = '''    def bind_auto_save(self):
        try:
            self.room_combo.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            # 送礼下拉框绑定
            self.gift_room_combo.bind("<KeyRelease>", lambda e: self.save_gift_config())
            self.gift_room_combo.bind("<<ComboboxSelected>>", self._on_gift_room_selected)
            self.gift_num_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())
        except Exception:
            pass'''

if old_bind in content:
    content = content.replace(old_bind, new_bind)
    print("6. bind_auto_save已添加送礼下拉框绑定")
else:
    print("6. 未找到bind_auto_save")

# ============================================================
# 7. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.0"', 'APP_VERSION = "v4.9.1"')
print("7. 版本号: v4.9.0 -> v4.9.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
