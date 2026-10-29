import json, requests, time

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)

# 用t0级长夜月lover(40电池)测试
acc = accounts[0]
name = acc.get('name')
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
print(f"测试账户: {name}, uid={uid}")

cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}
headers = {'User-Agent':'Mozilla/5.0','Referer':'https://live.bilibili.com/1791983148','Origin':'https://live.bilibili.com'}
room_id = '1791983148'
ruid = '3690972101740709'

# 1. 先查背包
print("\n=== 1. 查背包 ===")
url = 'https://api.live.bilibili.com/xlive/web-room/v1/gift/bag_list'
r = requests.get(url, cookies=cookies, headers=headers, timeout=10)
d = r.json()
print('code:', d.get('code'))
if d.get('code') == 0:
    bag_list = d.get('data',{}).get('list',[])
    print('背包礼物数量:', len(bag_list))
    for item in bag_list:
        print(f"  {item.get('gift_name')} id={item.get('gift_id')} 数量={item.get('gift_num')}")

# 2. bag_send测试小花花(背包没有的话不会扣电池)
print("\n=== 2. bag_send测试小花花 id=33664 ===")
url = 'https://api.live.bilibili.com/gift/v2/live/bag_send'
data = {'uid':uid,'gift_id':33664,'ruid':ruid,'gift_num':1,'bag_id':0,'platform':'pc','biz_code':'live','biz_id':room_id,'rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'0','csrf_token':bili_jct,'csrf':bili_jct}
r = requests.post(url,data=data,cookies=cookies,headers=headers,timeout=10)
d = r.json()
print('code:', d.get('code'), 'msg:', d.get('msg') or d.get('message'))

# 3. bag_send测试牛哇牛哇 id=31225
print("\n=== 3. bag_send测试牛哇牛哇 id=31225 ===")
data['gift_id'] = 31225
r = requests.post(url,data=data,cookies=cookies,headers=headers,timeout=10)
d = r.json()
print('code:', d.get('code'), 'msg:', d.get('msg') or d.get('message'))
