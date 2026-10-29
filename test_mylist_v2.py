# -*- coding: utf-8 -*-
"""测试领取记录API，使用移动端UA和完整Cookie"""

import json
import requests

# 读取账户
accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

target_acc = None
for acc in accounts:
    if acc.get("name") == "灵砂是无敌的":
        target_acc = acc
        break

print(f"账户字段: {list(target_acc.keys())}")

# 构造完整cookies（包含所有账户字段中可能的cookie字段）
cookies = {}
cookie_keys = ["SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", 
               "buvid3", "buvid4", "buvid_fp", "_uuid", "b_nut", "b_lsid", "bili_ticket"]
for key in cookie_keys:
    if key in target_acc and target_acc[key]:
        cookies[key] = str(target_acc[key])

print(f"使用的Cookie字段: {list(cookies.keys())}")

# 移动端UA（从截图中看到的）
mobile_ua = "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36 Edg/152.0.0.0"
pc_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

act_id = "1ERAzwloghvb5600"
url = f"https://api.bilibili.com/x/activity_components/mission/mylist?activity_id={act_id}"

# 测试不同的UA和请求头
test_configs = [
    ("移动端UA + 移动端Referer", mobile_ua, "https://www.bilibili.com/blackboard/era/award-exchange.html"),
    ("PC端UA + PC端Referer", pc_ua, "https://www.bilibili.com/blackboard/era/award-exchange.html"),
    ("移动端UA + 空Referer", mobile_ua, ""),
]

print("\n测试领取记录API...")
print("=" * 80)

for name, ua, referer in test_configs:
    headers = {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        data = resp.json()
        print(f"\n{name}:")
        print(f"  code: {data.get('code')}, message: {data.get('message')}")
        if data.get("data"):
            data_str = json.dumps(data["data"], ensure_ascii=False)
            print(f"  data前1500字符: {data_str[:1500]}")
        else:
            print(f"  data: {data.get('data')}")
    except Exception as e:
        print(f"\n{name}: 异常 - {e}")

print("\n" + "=" * 80)
print("测试完成")
