#!/usr/bin/env python3
"""修改看播任务直播间选择：用户名下拉+手动输入+历史记录"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 修改load_watch_config：添加room_history默认值 ==========
old_load = '''    def load_watch_config(self):
        default = {"room_id": "1791983148", "daily_minutes": 30, "heartbeat_interval": 60, "selected_accounts": []}'''
new_load = '''    def load_watch_config(self):
        default = {"room_id": "1791983148", "daily_minutes": 30, "heartbeat_interval": 60, "selected_accounts": [], "room_history": []}'''
content = content.replace(old_load, new_load)
print("1. load_watch_config: 添加room_history默认值")

# ========== 2. 修改save_watch_config：保存room_history ==========
old_save = '''    def save_watch_config(self):
        try:
            self.watch_config["room_id"] = self.room_entry.get().strip()
            self.watch_config["daily_minutes"] = self.duration_var.get()
            self.watch_config["heartbeat_interval"] = self.interval_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.watch_config["selected_accounts"] = selected
            config_file = BASE_DIR / "watch_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.watch_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass'''
new_save = '''    def save_watch_config(self):
        try:
            current_room = self.room_combo.get().strip()
            # 如果是纯数字直播间号，保存到历史记录
            if current_room and current_room.isdigit() and current_room not in self.watch_config.get("room_history", []):
                history = self.watch_config.get("room_history", [])
                history.insert(0, current_room)
                self.watch_config["room_history"] = history[:20]  # 最多保存20条
                self._refresh_room_combo_values()
            self.watch_config["room_id"] = current_room
            self.watch_config["daily_minutes"] = self.duration_var.get()
            self.watch_config["heartbeat_interval"] = self.interval_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.watch_config["selected_accounts"] = selected
            config_file = BASE_DIR / "watch_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.watch_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass'''
content = content.replace(old_save, new_save)
print("2. save_watch_config: 保存room_history")

# ========== 3. 修改apply_watch_config：恢复Combobox值 ==========
old_apply = '''    def apply_watch_config(self):
        try:
            self.room_entry.delete(0, tk.END)
            self.room_entry.insert(0, self.watch_config.get("room_id", ""))
            self.duration_var.set(self.watch_config.get("daily_minutes", 30))
            self.interval_var.set(self.watch_config.get("heartbeat_interval", 60))
            selected_names = self.watch_config.get("selected_accounts", [])
            # 如果配置中没有选中的账户（首次使用），默认全选
            if not selected_names:
                for name, var in self.account_vars.items():
                    var.set(True)
            else:
                for name, var in self.account_vars.items():
                    var.set(name in selected_names)
        except Exception:
            pass'''
new_apply = '''    def apply_watch_config(self):
        try:
            self._refresh_room_combo_values()
            self.room_combo.set(self.watch_config.get("room_id", ""))
            self.duration_var.set(self.watch_config.get("daily_minutes", 30))
            self.interval_var.set(self.watch_config.get("heartbeat_interval", 60))
            selected_names = self.watch_config.get("selected_accounts", [])
            # 如果配置中没有选中的账户（首次使用），默认全选
            if not selected_names:
                for name, var in self.account_vars.items():
                    var.set(True)
            else:
                for name, var in self.account_vars.items():
                    var.set(name in selected_names)
        except Exception:
            pass'''
content = content.replace(old_apply, new_apply)
print("3. apply_watch_config: 恢复Combobox值")

# ========== 4. 修改bind_auto_save：绑定Combobox事件 ==========
old_bind = '''    def bind_auto_save(self):
        try:
            self.room_entry.bind("<KeyRelease>", lambda e: self.save_watch_config())
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
        except Exception:
            pass

    def _refresh_room_combo_values(self):
        """刷新直播间下拉框选项：用户直播间 + 历史记录"""
        values = []
        # 添加所有用户的直播间选项
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            mid = acc.get("DedeUserID", "")
            values.append(f"【{name}】直播间")
        # 添加历史记录分隔
        if self.watch_config.get("room_history"):
            values.append("--- 历史记录 ---")
            values.extend(self.watch_config["room_history"])
        self.room_combo["values"] = values

    def _on_room_selected(self, event=None):
        """选择直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.room_combo.get().strip()
        if selected.startswith("【") and "】直播间" in selected:
            # 提取用户名
            name = selected[1:selected.index("】")]
            # 找到对应用户
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", "")
                    if mid:
                        room_id = self.get_user_room_id(mid)
                        if room_id:
                            self.room_combo.set(str(room_id))
                            self.log(f"已获取「{name}」的直播间号: {room_id}")
                        else:
                            self.log(f"获取「{name}」直播间号失败，请手动输入")
                    break
        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        self.save_watch_config()

    def get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                room_id = data["data"].get("roomid")
                if room_id and data["data"].get("roomStatus") == 1:
                    return room_id
        except Exception:
            pass
        return None'''
content = content.replace(old_bind, new_bind)
print("4. bind_auto_save: 添加用户直播间获取和历史记录")

# ========== 5. 修改build_ui中的直播间号输入框 ==========
old_room_ui = '''        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间号(多号逗号):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_entry = DarkEntry(row1, width=24)
        self.room_entry.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(row1, text="每日时长(分):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.duration_var = tk.IntVar(value=30)
        self.duration_combo = ttk.Combobox(row1, textvariable=self.duration_var, width=8, values=[10, 15, 20, 30, 45, 60, 90, 120], state="readonly")
        self.duration_combo.pack(side=tk.LEFT, padx=(8, 0))'''
new_room_ui = '''        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(row1, text="每日时长(分):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.duration_var = tk.IntVar(value=30)
        self.duration_combo = ttk.Combobox(row1, textvariable=self.duration_var, width=8, values=[10, 15, 20, 30, 45, 60, 90, 120], state="readonly")
        self.duration_combo.pack(side=tk.LEFT, padx=(8, 0))'''
content = content.replace(old_room_ui, new_room_ui)
print("5. build_ui: 直播间输入框改成Combobox")

# ========== 6. 修改start_watch中的room_input获取 ==========
old_start_room = '''        room_input = self.room_entry.get().strip()
        if not room_input:
            messagebox.showwarning("提示", "请输入直播间号")
            return'''
new_start_room = '''        room_input = self.room_combo.get().strip()
        if not room_input:
            messagebox.showwarning("提示", "请选择或输入直播间号")
            return'''
content = content.replace(old_start_room, new_start_room)
print("6. start_watch: room_entry改成room_combo")

# ========== 7. 修改start_watch中的禁用/启用 ==========
old_disable_room = '''        self.room_entry.config(state=tk.DISABLED)'''
new_disable_room = '''        self.room_combo.config(state=tk.DISABLED)'''
content = content.replace(old_disable_room, new_disable_room)
print("7. start_watch: 禁用room_combo")

# ========== 8. 修改stop_watch中的启用 ==========
old_enable_room = '''        self.room_entry.config(state=tk.NORMAL)'''
new_enable_room = '''        self.room_combo.config(state="normal")'''
content = content.replace(old_enable_room, new_enable_room)
print("8. stop_watch: 启用room_combo")

# ========== 9. 修改_on_watch_finished中的启用 ==========
old_finish_room = '''        self.room_entry.config(state=tk.NORMAL)'''
new_finish_room = '''        self.room_combo.config(state="normal")'''
content = content.replace(old_finish_room, new_finish_room)
print("9. _on_watch_finished: 启用room_combo")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n修改完成！")
