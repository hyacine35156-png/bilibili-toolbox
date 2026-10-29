import json, requests, time

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}
headers = {'User-Agent':'Mozilla/5.0'}

# 1. 找热门直播间
print("=== 1. 找热门直播间 ===")
url = 'https://api.live.bilibili.com/xlive/web-interface/v1/second/getList?platform=web&parent_area_id=0&area_id=0&page=1'
r = requests.get(url, headers=headers, timeout=10)
d = r.json()
if d.get('code') == 0:
    room_list = d.get('data',{}).get('list',[])
    print(f'找到 {len(room_list)} 个热门直播间')
    for i, room in enumerate(room_list[:5]):
        print(f"  {i+1}. room_id={room.get('roomid')}, title={room.get('title')[:20]}, uname={room.get('uname')}")
    
    # 用第一个热门直播间测试
    test_room = room_list[0]
    test_room_id = test_room.get('roomid')
    test_ruid = test_room.get('uid')
    test_title = test_room.get('title')[:20]
    print(f"\n测试直播间: room_id={test_room_id}, title={test_title}, ruid={test_ruid}")
    
    # 2. bag_send测试小花花(不扣电池)
    print("\n=== 2. bag_send测试小花花 id=33664 ===")
    url = 'https://api.live.bilibili.com/gift/v2/live/bag_send'
    headers2 = {'User-Agent':'Mozilla/5.0','Referer':f'https://live.bilibili.com/{test_room_id}','Origin':'https://live.bilibili.com'}
    data = {'uid':uid,'gift_id':33664,'ruid':test_ruid,'gift_num':1,'bag_id':0,'platform':'pc','biz_code':'live','biz_id':test_room_id,'rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'0','csrf_token':bili_jct,'csrf':bili_jct}
    r = requests.post(url,data=data,cookies=cookies,headers=headers2,timeout=10)
    d = r.json()
    print('code:', d.get('code'), 'msg:', d.get('msg') or d.get('message'))
    
    # 3. 再测原直播间
    print("\n=== 3. 原直播间1791983148 bag_send测试小花花 ===")
    data['ruid'] = '3690972101740709'
    data['biz_id'] = '1791983148'
    headers2['Referer'] = 'https://live.bilibili.com/1791983148'
    r = requests.post(url,data=data,cookies=cookies,headers=headers2,timeout=10)
    d = r.json()
    print('code:', d.get('code'), 'msg:', d.get('msg') or d.get('message'))
