# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json, requests
from main_gui_pro import HEADERS, cookies_from_account

new_bili = "740aeb860d40c482eb8dd0b10b49c652"
new_sess = "845daa89%2C1806768676%2Caac3b%2Aa1CjDwpHsD4TWP6Swoh-_pBeLVA_Du3ZddvKCDt_DcU_YNEgKE-egNmcJ-6Aetn8NG3vISVmwtaWlrTmU1U0pEa1BwcEZUVjU2S0lrWTRDbnBwYTRPdUVsMzdkM0ZJSjV5V3BHcG9tNkVSWU9SbEJEX1VYVGNVc19YMkJPSk83aWhKM21TSzZQcnRBIIEC"

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

for acc in accounts:
    if "灵砂" in acc.get("name", ""):
        acc["bili_jct"] = new_bili
        acc["sessdata"] = new_sess
        if "BILI_JCT" in acc:
            acc["BILI_JCT"] = new_bili
        if "SESSDATA" in acc:
            acc["SESSDATA"] = new_sess
        print(f"✓ 已更新: {acc['name']}")
        break

with open("dist/data/accounts.json", "w", encoding="utf-8") as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)

# 验证
account = next(a for a in accounts if "灵砂" in a.get("name", ""))
cookies = cookies_from_account(account)
resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=HEADERS, cookies=cookies, timeout=10)
data = resp.json()
if data.get("code") == 0:
    print(f"✓ 登录有效: {data['data']['uname']} (UID: {data['data']['mid']})")
else:
    print(f"✗ 登录失效: {data.get('message')}")
