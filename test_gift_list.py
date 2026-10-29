#!/usr/bin/env python3
"""查询1电池(price=100)的常驻礼物"""

import json
import requests

with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = accounts[5]
sessdata = account.get("SESSDATA", "")
bili_jct = account.get("bili_jct", "")
cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig?platform=pc"
resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
data = resp.json()

if data.get("code") == 0:
    gift_list = data.get("data", {}).get("list", [])
    print(f"总礼物数: {len(gift_list)}")
    print("\n=== price=100 (1电池) 的礼物 ===")
    count = 0
    for gift in gift_list:
        price = gift.get("price", 0)
        coin_type = gift.get("coin_type", "")
        name = gift.get("name", "")
        gift_id = gift.get("id", "")
        # price=100 且 金瓜子(电池) 且 不是活动限定(corner_mark为空)
        if price == 100 and coin_type == "gold":
            corner = gift.get("corner_mark", "")
            print(f"  id={gift_id}, name={name}, price={price}, coin_type={coin_type}, corner={corner}")
            count += 1
    print(f"\n共 {count} 个1电池礼物")
