FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 修改底部控制栏，添加设备码显示和复制按钮
old_footer = '''        # 底部控制栏（必须先pack，固定在底部，否则会被主内容区挤出窗口）
        footer = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)'''

new_footer = '''        # 底部控制栏（必须先pack，固定在底部，否则会被主内容区挤出窗口）
        footer = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        # 左侧：版本号 + 卡密信息
        left_info = tk.Frame(footer, bg=COLORS["bg_card"])
        left_info.pack(side=tk.LEFT, padx=20)
        tk.Label(left_info, text=f"{APP_VERSION}", 
                bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 15))
        self.footer_card_label = tk.Label(left_info, text=card_text, 
                bg=COLORS["bg_card"], fg=COLORS["success"],
                font=("微软雅黑", 10))
        self.footer_card_label.pack(side=tk.LEFT)
        
        # 右侧：设备码 + 复制按钮
        right_info = tk.Frame(footer, bg=COLORS["bg_card"])
        right_info.pack(side=tk.RIGHT, padx=20)
        machine_code = get_machine_code()
        tk.Label(right_info, text="设备码:", 
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 8))
        self.footer_machine_label = tk.Label(right_info, 
                text=f"{machine_code[:8]}...{machine_code[-8:]}", 
                bg=COLORS["bg_card"], fg=COLORS["accent"],
                font=("Consolas", 10))
        self.footer_machine_label.pack(side=tk.LEFT, padx=(0, 8))
        copy_machine_btn = tk.Button(right_info, text="📋 复制", 
                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                font=("微软雅黑", 9), relief=tk.FLAT, cursor="hand2",
                command=lambda: self._copy_machine_code())
        copy_machine_btn.pack(side=tk.LEFT, ipadx=8, ipady=2)'''

if old_footer in content:
    content = content.replace(old_footer, new_footer)
    print("✓ 底部控制栏已修改，添加设备码显示")
else:
    print("✗ 未找到底部控制栏")

# 添加复制设备码方法（在DanmakuApp类中）
# 找到合适的位置插入方法，比如在switch_tab方法之前
old_switch = '''    def switch_tab(self, tab_name):'''

new_switch = '''    def _copy_machine_code(self):
        """复制设备码到剪贴板"""
        try:
            machine_code = get_machine_code()
            self.root.clipboard_clear()
            self.root.clipboard_append(machine_code)
            self.root.update()
            # 临时显示复制成功
            old_text = self.footer_machine_label.cget("text")
            self.footer_machine_label.config(text="✓ 已复制", fg=COLORS["success"])
            self.root.after(1500, lambda: self.footer_machine_label.config(text=old_text, fg=COLORS["accent"]))
        except Exception as e:
            pass
    
    def switch_tab(self, tab_name):'''

if old_switch in content:
    content = content.replace(old_switch, new_switch, 1)
    print("✓ 已添加复制设备码方法")
else:
    print("✗ 未找到switch_tab方法位置")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\n软件修改完成！")
