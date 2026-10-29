#!/usr/bin/env python3
"""测试送礼API：giftConfig + bag_send"""

import json
import requests
import time

# 读取账户
with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = accounts[5]  # 苏霍伊
print("账户名:", account.get("name"))
print("账户字段:", list(account.keys()))
print("uid:", account.get("uid"))
print("DedeUserID:", account.get("DedeUserID"))

sessdata = account.get("SESSDATA", "")
bili_jct = account.get("bili_jct", "")
uid = account.get("uid", "") or account.get("DedeUserID", "")
print("使用uid:", uid)

cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 测试1: giftConfig
print("\n=== 测试1: giftConfig ===")
try:
    url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig?platform=pc"
    resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    print("status_code:", resp.status_code)
    print("content_type:", resp.headers.get("content-type"))
    print("text前500:", resp.text[:500])
    try:
        data = resp.json()
        print("code:", data.get("code"))
        if data.get("code") == 0:
            gift_list = data.get("data", {}).get("list", [])
            print("礼物数量:", len(gift_list))
            for gift in gift_list:
                name = gift.get("name", "")
                if "牛" in name or "蛙" in name or "哇" in name:
                    print(f"  找到: {name} id={gift.get('id')} price={gift.get('price')}")
    except Exception as e:
        print("JSON解析失败:", e)
except Exception as e:
    print("异常:", e)

# 测试2: 获取直播间信息
print("\n=== 测试2: 获取直播间信息 ===")
room_id = "1791983148"
try:
    url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}"
    resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    data = resp.json()
    print("code:", data.get("code"))
    if data.get("code") == 0:
        room_info = data.get("data", {}).get("room_info", {})
        print("ruid(uid):", room_info.get("uid"))
        print("room_id:", room_info.get("room_id"))
except Exception as e:
    print("异常:", e)

# 测试3: bag_send
print("\n=== 测试3: bag_send ===")
ruid = "3690972101740709"  # 灵砂是无敌的uid
gift_id = 30029
gift_num = 1
try:
    url = "https://api.live.bilibili.com/gift/v2/live/bag_send"
    data = {
        "uid": uid,
        "gift_id": gift_id,
        "ruid": ruid,
        "gift_num": gift_num,
        "bag_id": 0,
        "platform": "pc",
        "biz_code": "live",
        "biz_id": room_id,
        "rnd": int(time.time()),
        "storm_beat_id": "0",
        "metadata": "",
        "price": "0",
        "csrf_token": bili_jct,
        "csrf": bili_jct,
    }
    print("请求参数:", json.dumps(data, ensure_ascii=False))
    resp = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=10)
    print("status_code:", resp.status_code)
    print("返回:", resp.text[:500])
except Exception as e:
    print("异常:", e)
