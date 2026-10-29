# -*- coding: utf-8 -*-
import json

# 灵砂之前有效的cookies
lingsha_bili = "e93ddce4430e2dfd4d4baa49ae0de38f"
lingsha_sess = "914173e3%2C1806767546%2Cfcad2%2Aa1CjAvWiSxqUR_9hJbQng-u9M9Hqs1FWs96XLYdiBJeCefZSvpYJ4tOo5URTumRwoqxgUSVkpQR1FDVjBXVzVLQWRUNVRVOGZta0VZREd2NEFFZ3FmLThsOGRMRkhjQXpFQ3JYV1BYWGluMGN5TERvYVZkaEhEcERBbnMxRno4WUxPbzVQNkJIRm93IIEC"

# 新账号cookies
new_bili = "cc9ab732533b83d8b78492c51d4e7568"
new_sess = "312157d7%2C1806767546%2C66dbf%2Aa1CjCXERm92xEKfpSDhv0ym1thAZwhcL-ldrk8WN_6Lf7QRqwnV259Pidf4fQAXwASisMSVjhkN0JEWUFGeXpBa1VKS0dvMmdVa0s3TERqbWtWVGtZZWhRQ0tKZC1LZ2Myejd3cUZBY3UwQmZFRFV1bDBRTmJxVDFKTG5va2dEdURycVB3RkFKVEVRIIEC"

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 1. 恢复灵砂的cookies
for acc in accounts:
    if "灵砂" in acc.get("name", ""):
        acc["bili_jct"] = lingsha_bili
        acc["sessdata"] = lingsha_sess
        if "BILI_JCT" in acc:
            acc["BILI_JCT"] = lingsha_bili
        if "SESSDATA" in acc:
            acc["SESSDATA"] = lingsha_sess
        print(f"✓ 恢复: {acc['name']}")
        break

# 2. 检查新账号是否已存在
exists = any("知更鸟" in acc.get("name", "") for acc in accounts)
if not exists:
    # 新增账户（复制灵砂的结构）
    template = next(a for a in accounts if "灵砂" in a.get("name", ""))
    new_acc = {}
    for k, v in template.items():
        if k == "name":
            new_acc[k] = "t0级知更鸟晴歌lover"
        elif k in ["bili_jct", "BILI_JCT"]:
            new_acc[k] = new_bili
        elif k in ["sessdata", "SESSDATA"]:
            new_acc[k] = new_sess
        elif k in ["uid", "UID", "DedeUserID", "dedeuserid"]:
            new_acc[k] = "3546883148482831"
        else:
            new_acc[k] = v
    accounts.append(new_acc)
    print(f"✓ 新增账户: t0级知更鸟晴歌lover (UID: 3546883148482831)")
else:
    print("⚠ 账户已存在，跳过新增")

with open("dist/data/accounts.json", "w", encoding="utf-8") as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)

print(f"\n当前账户总数: {len(accounts)}")
for i, acc in enumerate(accounts):
    print(f"  {i+1}. {acc.get('name')}")
