#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, time, hashlib
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from functools import reduce

SESSDATA = "bbd7dca1%2C1804772776%2C95496%2A91CjA4ujQzWj3qCKEa2BgeU3MMCWaKJxraxqBfoMYNS3SIdzniwCH98TlOKK-yBzHr_04SVjE3bEoyckJwdTZVdElEQzJaZ1dVT3h2d2JEWFBWNE1ial92NjB0aGRQak1YczhXbk5aN2RBeVpsTTE0VkJ2SmpUZVZ3eXROb2RlQWd1N2RVdEZfZ2JBIIEC"
BILI_JCT = "beb3132b0c975c9ec5aea3222d4f9338"

mixinKeyEncTab = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
def get_mixin_key(orig): return reduce(lambda s,i: s+orig[i], mixinKeyEncTab, '')[:32]
def enc_wbi(params, img_key, sub_key):
    mixin_key = get_mixin_key(img_key+sub_key)
    params['wts'] = round(time.time())
    params = dict(sorted(params.items()))
    params = {k: ''.join(filter(lambda c: c not in "!'()*", str(v))) for k,v in params.items()}
    query = urlencode(params)
    params['w_rid'] = hashlib.md5((query+mixin_key).encode()).hexdigest()
    return params
def http_get(url, params=None, cookies=None):
    if params: url = url+'?'+urlencode(params)
    headers = {'User-Agent':'Mozilla/5.0','Referer':'https://www.bilibili.com/'}
    if cookies: headers['Cookie']=cookies
    req = Request(url, headers=headers)
    with urlopen(req, timeout=10) as resp: return json.loads(resp.read().decode('utf-8'))
def get_wbi_keys():
    cookies = f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}'
    data = http_get('https://api.bilibili.com/x/web-interface/nav', cookies=cookies)
    img_url = data['data']['wbi_img']['img_url']
    sub_url = data['data']['wbi_img']['sub_url']
    return img_url.rsplit('/',1)[1].split('.')[0], sub_url.rsplit('/',1)[1].split('.')[0]

def query(act_id, task_id):
    cookies = f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}'
    try:
        img_key, sub_key = get_wbi_keys()
        params = enc_wbi({'act_id':act_id,'task_id':task_id}, img_key, sub_key)
        data = http_get('https://api.bilibili.com/x/activity_components/mission/info', params=params, cookies=cookies)
        if data.get('code')!=0: return f'API错误: {data.get("code")} {data.get("message")}'
        d = data.get('data',{})
        status = d.get('status',-1)
        finished = d.get('task_finished',False)
        msg = d.get('message','')
        status_map = {0:'可领取',1:'可领取',2:'已领取/每日上限',6:'已领取过',7:'无资格',11:'未到时间'}
        st = status_map.get(status, str(status))
        fin = '是' if finished else '否'
        return f'状态:{st} | 完成:{fin} | {msg}'
    except Exception as e:
        return f'异常:{e}'

tasks = [
    ('1ERAzwloghvn7l00','6ERAcwloghvigh00','累计3天投稿≥1000播放≥10币(180星声)'),
    ('1ERAzwloghvn7l00','6ERAcwloghvu0800','累计2天投稿≥300播放≥3币(120星声)'),
    ('1ERAzwloghvn7l00','6ERAcwloghvy7300','累计1天投稿≥100播放(60星声)'),
]
for act, tid, name in tasks:
    print(f'{name}: {query(act,tid)}')
    time.sleep(3)
