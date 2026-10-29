# -*- coding: utf-8 -*-
"""直接调用领取记录API，查看返回结构"""

import json
import requests
import time
import hashlib
import urllib.parse

# 读取账户
accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

target_acc = next((a for a in accounts if a.get('name') == '灵砂是无敌的'), None)

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

# 调用领取记录API
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

print("\n调用领取记录API...")
resp = requests.get(url, headers=headers, cookies=cookies, params=signed_params, timeout=10)
print("状态码:", resp.status_code)
print("Bili-Status-Code:", resp.headers.get("Bili-Status-Code", "未知"))

result = resp.json()
print("code:", result.get("code"))
print("message:", result.get("message"))

if result.get("data"):
    data = result["data"]
    print("\ndata顶层字段:", list(data.keys()))
    print("had_address:", data.get("had_address"))
    
    if data.get("list"):
        record_list = data["list"]
        print(f"\nlist类型: {type(record_list).__name__}")
        print(f"list长度: {len(record_list)}")
        
        if isinstance(record_list, list) and len(record_list) > 0:
            print(f"\n第一条记录的字段: {list(record_list[0].keys())}")
            print(f"\n第一条记录完整内容:")
            print(json.dumps(record_list[0], ensure_ascii=False, indent=2))
            
            # 搜索所有可能的兑换码字段
            print("\n搜索所有可能的兑换码字段...")
            code_keys = ['cdk', 'redeem_code', 'redeemCode', 'award_code', 'awardCode', 
                         'gift_code', 'giftCode', 'exchange_code', 'exchangeCode', 
                         'code', 'key', 'ticket', 'coupon', 'cdkey', 'cd_key']
            
            def search_codes(obj, path=""):
                found = []
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        current_path = f"{path}.{k}" if path else k
                        if k.lower() in [ck.lower() for ck in code_keys]:
                            found.append((current_path, v))
                        if isinstance(v, (dict, list)):
                            found.extend(search_codes(v, current_path))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        found.extend(search_codes(item, f"{path}[{i}]"))
                return found
            
            found_codes = search_codes(record_list)
            if found_codes:
                print(f"找到 {len(found_codes)} 个可能的兑换码字段:")
                for path, value in found_codes:
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"  {path} = {value_str}")
            else:
                print("未找到任何兑换码字段")
                print("\n所有字段名:")
                def get_all_keys(obj, prefix=""):
                    keys = []
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            keys.append(f"{prefix}{k}")
                            if isinstance(v, (dict, list)):
                                keys.extend(get_all_keys(v, f"{prefix}{k}."))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj[:3]):
                            keys.extend(get_all_keys(item, f"{prefix}[{i}]."))
                    return keys
                
                all_keys = get_all_keys(record_list[0])
                for k in all_keys:
                    print(f"  {k}")
    else:
        print("list为None或空")
        print("\n完整data:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
else:
    print("data为None")
    print("\n完整响应:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
