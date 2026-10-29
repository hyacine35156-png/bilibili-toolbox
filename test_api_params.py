import json, requests, time

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[5]
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}
headers = {'User-Agent':'Mozilla/5.0','Referer':'https://live.bilibili.com/1791983148','Origin':'https://live.bilibili.com'}
room_id = '1791983148'
ruid = '3690972101740709'

# 测试不同参数组合
tests = [
    ('1. 不传price', {'price': None}),
    ('2. price=100(数字)', {'price': 100}),
    ('3. price=100(字符串)', {'price': '100'}),
    ('4. 加coin_type=gold', {'coin_type': 'gold', 'price': '100'}),
    ('5. 加total_coin=100', {'total_coin': '100', 'price': '100'}),
    ('6. 加gift_num=1, rnd', {'gift_num': 1, 'rnd': int(time.time())}),
    ('7. 加actionKey, appkey', {'actionKey': 'appkey', 'appkey': '1d8b6e7d42348978'}),
]

url = 'https://api.live.bilibili.com/gift/v2/live/send'
base_data = {'uid':uid,'gift_id':33664,'ruid':ruid,'gift_num':1,'platform':'pc','biz_code':'live','biz_id':room_id,'rnd':int(time.time()),'storm_beat_id':'0','metadata':'','csrf_token':bili_jct,'csrf':bili_jct}

for desc, extra in tests:
    data = base_data.copy()
    for k, v in extra.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    try:
        r = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=10)
        d = r.json()
        print(f"{desc}: code={d.get('code')}, msg={d.get('msg') or d.get('message')}")
    except Exception as e:
        print(f"{desc}: 异常 {e}")
    time.sleep(0.5)

# 测试bag_send接口
print("\n=== bag_send接口 ===")
url2 = 'https://api.live.bilibili.com/gift/v2/live/bag_send'
data2 = {'uid':uid,'gift_id':33664,'ruid':ruid,'gift_num':1,'bag_id':0,'platform':'pc','biz_code':'live','biz_id':room_id,'rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'0','csrf_token':bili_jct,'csrf':bili_jct}
r = requests.post(url2, data=data2, cookies=cookies, headers=headers, timeout=10)
d = r.json()
print(f"bag_send: code={d.get('code')}, msg={d.get('msg') or d.get('message')}")
