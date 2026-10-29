#!/usr/bin/env python3
"""v5.0.9: 弹幕直播间下拉框-FocusOut保存+删除历史记录按钮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在直播间下拉框旁边增加删除按钮
# ============================================================
old_room_combo = '''        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=24, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 20))'''

new_room_combo = '''        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=24, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 4))
        self.room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 9, "bold"),
                                       bd=0, padx=8, pady=2, cursor="hand2", command=self._delete_danmaku_room_history)
        self.room_del_btn.pack(side=tk.LEFT, padx=(0, 20))'''

if old_room_combo in content:
    content = content.replace(old_room_combo, new_room_combo)
    print("1. 直播间下拉框已增加删除按钮")
else:
    print("1. 未找到直播间下拉框代码")

# ============================================================
# 2. 把KeyRelease改成FocusOut（输入完退出才保存）
# ============================================================
old_bind = '''        self.room_combo.bind("<KeyRelease>", lambda e: self.save_config())
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)'''

new_bind = '''        self.room_combo.bind("<FocusOut>", lambda e: self.save_config())
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)'''

if old_bind in content:
    content = content.replace(old_bind, new_bind)
    print("2. 保存触发已改为FocusOut（输入完退出才保存）")
else:
    print("2. 未找到绑定事件代码")

# ============================================================
# 3. 添加删除历史记录的方法
# ============================================================
old_get_room_end = '''    def _get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                room_id = data["data"].get("roomid")
                if room_id and data["data"].get("roomStatus") == 1:
                    return room_id
        except Exception:
            pass
        return None

    def _get_danmaku_selected_accounts(self):'''

new_get_room_end = '''    def _get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                room_id = data["data"].get("roomid")
                if room_id and data["data"].get("roomStatus") == 1:
                    return room_id
        except Exception:
            pass
        return None

    def _delete_danmaku_room_history(self):
        """删除当前选中的直播间历史记录"""
        selected = self.room_combo.get().strip()
        if not selected or not selected.isdigit():
            messagebox.showinfo("提示", "请先从下拉框选择要删除的历史直播间号")
            return
        if "room_history" not in self.config:
            self.config["room_history"] = []
        if selected in self.config["room_history"]:
            self.config["room_history"].remove(selected)
            self.save_config()
            self._refresh_danmaku_room_combo_values()
            self.room_combo.set("")
            self.log(f"已删除直播间历史记录: {selected}")
        else:
            messagebox.showinfo("提示", f"直播间号 {selected} 不在历史记录中")

    def _get_danmaku_selected_accounts(self):'''

if old_get_room_end in content:
    content = content.replace(old_get_room_end, new_get_room_end)
    print("3. 已添加删除历史记录方法")
else:
    print("3. 未找到_get_user_room_id方法")

# 版本号
content = content.replace('APP_VERSION = "v5.0.8"', 'APP_VERSION = "v5.0.9"')
print("4. 版本号: v5.0.8 -> v5.0.9")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
