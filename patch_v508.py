#!/usr/bin/env python3
"""v5.0.8: 弹幕工具直播间号改成下拉选择框（和看播页面一样格式）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 把弹幕工具的直播间号输入框改成下拉选择框
# ============================================================
old_room_entry = '''        tk.Label(row1, text="直播间号", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.room_entry = DarkEntry(row1, width=14)
        self.room_entry.pack(side=tk.LEFT, padx=(8, 20))'''

new_room_entry = '''        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=24, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 20))'''

if old_room_entry in content:
    content = content.replace(old_room_entry, new_room_entry)
    print("1. 弹幕工具直播间号已改为下拉选择框")
else:
    print("1. 未找到弹幕工具直播间号输入框代码")

# ============================================================
# 2. 修改save_config中的room_entry引用
# ============================================================
old_save_room = '''            self.config["room_id"] = self.room_entry.get().strip()'''
new_save_room = '''            self.config["room_id"] = self.room_combo.get().strip()
            # 如果是纯数字直播间号，保存到历史记录
            room_id = self.room_combo.get().strip()
            if room_id.isdigit():
                if "room_history" not in self.config:
                    self.config["room_history"] = []
                if room_id not in self.config["room_history"]:
                    self.config["room_history"].insert(0, room_id)
                    self.config["room_history"] = self.config["room_history"][:10]  # 最多保留10条
                    self._refresh_danmaku_room_combo_values()'''

if old_save_room in content:
    content = content.replace(old_save_room, new_save_room)
    print("2. save_config已修改（room_combo + 历史记录）")
else:
    print("2. 未找到save_config中的room_entry代码")

# ============================================================
# 3. 修改apply_config中的room_entry引用
# ============================================================
old_apply_room = '''        if self.config.get("room_id"):
            self.room_entry.insert(0, self.config["room_id"])'''
new_apply_room = '''        if self.config.get("room_id"):
            self.room_combo.set(self.config["room_id"])
        # 初始化直播间下拉框选项
        self._refresh_danmaku_room_combo_values()'''

if old_apply_room in content:
    content = content.replace(old_apply_room, new_apply_room)
    print("3. apply_config已修改（room_combo + 初始化下拉框）")
else:
    print("3. 未找到apply_config中的room_entry代码")

# ============================================================
# 4. 修改绑定事件中的room_entry引用
# ============================================================
old_bind_room = '''        self.room_entry.bind("<FocusOut>", lambda e: self.save_config())'''
new_bind_room = '''        self.room_combo.bind("<KeyRelease>", lambda e: self.save_config())
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)'''

if old_bind_room in content:
    content = content.replace(old_bind_room, new_bind_room)
    print("4. 绑定事件已修改（room_combo）")
else:
    print("4. 未找到绑定事件中的room_entry代码")

# ============================================================
# 5. 修改start_sending中的room_entry引用
# ============================================================
old_start_room = '''        room_id = self.room_entry.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请输入有效的直播间号（数字）")
            return'''
new_start_room = '''        room_id = self.room_combo.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请选择或输入有效的直播间号（数字）")
            return'''

if old_start_room in content:
    content = content.replace(old_start_room, new_start_room)
    print("5. start_sending已修改（room_combo）")
else:
    print("5. 未找到start_sending中的room_entry代码")

# ============================================================
# 6. 在_refresh_danmaku_account_checkboxes方法后面添加弹幕直播间相关方法
# ============================================================
old_deselect_end = '''    def _danmaku_deselect_all(self):
        """弹幕账户取消全选"""
        for var in self.danmaku_account_vars.values():
            var.set(False)

    def _get_danmaku_selected_accounts(self):'''

new_deselect_end = '''    def _danmaku_deselect_all(self):
        """弹幕账户取消全选"""
        for var in self.danmaku_account_vars.values():
            var.set(False)

    def _refresh_danmaku_room_combo_values(self):
        """刷新弹幕直播间下拉框选项：用户直播间 + 历史记录"""
        if not hasattr(self, 'room_combo'):
            return
        values = []
        # 添加所有用户的直播间选项
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(f"【{name}】直播间")
        # 添加历史记录分隔
        if self.config.get("room_history"):
            values.append("--- 历史记录 ---")
            values.extend(self.config["room_history"])
        self.room_combo["values"] = values

    def _on_danmaku_room_selected(self, event=None):
        """选择弹幕直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.room_combo.get().strip()
        if selected.startswith("【") and "】直播间" in selected:
            # 提取用户名
            name = selected[1:selected.index("】")]
            # 找到对应用户
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", acc.get("uid", ""))
                    if mid:
                        room_id = self._get_user_room_id(mid)
                        if room_id:
                            self.room_combo.set(str(room_id))
                            self.log(f"已获取「{name}」的直播间号: {room_id}")
                        else:
                            self.log(f"获取「{name}」直播间号失败，请手动输入")
                    break
        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        self.save_config()

    def _get_user_room_id(self, mid):
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

if old_deselect_end in content:
    content = content.replace(old_deselect_end, new_deselect_end)
    print("6. 已添加弹幕直播间下拉框相关方法")
else:
    print("6. 未找到_danmaku_deselect_all方法")

# 版本号
content = content.replace('APP_VERSION = "v5.0.7"', 'APP_VERSION = "v5.0.8"')
print("7. 版本号: v5.0.7 -> v5.0.8")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
