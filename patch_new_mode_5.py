with open('main_gui_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        # 同时写主日志文件
        self.log(msg)

    def on_version_change(self):'''

new = '''        # 同时写主日志文件
        self.log(msg)

    # ========== 新模式·任务组管理 ==========
    def refresh_new_mode_group_list(self):
        """刷新任务组下拉列表"""
        group_names = [g["group_name"] for g in self.rush_groups]
        self.nm_group_combo.config(values=group_names)
        self.nm_current_group_combo.config(values=group_names)
        if self.rush_groups and not self.current_group_id:
            self.current_group_id = self.rush_groups[0]["group_id"]
        if self.current_group_id:
            current = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
            if current:
                self.nm_group_var.set(current["group_name"])
                self.nm_current_group_var.set(current["group_name"])
                self.nm_target_time_var.set(current.get("target_time", "00:00:00.000"))

    def refresh_new_mode_task_list(self):
        """刷新组内任务列表"""
        # 清空现有列表
        for widget in self.nm_task_list_frame.winfo_children():
            widget.destroy()
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        tasks = sorted(group.get("tasks", []), key=lambda t: t.get("priority", 99))
        for i, task in enumerate(tasks):
            row = tk.Frame(self.nm_task_list_frame, bg=COLORS["bg_card"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=str(task.get("priority", i+1)), bg=COLORS["bg_card"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"), width=5).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("name", "")[:30], bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 10), width=28, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("award", "")[:12], bg=COLORS["bg_card"],
                     fg=COLORS["success"], font=("微软雅黑", 10), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=f"{task.get('window_seconds', 15)}秒", bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=6).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("account_name", "")[:10], bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            # 操作按钮
            btn_frame = tk.Frame(row, bg=COLORS["bg_card"])
            btn_frame.pack(side=tk.LEFT, padx=5)
            tk.Button(btn_frame, text="↑", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                      font=("微软雅黑", 9), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_move_task(tid, -1)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="↓", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                      font=("微软雅黑", 9), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_move_task(tid, 1)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="×", bg="#c0392b", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_remove_task(tid)).pack(side=tk.LEFT, padx=1)

    def nm_update_task_list(self):
        """更新新模式任务下拉列表"""
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        task_type = self.nm_type_var.get()
        tasks = [t for t in ALL_TASKS if t["version"] == version and t["period"] == period and t["type"] == task_type]
        task_names = [f"{t['name']} => {t['award']}" for t in tasks]
        self.nm_task_combo.config(values=task_names)
        if task_names:
            self.nm_task_var.set(task_names[0])
        # 更新账户列表
        accounts = self.account_mgr.get_all_accounts()
        account_names = [a["name"] for a in accounts]
        self.nm_account_combo.config(values=account_names)
        if account_names and not self.nm_account_var.get():
            self.nm_account_var.set(account_names[0])

    def nm_on_group_change(self):
        """任务组切换"""
        group_name = self.nm_current_group_var.get()
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if group:
            self.current_group_id = group["group_id"]
            self.nm_target_time_var.set(group.get("target_time", "00:00:00.000"))
            self.refresh_new_mode_task_list()

    def nm_new_group(self):
        """新建任务组"""
        from tkinter import simpledialog
        name = simpledialog.askstring("新建任务组", "请输入任务组名称:", parent=self)
        if not name:
            return
        group_id = f"group_{int(time.time())}"
        new_group = {
            "group_id": group_id,
            "group_name": name,
            "target_time": "00:00:00.000",
            "tasks": []
        }
        self.rush_groups.append(new_group)
        self.current_group_id = group_id
        self.save_rush_groups()
        self.refresh_new_mode_group_list()
        self.refresh_new_mode_task_list()
        self.nm_log(f"新建任务组: {name}")

    def nm_del_group(self):
        """删除当前任务组"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        from tkinter import messagebox
        if not messagebox.askyesno("确认删除", f"确定删除任务组「{group['group_name']}」吗？"):
            return
        self.rush_groups = [g for g in self.rush_groups if g["group_id"] != self.current_group_id]
        self.current_group_id = self.rush_groups[0]["group_id"] if self.rush_groups else None
        self.save_rush_groups()
        self.refresh_new_mode_group_list()
        self.refresh_new_mode_task_list()
        self.nm_log(f"删除任务组: {group['group_name']}")

    def nm_add_task(self):
        """添加任务到当前组"""
        if not self.current_group_id:
            self.nm_log("请先选择或创建任务组")
            return
        task_text = self.nm_task_var.get()
        if not task_text:
            self.nm_log("请选择任务")
            return
        account_name = self.nm_account_var.get()
        if not account_name:
            self.nm_log("请选择账户")
            return
        # 从ALL_TASKS找到对应任务
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        task_type = self.nm_type_var.get()
        task = None
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] == period and t["type"] == task_type and f"{t['name']} => {t['award']}" == task_text:
                task = t
                break
        if not task:
            self.nm_log("未找到对应任务")
            return
        try:
            priority = int(self.nm_priority_entry.get())
        except ValueError:
            priority = 1
        try:
            window_seconds = int(self.nm_window_entry.get())
        except ValueError:
            window_seconds = 15
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            # 检查是否已存在
            if any(t["task_id"] == task["task_id"] for t in group["tasks"]):
                self.nm_log(f"任务已存在: {task['name']}")
                return
            group["tasks"].append({
                "task_id": task["task_id"],
                "name": task["name"],
                "award": task["award"],
                "period": task["period"],
                "type": task["type"],
                "version": task["version"],
                "account_name": account_name,
                "priority": priority,
                "window_seconds": window_seconds
            })
            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"添加任务: {task['name']} (优先级{priority}, 窗口期{window_seconds}秒)")

    def nm_remove_task(self, task_id):
        """从组中删除任务"""
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            group["tasks"] = [t for t in group["tasks"] if t["task_id"] != task_id]
            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"删除任务: {task_id}")

    def nm_move_task(self, task_id, direction):
        """调整任务优先级（上移/下移）"""
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        tasks = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
        idx = next((i for i, t in enumerate(tasks) if t["task_id"] == task_id), -1)
        if idx < 0:
            return
        swap_idx = idx + direction
        if swap_idx < 0 or swap_idx >= len(tasks):
            return
        # 交换优先级
        p1 = tasks[idx].get("priority", idx)
        p2 = tasks[swap_idx].get("priority", swap_idx)
        tasks[idx]["priority"] = p2
        tasks[swap_idx]["priority"] = p1
        self.save_rush_groups()
        self.refresh_new_mode_task_list()

    def nm_save_group_settings(self):
        """保存任务组设置"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            group["target_time"] = self.nm_target_time_var.get()
            self.save_rush_groups()
            self.nm_log(f"任务组设置已保存: 目标时间={group['target_time']}")

    # ========== 新模式·精准抢码核心逻辑 ==========
    def nm_start_rush(self):
        """启动精准抢码"""
        if not self.current_group_id:
            self.nm_log("请先选择任务组")
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group or not group.get("tasks"):
            self.nm_log("任务组为空，请先添加任务")
            return
        if self.new_mode_running:
            self.nm_log("抢码已在运行中")
            return
        self.new_mode_running = True
        self.new_mode_stop_flag = {"stop": False}
        self.nm_start_btn.config(state=tk.DISABLED)
        self.nm_stop_btn.config(state=tk.NORMAL)
        self.nm_status_label.config(text="● 运行中", fg=COLORS["success"])
        self.nm_log("=" * 50)
        self.nm_log(f"启动精准抢码: {group['group_name']}")
        self.nm_log(f"目标时间: {group['target_time']}")
        self.nm_log(f"任务数量: {len(group['tasks'])}")
        self.new_mode_thread = threading.Thread(target=self.nm_rush_worker, args=(group,), daemon=True)
        self.new_mode_thread.start()

    def nm_stop_rush(self):
        """停止精准抢码"""
        self.new_mode_stop_flag["stop"] = True
        self.nm_log("收到停止指令，等待当前请求完成后停止...")

    def nm_rush_worker(self, group):
        """精准抢码核心线程"""
        try:
            target_time_str = group.get("target_time", "00:00:00.000")
            # 解析目标时间（支持毫秒）
            parts = target_time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            sec_parts = parts[2].split(".")
            second = int(sec_parts[0])
            millisecond = int(sec_parts[1]) if len(sec_parts) > 1 else 0

            now = time.localtime()
            target_timestamp = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hour, minute, second, 0, 0, -1)) + millisecond / 1000.0
            if target_timestamp < time.time():
                target_timestamp += 86400  # 等到明天

            wait_seconds = target_timestamp - time.time()
            self.nm_log(f"等待 {wait_seconds:.1f} 秒后开始（目标: {time.strftime('%H:%M:%S', time.localtime(target_timestamp))}）")

            # ===== 阶段1: NTP同步（抢码前1分钟或立即）=====
            if wait_seconds > 60:
                # 等到抢码前1分钟再同步
                sync_time = target_timestamp - 60
                while time.time() < sync_time and not self.new_mode_stop_flag["stop"]:
                    time.sleep(1)
                if not self.new_mode_stop_flag["stop"]:
                    self.nm_ntp_sync()
            else:
                self.nm_ntp_sync()

            # ===== 阶段2: 等待到目标时间前3秒，连接预热 =====
            prewarm_time = target_timestamp - 3
            while time.time() < prewarm_time and not self.new_mode_stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if int(remaining) % 10 == 0 and int(remaining) > 0:
                    self.nm_log(f"  还剩 {int(remaining)} 秒...")
                time.sleep(0.5)

            if self.new_mode_stop_flag["stop"]:
                self.nm_log("抢码已取消")
                return

            # 连接预热：提前3秒获取任务信息并建立连接
            self.nm_log("[连接预热] 提前3秒建立连接并获取任务信息...")
            sessions = {}
            task_infos = {}
            for task in sorted(group["tasks"], key=lambda t: t.get("priority", 99)):
                account = self.account_mgr.get_account(task["account_name"])
                if not account:
                    self.nm_log(f"  ⚠ 账户不存在: {task['account_name']}")
                    continue
                cookies = cookies_from_account(account)
                session = requests.Session()
                session.headers.update(HEADERS)
                sessions[task["task_id"]] = session
                try:
                    info, msg = get_mission_info(task["task_id"], cookies)
                    if info:
                        task_infos[task["task_id"]] = info
                        self.nm_log(f"  ✓ {task['name']}: act_id={info.get('act_id', '')}")
                    else:
                        self.nm_log(f"  ⚠ {task['name']}: 获取任务信息失败: {msg}")
                except Exception as e:
                    self.nm_log(f"  ⚠ {task['name']}: 预热异常: {e}")

            # ===== 阶段3: 精准首发（自旋等待到目标时间-50ms）=====
            fire_time = target_timestamp - 0.05  # 提前50ms发送，补偿网络延迟
            self.nm_log(f"[精准首发] 目标 {target_time_str}，提前50ms发送，自旋等待中...")

            while time.time() < fire_time and not self.new_mode_stop_flag["stop"]:
                remaining = fire_time - time.time()
                if remaining > 0.1:
                    time.sleep(remaining / 2)
                elif remaining > 0.01:
                    time.sleep(0.001)
                # 小于10ms时自旋，不sleep

            if self.new_mode_stop_flag["stop"]:
                self.nm_log("抢码已取消")
                return

            actual_fire = time.time()
            self.nm_log(f"[精准首发] 发送！目标偏差: {(actual_fire - target_timestamp)*1000:.1f}ms")

            # ===== 阶段4: 按优先级依次执行任务 =====
            tasks_sorted = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
            for task in tasks_sorted:
                if self.new_mode_stop_flag["stop"]:
                    break

                task_deadline = target_timestamp + task.get("window_seconds", 15)
                if time.time() > task_deadline:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] {task['name']} 已过窗口期，跳过")
                    continue

                self.nm_log(f"[优先级{task.get('priority', '?')}] 开始: {task['name']} => {task['award']} (窗口期{task.get('window_seconds', 15)}秒)")

                success = self.nm_execute_task(task, task_infos.get(task["task_id"]),
                                               sessions.get(task["task_id"]), task_deadline)

                if success:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] ✓ 领取成功，立即启动下一个优先级")
                else:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] ✗ 未成功，启动下一个优先级")

            self.nm_log("=" * 50)
            self.nm_log("精准抢码全部结束")

        except Exception as e:
            self.nm_log(f"抢码异常: {e}")
            import traceback
            self.nm_log(traceback.format_exc())
        finally:
            self.new_mode_running = False
            try:
                self.after(0, lambda: self.nm_start_btn.config(state=tk.NORMAL))
                self.after(0, lambda: self.nm_stop_btn.config(state=tk.DISABLED))
                self.after(0, lambda: self.nm_status_label.config(text="● 未运行", fg=COLORS["text_muted"]))
            except Exception:
                pass

    def nm_ntp_sync(self):
        """NTP时间同步"""
        try:
            import ntplib
            client = ntplib.NTPClient()
            # 尝试多个NTP服务器
            for server in ["ntp.aliyun.com", "ntp.tencent.com", "cn.pool.ntp.org"]:
                try:
                    response = client.request(server, version=3, timeout=3)
                    offset = response.offset
                    self.nm_log(f"[NTP同步] 服务器={server}, 偏差={offset*1000:.1f}ms")
                    if abs(offset) > 0.5:
                        self.nm_log(f"[NTP同步] 偏差较大，建议手动同步系统时间")
                    return offset
                except Exception:
                    continue
            self.nm_log("[NTP同步] 所有NTP服务器均不可用，使用本地时间")
        except ImportError:
            self.nm_log("[NTP同步] ntplib未安装，跳过同步")
        except Exception as e:
            self.nm_log(f"[NTP同步] 异常: {e}")
        return 0

    def nm_execute_task(self, task, task_info, session, deadline):
        """执行单个任务的抢码（带风控递增延迟）"""
        account = self.account_mgr.get_account(task["account_name"])
        if not account:
            self.nm_log(f"  账户不存在: {task['account_name']}")
            return False

        cookies = cookies_from_account(account)
        if not task_info:
            task_info = self.build_task_info_from_task(task)

        # 预生成随机延迟增量（风控后递增用）
        import random
        random_increments = [random.randint(20, 40) for _ in range(50)]

        base_interval = 0.7  # 基础700ms
        current_interval = base_interval
        attempt = 0
        success = False

        while time.time() < deadline and not self.new_mode_stop_flag["stop"]:
            attempt += 1
            try:
                ok, msg = self.do_receive_fast(task, task_info, account)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.nm_log(f"  🎉 第{attempt}次: 领取成功！({task['account_name']})")
                self.nm_log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                break
            else:
                # 判断是否是未到领奖时间（202120），这种情况不切下一个优先级
                if "202120" in msg or "未到领取时间" in msg or "未到领奖时间" in msg:
                    self.nm_log(f"  第{attempt}次: 未到领取时间，继续等待... ({msg[:30]})")
                elif "75255" in msg or "库存已经使用完" in msg or "库存已使用完" in msg:
                    self.nm_log(f"  第{attempt}次: 库存已使用完，切下一个优先级")
                    break
                elif "-705" in msg or "-509" in msg or "-702" in msg or "请求过于频繁" in msg or "请求频率过高" in msg:
                    # 风控，递增延迟
                    increment = random_increments[min(attempt - 1, len(random_increments) - 1)] / 1000.0
                    current_interval = min(current_interval + increment, 1.0)  # 上限1000ms
                    self.nm_log(f"  第{attempt}次: 风控 {msg[:25]}，下次间隔 {current_interval*1000:.0f}ms")
                else:
                    self.nm_log(f"  第{attempt}次: {msg[:40]}")

            # 等待到下次尝试（窗口期结束时等当前请求返回后停止）
            next_time = time.time() + current_interval
            while time.time() < next_time and time.time() < deadline and not self.new_mode_stop_flag["stop"]:
                time.sleep(0.001)

        if not success and time.time() >= deadline:
            self.nm_log(f"  窗口期结束，共尝试{attempt}次")
        return success

    def on_version_change(self):'''

if old in content:
    content = content.replace(old, new, 1)
    with open('main_gui_pro.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("新模式核心逻辑添加完成")
else:
    print("未找到匹配位置")
