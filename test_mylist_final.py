# -*- coding: utf-8 -*-
"""测试领取记录API，只用基本Cookie"""

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

# WBI签名
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

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

# 1. 验证Cookie
print("1. 验证Cookie...")
resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, cookies=cookies, timeout=10)
data = resp.json()
print(f"   code: {data.get('code')}, 用户: {data.get('data', {}).get('uname', '未知')}")

if data.get("code") != 0:
    print("   Cookie无效，无法继续测试")
    exit()

# 获取WBI密钥
wbi_img = data["data"]["wbi_img"]
img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
print(f"   WBI密钥获取成功")

# 2. 尝试获取bili_ticket
print("\n2. 尝试获取bili_ticket...")
try:
    resp = requests.get("https://api.bilibili.com/x/frontend/finger/spi", headers=headers, cookies=cookies, timeout=10)
    ticket_data = resp.json()
    print(f"   code: {ticket_data.get('code')}")
    if ticket_data.get("data"):
        print(f"   data: {json.dumps(ticket_data['data'], ensure_ascii=False)[:500]}")
        if "b_3" in ticket_data["data"] or "b_4" in ticket_data["data"]:
            cookies["buvid3"] = ticket_data["data"].get("b_3", "")
            cookies["buvid4"] = ticket_data["data"].get("b_4", "")
            print(f"   已获取buvid3和buvid4")
except Exception as e:
    print(f"   获取bili_ticket失败: {e}")

# 3. 测试mylist API（PC端UA）
print("\n3. 测试mylist API（PC端UA）...")
act_id = "1ERAzwloghvb5600"
params = {
    "activity_id": act_id,
    "web_location": "888.126558",
}
signed_params = wbi_sign(params, img_key, sub_key)

url = "https://api.bilibili.com/x/activity_components/mission/mylist"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghvsaz00",
    "Origin": "https://www.bilibili.com",
    "Accept": "*/*",
}
resp = requests.get(url, headers=headers, cookies=cookies, params=signed_params, timeout=10)
result = resp.json()
print(f"   code: {result.get('code')}, message: {result.get('message')}")
if result.get("data"):
    data_str = json.dumps(result["data"], ensure_ascii=False, indent=2)
    print(f"   data前2000字符: {data_str[:2000]}")

# 4. 测试mylist API（移动端UA）
print("\n4. 测试mylist API（移动端UA）...")
headers_mobile = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36 Edg/152.0.0.0",
    "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghvsaz00",
    "Origin": "https://www.bilibili.com",
    "Accept": "*/*",
}
resp = requests.get(url, headers=headers_mobile, cookies=cookies, params=signed_params, timeout=10)
result = resp.json()
print(f"   code: {result.get('code')}, message: {result.get('message')}")
if result.get("data"):
    data_str = json.dumps(result["data"], ensure_ascii=False, indent=2)
    print(f"   data前2000字符: {data_str[:2000]}")

print("\n测试完成")
