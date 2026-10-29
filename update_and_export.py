# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json, requests
from main_gui_pro import HEADERS, cookies_from_account

new_bili = "cf7b4db1923af3a8b618ce1270a6c549"
new_sess = "9ed49f2e%2C1807101793%2Cf59d0%2Aa1CjCnIp35CSS-Rb_30QamRdW6RRjKETOzyTkjbVX1woTQD80JtvY5wAIYef0eL8efu-oSVlNnSDBsZ204STJiZ3JzR29maTBLSEtCVDlKcEprZVdFcDktTEtZYXE0cmZRYjVaTVIzbU1vM0dCbV8zeS10REpqREo3R1JZeHZqWlByUGFLNEVOa3JRIIEC"

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 更新t0级长夜月lover
for acc in accounts:
    if "长夜月lover" in acc.get("name", "") and "t0" in acc.get("name", ""):
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

# 输出所有账号的jct和sessdata
print("\n" + "="*60)
print("所有账号的 bili_jct 和 SESSDATA：")
print("="*60)
for i, acc in enumerate(accounts, 1):
    name = acc.get("name", "未知")
    jct = acc.get("bili_jct", acc.get("BILI_JCT", ""))
    sess = acc.get("sessdata", acc.get("SESSDATA", ""))
    print(f"\n【{i}】{name}")
    print(f"bili_jct: {jct}")
    print(f"SESSDATA: {sess}")
