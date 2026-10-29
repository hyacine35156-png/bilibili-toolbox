file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 修改__init__方法：添加account_vars
old_init = '''    def __init__(self, parent, account_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.running = False
        self.watch_thread = None
        self.stop_flag = {"stop": False}
        self.account_stats = {}
        self.watch_config = self.load_watch_config()
        self.build_ui()
        self.refresh_account_list()
        self.apply_watch_config()
        self.bind_auto_save()
        self.log("看播任务工具已启动，选择账户和直播间后点击「开始看播」")'''

new_init = '''    def __init__(self, parent, account_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.running = False
        self.watch_thread = None
        self.stop_flag = {"stop": False}
        self.account_stats = {}
        self.account_vars = {}  # 每个账户名对应一个BooleanVar
        self.account_checkbuttons = []  # 复选框列表，用于启用/禁用
        self.watch_config = self.load_watch_config()
        self.build_ui()
        self.refresh_account_list()
        self.apply_watch_config()
        self.bind_auto_save()
        self.log("看播任务工具已启动，勾选账户和直播间后点击「开始看播」")'''

if old_init in content:
    content = content.replace(old_init, new_init, 1)
    print("✓ __init__方法已修改")
else:
    print("✗ 未找到__init__方法")

# 2. 修改save_watch_config方法：从BooleanVar获取选中账户
old_save = '''    def save_watch_config(self):
        try:
            self.watch_config["room_id"] = self.room_entry.get().strip()
            self.watch_config["daily_minutes"] = self.duration_var.get()
            self.watch_config["heartbeat_interval"] = self.interval_var.get()
            selected = []
            for i in self.account_listbox.curselection():
                if i < len(self.account_mgr.accounts):
                    selected.append(self.account_mgr.accounts[i].get("name", ""))
            self.watch_config["selected_accounts"] = selected
            config_file = BASE_DIR / "watch_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.watch_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass'''

new_save = '''    def save_watch_config(self):
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

if old_save in content:
    content = content.replace(old_save, new_save, 1)
    print("✓ save_watch_config方法已修改")
else:
    print("✗ 未找到save_watch_config方法")

# 3. 修改apply_watch_config方法：直接设置BooleanVar
old_apply = '''    def apply_watch_config(self):
        try:
            self.room_entry.delete(0, tk.END)
            self.room_entry.insert(0, self.watch_config.get("room_id", ""))
            self.duration_var.set(self.watch_config.get("daily_minutes", 30))
            self.interval_var.set(self.watch_config.get("heartbeat_interval", 60))
            selected_names = self.watch_config.get("selected_accounts", [])
            if selected_names:
                self.after(300, lambda: self._restore_selected(selected_names))
        except Exception:
            pass

    def _restore_selected(self, names):
        try:
            self.account_listbox.selection_clear(0, tk.END)
            for i, acc in enumerate(self.account_mgr.accounts):
                if acc.get("name", "") in names:
                    self.account_listbox.selection_set(i)
        except Exception:
            pass'''

new_apply = '''    def apply_watch_config(self):
        try:
            self.room_entry.delete(0, tk.END)
            self.room_entry.insert(0, self.watch_config.get("room_id", ""))
            self.duration_var.set(self.watch_config.get("daily_minutes", 30))
            self.interval_var.set(self.watch_config.get("heartbeat_interval", 60))
            selected_names = self.watch_config.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected_names)
        except Exception:
            pass'''

if old_apply in content:
    content = content.replace(old_apply, new_apply, 1)
    print("✓ apply_watch_config方法已修改（删除_restore_selected）")
else:
    print("✗ 未找到apply_watch_config方法")

# 4. 修改bind_auto_save方法：复选框点击时保存
old_bind = '''    def bind_auto_save(self):
        try:
            self.room_entry.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.account_listbox.bind("<<ListboxSelect>>", lambda e: self.save_watch_config())
        except Exception:
            pass'''

new_bind = '''    def bind_auto_save(self):
        try:
            self.room_entry.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
        except Exception:
            pass

    def _on_account_check(self):
        """复选框点击时保存配置"""
        self.save_watch_config()'''

if old_bind in content:
    content = content.replace(old_bind, new_bind, 1)
    print("✓ bind_auto_save方法已修改")
else:
    print("✗ 未找到bind_auto_save方法")

# 5. 修改build_ui方法中的账户列表部分：从Listbox改成复选框滚动区域
old_ui_account = '''        # 左侧账户
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=220)
        tk.Label(left_card, text="选择看播账户", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（可多选，Ctrl+点击）", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))
        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)
        self.account_listbox = tk.Listbox(list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"], selectbackground=COLORS["accent"], selectforeground="#000000", font=("微软雅黑", 9), bd=0, highlightthickness=0, activestyle="none", exportselection=False, selectmode=tk.EXTENDED)
        self.account_listbox.pack(fill=tk.BOTH, expand=True)'''

new_ui_account = '''        # 左侧账户（复选框多选）
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=220)
        tk.Label(left_card, text="选择看播账户", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（打钩多选，可全选）", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))
        # 全选/取消全选按钮
        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.select_all_btn = tk.Button(btn_frame, text="全选", bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2", command=self._select_all_accounts)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.deselect_all_btn = tk.Button(btn_frame, text="取消全选", bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2", command=self._deselect_all_accounts)
        self.deselect_all_btn.pack(side=tk.LEFT)
        # 复选框滚动区域
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

if old_ui_account in content:
    content = content.replace(old_ui_account, new_ui_account, 1)
    print("✓ build_ui账户列表部分已修改为复选框")
else:
    print("✗ 未找到build_ui账户列表部分")

# 6. 修改refresh_account_list方法：刷新复选框
old_refresh = '''    def refresh_account_list(self):
        self.account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            self.account_listbox.insert(tk.END, acc.get("name", "未知账户"))
        self.refresh_status_tree()'''

new_refresh = '''    def refresh_account_list(self):
        # 清空旧的复选框
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        self.account_vars.clear()
        self.account_checkbuttons.clear()
        # 创建新的复选框
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            var = tk.BooleanVar(value=False)
            self.account_vars[name] = var
            cb = tk.Checkbutton(self.account_scrollable_frame, text=name, variable=var,
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["accent"], activebackground=COLORS["bg_input"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 9),
                                anchor="w", padx=8, pady=4, command=self._on_account_check)
            cb.pack(fill=tk.X, anchor="w")
            self.account_checkbuttons.append(cb)
        self.refresh_status_tree()

    def _select_all_accounts(self):
        for var in self.account_vars.values():
            var.set(True)
        self.save_watch_config()

    def _deselect_all_accounts(self):
        for var in self.account_vars.values():
            var.set(False)
        self.save_watch_config()'''

if old_refresh in content:
    content = content.replace(old_refresh, new_refresh, 1)
    print("✓ refresh_account_list方法已修改")
else:
    print("✗ 未找到refresh_account_list方法")

# 7. 修改start_watch方法：从BooleanVar获取选中账户
old_start = '''    def start_watch(self):
        if self.running:
            return
        room_input = self.room_entry.get().strip()
        if not room_input:
            messagebox.showwarning("提示", "请输入直播间号")
            return
        # 解析多个直播间号（逗号、空格、分号分隔）
        room_ids = []
        for r in room_input.replace("，", ",").replace(";", ",").replace(" ", ",").split(","):
            r = r.strip()
            if r and r.isdigit():
                room_ids.append(r)
        if not room_ids:
            messagebox.showwarning("提示", "请输入有效的直播间号（数字），多个用逗号分隔")
            return
        selected_indices = self.account_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请至少选择一个账户")
            return
        selected_accounts = [self.account_mgr.accounts[i] for i in selected_indices]
        self.running = True
        self.stop_flag = {"stop": False}
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.room_entry.config(state=tk.DISABLED)
        self.duration_combo.config(state=tk.DISABLED)
        self.interval_combo.config(state=tk.DISABLED)
        self.account_listbox.config(state=tk.DISABLED)
        self.account_stats = {}
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            self.account_stats[name] = {"watch_seconds": 0, "heartbeat_count": 0, "status": "进入中", "last_heartbeat": None, "account": acc}
        room_display = ", ".join(room_ids)
        self.log(f"开始看播，直播间: {room_display}（共{len(room_ids)}个），账户: {len(selected_accounts)}个")
        self.log(f"目标时长: {self.duration_var.get()} 分钟，心跳间隔: {self.interval_var.get()} 秒")
        self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_ids, selected_accounts), daemon=True)
        self.watch_thread.start()'''

new_start = '''    def start_watch(self):
        if self.running:
            return
        room_input = self.room_entry.get().strip()
        if not room_input:
            messagebox.showwarning("提示", "请输入直播间号")
            return
        # 解析多个直播间号（逗号、空格、分号分隔）
        room_ids = []
        for r in room_input.replace("，", ",").replace(";", ",").replace(" ", ",").split(","):
            r = r.strip()
            if r and r.isdigit():
                room_ids.append(r)
        if not room_ids:
            messagebox.showwarning("提示", "请输入有效的直播间号（数字），多个用逗号分隔")
            return
        # 从复选框获取选中账户
        selected_names = [name for name, var in self.account_vars.items() if var.get()]
        if not selected_names:
            messagebox.showwarning("提示", "请至少勾选一个账户")
            return
        selected_accounts = [acc for acc in self.account_mgr.accounts if acc.get("name", "") in selected_names]
        if not selected_accounts:
            messagebox.showwarning("提示", "未找到选中的账户")
            return
        self.running = True
        self.stop_flag = {"stop": False}
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.room_entry.config(state=tk.DISABLED)
        self.duration_combo.config(state=tk.DISABLED)
        self.interval_combo.config(state=tk.DISABLED)
        # 禁用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.DISABLED)
        self.select_all_btn.config(state=tk.DISABLED)
        self.deselect_all_btn.config(state=tk.DISABLED)
        self.account_stats = {}
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            self.account_stats[name] = {"watch_seconds": 0, "heartbeat_count": 0, "status": "进入中", "last_heartbeat": None, "account": acc}
        room_display = ", ".join(room_ids)
        self.log(f"开始看播，直播间: {room_display}（共{len(room_ids)}个），账户: {len(selected_accounts)}个")
        self.log(f"目标时长: {self.duration_var.get()} 分钟，心跳间隔: {self.interval_var.get()} 秒")
        self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_ids, selected_accounts), daemon=True)
        self.watch_thread.start()'''

if old_start in content:
    content = content.replace(old_start, new_start, 1)
    print("✓ start_watch方法已修改")
else:
    print("✗ 未找到start_watch方法")

# 8. 修改stop_watch方法：启用复选框
old_stop = '''    def stop_watch(self):
        if not self.running:
            return
        self.stop_flag["stop"] = True
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        self.account_listbox.config(state=tk.NORMAL)
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")'''

new_stop = '''    def stop_watch(self):
        if not self.running:
            return
        self.stop_flag["stop"] = True
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")'''

if old_stop in content:
    content = content.replace(old_stop, new_stop, 1)
    print("✓ stop_watch方法已修改")
else:
    print("✗ 未找到stop_watch方法")

# 9. 修改_on_watch_finished方法：启用复选框
old_finished = '''    def _on_watch_finished(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")'''

new_finished = '''    def _on_watch_finished(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)'''

if old_finished in content:
    content = content.replace(old_finished, new_finished, 1)
    print("✓ _on_watch_finished方法已修改")
else:
    print("✗ 未找到_on_watch_finished方法")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 文件已保存")
