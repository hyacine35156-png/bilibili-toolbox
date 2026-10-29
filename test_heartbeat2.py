import requests, json, time

with open('dist/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
cookie = f"SESSDATA={acc.get('SESSDATA','')}; bili_jct={acc.get('bili_jct','')}; DedeUserID={acc.get('DedeUserID','')}"
bili_jct = acc.get('bili_jct', '')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://live.bilibili.com/1791983148',
    'Origin': 'https://live.bilibili.com',
    'Cookie': cookie,
    'Content-Type': 'application/x-www-form-urlencoded'
}

parent_area_id = 3
area_id = 874
room_id = 1791983148

# 1. 请求E接口
ts = int(time.time() * 1000)
e_data = {
    'id': f'[{parent_area_id},{area_id},0,{room_id}]',
    'device': '["AUTO000000000000000","00000000-0000-0000-0000-000000000000"]',
    'is_patch': 0,
    'heart_beat': '[]',
    'csrf_token': bili_jct,
    'csrf': bili_jct,
    'visit_id': '',
    'ts': ts
}
e_resp = requests.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E', headers=headers, data=e_data, timeout=10)
e_result = e_resp.json()
print('E响应:', json.dumps(e_result, indent=2, ensure_ascii=False))

ets = e_result['data']['timestamp']
heartbeat_interval = e_result['data']['heartbeat_interval']
secret_key = e_result['data']['secret_key']

# 2. 测试X接口（不带s参数）
time.sleep(2)
ts2 = int(time.time() * 1000)
x_data = {
    'id': f'[{parent_area_id},{area_id},1,{room_id}]',
    'device': '["AUTO000000000000000","00000000-0000-0000-0000-000000000000"]',
    'ets': ets,
    'benchmark': secret_key,
    'time': heartbeat_interval,
    'ts': ts2,
    'ua': headers['User-Agent'],
    'csrf_token': bili_jct,
    'csrf': bili_jct,
    'visit_id': ''
}
print('\nX请求参数（不带s）:', json.dumps(x_data, indent=2, ensure_ascii=False))

x_resp = requests.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/X', headers=headers, data=x_data, timeout=10)
print('X响应状态码:', x_resp.status_code)
print('X响应:', json.dumps(x_resp.json(), indent=2, ensure_ascii=False))
