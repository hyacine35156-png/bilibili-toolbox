# -*- coding: utf-8 -*-
"""测试更多领取记录API端点"""

import json
import requests
import time
import hashlib
import urllib.parse

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
    "Content-Type": "application/x-www-form-urlencoded",
}

act_id = "1ERAzwloghvb5600"
task_id = "6ERAcwloghvsaz00"

# 更多API端点（GET和POST都测试）
test_endpoints = [
    # GET方法
    ("GET", "https://api.bilibili.com/x/activity/award/record", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity/mission/award/record", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/award/record", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/mission/history", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/mission/award/history", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/mission/receive/history", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/mission/list", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/mission/award", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/mission/receive/list", {"act_id": act_id}),
    ("GET", "https://api.bilibili.com/x/activity_components/mission/record/list", {"act_id": act_id}),
    # POST方法
    ("POST", "https://api.bilibili.com/x/activity_components/mission/award_record", {"act_id": act_id, "csrf": cookies["bili_jct"]}),
    ("POST", "https://api.bilibili.com/x/activity_components/mission/record", {"act_id": act_id, "csrf": cookies["bili_jct"]}),
    ("POST", "https://api.bilibili.com/x/activity_components/mission/award/list", {"act_id": act_id, "csrf": cookies["bili_jct"]}),
    ("POST", "https://api.bilibili.com/x/activity_components/mission/receive_record", {"act_id": act_id, "csrf": cookies["bili_jct"]}),
    ("POST", "https://api.bilibili.com/x/activity_components/mission/history", {"act_id": act_id, "csrf": cookies["bili_jct"]}),
]

print("测试更多API端点...")
print("=" * 80)

found = []
for method, endpoint, params in test_endpoints:
    try:
        if method == "GET":
            resp = requests.get(endpoint, headers=headers, cookies=cookies, params=params, timeout=10)
        else:
            resp = requests.post(endpoint, headers=headers, cookies=cookies, data=params, timeout=10)
        
        # 检查响应是否为空
        if not resp.text or resp.text.strip() == "":
            print(f"✗ {method} {endpoint} -> 空响应")
            continue
        
        try:
            data = resp.json()
            code = data.get("code")
            message = data.get("message", "")
            
            # 只打印有意义的结果
            if code not in [-404, -403, -400, -352, -412]:
                print(f"\n✓ {method} {endpoint}")
                print(f"  code: {code}, message: {message}")
                if data.get("data"):
                    data_str = json.dumps(data["data"], ensure_ascii=False)
                    print(f"  data前500字符: {data_str[:500]}")
                found.append((method, endpoint, code, message))
            else:
                print(f"✗ {method} {endpoint} -> code={code}, message={message}")
        except:
            print(f"✗ {method} {endpoint} -> 非JSON响应: {resp.text[:100]}")
    except Exception as e:
        print(f"✗ {method} {endpoint} -> 异常: {e}")

print("\n" + "=" * 80)
if found:
    print(f"找到 {len(found)} 个可能的端点:")
    for method, endpoint, code, message in found:
        print(f"  {method} {endpoint} -> code={code}, message={message}")
else:
    print("未找到有效的领取记录API端点")
print("\n测试完成")
