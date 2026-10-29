# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json
import requests
from main_gui_pro import HEADERS, cookies_from_account, get_mission_info

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = next(a for a in accounts if "灵砂" in a.get("name", ""))
cookies = cookies_from_account(account)

# 验证登录
resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=HEADERS, cookies=cookies, timeout=10)
data = resp.json()
if data.get("code") == 0:
    print(f"✓ 登录有效: {data['data']['uname']} (UID: {data['data']['mid']})")
else:
    print(f"✗ 登录失败: {data.get('message')}")

# 测试任务查询
info, msg = get_mission_info("6ERAcwloghvod500", cookies)
if info:
    print(f"\n任务: {info.get('task_name')}")
    print(f"  task_finished: {info.get('task_finished')}")
    print(f"  status: {info.get('status')}")
    print(f"  message: {info.get('message')}")
