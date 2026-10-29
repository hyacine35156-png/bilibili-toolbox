import json, requests, time

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[5]  # 苏霍伊，电池0
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}
headers = {'User-Agent':'Mozilla/5.0','Referer':'https://live.bilibili.com/1791983148','Origin':'https://live.bilibili.com'}
room_id = '1791983148'
ruid = '3690972101740709'

# 测试可直接用电池送的礼物
test_gifts = [
    (31039, '牛哇牛哇(bag_gift=0)'),
    (31036, '小花花(bag_gift=0)'),
    (30758, '这个好诶(bag_gift=0)'),
    (30244, '晃悠悠(bag_gift=0)'),
]

url = 'https://api.live.bilibili.com/gift/v2/live/send'
for gift_id, gift_name in test_gifts:
    data = {'uid':uid,'gift_id':gift_id,'ruid':ruid,'gift_num':1,'platform':'pc','biz_code':'live','biz_id':room_id,'rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'100','coin_type':'gold','csrf_token':bili_jct,'csrf':bili_jct}
    try:
        r = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=10)
        d = r.json()
        print(f"{gift_name}(id={gift_id}): code={d.get('code')}, msg={d.get('msg') or d.get('message')}")
    except Exception as e:
        print(f"{gift_name}(id={gift_id}): 异常 {e}")
    time.sleep(1)
