#!/usr/bin/env python3
"""测试电池余额查询API"""

import json
import requests

# 读取账户
with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = accounts[0]
print("账户名:", account.get("name"))
print("SESSDATA存在:", "SESSDATA" in account)
print("bili_jct存在:", "bili_jct" in account)

sessdata = account.get("SESSDATA", "")
bili_jct = account.get("bili_jct", "")
cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 测试1: User/getUserInfo
print("\n=== 测试1: User/getUserInfo ===")
try:
    url = "https://api.live.bilibili.com/User/getUserInfo"
    resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    data = resp.json()
    print("code:", data.get("code"))
    print("msg:", data.get("msg"))
    if data.get("code") == 0:
        user_info = data.get("data", {})
        print("data字段:", list(user_info.keys()))
        print("gold:", user_info.get("gold"))
        print("silver:", user_info.get("silver"))
        print("billCoin:", user_info.get("billCoin"))
    else:
        print("完整返回:", json.dumps(data, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print("异常:", e)

# 测试2: myWallet
print("\n=== 测试2: xlive/revenue/v1/wallet/myWallet ===")
try:
    url = "https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1"
    resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    data = resp.json()
    print("code:", data.get("code"))
    print("msg:", data.get("msg"))
    if data.get("code") == 0:
        wallet = data.get("data", {})
        print("data字段:", list(wallet.keys()))
        print("完整data:", json.dumps(wallet, ensure_ascii=False, indent=2)[:1000])
    else:
        print("完整返回:", json.dumps(data, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print("异常:", e)

# 测试3: 直播钱包新接口
print("\n=== 测试3: xlivedata/v1/DataSource/getData ===")
try:
    url = "https://api.live.bilibili.com/xlivedata/v1/DataSource/getData?type=wallet"
    resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    data = resp.json()
    print("code:", data.get("code"))
    print("完整返回:", json.dumps(data, ensure_ascii=False, indent=2)[:1000])
except Exception as e:
    print("异常:", e)
