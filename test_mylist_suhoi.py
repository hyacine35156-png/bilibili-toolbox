# -*- coding: utf-8 -*-
"""用苏霍伊账户测试mylist API"""

import json
import requests
import time
import hashlib
import urllib.parse

# 读取账户
accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

target_acc = next((a for a in accounts if a.get('name') == '苏霍伊'), None)

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
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, cookies=cookies, timeout=10)
data = resp.json()
print("Cookie验证: code=", data.get("code"), ", 用户=", data.get("data", {}).get("uname", "未知"))

wbi_img = data["data"]["wbi_img"]
img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]

# 测试mylist API
act_id = "1ERAzwloghvb5600"
params = {"activity_id": act_id, "web_location": "888.126558"}
signed_params = wbi_sign(params, img_key, sub_key)

url = "https://api.bilibili.com/x/activity_components/mission/mylist"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/blackboard/era/award-exchange.html",
    "Origin": "https://www.bilibili.com",
    "Accept": "*/*",
}

print("\n请求mylist API...")
resp = requests.get(url, headers=headers, cookies=cookies, params=signed_params, timeout=10)
print("状态码:", resp.status_code)
print("Bili-Status-Code:", resp.headers.get("Bili-Status-Code", "未知"))

result = resp.json()
print("code:", result.get("code"))
print("message:", result.get("message"))

if result.get("data"):
    data_str = json.dumps(result["data"], ensure_ascii=False, indent=2)
    print("\ndata内容（前3000字符）:")
    print(data_str[:3000])
else:
    print("data:", result.get("data"))
    print("\n完整响应:", json.dumps(result, ensure_ascii=False)[:1000])
