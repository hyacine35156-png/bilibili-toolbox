# -*- coding: utf-8 -*-
"""更新灵砂是无敌的账户Cookie并验证"""

import json
import urllib.parse
import requests

accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json"

# 新的Cookie
new_bili_jct = "12eefcb772f39587a1042016bbc12d2e"
sessdata_encoded = "2ada7d56%2C1804350448%2C34f5a%2A91CjB0YAGbun6p2ee0jFQ75CmcVz08HemHDBnKfzkWA1w_3nEbDRKz2tNCLvgJlWHe1MESVk81clBWcUNnTXA1em9kbTd3aUxrX2JNOXhBcHkxUUFQNHBBTFh0QzJCWngzZnBXVUc2UC1yTHNVdHlUQzAwaWpGeWNSdEVkVUJfMmlPRndoLXVqN0F3IIEC"
new_sessdata = urllib.parse.unquote(sessdata_encoded)

# 读取账户文件
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 找到并更新账户
updated = False
for acc in accounts:
    if acc.get("name") == "灵砂是无敌的":
        old_sessdata = acc.get("SESSDATA", "")
        acc["SESSDATA"] = new_sessdata
        acc["bili_jct"] = new_bili_jct
        updated = True
        print(f"✓ 已更新账户: {acc['name']}")
        print(f"  旧SESSDATA前20字符: {old_sessdata[:20]}...")
        print(f"  新SESSDATA前20字符: {new_sessdata[:20]}...")
        print(f"  新bili_jct: {new_bili_jct}")
        break

if not updated:
    print("✗ 未找到账户'灵砂是无敌的'")
    exit()

# 保存文件
with open(accounts_file, "w", encoding="utf-8") as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)
print(f"\n✓ 账户文件已保存")

# 验证Cookie
print("\n验证Cookie...")
cookies = {
    "SESSDATA": new_sessdata,
    "bili_jct": new_bili_jct,
}
if accounts[0].get("DedeUserID"):
    cookies["DedeUserID"] = accounts[0]["DedeUserID"]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
try:
    resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, cookies=cookies, timeout=10)
    data = resp.json()
    print(f"  code: {data.get('code')}")
    print(f"  用户: {data.get('data', {}).get('uname', '未知')}")
    print(f"  等级: {data.get('data', {}).get('level_info', {}).get('current_level', '未知')}")
    if data.get("code") == 0:
        print("\n✓ Cookie验证成功！")
    else:
        print(f"\n✗ Cookie验证失败: {data.get('message')}")
except Exception as e:
    print(f"✗ 验证异常: {e}")
