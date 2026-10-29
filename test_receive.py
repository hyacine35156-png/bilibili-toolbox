#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试领取请求，看返回的是风控码还是业务错误码"""

import json
import time
import hashlib
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from functools import reduce

# 账户信息（灵砂是无敌的）
SESSDATA = "bbd7dca1%2C1804772776%2C95496%2A91CjA4ujQzWj3qCKEa2BgeU3MMCWaKJxraxqBfoMYNS3SIdzniwCH98TlOKK-yBzHr_04SVjE3bEoyckJwdTZVdElEQzJaZ1dVT3h2d2JEWFBWNE1ial92NjB0aGRQak1YczhXbk5aN2RBeVpsTTE0VkJ2SmpUZVZ3eXROb2RlQWd1N2RVdEZfZ2JBIIEC"
BILI_JCT = "beb3132b0c975c9ec5aea3222d4f9338"

mixinKeyEncTab = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

def get_mixin_key(orig):
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def enc_wbi(params, img_key, sub_key):
    mixin_key = get_mixin_key(img_key + sub_key)
    params['wts'] = round(time.time())
    params = dict(sorted(params.items()))
    params = {k: ''.join(filter(lambda c: c not in "!'()*", str(v))) for k, v in params.items()}
    query = urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = wbi_sign
    return params

def http_get(url, params=None, cookies=None):
    if params:
        url = url + '?' + urlencode(params)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com/',
    }
    if cookies:
        headers['Cookie'] = cookies
    req = Request(url, headers=headers)
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_post(url, data=None, cookies=None):
    if data:
        data = urlencode(data).encode('utf-8')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    if cookies:
        headers['Cookie'] = cookies
    req = Request(url, data=data, headers=headers, method='POST')
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_wbi_keys():
    cookies = f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}'
    data = http_get('https://api.bilibili.com/x/web-interface/nav', cookies=cookies)
    img_url = data['data']['wbi_img']['img_url']
    sub_url = data['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

# 测试任务：累计1天投稿（已领取过）
act_id = "1ERAzwloghvb5600"
task_id = "6ERAcwloghvyud00"
task_name = "累计1天投稿"

print("=" * 60)
print(f"测试任务: {task_name}")
print(f"act_id: {act_id}")
print(f"task_id: {task_id}")
print("=" * 60)

# 先查询任务状态
print("\n[1] 查询任务状态...")
cookies = f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}'
try:
    img_key, sub_key = get_wbi_keys()
    params = enc_wbi({'act_id': act_id, 'task_id': task_id}, img_key, sub_key)
    data = http_get('https://api.bilibili.com/x/activity_components/mission/info', params=params, cookies=cookies)
    print(f"  返回码: {data.get('code')}")
    print(f"  消息: {data.get('message')}")
    if data.get('code') == 0:
        d = data.get('data', {})
        print(f"  状态: {d.get('status')}")
        print(f"  任务完成: {d.get('task_finished')}")
        print(f"  消息: {d.get('message')}")
except Exception as e:
    print(f"  查询异常: {e}")

# 等待2秒
print("\n等待2秒...")
time.sleep(2)

# 发送领取请求
print("\n[2] 发送领取请求...")
start_time = time.time()
try:
    receive_data = {
        'task_id': task_id,
        'activity_id': act_id,
        'ActivityId': act_id,
        'act_id': act_id,
        'activity_name': '崩坏星穹铁道4.5版本激励计划',
        'ActivityName': '崩坏星穹铁道4.5版本激励计划',
        'act_name': '崩坏星穹铁道4.5版本激励计划',
        'task_name': '累计1天投稿-下半',
        'TaskName': '累计1天投稿-下半',
        'reward_name': '星琼*50-上半任务1',
        'RewardName': '星琼*50-上半任务1',
        'gaia_vtoken': '',
        'receive_from': 'missionPage',
        'csrf': BILI_JCT,
    }
    result = http_post('https://api.bilibili.com/x/activity_components/mission/receive', data=receive_data, cookies=cookies)
    end_time = time.time()
    elapsed = (end_time - start_time) * 1000
    print(f"  返回时间: {elapsed:.0f}ms")
    print(f"  返回码: {result.get('code')}")
    print(f"  消息: {result.get('message')}")
    print(f"  完整返回: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
    
    # 判断错误类型
    code = result.get('code')
    if code in [-702, -705, -509, -412]:
        print(f"\n  ❌ 这是风控错误码 ({code})")
    elif code == 0:
        print(f"\n  ✅ 领取成功！")
    elif code in [202100, 202118, 202032]:
        print(f"\n  📦 这是业务错误码 ({code})，不是风控")
    else:
        print(f"\n  ❓ 未知错误码 ({code})")
except Exception as e:
    end_time = time.time()
    elapsed = (end_time - start_time) * 1000
    print(f"  返回时间: {elapsed:.0f}ms")
    print(f"  请求异常: {e}")

print("\n" + "=" * 60)
