# -*- coding: utf-8 -*-
"""简化版测试：先确认Cookie和网络，再测试API端点"""

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

print(f"使用账户: {target_acc['name']}")

# 构造cookies
cookies = {
    "SESSDATA": target_acc["SESSDATA"],
    "bili_jct": target_acc["bili_jct"],
}
if target_acc.get("DedeUserID"):
    cookies["DedeUserID"] = target_acc["DedeUserID"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

# 1. 测试网络连接和Cookie
print("\n1. 测试网络连接和Cookie...")
try:
    resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, cookies=cookies, timeout=10)
    print(f"   状态码: {resp.status_code}")
    print(f"   响应前200字符: {resp.text[:200]}")
    data = resp.json()
    if data.get("code") == 0:
        print(f"   ✓ Cookie有效，用户: {data['data'].get('uname', '未知')}")
    else:
        print(f"   ✗ Cookie无效: {data.get('message')}")
except Exception as e:
    print(f"   ✗ 网络异常: {e}")

# 2. 测试任务信息API（确认WBI签名是否工作）
print("\n2. 测试任务信息API...")
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
    25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]

def get_mixin_key(orig):
    return "".join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]

def wbi_sign(params, img_key, sub_key):
    mixin_key = get_mixin_key(img_key + sub_key)
    params["wts"] = int(time.time())
    sorted_params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(sorted_params)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    sorted_params["w_rid"] = w_rid
    return sorted_params

# 获取WBI密钥
try:
    resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, cookies=cookies, timeout=10)
    data = resp.json()
    wbi_img = data["data"]["wbi_img"]
    img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
    print(f"   ✓ WBI密钥获取成功")
except Exception as e:
    print(f"   ✗ WBI密钥获取失败: {e}")
    img_key, sub_key = None, None

if img_key:
    task_id = "6ERAcwloghvsaz00"
    params = {
        "task_id": task_id,
        "web_location": "888.126558",
    }
    signed_params = wbi_sign(params, img_key, sub_key)
    try:
        resp = requests.get("https://api.bilibili.com/x/activity_components/mission/info", 
                           headers={**headers, "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}"},
                           cookies=cookies, params=signed_params, timeout=10)
        data = resp.json()
        print(f"   任务信息API code: {data.get('code')}, message: {data.get('message')}")
        if data.get("code") == 0:
            print(f"   ✓ 任务信息API工作正常")
        else:
            print(f"   ✗ 任务信息API失败")
    except Exception as e:
        print(f"   ✗ 任务信息API异常: {e}")

# 3. 测试领取记录API端点（不签名，直接请求）
print("\n3. 测试领取记录API端点（不签名）...")
act_id = "1ERAzwloghvb5600"
test_endpoints = [
    "https://api.bilibili.com/x/activity_components/mission/award_record",
    "https://api.bilibili.com/x/activity_components/mission/record",
    "https://api.bilibili.com/x/activity_components/mission/award/list",
    "https://api.bilibili.com/x/activity_components/mission/receive_record",
    "https://api.bilibili.com/x/activity_components/mission/award/records",
]

for endpoint in test_endpoints:
    try:
        resp = requests.get(endpoint, headers=headers, cookies=cookies, 
                           params={"act_id": act_id}, timeout=10)
        data = resp.json()
        code = data.get("code")
        if code not in [-404, -403, -400, -352]:
            print(f"   ✓ {endpoint}")
            print(f"     code: {code}, message: {data.get('message')}")
            if data.get("data"):
                print(f"     data前300字符: {json.dumps(data['data'], ensure_ascii=False)[:300]}")
        else:
            print(f"   ✗ {endpoint} -> code={code}")
    except Exception as e:
        print(f"   ✗ {endpoint} -> 异常: {e}")

print("\n测试完成")
