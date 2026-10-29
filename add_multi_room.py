file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 修改界面提示：直播间号支持多个（逗号分隔）
old_label = '''        tk.Label(row1, text="直播间号:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_entry = DarkEntry(row1, width=16)
        self.room_entry.pack(side=tk.LEFT, padx=(8, 20))'''

new_label = '''        tk.Label(row1, text="直播间号(多号逗号):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_entry = DarkEntry(row1, width=24)
        self.room_entry.pack(side=tk.LEFT, padx=(8, 20))'''

if old_label in content:
    content = content.replace(old_label, new_label, 1)
    print("✓ 界面提示已修改：支持多个直播间号（逗号分隔）")
else:
    print("✗ 未找到直播间号标签")

# 2. 修改start_watch方法：解析多个直播间号
old_start = '''    def start_watch(self):
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

if old_start in content:
    content = content.replace(old_start, new_start, 1)
    print("✓ start_watch方法已修改：支持多个直播间号")
else:
    print("✗ 未找到start_watch方法")

# 3. 修改_watch_loop方法：对每个直播间进入和发送心跳
old_loop = '''    def _watch_loop(self, room_id, selected_accounts):
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
        self.after(100, self._on_watch_finished)'''

new_loop = '''    def _watch_loop(self, room_ids, selected_accounts):
        import random
        base_interval = self.interval_var.get()
        target_seconds = self.duration_var.get() * 60
        # 进入所有直播间
        for acc in selected_accounts:
            if self.stop_flag["stop"]:
                break
            name = acc.get("name", "未知")
            entered_count = 0
            for rid in room_ids:
                if self.stop_flag["stop"]:
                    break
                self.log(f"  [{name}] 正在进入直播间 {rid}...")
                success, msg = self.enter_room(acc, rid)
                if success:
                    entered_count += 1
                    self.log(f"  [{name}] ✓ 直播间 {rid} {msg}")
                else:
                    self.log(f"  [{name}] ✗ 直播间 {rid} {msg}")
                time.sleep(random.uniform(0.5, 1.5))
            if entered_count > 0:
                self.account_stats[name]["status"] = "观看中"
                self.account_stats[name]["heartbeat_count"] = entered_count
            else:
                self.account_stats[name]["status"] = "进入失败"
            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))
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
                # 对每个直播间发送心跳
                for rid in room_ids:
                    if self.stop_flag["stop"]:
                        break
                    success, msg = self.send_heartbeat(acc, rid)
                    stats["heartbeat_count"] += 1
                    stats["last_heartbeat"] = datetime.now()
                    if not success:
                        self.log(f"  [{name}] 直播间{rid} 心跳失败: {msg}")
                    time.sleep(random.uniform(0.3, 0.8))
                if stats["heartbeat_count"] % (5 * len(room_ids)) < len(room_ids):
                    watch_min = stats["watch_seconds"] // 60
                    self.log(f"  [{name}] 心跳累计 #{stats['heartbeat_count']}，已观看 {watch_min} 分钟")
                self.refresh_status_tree()
                time.sleep(random.uniform(0.5, 2))
        self.running = False
        self.after(100, self._on_watch_finished)'''

if old_loop in content:
    content = content.replace(old_loop, new_loop, 1)
    print("✓ _watch_loop方法已修改：支持多直播间心跳")
else:
    print("✗ 未找到_watch_loop方法")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 文件已保存")
