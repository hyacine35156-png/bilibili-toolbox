import json

accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json"

with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 灵砂是无敌的 新cookie
lingsha_sessdata = "719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC"
lingsha_bili_jct = "499f38b6a5bdf6dc1b48ea9333bca67d"

# 苏霍伊 新cookie
sukhoi_sessdata = "379099f5%2C1803972548%2Ce3d26%2A92CjAx0FYIw7PcHTyzPAp-Vc8I1mmh3OaeuEJOJ_mUyjAW5V3GJLss91Tmsa4T7EGIdBYSVmNBcWFjdTg0ekhvQ29kRXNwMThvU0FOSV82b1Vqa1VDOXBjQ2VXOXpjVzFrdmVSNjd6UVllaF9WeFUyRExXSTBqNFFScHlnMzI3clNyTGV5c0drQXFnIIEC"
sukhoi_bili_jct = "3675fd5271db0e3e0105c0c39ede06d4"

for acc in accounts:
    if acc["name"] == "灵砂是无敌的":
        acc["SESSDATA"] = lingsha_sessdata
        acc["bili_jct"] = lingsha_bili_jct
        acc["DedeUserID"] = ""
        print("✓ 已更新 灵砂是无敌的 cookie")
    elif acc["name"] == "苏霍伊":
        acc["SESSDATA"] = sukhoi_sessdata
        acc["bili_jct"] = sukhoi_bili_jct
        acc["DedeUserID"] = ""
        print("✓ 已更新 苏霍伊 cookie")

with open(accounts_file, "w", encoding="utf-8") as f:
    json.dump(accounts, f, ensure_ascii=False, indent=2)

print("\n✓ accounts.json已保存")
