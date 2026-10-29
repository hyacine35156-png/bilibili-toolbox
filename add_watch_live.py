import re

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# WatchLiveFrame类代码
watch_live_class = '''
# ========== 看播任务工具 ==========
class WatchLiveFrame(tk.Frame):
    """看播任务工具：模拟观看B站直播间，完成看播里程碑任务"""

    ROOM_ENTRY_API = "https://api.live.bilibili.com/room/v1/Room/room_entry_action"
    HEARTBEAT_API = "https://api.live.bilibili.com/relation/v1/Feed/heartBeat"

    def __init__(self, parent, account_mgr):
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
        self.log("看播任务工具已启动，选择账户和直播间后点击「开始看播」")

    def load_watch_config(self):
        default = {"room_id": "", "daily_minutes": 30, "heartbeat_interval": 60, "selected_accounts": []}
        config_file = BASE_DIR / "watch_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default.update(cfg)
            except Exception:
                pass
        return default

    def save_watch_config(self):
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
            pass

    def apply_watch_config(self):
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
            pass

    def bind_auto_save(self):
        try:
            self.room_entry.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.account_listbox.bind("<<ListboxSelect>>", lambda e: self.save_watch_config())
        except Exception:
            pass

    def on_close(self):
        self.stop_watch()
        self.save_watch_config()

    def build_ui(self):
        main = tk.Frame(self, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True)

        # 左侧账户
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=220)
        tk.Label(left_card, text="选择看播账户", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（可多选，Ctrl+点击）", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))
        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)
        self.account_listbox = tk.Listbox(list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"], selectbackground=COLORS["accent"], selectforeground="#000000", font=("微软雅黑", 9), bd=0, highlightthickness=0, activestyle="none", exportselection=False, selectmode=tk.EXTENDED)
        self.account_listbox.pack(fill=tk.BOTH, expand=True)

        # 右侧
        right = tk.Frame(main, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # 设置卡片
        settings_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(settings_card, text="看播设置", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间号:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_entry = DarkEntry(row1, width=16)
        self.room_entry.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(row1, text="每日时长(分):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.duration_var = tk.IntVar(value=30)
        self.duration_combo = ttk.Combobox(row1, textvariable=self.duration_var, width=8, values=[10, 15, 20, 30, 45, 60, 90, 120], state="readonly")
        self.duration_combo.pack(side=tk.LEFT, padx=(8, 0))

        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="心跳间隔(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(value=60)
        self.interval_combo = ttk.Combobox(row2, textvariable=self.interval_var, width=8, values=[30, 45, 50, 60, 70, 90, 120], state="readonly")
        self.interval_combo.pack(side=tk.LEFT, padx=(8, 20))
        self.start_btn = DarkButton(row2, "▶ 开始看播", command=self.start_watch, width=120, height=32, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = DarkButton(row2, "■ 停止看播", command=self.stop_watch, width=120, height=32, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT)
        self.stop_btn.config(state=tk.DISABLED)

        # 状态卡片
        status_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        status_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(status_card, text="观看状态", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        tree_frame = tk.Frame(status_card, bg=COLORS["bg_card"])
        tree_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        columns = ("account", "status", "watch_time", "heartbeat", "target")
        self.status_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=5)
        self.status_tree.heading("account", text="账户")
        self.status_tree.heading("status", text="状态")
        self.status_tree.heading("watch_time", text="已观看")
        self.status_tree.heading("heartbeat", text="心跳次数")
        self.status_tree.heading("target", text="目标时长")
        self.status_tree.column("account", width=140, anchor=tk.CENTER)
        self.status_tree.column("status", width=80, anchor=tk.CENTER)
        self.status_tree.column("watch_time", width=100, anchor=tk.CENTER)
        self.status_tree.column("heartbeat", width=80, anchor=tk.CENTER)
        self.status_tree.column("target", width=100, anchor=tk.CENTER)
        self.status_tree.pack(fill=tk.X)

        # 日志卡片
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))
        self.log_text = tk.Text(log_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("Consolas", 9), bd=0, highlightthickness=0, wrap=tk.WORD, insertbackground=COLORS["text_primary"])
        log_scroll = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(state=tk.DISABLED)

    def refresh_account_list(self):
        self.account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            self.account_listbox.insert(tk.END, acc.get("name", "未知账户"))
        self.refresh_status_tree()

    def refresh_status_tree(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            stats = self.account_stats.get(name, {"status": "待开始", "watch_seconds": 0, "heartbeat_count": 0})
            watch_min = stats.get("watch_seconds", 0) // 60
            watch_sec = stats.get("watch_seconds", 0) % 60
            self.status_tree.insert("", tk.END, values=(name, stats.get("status", "待开始"), f"{watch_min}分{watch_sec}秒", stats.get("heartbeat_count", 0), f"{self.duration_var.get()}分钟"))

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}\\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_msg)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def get_cookie(self, account):
        return f"SESSDATA={account.get('sessdata', '')}; bili_jct={account.get('bili_jct', '')}"

    def enter_room(self, account, room_id):
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}", "Origin": "https://live.bilibili.com", "Content-Type": "application/x-www-form-urlencoded"}
            data = {"room_id": room_id, "platform": "pc", "csrf": account.get("bili_jct", ""), "csrf_token": account.get("bili_jct", ""), "visit_id": ""}
            resp = requests.post(self.ROOM_ENTRY_API, headers=headers, data=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True, "进入直播间成功"
            return False, f"进入失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"进入异常: {e}"

    def send_heartbeat(self, account, room_id):
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}"}
            resp = requests.get(self.HEARTBEAT_API, headers=headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True, "心跳成功"
            return False, f"心跳失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"心跳异常: {e}"

    def start_watch(self):
        if self.running:
            return
        room_id = self.room_entry.get().strip()
        if not room_id:
            messagebox.showwarning("提示", "请输入直播间号")
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
        self.log(f"开始看播，直播间: {room_id}，共 {len(selected_accounts)} 个账户")
        self.log(f"目标时长: {self.duration_var.get()} 分钟，心跳间隔: {self.interval_var.get()} 秒")
        self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_id, selected_accounts), daemon=True)
        self.watch_thread.start()

    def stop_watch(self):
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
        self.log("已停止看播")

    def _watch_loop(self, room_id, selected_accounts):
        import random
        base_interval = self.interval_var.get()
        target_seconds = self.duration_var.get() * 60
        # 进入直播间
        for acc in selected_accounts:
            if self.stop_flag["stop"]:
                break
            name = acc.get("name", "未知")
            self.log(f"  [{name}] 正在进入直播间...")
            success, msg = self.enter_room(acc, room_id)
            if success:
                self.account_stats[name]["status"] = "观看中"
                self.account_stats[name]["heartbeat_count"] = 1
                self.log(f"  [{name}] ✓ {msg}")
            else:
                self.account_stats[name]["status"] = "进入失败"
                self.log(f"  [{name}] ✗ {msg}")
            self.refresh_status_tree()
            time.sleep(random.uniform(1, 3))
        # 心跳循环
        while not self.stop_flag["stop"]:
            all_done = True
            for name, stats in self.account_stats.items():
                if stats["status"] == "观看中" and stats["watch_seconds"] < target_seconds:
                    all_done = False
                    break
            if all_done:
                self.log("所有账户已达到目标观看时长，自动停止")
                break
            interval = base_interval * random.uniform(0.8, 1.2)
            wait_segments = int(interval)
            for _ in range(wait_segments):
                if self.stop_flag["stop"]:
                    break
                time.sleep(1)
                for name, stats in self.account_stats.items():
                    if stats["status"] == "观看中":
                        stats["watch_seconds"] += 1
                if int(time.time()) % 10 == 0:
                    self.refresh_status_tree()
            if self.stop_flag["stop"]:
                break
            for acc in selected_accounts:
                if self.stop_flag["stop"]:
                    break
                name = acc.get("name", "未知")
                stats = self.account_stats.get(name)
                if not stats or stats["status"] != "观看中":
                    continue
                if stats["watch_seconds"] >= target_seconds:
                    stats["status"] = "已完成"
                    self.log(f"  [{name}] ✓ 已达到目标时长 ({self.duration_var.get()}分钟)")
                    self.refresh_status_tree()
                    continue
                success, msg = self.send_heartbeat(acc, room_id)
                stats["heartbeat_count"] += 1
                stats["last_heartbeat"] = datetime.now()
                if success:
                    if stats["heartbeat_count"] % 5 == 0:
                        watch_min = stats["watch_seconds"] // 60
                        self.log(f"  [{name}] 心跳 #{stats['heartbeat_count']}，已观看 {watch_min} 分钟")
                else:
                    self.log(f"  [{name}] 心跳 #{stats['heartbeat_count']} 失败: {msg}")
                self.refresh_status_tree()
                time.sleep(random.uniform(0.5, 2))
        self.running = False
        self.after(100, self._on_watch_finished)

    def _on_watch_finished(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        self.account_listbox.config(state=tk.NORMAL)
        self.refresh_status_tree()
        self.log("看播任务结束")

'''

# 在"# ========== 主界面 =========="之前插入
insert_marker = "# ========== 主界面 =========="
if insert_marker in content:
    content = content.replace(insert_marker, watch_live_class + "\n" + insert_marker, 1)
    print("✓ WatchLiveFrame类已插入")
else:
    print("✗ 未找到插入点")

# 修改窗口标题
content = content.replace(
    'self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机")',
    'self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务")'
)
print("✓ 窗口标题已更新")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✓ 文件已保存")
