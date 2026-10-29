#!/usr/bin/env python3
"""v5.2.0 part1: 直播间管理模块(RoomManager)+账户管理页面添加直播间管理子区域"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在AccountManager类后面添加RoomManager类
# ============================================================
old_account_mgr_end = '''    def get_cookie_string(self, name):
        acc = self.get_account(name)
        if not acc:
            return ""
        parts = [f"SESSDATA={acc['SESSDATA']}", f"bili_jct={acc['bili_jct']}"]
        if acc.get("DedeUserID"):
            parts.append(f"DedeUserID={acc['DedeUserID']}")
        return "; ".join(parts)'''

new_account_mgr_end = '''    def get_cookie_string(self, name):
        acc = self.get_account(name)
        if not acc:
            return ""
        parts = [f"SESSDATA={acc['SESSDATA']}", f"bili_jct={acc['bili_jct']}"]
        if acc.get("DedeUserID"):
            parts.append(f"DedeUserID={acc['DedeUserID']}")
        return "; ".join(parts)


class RoomManager:
    """直播间管理器"""
    def __init__(self):
        self.rooms = []
        self.load()

    def load(self):
        config_file = BASE_DIR / "rooms_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.rooms = data.get("rooms", [])
            except Exception:
                self.rooms = []

    def save(self):
        config_file = BASE_DIR / "rooms_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"rooms": self.rooms}, f, ensure_ascii=False, indent=2)

    def add_room(self, room_id, name, remark=""):
        room_id = str(room_id).strip()
        if not room_id or not room_id.isdigit():
            return False, "直播间号必须是数字"
        for room in self.rooms:
            if room["id"] == room_id:
                return False, "直播间号已存在"
        self.rooms.append({"id": room_id, "name": name, "remark": remark})
        self.save()
        return True, "添加成功"

    def delete_room(self, room_id):
        self.rooms = [r for r in self.rooms if r["id"] != str(room_id)]
        self.save()

    def update_room(self, room_id, name=None, remark=None):
        for room in self.rooms:
            if room["id"] == str(room_id):
                if name is not None:
                    room["name"] = name
                if remark is not None:
                    room["remark"] = remark
                self.save()
                return True
        return False

    def get_room(self, room_id):
        for room in self.rooms:
            if room["id"] == str(room_id):
                return room
        return None

    def get_room_names(self):
        """获取所有直播间的显示名称列表"""
        return [f"{r['name']}（{r['id']}）" for r in self.rooms]

    def import_from_accounts(self, account_mgr, log_func=None):
        """从账户导入直播间（自动获取所有账户的直播间号）"""
        added = 0
        for acc in account_mgr.accounts:
            name = acc.get("name", "未知")
            mid = acc.get("DedeUserID", "")
            if not mid:
                continue
            try:
                url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                data = resp.json()
                if data.get("code") == 0 and data.get("data"):
                    room_id = data["data"].get("roomid")
                    if room_id and data["data"].get("roomStatus") == 1:
                        room_name = f"{name}的房间"
                        if not self.get_room(room_id):
                            self.add_room(room_id, room_name, "从账户导入")
                            added += 1
                            if log_func:
                                log_func(f"已导入「{name}」的直播间: {room_id}")
            except Exception:
                pass
        if log_func:
            log_func(f"从账户导入完成，共新增 {added} 个直播间")
        return added'''

if old_account_mgr_end in content:
    content = content.replace(old_account_mgr_end, new_account_mgr_end)
    print("1. 已添加RoomManager类")
else:
    print("1. 未找到AccountManager.get_cookie_string方法")

# ============================================================
# 2. 在主应用类__init__中初始化room_mgr
# ============================================================
old_account_mgr_init = '''        self.account_mgr = AccountManager()'''
new_account_mgr_init = '''        self.account_mgr = AccountManager()
        self.room_mgr = RoomManager()'''

if old_account_mgr_init in content:
    content = content.replace(old_account_mgr_init, new_account_mgr_init)
    print("2. 已初始化room_mgr")
else:
    print("2. 未找到account_mgr初始化代码")

# ============================================================
# 3. 修改build_account_page，添加直播间管理子区域
# ============================================================
old_account_page_end = '''        self.manager_info_text.pack(fill=tk.BOTH, expand=True)
        self.manager_info_text.config(state=tk.DISABLED)
        self._manager_show_info(None)

    def refresh_account_manager_list(self):'''

new_account_page_end = '''        self.manager_info_text.pack(fill=tk.BOTH, expand=True)
        self.manager_info_text.config(state=tk.DISABLED)
        self._manager_show_info(None)

        # ===== 直播间管理子区域 =====
        room_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        room_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        tk.Label(room_card, text="直播间管理", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        room_inner = tk.Frame(room_card, bg=COLORS["bg_card"])
        room_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # 左侧：直播间列表
        room_left = tk.Frame(room_inner, bg=COLORS["bg_card"])
        room_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.manager_room_listbox = tk.Listbox(room_left, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                                  selectbackground=COLORS["accent"], selectforeground="#000000",
                                                  font=("微软雅黑", 10), bd=0, highlightthickness=0,
                                                  activestyle="none", exportselection=False)
        self.manager_room_listbox.pack(fill=tk.BOTH, expand=True)
        self.manager_room_listbox.bind("<<ListboxSelect>>", self._on_manager_room_select)

        # 右侧：添加/编辑表单
        room_right = tk.Frame(room_inner, bg=COLORS["bg_card"], width=280)
        room_right.pack(side=tk.LEFT, fill=tk.Y)
        room_right.pack_propagate(False)

        tk.Label(room_right, text="直播间号:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(anchor=tk.W)
        self.room_id_entry = DarkEntry(room_right, width=28)
        self.room_id_entry.pack(fill=tk.X, pady=(2, 8))

        tk.Label(room_right, text="显示名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(anchor=tk.W)
        self.room_name_entry = DarkEntry(room_right, width=28)
        self.room_name_entry.pack(fill=tk.X, pady=(2, 8))

        tk.Label(room_right, text="备注:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(anchor=tk.W)
        self.room_remark_entry = DarkEntry(room_right, width=28)
        self.room_remark_entry.pack(fill=tk.X, pady=(2, 10))

        DarkButton(room_right, "+ 添加直播间", command=self._manager_add_room,
                   width=260, height=34).pack(pady=(0, 5))
        DarkButton(room_right, "删除直播间", command=self._manager_delete_room,
                   width=260, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 5))
        DarkButton(room_right, "从账户导入", command=self._manager_import_rooms_from_accounts,
                   width=260, height=34, bg_color="#2980b9", text_color="#ffffff").pack()

        self._refresh_manager_room_list()

    def _refresh_manager_room_list(self):
        """刷新直播间管理列表"""
        if not hasattr(self, 'manager_room_listbox') or not self.manager_room_listbox.winfo_exists():
            return
        self.manager_room_listbox.delete(0, tk.END)
        for room in self.room_mgr.rooms:
            display = f"  {room['name']}"
            if room.get('remark'):
                display += f"  [{room['remark']}]"
            self.manager_room_listbox.insert(tk.END, display)

    def _on_manager_room_select(self, event):
        """选择直播间时填充表单"""
        selection = self.manager_room_listbox.curselection()
        if not selection:
            return
        room = self.room_mgr.rooms[selection[0]]
        self.room_id_entry.delete(0, tk.END)
        self.room_id_entry.insert(0, room["id"])
        self.room_name_entry.delete(0, tk.END)
        self.room_name_entry.insert(0, room["name"])
        self.room_remark_entry.delete(0, tk.END)
        self.room_remark_entry.insert(0, room.get("remark", ""))

    def _manager_add_room(self):
        """添加直播间"""
        room_id = self.room_id_entry.get().strip()
        name = self.room_name_entry.get().strip()
        remark = self.room_remark_entry.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请输入有效的直播间号（数字）")
            return
        if not name:
            name = f"直播间{room_id}"
        ok, msg = self.room_mgr.add_room(room_id, name, remark)
        if ok:
            self._refresh_manager_room_list()
            self.room_id_entry.delete(0, tk.END)
            self.room_name_entry.delete(0, tk.END)
            self.room_remark_entry.delete(0, tk.END)
            self.log(f"已添加直播间: {name}（{room_id}）")
        else:
            messagebox.showwarning("提示", msg)

    def _manager_delete_room(self):
        """删除直播间"""
        selection = self.manager_room_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的直播间")
            return
        room = self.room_mgr.rooms[selection[0]]
        if custom_askyesno(self.root, "确认", f"确定删除直播间「{room['name']}」吗？"):
            self.room_mgr.delete_room(room["id"])
            self._refresh_manager_room_list()
            self.room_id_entry.delete(0, tk.END)
            self.room_name_entry.delete(0, tk.END)
            self.room_remark_entry.delete(0, tk.END)
            self.log(f"已删除直播间: {room['name']}（{room['id']}）")

    def _manager_import_rooms_from_accounts(self):
        """从账户导入直播间"""
        count = self.room_mgr.import_from_accounts(self.account_mgr, self.log)
        self._refresh_manager_room_list()
        messagebox.showinfo("提示", f"从账户导入完成，共新增 {count} 个直播间")

    def refresh_account_manager_list(self):'''

if old_account_page_end in content:
    content = content.replace(old_account_page_end, new_account_page_end)
    print("3. 已在账户管理页面添加直播间管理子区域")
else:
    print("3. 未找到build_account_page结尾代码")

# 版本号
content = content.replace('APP_VERSION = "v5.1.1"', 'APP_VERSION = "v5.2.0"')
print("4. 版本号: v5.1.1 -> v5.2.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
