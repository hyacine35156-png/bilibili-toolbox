#!/usr/bin/env python3
"""v4.4.6: 抢码新增"开始领取"按钮，点击后立即按上面设置的数据持续领取"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在按钮行新增"🚀 开始领取"按钮（在手动领取后面）
# ============================================================
old_buttons = '''        self.manual_receive_btn = DarkButton(btn_row, "🎯 手动领取", command=self.manual_receive,
                                              width=100, height=32, bg_color="#ff6b35", text_color="#ffffff")
        self.manual_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.schedule_receive_btn = DarkButton(btn_row, "⏰ 定时领取", command=self.schedule_receive,
                                                width=100, height=32, bg_color="#9b59b6", text_color="#ffffff")
        self.schedule_receive_btn.pack(side=tk.LEFT, padx=(8, 0))'''

new_buttons = '''        self.manual_receive_btn = DarkButton(btn_row, "🎯 手动领取", command=self.manual_receive,
                                              width=100, height=32, bg_color="#ff6b35", text_color="#ffffff")
        self.manual_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.start_receive_now_btn = DarkButton(btn_row, "🚀 开始领取", command=self.start_receive_now,
                                                 width=100, height=32, bg_color="#e74c3c", text_color="#ffffff")
        self.start_receive_now_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.schedule_receive_btn = DarkButton(btn_row, "⏰ 定时领取", command=self.schedule_receive,
                                                width=100, height=32, bg_color="#9b59b6", text_color="#ffffff")
        self.schedule_receive_btn.pack(side=tk.LEFT, padx=(8, 0))'''

if old_buttons in content:
    content = content.replace(old_buttons, new_buttons)
    print("1. 新增「🚀 开始领取」按钮")
else:
    print("1. 未找到按钮行代码")

# ============================================================
# 2. 在schedule_receive方法中禁用开始领取按钮
# ============================================================
old_schedule_disable = '''        self.running = True
        self.manual_receive_btn.set_state("disabled")
        self.schedule_receive_btn.set_state("disabled")
        self.start_rush_btn.set_state("disabled")
        self.stop_rush_btn.set_state("normal")'''

new_schedule_disable = '''        self.running = True
        self.manual_receive_btn.set_state("disabled")
        self.start_receive_now_btn.set_state("disabled")
        self.schedule_receive_btn.set_state("disabled")
        self.start_rush_btn.set_state("disabled")
        self.stop_rush_btn.set_state("normal")'''

if old_schedule_disable in content:
    content = content.replace(old_schedule_disable, new_schedule_disable)
    print("2. 定时领取时禁用开始领取按钮")
else:
    print("2. 未找到定时领取禁用代码")

# ============================================================
# 3. 在stop_rush方法中启用开始领取按钮
# ============================================================
# 先找到stop_rush方法
old_stop_enable = '''        self.manual_receive_btn.set_state("normal")
        self.schedule_receive_btn.set_state("normal")
        self.start_rush_btn.set_state("normal")
        self.stop_rush_btn.set_state("disabled")'''

new_stop_enable = '''        self.manual_receive_btn.set_state("normal")
        self.start_receive_now_btn.set_state("normal")
        self.schedule_receive_btn.set_state("normal")
        self.start_rush_btn.set_state("normal")
        self.stop_rush_btn.set_state("disabled")'''

if old_stop_enable in content:
    content = content.replace(old_stop_enable, new_stop_enable)
    print("3. 停止时启用开始领取按钮")
else:
    print("3. 未找到停止启用代码")

# ============================================================
# 4. 新增start_receive_now方法和receive_now_loop方法
# 在schedule_receive方法之前插入
# ============================================================
old_schedule_def = '''    def schedule_receive(self):
        """定时领取：在指定时间开始，持续领取指定时长"""'''

new_schedule_def = '''    def start_receive_now(self):
        """开始领取：点击后立即按上面设置的数据持续领取（不等待定时时间）"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return

        # 解析参数（领取时长、间隔）
        try:
            duration = float(self.duration_entry.get())
            interval_mode = self.interval_mode.get()
            if interval_mode == "fixed":
                fixed_interval = float(self.fixed_interval_entry.get()) / 1000.0
                min_interval = fixed_interval
                max_interval = fixed_interval
                if duration <= 0 or fixed_interval <= 0:
                    raise ValueError
            else:
                min_interval = float(self.min_interval_entry.get()) / 1000.0
                max_interval = float(self.max_interval_entry.get()) / 1000.0
                if duration <= 0 or min_interval <= 0 or max_interval <= 0:
                    raise ValueError
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的领取时长（秒）和间隔（毫秒）")
            return

        # 验证账户
        valid_accounts = []
        for acc in accounts:
            ok, msg = verify_login(self.account_mgr.get_cookie_string(acc["name"]))
            if ok:
                valid_accounts.append(acc)
            else:
                self.log(f"⚠ 账户「{acc['name']}」登录失效，已跳过")
        if not valid_accounts:
            messagebox.showerror("登录失效", "所有账户登录验证都失败了")
            return

        self.running = True
        self.manual_receive_btn.set_state("disabled")
        self.start_receive_now_btn.set_state("disabled")
        self.schedule_receive_btn.set_state("disabled")
        self.start_rush_btn.set_state("disabled")
        self.stop_rush_btn.set_state("normal")
        self.rush_status.config(text="● 领取中", fg=COLORS["success"])

        self.log("=" * 40)
        self.log(f"🚀 开始领取（立即执行）")
        self.log(f"任务: [{task['period']}][{task['type']}] {task['name']} => {task['award']}")
        if interval_mode == "fixed":
            self.log(f"领取时长: {duration}秒 | 固定间隔: {min_interval*1000:.0f}毫秒")
        else:
            self.log(f"领取时长: {duration}秒 | 随机间隔: {min_interval*1000:.0f}~{max_interval*1000:.0f}毫秒")
        self.log(f"账户: {', '.join([a['name'] for a in valid_accounts])}")
        self.log("-" * 40)

        self.rush_thread = threading.Thread(
            target=self.receive_now_loop,
            args=(task, valid_accounts, duration, min_interval, max_interval),
            daemon=True
        )
        self.rush_thread.start()

    def receive_now_loop(self, task, accounts, duration, min_interval, max_interval):
        """立即领取循环：不等待定时时间，直接开始持续领取"""
        # 一开始就获取任务信息（actid）
        task_info = self.build_task_info_from_task(task)
        try:
            first_account = accounts[0]
            cookies = cookies_from_account(first_account)
            info, msg = get_mission_info(task["task_id"], cookies)
            if info:
                task_info = info
                act_id = info.get('act_id', '')
                self.log(f"  ✓ 已获取任务信息，act_id: {act_id}")
            else:
                self.log(f"  ⚠ 获取任务信息失败: {msg}，使用备用数据")
        except Exception as e:
            self.log(f"  ⚠ 获取任务信息异常: {e}，使用备用数据")

        # 立即开始领取
        self.log(f"★ 立即开始领取！")
        actual_start = time.time()
        try:
            self.after(0, lambda: self.rush_status.config(text="● 领取中", fg=COLORS["success"]))
        except Exception:
            pass
        if min_interval == max_interval:
            self.log(f"  持续 {duration} 秒，固定间隔 {min_interval*1000:.0f} 毫秒")
        else:
            self.log(f"  持续 {duration} 秒，随机间隔 {min_interval*1000:.0f}~{max_interval*1000:.0f} 毫秒")

        # 快速领取循环（复用定时领取的领取逻辑）
        start_time = time.time()
        attempt = 0
        success = False
        acc_index = 0
        stock_empty_count = 0
        max_stock_seen = 0
        last_stock_check = 0

        # 从任务信息中获取初始库存
        try:
            if task_info:
                day_s, total_s, _, _, _, _, _ = parse_stock_info(task_info)
                initial_stock = max(day_s, total_s)
                if initial_stock > max_stock_seen:
                    max_stock_seen = initial_stock
                self.log(f"  初始库存: 今日剩余={day_s}, 剩余总量={total_s}%")
        except Exception:
            pass

        while self.running and (time.time() - start_time) < duration and not success:
            account = accounts[acc_index % len(accounts)]
            acc_index += 1
            attempt += 1

            # 每隔5次尝试或每隔5秒查询一次库存
            current_time = time.time()
            if attempt % 5 == 1 or (current_time - last_stock_check) > 5:
                last_stock_check = current_time
                try:
                    cookies = cookies_from_account(account)
                    info, _ = get_mission_info(task["task_id"], cookies)
                    if info:
                        day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                        current_stock = max(day_s, total_s)
                        if current_stock > max_stock_seen:
                            max_stock_seen = current_stock
                except Exception:
                    pass

            try:
                ok, msg = self.do_receive_fast(task, task_info, account)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                self.log(f"  账户：{account['name']} | 第{attempt}次尝试")
                break
            else:
                self.log(f"  第{attempt}次: {msg} ({account['name']})")

            # 检测库存是否为空
            if "库存已经使用完" in msg or "75255" in msg:
                if max_stock_seen > 0:
                    stock_empty_count += 1
                    if stock_empty_count == 1:
                        self.log(f"  ⚠ 库存曾有{max_stock_seen}%现已为空，将再尝试一次后停止")
                    elif stock_empty_count >= 2:
                        self.log(f"  ⚠ 库存确认为空，自动停止领取")
                        break
                else:
                    stock_empty_count = 0
                    if attempt % 5 == 0:
                        self.log(f"  ⚠ 库存持续为空（尚未见发放），继续等待抢码")
            else:
                stock_empty_count = 0

            # 随机等待间隔
            import random
            random_interval = random.uniform(min_interval, max_interval)
            self.log(f"  第{attempt}次后等待 {random_interval*1000:.0f}ms")
            next_attempt_time = time.time() + random_interval
            while time.time() < next_attempt_time and self.running:
                time.sleep(0.001)

        elapsed = time.time() - start_time
        if not success:
            self.log(f"领取结束，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒，未成功")
        else:
            self.log(f"领取完成，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒")

        try:
            self.after(0, self.stop_rush)
        except Exception:
            pass

    def schedule_receive(self):
        """定时领取：在指定时间开始，持续领取指定时长"""'''

if old_schedule_def in content:
    content = content.replace(old_schedule_def, new_schedule_def)
    print("4. 新增start_receive_now和receive_now_loop方法")
else:
    print("4. 未找到schedule_receive定义")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.5"', 'APP_VERSION = "v4.4.6"')
print("5. 版本号已更新到 v4.4.6")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
