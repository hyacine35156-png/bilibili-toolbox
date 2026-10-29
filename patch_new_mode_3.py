with open('main_gui_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修改build_ui开头：添加模式切换栏，把main改名为old_mode_frame
old = '''        self.rush_status.pack(side=tk.RIGHT, padx=20)

        # 主内容区
        main = tk.Frame(self, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 上半部分：设置
        settings_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])'''

new = '''        self.rush_status.pack(side=tk.RIGHT, padx=20)

        # 模式切换栏
        mode_bar = tk.Frame(self, bg=COLORS["bg_card"], height=42)
        mode_bar.pack(fill=tk.X)
        mode_bar.pack_propagate(False)
        self.new_mode_mode_var = tk.StringVar(value="old")
        self.old_mode_btn = tk.Label(mode_bar, text="  旧模式  ", bg=COLORS["accent"], fg="#000000",
                                     font=("微软雅黑", 11, "bold"), padx=20, pady=6, cursor="hand2")
        self.old_mode_btn.pack(side=tk.LEFT, padx=(15, 5), pady=5)
        self.old_mode_btn.bind("<Button-1>", lambda e: self.switch_rush_mode("old"))
        self.new_mode_btn = tk.Label(mode_bar, text="  ✨ 新模式·精准抢码  ", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=("微软雅黑", 11), padx=20, pady=6, cursor="hand2")
        self.new_mode_btn.pack(side=tk.LEFT, padx=(0, 15), pady=5)
        self.new_mode_btn.bind("<Button-1>", lambda e: self.switch_rush_mode("new"))

        # 旧模式内容区
        self.old_mode_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self.old_mode_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        main = self.old_mode_frame

        # 新模式内容区（默认隐藏）
        self.new_mode_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self.build_new_mode_ui()

        # 上半部分：设置
        settings_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])'''

if old in content:
    content = content.replace(old, new, 1)
    with open('main_gui_pro.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("模式切换栏和旧模式框架添加完成")
else:
    print("未找到匹配位置")
