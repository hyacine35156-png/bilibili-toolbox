#!/usr/bin/env python3
"""v4.4.3: 彻底重构弹幕页面布局 - 底部固定日志+按钮，中间弹幕列表"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 找到要替换的大块代码：从弹幕列表卡片开始，到控制栏结束
# ============================================================

old_block = '''        # 弹幕列表卡片
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(danmaku_header, text="弹幕列表（三列显示，每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        DarkButton(danmaku_header, "+ 添加", command=self.add_single_danmaku,
                   width=60, height=26, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(danmaku_header, "批量生成", command=self.batch_generate_danmaku,
                   width=70, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT)
        DarkButton(danmaku_header, "保存列表", command=self.save_danmaku,
                   width=80, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT, padx=(0, 4))

        # 三列弹幕列表（使用grid布局，三列平均分配宽度）
        columns_frame = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        columns_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 设置三列等宽
        for i in range(3):
            columns_frame.grid_columnconfigure(i, weight=1, uniform="column")

        self.danmaku_texts = []
        for i in range(3):
            col_frame = tk.Frame(columns_frame, bg=COLORS["bg_card"])
            col_frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 0 if i == 2 else 4))
            col_frame.grid_rowconfigure(1, weight=1)
            col_frame.grid_columnconfigure(0, weight=1)

            # 列标题
            tk.Label(col_frame, text=f"第{i+1}列", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 8)).grid(row=0, column=0, sticky="w", pady=(0, 2))

            text_with_scroll = tk.Frame(col_frame, bg=COLORS["bg_card"])
            text_with_scroll.grid(row=1, column=0, sticky="nsew")
            text_with_scroll.grid_rowconfigure(0, weight=1)
            text_with_scroll.grid_columnconfigure(0, weight=1)

            text_widget = tk.Text(text_with_scroll, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                  insertbackground=COLORS["accent"], font=("微软雅黑", 9),
                                  bd=0, highlightthickness=0, wrap=tk.WORD, width=20)
            text_widget.grid(row=0, column=0, sticky="nsew")
            self.danmaku_texts.append(text_widget)

        # 日志卡片（固定高度180px，确保能显示多行日志）
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(6, 0))
        log_card.pack_propagate(False)
        log_card.configure(height=180)

        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                 insertbackground=COLORS["accent"], font=("Consolas", 9),
                                 bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview, style="Dark.Horizontal.TScrollbar")
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # 底部控制栏按钮（移到弹幕页面内部，只在弹幕页显示）
        # 在日志卡片下方添加控制栏，固定高度
        danmaku_ctrl = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X, pady=(6, 0))
        danmaku_ctrl.pack_propagate(False)
        danmaku_ctrl.configure(height=60)

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.BOTH, expand=True, padx=15)

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

new_block = '''        # ===== 底部容器：日志 + 控制栏（固定高度，先pack到BOTTOM）=====
        bottom_container = tk.Frame(right, bg=COLORS["bg_dark"])
        bottom_container.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        # 日志卡片（固定高度160px）
        log_card = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(0, 6))
        log_card.pack_propagate(False)
        log_card.configure(height=160)

        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                 insertbackground=COLORS["accent"], font=("Consolas", 9),
                                 bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview, style="Dark.Horizontal.TScrollbar")
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # 控制栏（固定高度56px）
        danmaku_ctrl = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X)
        danmaku_ctrl.pack_propagate(False)
        danmaku_ctrl.configure(height=56)

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.BOTH, expand=True, padx=15)

        self.start_btn = DarkButton(ctrl_inner, "▶ 启动发送", command=self.start_sending,
                                     width=130, height=36, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, pady=10)

        self.stop_btn = DarkButton(ctrl_inner, "■ 停止发送", command=self.stop_sending,
                                    width=130, height=36, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0), pady=10)
        self.stop_btn.set_state("disabled")

        self.status_label = tk.Label(ctrl_inner, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.status_label.pack(side=tk.RIGHT)

        # ===== 中间：弹幕列表卡片（expand=True，占据剩余空间）=====
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(danmaku_header, text="弹幕列表（三列显示，每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        DarkButton(danmaku_header, "+ 添加", command=self.add_single_danmaku,
                   width=60, height=26, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(danmaku_header, "批量生成", command=self.batch_generate_danmaku,
                   width=70, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT)
        DarkButton(danmaku_header, "保存列表", command=self.save_danmaku,
                   width=80, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT, padx=(0, 4))

        # 三列弹幕列表（使用grid布局，三列平均分配宽度）
        columns_frame = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        columns_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 设置三列等宽
        for i in range(3):
            columns_frame.grid_columnconfigure(i, weight=1, uniform="column")

        self.danmaku_texts = []
        for i in range(3):
            col_frame = tk.Frame(columns_frame, bg=COLORS["bg_card"])
            col_frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 0 if i == 2 else 4))
            col_frame.grid_rowconfigure(1, weight=1)
            col_frame.grid_columnconfigure(0, weight=1)

            # 列标题
            tk.Label(col_frame, text=f"第{i+1}列", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 8)).grid(row=0, column=0, sticky="w", pady=(0, 2))

            text_with_scroll = tk.Frame(col_frame, bg=COLORS["bg_card"])
            text_with_scroll.grid(row=1, column=0, sticky="nsew")
            text_with_scroll.grid_rowconfigure(0, weight=1)
            text_with_scroll.grid_columnconfigure(0, weight=1)

            text_widget = tk.Text(text_with_scroll, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                  insertbackground=COLORS["accent"], font=("微软雅黑", 9),
                                  bd=0, highlightthickness=0, wrap=tk.WORD, width=20)
            text_widget.grid(row=0, column=0, sticky="nsew")
            self.danmaku_texts.append(text_widget)'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("1. 布局重构成功：底部固定日志+按钮，中间弹幕列表")
else:
    print("1. 未找到要替换的代码块")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.2"', 'APP_VERSION = "v4.4.3"')
print("2. 版本号已更新到 v4.4.3")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
