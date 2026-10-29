# -*- coding: utf-8 -*-
"""测试领取记录API，使用WBI签名"""

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

# 获取WBI密钥
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36 Edg/152.0.0.0",
    "Referer": "https://www.bilibili.com/",
}
resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, cookies=cookies, timeout=10)
data = resp.json()
wbi_img = data["data"]["wbi_img"]
img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
print(f"WBI密钥获取成功")

# 构造请求参数
act_id = "1ERAzwloghvb5600"
params = {
    "activity_id": act_id,
    "web_location": "888.126558",
}
signed_params = wbi_sign(params, img_key, sub_key)
print(f"签名参数: {signed_params}")

# 发送请求
url = "https://api.bilibili.com/x/activity_components/mission/mylist"
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36 Edg/152.0.0.0",
    "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghvsaz00",
    "Origin": "https://www.bilibili.com",
    "Accept": "*/*",
}

print(f"\n发送请求到: {url}")
resp = requests.get(url, headers=headers, cookies=cookies, params=signed_params, timeout=10)
print(f"状态码: {resp.status_code}")
print(f"Bili-Status-Code: {resp.headers.get('Bili-Status-Code', '未知')}")

result = resp.json()
print(f"\ncode: {result.get('code')}")
print(f"message: {result.get('message')}")

if result.get("data"):
    data_str = json.dumps(result["data"], ensure_ascii=False, indent=2)
    print(f"\ndata内容（前3000字符）:")
    print(data_str[:3000])
else:
    print(f"data: {result.get('data')}")
    print(f"\n完整响应: {json.dumps(result, ensure_ascii=False)[:1000]}")
