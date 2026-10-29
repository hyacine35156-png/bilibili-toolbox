# -*- coding: utf-8 -*-
import json

new_bili_jct = "cc9ab732533b83d8b78492c51d4e7568"
new_sessdata = "312157d7%2C1806767546%2C66dbf%2Aa1CjCXERm92xEKfpSDhv0ym1thAZwhcL-ldrk8WN_6Lf7QRqwnV259Pidf4fQAXwASisMSVjhkN0JEWUFGeXpBa1VKS0dvMmdVa0s3TERqbWtWVGtZZWhRQ0tKZC1LZ2Myejd3cUZBY3UwQmZFRFV1bDBRTmJxVDFKTG5va2dEdURycVB3RkFKVEVRIIEC"

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

for acc in accounts:
    if "灵砂" in acc.get("name", ""):
        acc["bili_jct"] = new_bili_jct
        acc["sessdata"] = new_sessdata
        if "BILI_JCT" in acc:
            acc["BILI_JCT"] = new_bili_jct
        if "SESSDATA" in acc:
            acc["SESSDATA"] = new_sessdata
        print(f"✓ 已更新: {acc['name']}")
        break

with open("dist/data/accounts.json", "w", encoding="utf-8") as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)
print("✓ 已保存")
