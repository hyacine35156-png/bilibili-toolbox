# -*- coding: utf-8 -*-
import json

new_bili_jct = "e93ddce4430e2dfd4d4baa49ae0de38f"
new_sessdata = "914173e3%2C1806734817%2Cfcad2%2Aa1CjAvWiSxqUR_9hJbQng-u9M9Hqs1FWs96XLYdiBJeCefZSvpYJ4tOo5URTumRwoqxgUSVkpQR1FDVjBXVzVLQWRUNVRVOGZta0VZREd2NEFFZ3FmLThsOGRMRkhjQXpFQ3JYV1BYWGluMGN5TERvYVZkaEhEcERBbnMxRno4WUxPbzVQNkJIRm93IIEC"

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

for acc in accounts:
    if "灵砂" in acc.get("name", ""):
        old_bili = acc.get("bili_jct", "")
        old_sess = acc.get("sessdata", "")
        acc["bili_jct"] = new_bili_jct
        acc["sessdata"] = new_sessdata
        if "BILI_JCT" in acc:
            acc["BILI_JCT"] = new_bili_jct
        if "SESSDATA" in acc:
            acc["SESSDATA"] = new_sessdata
        print(f"✓ 已更新: {acc['name']}")
        print(f"  bili_jct: {old_bili[:16]}... -> {new_bili_jct[:16]}...")
        print(f"  SESSDATA: {old_sess[:20]}... -> {new_sessdata[:20]}...")
        break

with open("dist/data/accounts.json", "w", encoding="utf-8") as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)
print("✓ 已保存")
