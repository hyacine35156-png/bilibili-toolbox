with open('main_gui_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在build_ui方法后面（找到def on_version_change之前）添加switch_rush_mode和build_new_mode_ui方法
old = '''    def on_version_change(self):
        """版本切换时更新期数下拉框选项，并自动重置期数为该版本的第一个可用期数"""'''

new = '''    def switch_rush_mode(self, mode):
        """切换抢码模式"""
        self.new_mode_mode_var.set(mode)
        if mode == "old":
            self.old_mode_btn.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 11, "bold"))
            self.new_mode_btn.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 11))
            self.new_mode_frame.pack_forget()
            self.old_mode_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        else:
            self.new_mode_btn.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 11, "bold"))
            self.old_mode_btn.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 11))
            self.old_mode_frame.pack_forget()
            self.new_mode_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
            self.refresh_new_mode_group_list()
            self.refresh_new_mode_task_list()

    def build_new_mode_ui(self):
        """构建新模式精准抢码UI"""
        frame = self.new_mode_frame

        # ===== 任务设置（添加任务）=====
        add_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        add_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(add_card, text="任务设置（添加任务到组）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        add_inner = tk.Frame(add_card, bg=COLORS["bg_card"])
        add_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行：版本+期数+类型
        row1 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="版本", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_version_var = tk.StringVar(value="崩坏星穹铁道4.5")
        self.nm_version_combo = ttk.Combobox(row1, textvariable=self.nm_version_var,
                                             values=["鸣潮3.6", "原神7.0", "崩坏星穹铁道4.5", "绝区零3.2"],
                                             state="readonly", width=14, font=("微软雅黑", 11))
        self.nm_version_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_version_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_update_task_list())

        tk.Label(row1, text="期数", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_period_var = tk.StringVar(value="上半")
        self.nm_period_combo = ttk.Combobox(row1, textvariable=self.nm_period_var,
                                            values=["上半", "下半", "全版本", "限时任务1", "限时任务2", "限时直播", "新人限定"],
                                            state="readonly", width=10, font=("微软雅黑", 11))
        self.nm_period_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_period_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_update_task_list())

        tk.Label(row1, text="类型", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_type_var = tk.StringVar(value="投稿")
        self.nm_type_combo = ttk.Combobox(row1, textvariable=self.nm_type_var,
                                          values=["投稿", "直播", "直播里程碑", "看播里程碑", "新人开播"],
                                          state="readonly", width=12, font=("微软雅黑", 11))
        self.nm_type_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_type_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_update_task_list())

        # 第二行：任务+账户+优先级+窗口期
        row2 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="任务", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_task_var = tk.StringVar()
        self.nm_task_combo = ttk.Combobox(row2, textvariable=self.nm_task_var, values=[],
                                          state="readonly", width=35, font=("微软雅黑", 11))
        self.nm_task_combo.pack(side=tk.LEFT, padx=(8, 15))

        tk.Label(row2, text="账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_account_var = tk.StringVar()
        self.nm_account_combo = ttk.Combobox(row2, textvariable=self.nm_account_var, values=[],
                                             state="readonly", width=14, font=("微软雅黑", 11))
        self.nm_account_combo.pack(side=tk.LEFT, padx=(8, 15))

        tk.Label(row2, text="优先级", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_priority_var = tk.StringVar(value="1")
        self.nm_priority_entry = DarkEntry(row2, width=5)
        self.nm_priority_entry.insert(0, "1")
        self.nm_priority_entry.pack(side=tk.LEFT, padx=(8, 15))

        tk.Label(row2, text="窗口期", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_window_var = tk.StringVar(value="15")
        self.nm_window_entry = DarkEntry(row2, width=5)
        self.nm_window_entry.insert(0, "15")
        self.nm_window_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row2, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        # 第三行：任务组选择+添加按钮
        row3 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=3)
        tk.Label(row3, text="任务组", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_group_var = tk.StringVar()
        self.nm_group_combo = ttk.Combobox(row3, textvariable=self.nm_group_var, values=[],
                                           state="readonly", width=18, font=("微软雅黑", 11))
        self.nm_group_combo.pack(side=tk.LEFT, padx=(8, 15))

        self.nm_add_task_btn = tk.Button(row3, text="+ 添加到任务组", bg=COLORS["accent"], fg="#000000",
                                         font=("微软雅黑", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                                         command=self.nm_add_task)
        self.nm_add_task_btn.pack(side=tk.LEFT, padx=10, ipadx=15, ipady=4)

        # ===== 任务组设置 =====
        group_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        group_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(group_card, text="任务组设置", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        group_inner = tk.Frame(group_card, bg=COLORS["bg_card"])
        group_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        grow1 = tk.Frame(group_inner, bg=COLORS["bg_card"])
        grow1.pack(fill=tk.X, pady=3)
        tk.Label(grow1, text="当前组", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_current_group_var = tk.StringVar()
        self.nm_current_group_combo = ttk.Combobox(grow1, textvariable=self.nm_current_group_var, values=[],
                                                   state="readonly", width=18, font=("微软雅黑", 11))
        self.nm_current_group_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_current_group_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_on_group_change())

        self.nm_new_group_btn = tk.Button(grow1, text="新建组", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                          font=("微软雅黑", 10), relief=tk.FLAT, cursor="hand2",
                                          command=self.nm_new_group)
        self.nm_new_group_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        self.nm_del_group_btn = tk.Button(grow1, text="删除组", bg="#c0392b", fg="#ffffff",
                                          font=("微软雅黑", 10), relief=tk.FLAT, cursor="hand2",
                                          command=self.nm_del_group)
        self.nm_del_group_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)

        grow2 = tk.Frame(group_inner, bg=COLORS["bg_card"])
        grow2.pack(fill=tk.X, pady=3)
        tk.Label(grow2, text="目标时间", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_target_time_var = tk.StringVar(value="00:00:00.000")
        self.nm_target_time_entry = DarkEntry(grow2, width=14)
        self.nm_target_time_entry.insert(0, "00:00:00.000")
        self.nm_target_time_entry.pack(side=tk.LEFT, padx=(8, 10))
        tk.Label(grow2, text="（毫秒级，组内所有任务统一首发时间）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(side=tk.LEFT)

        self.nm_save_group_btn = tk.Button(grow2, text="保存组设置", bg=COLORS["success"], fg="#ffffff",
                                           font=("微软雅黑", 10), relief=tk.FLAT, cursor="hand2",
                                           command=self.nm_save_group_settings)
        self.nm_save_group_btn.pack(side=tk.RIGHT, padx=5, ipadx=10, ipady=3)

        # ===== 组内任务列表 =====
        list_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        tk.Label(list_card, text="组内任务（按优先级依次执行）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))

        # 表头
        list_header = tk.Frame(list_card, bg=COLORS["bg_input"])
        list_header.pack(fill=tk.X, padx=15)
        headers = [("优先级", 60), ("任务名称", 220), ("奖励", 100), ("窗口期", 60), ("账户", 100), ("操作", 120)]
        for text, width in headers:
            tk.Label(list_header, text=text, bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10, "bold"), width=width // 7, anchor=tk.W).pack(side=tk.LEFT, padx=5, pady=5)

        # 任务列表容器（可滚动）
        list_container = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 10))
        self.nm_task_list_frame = tk.Frame(list_container, bg=COLORS["bg_card"])
        self.nm_task_list_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 启动控制 =====
        ctrl_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        ctrl_card.pack(fill=tk.X, pady=(0, 8))
        ctrl_inner = tk.Frame(ctrl_card, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.X, padx=15, pady=10)

        self.nm_start_btn = tk.Button(ctrl_inner, text="🚀 启动精准抢码", bg=COLORS["accent"], fg="#000000",
                                      font=("微软雅黑", 12, "bold"), relief=tk.FLAT, cursor="hand2",
                                      command=self.nm_start_rush)
        self.nm_start_btn.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=6)
        self.nm_stop_btn = tk.Button(ctrl_inner, text="⏹ 停止", bg="#c0392b", fg="#ffffff",
                                     font=("微软雅黑", 12, "bold"), relief=tk.FLAT, cursor="hand2",
                                     command=self.nm_stop_rush, state=tk.DISABLED)
        self.nm_stop_btn.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=6)
        self.nm_status_label = tk.Label(ctrl_inner, text="● 未运行", bg=COLORS["bg_card"],
                                        fg=COLORS["text_muted"], font=("微软雅黑", 11))
        self.nm_status_label.pack(side=tk.LEFT, padx=20)

        # ===== 日志 =====
        log_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_card, text="抢码日志（详细模式）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        log_inner = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        self.nm_log_text = tk.Text(log_inner, bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                                   font=("Consolas", 10), wrap=tk.WORD, height=8)
        nm_log_scroll = ttk.Scrollbar(log_inner, command=self.nm_log_text.yview)
        self.nm_log_text.config(yscrollcommand=nm_log_scroll.set)
        nm_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.nm_log_text.pack(fill=tk.BOTH, expand=True)

        # 初始化任务列表
        self.nm_update_task_list()

    def nm_log(self, msg):
        """新模式日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\\n"
        try:
            self.nm_log_text.insert(tk.END, line)
            self.nm_log_text.see(tk.END)
        except Exception:
            pass
        # 同时写主日志文件
        self.log(msg)

    def on_version_change(self):
        """版本切换时更新期数下拉框选项"""'''

if old in content:
    content = content.replace(old, new, 1)
    with open('main_gui_pro.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("模式切换方法和新模式UI框架添加完成")
else:
    print("未找到匹配位置")
