# -*- coding: utf-8 -*-
import json
from urllib.parse import unquote

# 新的cookies
new_bili_jct = "f0c51ff8eec840f4037dad6703a9c3a4"
new_sessdata_encoded = "4a96ca71%2C1806517008%2C91eb8%2Aa1CjBUCv03MzJ1u9M-IIDgsTaIJyeHBl3TYPP2ZVroMZ1grA_WyKomN0qtF00p0A37ZhISVmdYY3NjYjVIRlRRRU90UmJOLXdLdmJzLTdYOHpGMThObmd6b2tTaWdVN21fX0Z5U3d5YlZxdlFfc2lFUks2NFpRRXpjRFlucElzS1JIRGtnb0t1NGNnIIEC"
new_sessdata = unquote(new_sessdata_encoded)

print(f"新bili_jct: {new_bili_jct} (长度{len(new_bili_jct)})")
print(f"新SESSDATA: {new_sessdata[:40]}... (长度{len(new_sessdata)})")

# 读取accounts.json
with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 找到t0级长夜月lover账户
updated = False
for acc in accounts:
    if "t0" in acc.get("name", "") and "长夜月" in acc.get("name", ""):
        old_bili = acc.get("bili_jct", "")
        old_sess = acc.get("sessdata", "")
        acc["bili_jct"] = new_bili_jct
        acc["sessdata"] = new_sessdata
        # 同时更新大写键（如果存在）
        if "BILI_JCT" in acc:
            acc["BILI_JCT"] = new_bili_jct
        if "SESSDATA" in acc:
            acc["SESSDATA"] = new_sessdata
        print(f"\n✓ 已更新账户: {acc['name']}")
        print(f"  bili_jct: {old_bili[:16]}... -> {new_bili_jct[:16]}...")
        print(f"  SESSDATA: {old_sess[:20]}... -> {new_sessdata[:20]}...")
        updated = True
        break

if not updated:
    print("✗ 未找到t0级长夜月lover账户")
else:
    # 保存
    with open("dist/data/accounts.json", "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)
    print("\n✓ accounts.json已保存")
