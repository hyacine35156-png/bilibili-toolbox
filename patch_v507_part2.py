#!/usr/bin/env python3
"""v5.0.7 part2: 账户管理页面UI + 弹幕账户多选方法 + 修改发送逻辑"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在refresh_account_list方法后面插入账户管理页面相关方法
# ============================================================
old_refresh_end = '''    def refresh_account_list(self):
        self.account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            display = f"  {acc['name']}"
            self.account_listbox.insert(tk.END, display)

    def on_account_select(self, event):'''

new_refresh_end = '''    def refresh_account_list(self):
        # 兼容旧的account_listbox（如果存在）
        if hasattr(self, 'account_listbox') and self.account_listbox.winfo_exists():
            self.account_listbox.delete(0, tk.END)
            for acc in self.account_mgr.accounts:
                display = f"  {acc['name']}"
                self.account_listbox.insert(tk.END, display)

    def build_account_page(self):
        """构建账户管理页面（独立标签页）"""
        main = tk.Frame(self.account_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 左侧：账户列表
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left_card.pack_propagate(False)
        left_card.configure(width=300)

        tk.Label(left_card, text="账户列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        # 账户列表（Listbox）
        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)
        self.manager_account_listbox = tk.Listbox(list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                                    selectbackground=COLORS["accent"], selectforeground="#000000",
                                                    font=("微软雅黑", 10), bd=0, highlightthickness=0,
                                                    activestyle="none", exportselection=False)
        self.manager_account_listbox.pack(fill=tk.BOTH, expand=True)
        self.manager_account_listbox.bind("<<ListboxSelect>>", self._on_manager_account_select)

        # 按钮区
        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=(10, 12))
        DarkButton(btn_frame, "+ 添加账户", command=self.add_account,
                   width=270, height=38).pack(pady=(0, 6))
        DarkButton(btn_frame, "删除账户", command=self._manager_delete_account,
                   width=270, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "验证登录", command=self._manager_verify_account,
                   width=270, height=38, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "刷新信息", command=self._manager_refresh_info,
                   width=270, height=38, bg_color="#2980b9", text_color="#ffffff").pack()

        # 右侧：账户详细信息
        right_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        right_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        tk.Label(right_card, text="账户详细信息", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        info_frame = tk.Frame(right_card, bg=COLORS["bg_card"])
        info_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # 信息展示区
        self.manager_info_text = tk.Text(info_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                          font=("Consolas", 10), bd=0, highlightthickness=0, wrap=tk.WORD,
                                          padx=12, pady=12)
        self.manager_info_text.pack(fill=tk.BOTH, expand=True)
        self.manager_info_text.config(state=tk.DISABLED)
        self._manager_show_info(None)

    def refresh_account_manager_list(self):
        """刷新账户管理页面的账户列表"""
        if not hasattr(self, 'manager_account_listbox') or not self.manager_account_listbox.winfo_exists():
            return
        self.manager_account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            display = f"  {acc['name']}"
            self.manager_account_listbox.insert(tk.END, display)
        # 刷新弹幕工具页面的账户多选
        self._refresh_danmaku_account_checkboxes()

    def _on_manager_account_select(self, event):
        """账户管理页面选择账户时显示详细信息"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            self._manager_show_info(None)
            return
        acc = self.account_mgr.accounts[selection[0]]
        self._manager_show_info(acc)

    def _manager_show_info(self, acc):
        """显示账户详细信息"""
        self.manager_info_text.config(state=tk.NORMAL)
        self.manager_info_text.delete(1.0, tk.END)
        if not acc:
            self.manager_info_text.insert(tk.END, "请从左侧列表选择一个账户查看详细信息")
            self.manager_info_text.config(state=tk.DISABLED)
            return

        name = acc.get("name", "未知")
        uid = acc.get("DedeUserID", acc.get("uid", "未设置"))
        sessdata = acc.get("SESSDATA", "")
        bili_jct = acc.get("bili_jct", "")
        sessdata_preview = sessdata[:20] + "..." if len(sessdata) > 20 else sessdata
        jct_preview = bili_jct[:15] + "..." if len(bili_jct) > 15 else bili_jct

        info = f"""账户名称: {name}
用户UID: {uid}
SESSDATA: {sessdata_preview}
bili_jct: {jct_preview}

--- 直播间信息 ---
直播间号: 查询中...
直播状态: 查询中...

--- 电池余额 ---
电池数量: 查询中...

提示: 点击「刷新信息」按钮获取最新的直播间号和电池余额
"""
        self.manager_info_text.insert(tk.END, info)
        self.manager_info_text.config(state=tk.DISABLED)

    def _manager_refresh_info(self):
        """刷新选中账户的详细信息（直播间号、电池余额）"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        name = acc.get("name", "未知")
        uid = acc.get("DedeUserID", acc.get("uid", ""))

        # 获取直播间号
        room_id = "未开播"
        room_status = "未开播"
        if uid:
            try:
                url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={uid}"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                data = resp.json()
                if data.get("code") == 0 and data.get("data"):
                    room_id = data["data"].get("roomid", "未开播")
                    if data["data"].get("roomStatus") == 1:
                        room_status = "直播中"
                    else:
                        room_status = "未开播"
            except Exception:
                room_id = "查询失败"
                room_status = "查询失败"

        # 获取电池余额
        battery = "查询失败"
        try:
            sessdata = acc.get("SESSDATA", "")
            cookies = {"SESSDATA": sessdata}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get("https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1",
                                cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                gold = data["data"].get("gold", 0)
                battery = f"{gold / 100:.1f} 电池"
        except Exception:
            battery = "查询失败"

        # 更新显示
        sessdata = acc.get("SESSDATA", "")
        bili_jct = acc.get("bili_jct", "")
        sessdata_preview = sessdata[:20] + "..." if len(sessdata) > 20 else sessdata
        jct_preview = bili_jct[:15] + "..." if len(bili_jct) > 15 else bili_jct

        self.manager_info_text.config(state=tk.NORMAL)
        self.manager_info_text.delete(1.0, tk.END)
        info = f"""账户名称: {name}
用户UID: {uid}
SESSDATA: {sessdata_preview}
bili_jct: {jct_preview}

--- 直播间信息 ---
直播间号: {room_id}
直播状态: {room_status}

--- 电池余额 ---
电池数量: {battery}
"""
        self.manager_info_text.insert(tk.END, info)
        self.manager_info_text.config(state=tk.DISABLED)
        self.log(f"已刷新账户「{name}」的详细信息")

    def _manager_delete_account(self):
        """账户管理页面删除账户"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        if custom_askyesno(self.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_manager_list()
            self._manager_show_info(None)
            self.log(f"已删除账户: {acc['name']}")

    def _manager_verify_account(self):
        """账户管理页面验证登录"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        cookie_str = self.account_mgr.get_cookie_string(acc["name"])
        ok, msg = verify_login(cookie_str)
        if ok:
            messagebox.showinfo("验证成功", f"账户「{acc['name']}」登录有效\n当前用户: {msg}")
            self.log(f"账户「{acc['name']}」验证成功，用户: {msg}")
        else:
            messagebox.showerror("验证失败", f"账户「{acc['name']}」验证失败: {msg}")
            self.log(f"账户「{acc['name']}」验证失败: {msg}")

    # ========== 弹幕工具页面账户多选 ==========
    def _refresh_danmaku_account_checkboxes(self):
        """刷新弹幕工具页面的账户多选复选框"""
        if not hasattr(self, 'danmaku_account_frame') or not self.danmaku_account_frame.winfo_exists():
            return
        for widget in self.danmaku_account_frame.winfo_children():
            widget.destroy()
        self.danmaku_account_vars.clear()
        self.danmaku_account_checkbuttons.clear()
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            var = tk.BooleanVar(value=True)
            self.danmaku_account_vars[name] = var
            cb = tk.Checkbutton(self.danmaku_account_frame, text=name, variable=var,
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["accent"], activebackground=COLORS["bg_input"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 9),
                                anchor="w", padx=8, pady=4)
            cb.pack(fill=tk.X, anchor="w")
            self.danmaku_account_checkbuttons.append(cb)

    def _danmaku_select_all(self):
        """弹幕账户全选"""
        for var in self.danmaku_account_vars.values():
            var.set(True)

    def _danmaku_deselect_all(self):
        """弹幕账户取消全选"""
        for var in self.danmaku_account_vars.values():
            var.set(False)

    def _get_danmaku_selected_accounts(self):
        """获取弹幕工具页面选中的账户列表"""
        selected = []
        for name, var in self.danmaku_account_vars.items():
            if var.get():
                for acc in self.account_mgr.accounts:
                    if acc.get("name") == name:
                        selected.append(acc)
                        break
        return selected

    def on_account_select(self, event):'''

if old_refresh_end in content:
    content = content.replace(old_refresh_end, new_refresh_end)
    print("1. 已插入账户管理页面方法 + 弹幕账户多选方法")
else:
    print("1. 未找到refresh_account_list方法")

# ============================================================
# 2. 修改add_account方法，添加后刷新账户管理列表
# ============================================================
old_add_account = '''    def add_account(self):
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()'''

new_add_account = '''    def add_account(self):
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()
        self.refresh_account_manager_list()'''

if old_add_account in content:
    content = content.replace(old_add_account, new_add_account)
    print("2. add_account方法已更新（添加后刷新账户管理列表）")
else:
    print("2. 未找到add_account方法")

# ============================================================
# 3. 修改start_sending方法，使用弹幕账户多选
# ============================================================
old_start_sending = '''    def start_sending(self):
        account_mode = self.account_mode_var.get()
        if account_mode == "single":
            acc = self.get_current_account()
            if not acc:
                messagebox.showwarning("提示", "请先选择一个账户")
                return
            accounts = [acc]
        else:
            accounts = self.account_mgr.accounts
            if len(accounts) < 1:
                messagebox.showwarning("提示", "没有可用账户，请先添加账户")
                return'''

new_start_sending = '''    def start_sending(self):
        # 从弹幕工具页面的账户多选复选框获取选中的账户
        accounts = self._get_danmaku_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先勾选至少一个发送账户")
            return
        account_mode = "multi" if len(accounts) > 1 else "single"'''

if old_start_sending in content:
    content = content.replace(old_start_sending, new_start_sending)
    print("3. start_sending方法已修改（使用弹幕账户多选）")
else:
    print("3. 未找到start_sending方法")

# ============================================================
# 4. 在弹幕工具页面构建完成后刷新账户多选
# ============================================================
# 找到弹幕工具页面构建完成的位置（在build_ui方法末尾，self.current_tab = "rush"之前）
# 实际上账户多选在part1已经创建了，需要在初始化时调用刷新
# 在build_account_page调用后面添加刷新
old_build_account = '''        self.build_account_page()

        self.current_tab = "rush"'''

new_build_account = '''        self.build_account_page()
        # 初始化弹幕工具页面的账户多选
        self._refresh_danmaku_account_checkboxes()

        self.current_tab = "rush"'''

if old_build_account in content:
    content = content.replace(old_build_account, new_build_account)
    print("4. 已添加弹幕账户多选初始化")
else:
    print("4. 未找到build_account_page调用位置")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
