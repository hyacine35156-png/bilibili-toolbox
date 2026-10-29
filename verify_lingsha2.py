# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json, requests
from main_gui_pro import HEADERS, cookies_from_account
with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)
account = next(a for a in accounts if "灵砂" in a.get("name", ""))
cookies = cookies_from_account(account)
resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=HEADERS, cookies=cookies, timeout=10)
data = resp.json()
if data.get("code") == 0:
    print(f"✓ 登录有效: {data['data']['uname']} (UID: {data['data']['mid']})")
else:
    print(f"✗ 登录失败: {data.get('message')}")
