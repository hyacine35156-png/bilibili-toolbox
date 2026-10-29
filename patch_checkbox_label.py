file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 左边多选框加文字"选"
old1 = '''            check_chk = tk.Checkbutton(row_frame, variable=check_var, command=toggle_check,
                                        bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"])
            check_chk.pack(side=tk.LEFT, padx=(4, 2), pady=8)'''
new1 = '''            check_chk = tk.Checkbutton(row_frame, text="选", variable=check_var, command=toggle_check,
                                        bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"],
                                        fg=text_color, font=("微软雅黑", 8))
            check_chk.pack(side=tk.LEFT, padx=(4, 2), pady=8)'''
content = content.replace(old1, new1)

# 右边启用框加文字"用"
old2 = '''            chk = tk.Checkbutton(row_frame, variable=enabled_var, command=toggle_enabled,
                                 bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"])
            chk.pack(side=tk.LEFT, padx=(2, 4), pady=8)'''
new2 = '''            chk = tk.Checkbutton(row_frame, text="用", variable=enabled_var, command=toggle_enabled,
                                 bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"],
                                 fg=text_color, font=("微软雅黑", 8))
            chk.pack(side=tk.LEFT, padx=(2, 4), pady=8)'''
content = content.replace(old2, new2)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("勾选框已加文字标签")
