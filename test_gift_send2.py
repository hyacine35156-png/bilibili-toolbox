import json, requests, time
with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)
acc = accounts[5]
sessdata = acc.get('SESSDATA','')
bili_jct = acc.get('bili_jct','')
uid = acc.get('DedeUserID','')
cookies = {'SESSDATA':sessdata,'bili_jct':bili_jct}
headers = {'User-Agent':'Mozilla/5.0','Referer':'https://live.bilibili.com/1791983148','Origin':'https://live.bilibili.com'}
for gid in [33664, 33415, 30758, 33414, 30244]:
    url = 'https://api.live.bilibili.com/gift/v2/live/send'
    data = {'uid':uid,'gift_id':gid,'ruid':'3690972101740709','gift_num':1,'platform':'pc','biz_code':'live','biz_id':'1791983148','rnd':int(time.time()),'storm_beat_id':'0','metadata':'','price':'100','csrf_token':bili_jct,'csrf':bili_jct}
    resp = requests.post(url,data=data,cookies=cookies,headers=headers,timeout=10)
    r = resp.json()
    code = r.get('code')
    msg = r.get('msg') or r.get('message')
    print(f'gift_id={gid}: code={code}, msg={msg}')
    if code == 0:
        print(f'  成功! 停止测试')
        break
    time.sleep(1)
