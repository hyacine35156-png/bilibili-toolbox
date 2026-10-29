import json, requests, time

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}

# 测试几个不同的直播间
test_rooms = [
    ('1791983148', '3690972101740709', '灵砂是无敌的(原直播间)'),
    ('21452545', '21452545', '测试房间1'),
    ('1', '1', '测试房间2(room_id=1)'),
]

for room_id, ruid, desc in test_rooms:
    print(f"\n=== 测试: {desc} (room_id={room_id}, ruid={ruid}) ===")
    url = 'https://api.live.bilibili.com/gift/v2/live/bag_send'
    headers = {'User-Agent':'Mozilla/5.0','Referer':f'https://live.bilibili.com/{room_id}','Origin':'https://live.bilibili.com'}
    data = {'uid':uid,'gift_id':33664,'ruid':ruid,'gift_num':1,'bag_id':0,'platform':'pc','biz_code':'live','biz_id':room_id,'rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'0','csrf_token':bili_jct,'csrf':bili_jct}
    try:
        r = requests.post(url,data=data,cookies=cookies,headers=headers,timeout=10)
        d = r.json()
        print('code:', d.get('code'), 'msg:', d.get('msg') or d.get('message'))
    except Exception as e:
        print('异常:', e)
        print('status:', r.status_code, 'text:', r.text[:200])
    time.sleep(1)
