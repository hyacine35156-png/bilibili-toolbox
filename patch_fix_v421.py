#!/usr/bin/env python3
"""修复：1.抢码日程改全部开始 2.关机加确认 3.日程加关机类型"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 抢码日程执行改为start_all_scheduled_tasks ==========
old_rush_exec = '''    def _start_rush_safe(self, task):
        try:
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_rush'):
                self.app.rush_page.start_rush()
                self.log(f"✓ 抢码任务已启动")
        except Exception as e:
            self.log(f"✗ 启动抢码失败: {e}")'''

new_rush_exec = '''    def _start_rush_safe(self, task):
        try:
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_all_scheduled_tasks'):
                self.app.rush_page.start_all_scheduled_tasks()
                self.log(f"✓ 抢码定时任务已全部启动")
            elif hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_rush'):
                self.app.rush_page.start_rush()
                self.log(f"✓ 抢码监控已启动")
        except Exception as e:
            self.log(f"✗ 启动抢码失败: {e}")'''

content = content.replace(old_rush_exec, new_rush_exec)
print("1. 抢码日程执行改为全部开始")

# ========== 2. 日程任务类型添加"关机"选项 ==========
old_type_radio = '''        ttk.Radiobutton(row1, text="📺 看播", variable=self.task_type_var, value="watch",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="💬 弹幕", variable=self.task_type_var, value="danmaku",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⚡ 抢码", variable=self.task_type_var, value="rush",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)'''

new_type_radio = '''        ttk.Radiobutton(row1, text="📺 看播", variable=self.task_type_var, value="watch",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="💬 弹幕", variable=self.task_type_var, value="danmaku",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⚡ 抢码", variable=self.task_type_var, value="rush",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⏻ 关机", variable=self.task_type_var, value="shutdown",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)'''

content = content.replace(old_type_radio, new_type_radio)
print("2. 日程任务类型添加关机选项")

# ========== 3. type_names添加shutdown ==========
old_type_names = '''        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码"}'''
new_type_names = '''        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}'''
content = content.replace(old_type_names, new_type_names)
print("3. type_names添加shutdown")

# ========== 4. execute_task添加shutdown分支 ==========
old_execute_rush = '''            elif task["type"] == "rush":
                # 切换到抢码页面并开始
                self.app.after(0, lambda: self.app.switch_tab("rush"))
                self.app.after(500, lambda: self._start_rush_safe(task))'''

new_execute_rush = '''            elif task["type"] == "rush":
                # 切换到抢码页面并开始
                self.app.after(0, lambda: self.app.switch_tab("rush"))
                self.app.after(500, lambda: self._start_rush_safe(task))
            elif task["type"] == "shutdown":
                # 执行关机（带确认）
                self.app.after(0, lambda: self._execute_shutdown_safe(task))'''

content = content.replace(old_execute_rush, new_execute_rush)
print("4. execute_task添加shutdown分支")

# ========== 5. 添加_execute_shutdown_safe方法（在_mark_task_done之前） ==========
old_mark_done = '''    def _mark_task_done(self, task):'''
new_shutdown_method = '''    def _execute_shutdown_safe(self, task):
        """执行关机任务（带确认弹窗，超时60秒自动关机）"""
        try:
            self.log(f"⏻ 关机任务「{task['name']}」已触发，弹出确认窗口...")
            # 创建确认对话框
            confirm_win = tk.Toplevel(self.app.root)
            confirm_win.title("关机确认")
            confirm_win.geometry("360x200")
            confirm_win.configure(bg=COLORS["bg_card"])
            confirm_win.resizable(False, False)
            # 置顶
            confirm_win.attributes("-topmost", True)
            confirm_win.grab_set()

            # 居中
            confirm_win.update_idletasks()
            x = (confirm_win.winfo_screenwidth() // 2) - 180
            y = (confirm_win.winfo_screenheight() // 2) - 100
            confirm_win.geometry(f"360x200+{x}+{y}")

            tk.Label(confirm_win, text="⏻ 定时关机", bg=COLORS["bg_card"], fg=COLORS["accent"],
                     font=("微软雅黑", 16, "bold")).pack(pady=(20, 10))
            tk.Label(confirm_win, text=f"任务「{task['name']}」时间到", bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 11)).pack()
            countdown_label = tk.Label(confirm_win, text="60秒后自动关机...", bg=COLORS["bg_card"],
                                       fg=COLORS["warning"], font=("微软雅黑", 12, "bold"))
            countdown_label.pack(pady=(8, 15))

            result = {"confirmed": False, "window": confirm_win}

            def confirm_shutdown():
                result["confirmed"] = True
                confirm_win.destroy()

            def cancel_shutdown():
                result["confirmed"] = False
                confirm_win.destroy()

            btn_frame = tk.Frame(confirm_win, bg=COLORS["bg_card"])
            btn_frame.pack()
            DarkButton(btn_frame, "确认关机", command=confirm_shutdown,
                       width=100, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
            DarkButton(btn_frame, "取消", command=cancel_shutdown,
                       width=100, height=32, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

            # 倒计时
            remaining = [60]
            def update_countdown():
                if remaining[0] > 0 and confirm_win.winfo_exists():
                    remaining[0] -= 1
                    countdown_label.config(text=f"{remaining[0]}秒后自动关机...")
                    confirm_win.after(1000, update_countdown)
                elif confirm_win.winfo_exists():
                    # 超时自动确认
                    result["confirmed"] = True
                    confirm_win.destroy()
            confirm_win.after(1000, update_countdown)

            # 等待对话框关闭
            self.app.root.wait_window(confirm_win)

            if result["confirmed"]:
                self.log(f"⏻ 确认关机，正在执行关机命令...")
                import subprocess
                subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
            else:
                self.log(f"■ 关机任务「{task['name']}」已取消")
        except Exception as e:
            self.log(f"✗ 关机任务执行失败: {e}")

    def _mark_task_done(self, task):'''

content = content.replace(old_mark_done, new_shutdown_method)
print("5. 添加_execute_shutdown_safe方法")

# ========== 6. 修复定时关机页面的确认功能（shutdown_task_worker到点也加确认） ==========
old_shutdown_exec = '''            # 时间到，执行关机
            if not task["stop_flag"]["stop"]:
                task["status"] = "执行中"
                self.after(0, self.refresh_shutdown_task_list)
                self.log(f"⏻ 任务「{task['name']}」时间到，正在执行关机...")
                time.sleep(1)
                # 执行Windows关机命令
                import subprocess
                subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)'''

new_shutdown_exec = '''            # 时间到，弹出确认窗口
            if not task["stop_flag"]["stop"]:
                task["status"] = "待确认"
                self.after(0, self.refresh_shutdown_task_list)
                self.log(f"⏻ 任务「{task['name']}」时间到，弹出关机确认窗口...")

                # 在UI线程弹出确认对话框
                confirm_result = {"confirmed": False, "done": False}

                def show_confirm_dialog():
                    try:
                        confirm_win = tk.Toplevel(self.root)
                        confirm_win.title("关机确认")
                        confirm_win.geometry("360x200")
                        confirm_win.configure(bg=COLORS["bg_card"])
                        confirm_win.resizable(False, False)
                        confirm_win.attributes("-topmost", True)
                        confirm_win.grab_set()
                        confirm_win.update_idletasks()
                        x = (confirm_win.winfo_screenwidth() // 2) - 180
                        y = (confirm_win.winfo_screenheight() // 2) - 100
                        confirm_win.geometry(f"360x200+{x}+{y}")

                        tk.Label(confirm_win, text="⏻ 定时关机", bg=COLORS["bg_card"], fg=COLORS["accent"],
                                 font=("微软雅黑", 16, "bold")).pack(pady=(20, 10))
                        tk.Label(confirm_win, text=f"任务「{task['name']}」时间到", bg=COLORS["bg_card"],
                                 fg=COLORS["text_primary"], font=("微软雅黑", 11)).pack()
                        countdown_label = tk.Label(confirm_win, text="60秒后自动关机...", bg=COLORS["bg_card"],
                                                   fg=COLORS["warning"], font=("微软雅黑", 12, "bold"))
                        countdown_label.pack(pady=(8, 15))

                        def do_confirm():
                            confirm_result["confirmed"] = True
                            confirm_result["done"] = True
                            confirm_win.destroy()

                        def do_cancel():
                            confirm_result["confirmed"] = False
                            confirm_result["done"] = True
                            confirm_win.destroy()

                        btn_frame = tk.Frame(confirm_win, bg=COLORS["bg_card"])
                        btn_frame.pack()
                        DarkButton(btn_frame, "确认关机", command=do_confirm,
                                   width=100, height=32, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
                        DarkButton(btn_frame, "取消", command=do_cancel,
                                   width=100, height=32, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

                        remaining = [60]
                        def tick():
                            if remaining[0] > 0 and confirm_win.winfo_exists():
                                remaining[0] -= 1
                                countdown_label.config(text=f"{remaining[0]}秒后自动关机...")
                                confirm_win.after(1000, tick)
                            elif confirm_win.winfo_exists():
                                confirm_result["confirmed"] = True
                                confirm_result["done"] = True
                                confirm_win.destroy()
                        confirm_win.after(1000, tick)

                        self.root.wait_window(confirm_win)
                    except Exception as e:
                        confirm_result["confirmed"] = True  # 弹窗失败则直接关机
                        confirm_result["done"] = True

                self.after(0, show_confirm_dialog)

                # 等待确认结果（最多等90秒）
                wait_count = 0
                while not confirm_result["done"] and wait_count < 90:
                    if task["stop_flag"]["stop"]:
                        break
                    time.sleep(1)
                    wait_count += 1

                if task["stop_flag"]["stop"]:
                    task["status"] = "已取消"
                    self.after(0, self.refresh_shutdown_task_list)
                    return

                if confirm_result["confirmed"]:
                    task["status"] = "执行中"
                    self.after(0, self.refresh_shutdown_task_list)
                    self.log(f"⏻ 确认关机，正在执行关机命令...")
                    time.sleep(1)
                    import subprocess
                    subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
                else:
                    task["status"] = "已取消"
                    self.after(0, self.refresh_shutdown_task_list)
                    self.after(0, self.update_shutdown_status)
                    self.log(f"■ 关机任务「{task['name']}」已取消")'''

content = content.replace(old_shutdown_exec, new_shutdown_exec)
print("6. 定时关机页面添加确认弹窗")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n所有修复完成！")
