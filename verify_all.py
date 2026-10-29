# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json, requests
from main_gui_pro import HEADERS, cookies_from_account

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

print("账号登录状态验证：")
print("="*60)
valid_count = 0
for i, acc in enumerate(accounts, 1):
    name = acc.get("name", "未知")
    cookies = cookies_from_account(acc)
    try:
        resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=HEADERS, cookies=cookies, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            uname = data["data"]["uname"]
            mid = data["data"]["mid"]
            print(f"【{i}】{name}: ✓ 有效 ({uname}, UID:{mid})")
            valid_count += 1
        else:
            print(f"【{i}】{name}: ✗ 失效 - {data.get('message')}")
    except Exception as e:
        print(f"【{i}】{name}: ✗ 异常 - {e}")

print("="*60)
print(f"总计: {valid_count}/{len(accounts)} 个账号有效")
