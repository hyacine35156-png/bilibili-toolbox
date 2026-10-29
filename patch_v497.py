#!/usr/bin/env python3
"""v4.9.7: 修复电池余额查询，改用User/getUserInfo接口，字段gold"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 替换get_battery_balance方法
# ============================================================
old_method = '''    def get_battery_balance(self, account):
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
            return None'''

new_method = '''    def get_battery_balance(self, account):
        """查询账户电池余额（gold字段，后两位为小数，100=1电池）"""
        try:
            sessdata = account.get("sessdata", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = "https://api.live.bilibili.com/User/getUserInfo"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                user_info = data.get("data", {})
                # gold字段是电池数，后两位为小数，如100=1电池
                gold_raw = user_info.get("gold", 0)
                battery = gold_raw / 100.0 if gold_raw else 0
                return battery
            return None
        except Exception:
            return None'''

if old_method in content:
    content = content.replace(old_method, new_method)
    print("1. get_battery_balance方法已修复")
else:
    print("1. 未找到get_battery_balance方法")

# ============================================================
# 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.6"', 'APP_VERSION = "v4.9.7"')
print("2. 版本号: v4.9.6 -> v4.9.7")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
