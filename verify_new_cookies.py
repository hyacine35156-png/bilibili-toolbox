import json
import requests

accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json"

with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"}

for acc in accounts:
    if acc["name"] in ["灵砂是无敌的", "苏霍伊"]:
        cookie = f"SESSDATA={acc['SESSDATA']}; bili_jct={acc['bili_jct']}"
        resp = requests.get("https://api.bilibili.com/x/web-interface/nav",
                            headers={**headers, "Cookie": cookie}, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            user = data.get("data", {})
            print(f"✓ {acc['name']}: 有效, UID={user.get('mid')}, 用户名={user.get('uname')}, 等级=Lv{user.get('level_info',{}).get('current_level')}")
            acc["DedeUserID"] = str(user.get("mid"))
            acc["username"] = user.get("uname")
        else:
            print(f"❌ {acc['name']}: 失效, code={data.get('code')}, message={data.get('message')}")

with open(accounts_file, "w", encoding="utf-8") as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)

print("\n✓ 验证完成，已更新UID和用户名")
