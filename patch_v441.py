#!/usr/bin/env python3
"""v4.4.1: 全部执行改为按时间启用 + 弹幕日志区域加大 + 启动停止按钮只在弹幕页显示"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. "全部执行"按钮改为"全部启用"，功能是启用所有任务按时间执行
# ============================================================
old_button = '''        DarkButton(row3, "⚡ 全部执行", command=self.run_all_tasks,
                   width=100, height=32, bg_color="#e67e22", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))'''

new_button = '''        DarkButton(row3, "⚡ 全部启用", command=self.enable_all_tasks,
                   width=100, height=32, bg_color="#e67e22", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))'''

if old_button in content:
    content = content.replace(old_button, new_button)
    print("1. 按钮文字改为「⚡ 全部启用」")
else:
    print("1. 未找到全部执行按钮")

# ============================================================
# 2. 替换 run_all_tasks 方法为 enable_all_tasks
# ============================================================
old_run_all = '''    def run_all_tasks(self):
        """一键执行全部已启用的日程任务"""
        enabled_tasks = [t for t in self.schedule_tasks if t["enabled"]]
        if not enabled_tasks:
            messagebox.showwarning("提示", "没有已启用的日程任务")
            return
        if not messagebox.askyesno("确认", f"确定立即执行全部 {len(enabled_tasks)} 个已启用的日程任务吗？"):
            return
        self.log(f"⚡ 一键执行全部 {len(enabled_tasks)} 个日程任务")
        for idx, task in enumerate(enabled_tasks):
            # 每个任务间隔500ms，避免同时启动冲突
            self.app.root.after(idx * 500, lambda t=task: self.execute_task(t, manual=True))'''

new_enable_all = '''    def enable_all_tasks(self):
        """全部启用：让所有任务按设定时间执行（不立即执行）"""
        disabled_tasks = [t for t in self.schedule_tasks if not t["enabled"]]
        if not disabled_tasks:
            messagebox.showinfo("提示", "所有日程任务都已启用")
            return
        if not messagebox.askyesno("确认", f"确定启用全部 {len(disabled_tasks)} 个已取消的日程任务吗？\\n启用后任务将按设定时间自动执行"):
            return
        for task in disabled_tasks:
            task["enabled"] = True
        self.save_schedule()
        self.refresh_task_list()
        self.log(f"⚡ 已全部启用 {len(disabled_tasks)} 个日程任务，将按设定时间执行")'''

if old_run_all in content:
    content = content.replace(old_run_all, new_enable_all)
    print("2. run_all_tasks 替换为 enable_all_tasks")
else:
    print("2. 未找到 run_all_tasks 方法")

# ============================================================
# 3. 弹幕日志区域加大：给日志卡片设置最小高度，调整expand比例
# ============================================================
old_log_card = '''        # 日志卡片
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True, pady=(6, 0))'''

new_log_card = '''        # 日志卡片（设置最小高度200px，确保能显示多行日志）
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        log_card.pack_propagate(False)
        log_card.configure(height=220)'''

if old_log_card in content:
    content = content.replace(old_log_card, new_log_card)
    print("3. 弹幕日志卡片设置最小高度220px")
else:
    print("3. 未找到日志卡片代码")

# ============================================================
# 4. 启动/停止按钮只在弹幕页面显示：从footer移到弹幕页面内部
# ============================================================
# 4a. 把footer里的启动/停止按钮代码注释掉（改为只在弹幕页显示）
old_footer_buttons = '''        # 底部控制栏按钮（footer已在前面创建并pack）
        ctrl_frame = tk.Frame(footer, bg=COLORS["bg_card"])
        ctrl_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        self.start_btn = DarkButton(ctrl_frame, "▶ 启动发送", command=self.start_sending,
                                     width=130, height=36, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, pady=10)

        self.stop_btn = DarkButton(ctrl_frame, "■ 停止发送", command=self.stop_sending,
                                    width=130, height=36, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0), pady=10)
        self.stop_btn.set_state("disabled")

        self.status_label = tk.Label(ctrl_frame, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.status_label.pack(side=tk.RIGHT)'''

new_footer_buttons = '''        # 底部控制栏按钮（移到弹幕页面内部，只在弹幕页显示）
        # 在日志卡片下方添加控制栏
        danmaku_ctrl = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X, pady=(6, 0))

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.X, padx=15, pady=10)

        self.start_btn = DarkButton(ctrl_inner, "▶ 启动发送", command=self.start_sending,
                                     width=130, height=36, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = DarkButton(ctrl_inner, "■ 停止发送", command=self.stop_sending,
                                    width=130, height=36, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.stop_btn.set_state("disabled")

        self.status_label = tk.Label(ctrl_inner, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.status_label.pack(side=tk.RIGHT)'''

if old_footer_buttons in content:
    content = content.replace(old_footer_buttons, new_footer_buttons)
    print("4. 启动/停止按钮从footer移到弹幕页面内部")
else:
    print("4. 未找到footer按钮代码")

# ============================================================
# 5. 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.0"', 'APP_VERSION = "v4.4.1"')
print("5. 版本号已更新到 v4.4.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
