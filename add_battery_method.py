#!/usr/bin/env python3
"""添加get_battery_balance方法"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 在_on_account_check之前添加get_battery_balance方法
old_text = '''    def _on_account_check(self):
        """复选框点击时保存配置"""'''

new_text = '''    def get_battery_balance(self, account):
        """查询账户电池余额"""
        try:
            sessdata = account.get("sessdata", "")
            cookies = {"SESSDATA": sessdata}
            url = "https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1"
            resp = requests.get(url, cookies=cookies, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                wallet = data.get("data", {})
                battery = wallet.get("bp", wallet.get("battery", 0))
                return battery
            return None
        except Exception:
            return None

    def _on_account_check(self):
        """复选框点击时保存配置"""'''

if old_text in content:
    content = content.replace(old_text, new_text)
    print("已添加get_battery_balance方法")
else:
    print("未找到插入点")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
