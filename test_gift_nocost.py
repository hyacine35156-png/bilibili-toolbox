import json, requests, time

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)

# 查所有账户电池余额
print("=== 所有账户电池余额 ===")
headers = {'User-Agent':'Mozilla/5.0'}
for acc in accounts:
    name = acc.get('name')
    sessdata = acc.get('SESSDATA','')
    cookies = {'SESSDATA':sessdata}
    url = 'https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1'
    r = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    d = r.json()
    if d.get('code') == 0:
        gold = d.get('data',{}).get('gold',0)
        battery = gold / 100.0 if gold else 0
        print(f"  {name}: 电池={battery} (gold={gold})")
    else:
        print(f"  {name}: 查询失败 code={d.get('code')}")
    time.sleep(0.5)

# 用苏霍伊(电池0)测试常驻礼物小花花，不会扣电池
print("\n=== 苏霍伊(电池0)测试小花花 id=33664 ===")
acc = accounts[5]
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}
headers = {'User-Agent':'Mozilla/5.0','Referer':'https://live.bilibili.com/1791983148','Origin':'https://live.bilibili.com'}

for gid, gname in [(33664,'小花花'), (33415,'吃瓜'), (30758,'这个好诶')]:
    url = 'https://api.live.bilibili.com/gift/v2/live/send'
    data = {'uid':uid,'gift_id':gid,'ruid':'3690972101740709','gift_num':1,'platform':'pc','biz_code':'live','biz_id':'1791983148','rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'100','csrf_token':bili_jct,'csrf':bili_jct}
    r = requests.post(url,data=data,cookies=cookies,headers=headers,timeout=10)
    d = r.json()
    code = d.get('code')
    msg = d.get('msg') or d.get('message')
    print(f"  {gname}(id={gid}): code={code}, msg={msg}")
    time.sleep(1)
