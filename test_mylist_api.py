# -*- coding: utf-8 -*-
"""测试领取记录API mylist"""

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

cookies = {
    "SESSDATA": target_acc["SESSDATA"],
    "bili_jct": target_acc["bili_jct"],
}
if target_acc.get("DedeUserID"):
    cookies["DedeUserID"] = target_acc["DedeUserID"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/blackboard/era/award-exchange.html",
}

act_id = "1ERAzwloghvb5600"

# 测试可能的URL
test_urls = [
    f"https://api.bilibili.com/x/activity_components/mission/mylist?activity_id={act_id}",
    f"https://data.bilibili.com/x/activity_components/mission/mylist?activity_id={act_id}",
    f"https://api.bilibili.com/x/activity_components/mission/mylist?act_id={act_id}",
    f"https://api.bilibili.com/x/activity/mission/mylist?activity_id={act_id}",
]

print("测试领取记录API...")
print("=" * 80)

for url in test_urls:
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        print(f"\nURL: {url}")
        print(f"  状态码: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('Content-Type', '未知')}")
        
        if resp.text and resp.text.strip():
            try:
                data = resp.json()
                print(f"  code: {data.get('code')}, message: {data.get('message')}")
                if data.get("data"):
                    data_str = json.dumps(data["data"], ensure_ascii=False)
                    print(f"  data前1000字符: {data_str[:1000]}")
                else:
                    print(f"  data: {data.get('data')}")
            except:
                print(f"  非JSON响应前200字符: {resp.text[:200]}")
        else:
            print(f"  空响应")
    except Exception as e:
        print(f"\nURL: {url}")
        print(f"  异常: {e}")

print("\n" + "=" * 80)
print("测试完成")
