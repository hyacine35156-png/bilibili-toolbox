# -*- coding: utf-8 -*-
"""测试B站活动领取记录API端点"""

import json
import requests
import time
import hashlib
import urllib.parse

# 读取账户
accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 找到"灵砂是无敌的"账户
target_acc = None
for acc in accounts:
    if acc.get("name") == "灵砂是无敌的":
        target_acc = acc
        break

if not target_acc:
    print("未找到账户")
    exit()

print(f"使用账户: {target_acc['name']}")

# 构造cookies
cookies = {}
for key in ["SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid"]:
    if key in target_acc:
        cookies[key] = target_acc[key]

print(f"Cookies字段: {list(cookies.keys())}")

# WBI签名函数
def get_wbi_keys(cookies_dict):
    try:
        resp = requests.get("https://api.bilibili.com/x/web-interface/nav", cookies=cookies_dict, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            wbi_img = data["data"]["wbi_img"]
            return wbi_img["img_url"].split("/")[-1].split(".")[0], wbi_img["sub_url"].split("/")[-1].split(".")[0]
    except Exception as e:
        print(f"获取WBI密钥失败: {e}")
    return None, None

def get_mixin_key(orig):
    mixin_key_enc_table = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
        25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
    ]
    return "".join(orig[i] for i in mixin_key_enc_table if i < len(orig))[:32]

def wbi_sign(params, img_key, sub_key):
    mixin_key = get_mixin_key(img_key + sub_key)
    params["wts"] = int(time.time())
    sorted_params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(sorted_params)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    sorted_params["w_rid"] = w_rid
    return sorted_params

# 获取WBI密钥
img_key, sub_key = get_wbi_keys(cookies)
if not img_key:
    print("无法获取WBI密钥")
    exit()
print(f"WBI密钥获取成功")

# 测试的API端点
test_endpoints = [
    "https://api.bilibili.com/x/activity_components/mission/award_record",
    "https://api.bilibili.com/x/activity_components/mission/record",
    "https://api.bilibili.com/x/activity_components/mission/award/list",
    "https://api.bilibili.com/x/activity_components/mission/receive_record",
    "https://api.bilibili.com/x/activity_components/mission/award/records",
    "https://api.bilibili.com/x/activity_components/mission/award_records",
    "https://api.bilibili.com/x/activity_components/mission/receive/record",
    "https://api.bilibili.com/x/activity_components/mission/list",
]

act_id = "1ERAzwloghvb5600"
task_id = "6ERAcwloghvsaz00"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}",
}

print("\n开始测试API端点...")
print("=" * 80)

for endpoint in test_endpoints:
    # 测试带act_id的参数
    params = {
        "act_id": act_id,
        "web_location": "888.126558",
    }
    try:
        signed_params = wbi_sign(params, img_key, sub_key)
        resp = requests.get(endpoint, headers=headers, cookies=cookies, params=signed_params, timeout=10)
        result = resp.json()
        code = result.get("code")
        message = result.get("message", "")
        data = result.get("data")
        
        # 只打印有意义的结果（code不是-404或-403的）
        if code not in [-404, -403, -400]:
            print(f"\n✓ 端点: {endpoint}")
            print(f"  code: {code}, message: {message}")
            if data:
                data_str = json.dumps(data, ensure_ascii=False)
                print(f"  data前500字符: {data_str[:500]}")
            else:
                print(f"  data: None")
        else:
            print(f"✗ 端点: {endpoint} -> code={code}, message={message}")
    except Exception as e:
        print(f"✗ 端点: {endpoint} -> 异常: {e}")

print("\n" + "=" * 80)
print("测试完成")
