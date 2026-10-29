# -*- coding: utf-8 -*-
"""修改兑换码导入功能：下拉选择活动 + 全部导入"""

FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 替换import_from_records函数的开头部分（act_id输入改成活动选择）
old_import_start = '''    def import_from_records(self):
        """从领取记录导入所有兑换码"""
        # 让用户输入act_id
        from tkinter import simpledialog
        default_act_id = "1ERAzwloghvb5600"
        act_id = simpledialog.askstring("输入活动ID", "请输入活动ID (act_id):", 
                                          initialvalue=default_act_id, parent=self)
        if not act_id:
            return
        act_id = act_id.strip()

        # 获取所有账户
        accounts = []
        try:
            if self.account_mgr and hasattr(self.account_mgr, 'accounts'):
                accounts = self.account_mgr.accounts
            else:
                # 从文件读取（使用统一的ACCOUNTS_FILE路径）
                if os.path.exists(str(ACCOUNTS_FILE)):
                    with open(str(ACCOUNTS_FILE), "r", encoding="utf-8") as f:
                        accounts = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"读取账户失败: {e}")
            return

        if not accounts:
            messagebox.showwarning("提示", "没有可用的账户，请先导入账户")
            return

        # 遍历所有账户，调用领取记录API
        total_imported = 0
        total_skipped = 0
        account_results = []

        for acc in accounts:
            try:
                cookies = cookies_from_account(acc)
                record_data, record_msg = get_award_record(act_id, cookies)'''

new_import_start = '''    def import_from_records(self):
        """从领取记录导入所有兑换码（选择活动或全部导入）"""
        # 创建活动选择对话框
        dialog = tk.Toplevel(self)
        dialog.title("选择活动")
        dialog.geometry("360x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 360) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="请选择要导入兑换码的活动：", 
                 font=("微软雅黑", 11), bg=COLORS["bg_dark"], fg=COLORS["text_primary"]).pack(pady=(20, 10))
        
        # 活动列表（从VERSION_DEFAULT_ACT_ID获取）
        activity_list = ["全部活动"] + list(VERSION_DEFAULT_ACT_ID.keys())
        activity_var = tk.StringVar(value=activity_list[0])
        
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Activity.TCombobox', 
                        fieldbackground=COLORS["bg_input"], 
                        background=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        arrowcolor=COLORS["accent"])
        
        activity_combo = ttk.Combobox(dialog, textvariable=activity_var, 
                                        values=activity_list, state="readonly",
                                        font=("微软雅黑", 11), width=25,
                                        style='Activity.TCombobox')
        activity_combo.pack(pady=10)
        
        result = {"selected": None}
        
        def on_confirm():
            result["selected"] = activity_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="确定", bg=COLORS["accent"], fg="#000000",
                  font=("微软雅黑", 10, "bold"), bd=0, padx=25, pady=6, cursor="hand2",
                  command=on_confirm).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text="取消", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                  font=("微软雅黑", 10), bd=0, padx=25, pady=6, cursor="hand2",
                  command=on_cancel).pack(side=tk.LEFT, padx=10)
        
        dialog.configure(bg=COLORS["bg_dark"])
        self.wait_window(dialog)
        
        selected_activity = result["selected"]
        if not selected_activity:
            return
        
        # 根据选择获取act_id列表
        if selected_activity == "全部活动":
            act_id_list = list(VERSION_DEFAULT_ACT_ID.values())
            activity_names = list(VERSION_DEFAULT_ACT_ID.keys())
        else:
            act_id_list = [VERSION_DEFAULT_ACT_ID.get(selected_activity, "")]
            activity_names = [selected_activity]
        
        # 过滤掉空的act_id
        valid_pairs = [(name, aid) for name, aid in zip(activity_names, act_id_list) if aid]
        if not valid_pairs:
            messagebox.showwarning("提示", "未找到有效的活动ID")
            return

        # 获取所有账户
        accounts = []
        try:
            if self.account_mgr and hasattr(self.account_mgr, 'accounts'):
                accounts = self.account_mgr.accounts
            else:
                # 从文件读取（使用统一的ACCOUNTS_FILE路径）
                if os.path.exists(str(ACCOUNTS_FILE)):
                    with open(str(ACCOUNTS_FILE), "r", encoding="utf-8") as f:
                        accounts = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"读取账户失败: {e}")
            return

        if not accounts:
            messagebox.showwarning("提示", "没有可用的账户，请先导入账户")
            return

        # 遍历所有活动和账户，调用领取记录API
        total_imported = 0
        total_skipped = 0
        account_results = []

        for activity_name, act_id in valid_pairs:
            for acc in accounts:
                try:
                    cookies = cookies_from_account(acc)
                    record_data, record_msg = get_award_record(act_id, cookies)'''

if old_import_start in content:
    content = content.replace(old_import_start, new_import_start, 1)
    print("✓ 已修改import_from_records函数开头")
else:
    print("✗ 未找到import_from_records开头代码")

# 修改结果显示部分，添加活动名称
old_result = '''                    account_results.append(f"  {acc['name']}: 导入 {account_codes} 个，共 {len(record_list)} 条记录")
                else:
                    account_results.append(f"  {acc['name']}: 无领取记录 ({record_msg})")
            except Exception as e:
                account_results.append(f"  {acc['name']}: 异常 - {e}")

        # 刷新列表
        self.refresh_list()

        # 显示结果
        result_msg = f"导入完成！\n\n共导入 {total_imported} 个兑换码\n跳过 {total_skipped} 个（重复）\n\n详情：\n" + "\n".join(account_results)
        messagebox.showinfo("导入结果", result_msg)'''

new_result = '''                    account_results.append(f"  [{activity_name}] {acc['name']}: 导入 {account_codes} 个，共 {len(record_list)} 条记录")
                else:
                    account_results.append(f"  [{activity_name}] {acc['name']}: 无领取记录 ({record_msg})")
            except Exception as e:
                account_results.append(f"  [{activity_name}] {acc['name']}: 异常 - {e}")

        # 刷新列表
        self.refresh_list()

        # 显示结果
        result_msg = f"导入完成！\n\n共导入 {total_imported} 个兑换码\n跳过 {total_skipped} 个（重复）\n\n详情：\n" + "\n".join(account_results)
        messagebox.showinfo("导入结果", result_msg)'''

if old_result in content:
    content = content.replace(old_result, new_result, 1)
    print("✓ 已修改结果显示部分")
else:
    print("✗ 未找到结果显示代码")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 修改完成")
