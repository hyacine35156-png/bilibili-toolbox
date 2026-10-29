#!/usr/bin/env python3
"""测试普通送礼接口（非背包）"""

import json
import requests
import time

# 读取账户
with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = accounts[5]  # 苏霍伊
sessdata = account.get("SESSDATA", "")
bili_jct = account.get("bili_jct", "")
uid = account.get("DedeUserID", "")
print("账户:", account.get("name"), "uid:", uid)

cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://live.bilibili.com/1791983148",
    "Origin": "https://live.bilibili.com",
}

room_id = "1791983148"
ruid = "3690972101740709"

# 测试1: 普通送礼接口 /gift/v2/live/send
print("\n=== 测试1: /gift/v2/live/send (普通送礼) ===")
for gift_id in [31225, 31039, 31214]:
    try:
        url = "https://api.live.bilibili.com/gift/v2/live/send"
        data = {
            "uid": uid,
            "gift_id": gift_id,
            "ruid": ruid,
            "gift_num": 1,
            "platform": "pc",
            "biz_code": "live",
            "biz_id": room_id,
            "rnd": int(time.time()),
            "storm_beat_id": "0",
            "metadata": "",
            "price": "100",
            "csrf_token": bili_jct,
            "csrf": bili_jct,
        }
        resp = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=10)
        result = resp.json()
        print(f"  gift_id={gift_id}: code={result.get('code')}, msg={result.get('msg') or result.get('message')}")
        if result.get("code") == 0:
            print(f"    成功! data={json.dumps(result.get('data'), ensure_ascii=False)[:200]}")
            break
    except Exception as e:
        print(f"  gift_id={gift_id}: 异常 {e}")

# 测试2: 查背包
print("\n=== 测试2: 查背包 ===")
try:
    url = "https://api.live.bilibili.com/xlive/web-room/v1/gift/bag_list"
    resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    data = resp.json()
    print("code:", data.get("code"))
    if data.get("code") == 0:
        bag_list = data.get("data", {}).get("list", [])
        print("背包礼物数量:", len(bag_list))
        for item in bag_list:
            print(f"  {item.get('gift_name')} id={item.get('gift_id')} 数量={item.get('gift_num')}")
except Exception as e:
    print("异常:", e)
