#!/usr/bin/env python3
"""v5.2.5: 送礼功能直播间下拉框改成新的直播间管理模式"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 送礼直播间下拉框改成只读，只显示直播间名称
# ============================================================
old_gift_room_ui = '''        tk.Label(gift_row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_room_combo = ttk.Combobox(gift_row1, width=24, values=[])
        self.gift_room_combo.pack(side=tk.LEFT, padx=(8, 20))'''

new_gift_room_ui = '''        tk.Label(gift_row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_room_combo = ttk.Combobox(gift_row1, width=24, values=[], state="readonly")
        self.gift_room_combo.pack(side=tk.LEFT, padx=(8, 20))'''

if old_gift_room_ui in content:
    content = content.replace(old_gift_room_ui, new_gift_room_ui)
    print("1. 送礼直播间下拉框改成只读")
else:
    print("1. 未找到送礼直播间下拉框UI代码")

# ============================================================
# 2. save_gift_config：改成保存直播间名称，不再保存历史记录
# ============================================================
old_save_gift = '''    def save_gift_config(self):
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
            # 保存选中的送礼账户
            selected = self.gift_account_combo.get()
            self.gift_config["selected_account"] = selected
            config_file = BASE_DIR / "gift_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.gift_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass'''

new_save_gift = '''    def save_gift_config(self):
        try:
            current_room = self.gift_room_combo.get().strip()
            self.gift_config["room_name"] = current_room  # 保存直播间名称
            self.gift_config["gift_num"] = self.gift_num_var.get()
            self.gift_config["interval"] = self.gift_interval_var.get()
            self.gift_config["max_count"] = self.gift_count_var.get()
            # 保存选中的送礼账户
            selected = self.gift_account_combo.get()
            self.gift_config["selected_account"] = selected
            config_file = BASE_DIR / "gift_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.gift_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass'''

if old_save_gift in content:
    content = content.replace(old_save_gift, new_save_gift)
    print("2. save_gift_config已修改：保存直播间名称")
else:
    print("2. 未找到save_gift_config代码")

# ============================================================
# 3. apply_gift_config：改成恢复直播间名称
# ============================================================
old_apply_gift = '''    def apply_gift_config(self):
        try:
            cfg = self.gift_config
            self._refresh_gift_room_combo_values()
            self.gift_room_combo.set(cfg.get("room_id", ""))
            self.gift_num_var.set(cfg.get("gift_num", 1))
            self.gift_interval_var.set(cfg.get("interval", 10))
            self.gift_count_var.set(cfg.get("max_count", 0))
            # 恢复选中的送礼账户
            selected = cfg.get("selected_account", "")
            if selected and selected in self.gift_account_combo["values"]:
                self.gift_account_combo.set(selected)
        except Exception:
            pass'''

new_apply_gift = '''    def apply_gift_config(self):
        try:
            cfg = self.gift_config
            self._refresh_gift_room_combo_values()
            # 恢复直播间名称（兼容旧配置的room_id）
            room_name = cfg.get("room_name", cfg.get("room_id", ""))
            if room_name:
                self.gift_room_combo.set(room_name)
            self.gift_num_var.set(cfg.get("gift_num", 1))
            self.gift_interval_var.set(cfg.get("interval", 10))
            self.gift_count_var.set(cfg.get("max_count", 0))
            # 恢复选中的送礼账户
            selected = cfg.get("selected_account", "")
            if selected and selected in self.gift_account_combo["values"]:
                self.gift_account_combo.set(selected)
        except Exception:
            pass'''

if old_apply_gift in content:
    content = content.replace(old_apply_gift, new_apply_gift)
    print("3. apply_gift_config已修改：恢复直播间名称")
else:
    print("3. 未找到apply_gift_config代码")

# ============================================================
# 4. _refresh_gift_room_combo_values：改成从直播间管理获取名称
# ============================================================
old_refresh_gift_room = '''    def _refresh_gift_room_combo_values(self):
        """刷新送礼直播间下拉框选项：用户直播间 + 历史记录"""
        values = []
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(f"【{name}】直播间")
        if self.gift_config.get("room_history"):
            values.append("--- 历史记录 ---")
            values.extend(self.gift_config["room_history"])
        self.gift_room_combo["values"] = values'''

new_refresh_gift_room = '''    def _refresh_gift_room_combo_values(self):
        """刷新送礼直播间下拉框选项：只显示直播间管理中的直播间名称"""
        if not hasattr(self, 'gift_room_combo') or not self.gift_room_combo.winfo_exists():
            return
        values = []
        for room in self.room_mgr.rooms:
            values.append(room["name"])
        self.gift_room_combo["values"] = values
        # 如果当前选中的不在列表中，清空
        if self.gift_room_combo.get() not in values:
            self.gift_room_combo.set("")'''

if old_refresh_gift_room in content:
    content = content.replace(old_refresh_gift_room, new_refresh_gift_room)
    print("4. _refresh_gift_room_combo_values已修改：从直播间管理获取")
else:
    print("4. 未找到_refresh_gift_room_combo_values代码")

# ============================================================
# 5. _on_gift_room_selected：简化，只保存配置
# ============================================================
old_on_gift_room = '''    def _on_gift_room_selected(self, event=None):
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

new_on_gift_room = '''    def _on_gift_room_selected(self, event=None):
        """选择送礼直播间下拉框时：保存配置"""
        self.save_gift_config()

    def _get_gift_room_id(self):
        """根据选中的直播间名称获取直播间号"""
        selected_name = self.gift_room_combo.get().strip()
        if not selected_name:
            return None
        for room in self.room_mgr.rooms:
            if room["name"] == selected_name:
                return room["id"]
        return None'''

if old_on_gift_room in content:
    content = content.replace(old_on_gift_room, new_on_gift_room)
    print("5. _on_gift_room_selected已简化，新增_get_gift_room_id")
else:
    print("5. 未找到_on_gift_room_selected代码")

# ============================================================
# 6. 送礼启动方法中使用_get_gift_room_id获取直播间号
# ============================================================
old_gift_start_room = '''        room_id = self.gift_room_combo.get().strip()
        if not room_id:
            self.log("请先选择或输入直播间号")
            return'''

new_gift_start_room = '''        room_id = self._get_gift_room_id()
        if not room_id:
            self.log("请先选择直播间（可在账户管理页面添加直播间）")
            return'''

if old_gift_start_room in content:
    content = content.replace(old_gift_start_room, new_gift_start_room)
    print("6. 送礼启动方法已使用_get_gift_room_id")
else:
    print("6. 未找到送礼启动方法代码")

# ============================================================
# 7. bind_auto_save中修改送礼直播间绑定
# ============================================================
old_bind_gift = '''            self.gift_room_combo.bind("<KeyRelease>", lambda e: self.save_gift_config())
            self.gift_room_combo.bind("<<ComboboxSelected>>", self._on_gift_room_selected)'''

new_bind_gift = '''            self.gift_room_combo.bind("<<ComboboxSelected>>", self._on_gift_room_selected)'''

if old_bind_gift in content:
    content = content.replace(old_bind_gift, new_bind_gift)
    print("7. bind_auto_save已修改送礼直播间绑定")
else:
    print("7. 未找到bind_auto_save送礼直播间代码")

# 版本号
content = content.replace('APP_VERSION = "v5.2.4"', 'APP_VERSION = "v5.2.5"')
print("8. 版本号: v5.2.4 -> v5.2.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
