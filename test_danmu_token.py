# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json
import requests
from main_gui_pro import HEADERS

# 读取账户
with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = accounts[4]  # 灵砂是无敌的
room_id = "1791983148"

# 测试获取弹幕token
cookie = "; ".join([f"{k}={v}" for k, v in {
    "SESSDATA": account.get("sessdata", ""),
    "bili_jct": account.get("bili_jct", ""),
    "DedeUserID": account.get("dede_userid", ""),
}.items() if v])

headers = {**HEADERS, "Cookie": cookie}
try:
    resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}",
                       headers=headers, timeout=10)
    data = resp.json()
    print(f"API返回code: {data.get('code')}")
    print(f"API返回message: {data.get('message')}")
    if data.get("code") == 0:
        token = data["data"].get("token", "")
        host = data["data"].get("host", "")
        print(f"token: {token[:30]}..." if len(token) > 30 else f"token: {token}")
        print(f"host: {host}")
        print(f"token长度: {len(token)}")
    else:
        print(f"完整返回: {json.dumps(data, ensure_ascii=False)[:500]}")
except Exception as e:
    print(f"异常: {e}")
