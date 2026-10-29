# -*- coding: utf-8 -*-
"""添加从领取记录导入所有兑换码功能"""

FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在刷新列表按钮后面添加"从领取记录导入"按钮
old_btn = '''        self.refresh_btn = tk.Button(btn_frame, text="🔄 刷新列表", bg=COLORS["bg_input"],
                                      fg=COLORS["text_secondary"], font=("微软雅黑", 10),
                                      bd=0, padx=16, pady=6, cursor="hand2", command=self.refresh_list)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 8))'''

new_btn = '''        self.refresh_btn = tk.Button(btn_frame, text="🔄 刷新列表", bg=COLORS["bg_input"],
                                      fg=COLORS["text_secondary"], font=("微软雅黑", 10),
                                      bd=0, padx=16, pady=6, cursor="hand2", command=self.refresh_list)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.import_btn = tk.Button(btn_frame, text="📥 从领取记录导入", bg="#FF8F00",
                                     fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                     bd=0, padx=16, pady=6, cursor="hand2", command=self.import_from_records)
        self.import_btn.pack(side=tk.LEFT, padx=(0, 8))'''

if old_btn in content:
    content = content.replace(old_btn, new_btn, 1)
    print("✓ 已添加导入按钮")
else:
    print("✗ 未找到刷新按钮代码")

# 2. 在refresh_list函数前面添加import_from_records函数
old_refresh = '''    def refresh_list(self):
        """刷新兑换码列表"""'''

new_refresh = '''    def import_from_records(self):
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
                # 从文件读取
                import os
                accounts_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "data", "accounts.json")
                if not os.path.exists(accounts_file):
                    accounts_file = os.path.join(os.getcwd(), "data", "accounts.json")
                if os.path.exists(accounts_file):
                    with open(accounts_file, "r", encoding="utf-8") as f:
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
                record_data, record_msg = get_award_record(act_id, cookies)
                
                if record_data and record_data.get("list"):
                    record_list = record_data["list"]
                    account_codes = 0
                    
                    for record in record_list:
                        # 提取兑换码
                        codes = extract_redeem_codes(record)
                        for code_info in codes:
                            # 保存兑换码（去重）
                            ok_save, save_msg = save_redeem_code(
                                record.get("award_name", "未知任务"),
                                acc.get("name", "未知"),
                                record,
                                task_period="",
                                task_type=record.get("type", "")
                            )
                            if ok_save:
                                total_imported += 1
                                account_codes += 1
                            else:
                                total_skipped += 1
                    
                    account_results.append(f"  {acc['name']}: 导入 {account_codes} 个，共 {len(record_list)} 条记录")
                else:
                    account_results.append(f"  {acc['name']}: 无领取记录 ({record_msg})")
            except Exception as e:
                account_results.append(f"  {acc['name']}: 异常 - {e}")

        # 刷新列表
        self.refresh_list()

        # 显示结果
        result_msg = f"导入完成！\\n\\n共导入 {total_imported} 个兑换码\\n跳过 {total_skipped} 个（重复）\\n\\n详情：\\n" + "\\n".join(account_results)
        messagebox.showinfo("导入结果", result_msg)

    def refresh_list(self):
        """刷新兑换码列表"""'''

if old_refresh in content:
    content = content.replace(old_refresh, new_refresh, 1)
    print("✓ 已添加import_from_records函数")
else:
    print("✗ 未找到refresh_list函数")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 修改完成")
