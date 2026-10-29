# -*- coding: utf-8 -*-
"""添加启动时账号登录状态验证功能"""

with open("main_gui_pro.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在__init__最后添加启动验证线程（在第9970行日志之后）
old_init_end = '''        self.log("(配置文件已自动存到data子文件夹，不会铺满桌面)")

    def restore_selected_account(self):'''

new_init_end = '''        self.log("(配置文件已自动存到data子文件夹，不会铺满桌面)")
        # 启动时后台验证所有账号登录状态
        self._startup_check_accounts()

    def _startup_check_accounts(self):
        """启动时在后台线程验证所有账号登录状态，失效则弹窗报错"""
        import threading
        def _check():
            try:
                import requests
                time.sleep(2)  # 等UI完全加载
                failed = []
                for acc in self.account_mgr.accounts:
                    name = acc.get("name", "未知")
                    try:
                        cookies = cookies_from_account(acc)
                        resp = requests.get("https://api.bilibili.com/x/web-interface/nav",
                                            headers=HEADERS, cookies=cookies, timeout=8)
                        data = resp.json()
                        if data.get("code") != 0:
                            failed.append(f"{name}（{data.get('message', '未知错误')}）")
                    except Exception as e:
                        failed.append(f"{name}（验证异常: {str(e)[:30]}）")
                if failed:
                    msg = f"以下 {len(failed)} 个账号登录已失效，请重新登录：\n\n" + "\n".join(failed)
                    self.root.after(0, lambda: self._show_account_login_error(msg))
                else:
                    self.log(f"✓ 启动账号验证: 全部 {len(self.account_mgr.accounts)} 个账号登录有效")
            except Exception as e:
                self.log(f"⚠ 启动账号验证异常: {e}")
        threading.Thread(target=_check, daemon=True).start()

    def _show_account_login_error(self, msg):
        """在主线程弹出账号登录失效错误"""
        from tkinter import messagebox
        self.log(f"⚠ {msg}")
        messagebox.showerror("账号登录失效", msg)

    def restore_selected_account(self):'''

content = content.replace(old_init_end, new_init_end)

# 2. 更新版本号
content = content.replace('APP_VERSION = "v5.9.51"', 'APP_VERSION = "v5.9.52"')

with open("main_gui_pro.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ 已添加启动账号验证功能")
print("✓ 版本号已更新为v5.9.52")
