import json, requests, time

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)
acc = accounts[5]
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}
headers = {'User-Agent':'Mozilla/5.0','Referer':'https://live.bilibili.com/1791983148','Origin':'https://live.bilibili.com'}

# 1. 查电池余额
print("=== 1. 查电池余额 ===")
url = 'https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1'
r = requests.get(url, cookies=cookies, headers=headers, timeout=10)
d = r.json()
print('code:', d.get('code'))
if d.get('code') == 0:
    wallet = d.get('data', {})
    print('gold(电池,后两位小数):', wallet.get('gold'))
    print('silver(银瓜子):', wallet.get('silver'))
    print('bp(电池):', wallet.get('bp'))

# 2. 用不存在的gift_id测试
print("\n=== 2. 不存在的gift_id=999999 ===")
url = 'https://api.live.bilibili.com/gift/v2/live/send'
data = {'uid':uid,'gift_id':999999,'ruid':'3690972101740709','gift_num':1,'platform':'pc','biz_code':'live','biz_id':'1791983148','rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'100','csrf_token':bili_jct,'csrf':bili_jct}
r = requests.post(url,data=data,cookies=cookies,headers=headers,timeout=10)
d = r.json()
print('code:', d.get('code'), 'msg:', d.get('msg') or d.get('message'))

# 3. 用bag_send测试不存在的gift_id
print("\n=== 3. bag_send 不存在的gift_id=999999 ===")
url = 'https://api.live.bilibili.com/gift/v2/live/bag_send'
data = {'uid':uid,'gift_id':999999,'ruid':'3690972101740709','gift_num':1,'bag_id':0,'platform':'pc','biz_code':'live','biz_id':'1791983148','rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'0','csrf_token':bili_jct,'csrf':bili_jct}
r = requests.post(url,data=data,cookies=cookies,headers=headers,timeout=10)
d = r.json()
print('code:', d.get('code'), 'msg:', d.get('msg') or d.get('message'))
