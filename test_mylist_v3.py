# -*- coding: utf-8 -*-
"""测试领取记录API，尝试POST方法和额外参数"""

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

# 先验证Cookie是否有效
resp = requests.get("https://api.bilibili.com/x/web-interface/nav", cookies=cookies, timeout=10)
nav_data = resp.json()
print(f"Cookie验证: code={nav_data.get('code')}, 用户={nav_data.get('data', {}).get('uname', '未知')}")

act_id = "1ERAzwloghvb5600"
base_url = "https://api.bilibili.com/x/activity_components/mission/mylist"

# 测试不同的请求方式和参数
test_configs = [
    ("GET + activity_id", "GET", f"{base_url}?activity_id={act_id}", None),
    ("GET + act_id", "GET", f"{base_url}?act_id={act_id}", None),
    ("GET + activity_id + csrf", "GET", f"{base_url}?activity_id={act_id}&csrf={cookies['bili_jct']}", None),
    ("POST + activity_id (form)", "POST", base_url, {"activity_id": act_id}),
    ("POST + act_id (form)", "POST", base_url, {"act_id": act_id}),
    ("POST + activity_id + csrf (form)", "POST", base_url, {"activity_id": act_id, "csrf": cookies["bili_jct"]}),
    ("POST + activity_id (json)", "POST", base_url, {"activity_id": act_id}),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/blackboard/era/award-exchange.html",
    "Origin": "https://www.bilibili.com",
}

print("\n测试领取记录API...")
print("=" * 80)

for name, method, url, data in test_configs:
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        else:
            if "json" in name:
                resp = requests.post(url, headers={**headers, "Content-Type": "application/json"}, 
                                     cookies=cookies, json=data, timeout=10)
            else:
                resp = requests.post(url, headers={**headers, "Content-Type": "application/x-www-form-urlencoded"}, 
                                     cookies=cookies, data=data, timeout=10)
        
        result = resp.json()
        code = result.get("code")
        message = result.get("message")
        
        if code == 0:
            print(f"\n✓ {name}:")
            print(f"  code: {code}, message: {message}")
            if result.get("data"):
                data_str = json.dumps(result["data"], ensure_ascii=False)
                print(f"  data前2000字符: {data_str[:2000]}")
            else:
                print(f"  data: {result.get('data')}")
        else:
            print(f"✗ {name}: code={code}, message={message}")
    except Exception as e:
        print(f"✗ {name}: 异常 - {e}")

print("\n" + "=" * 80)
print("测试完成")
