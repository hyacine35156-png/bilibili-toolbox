import requests, json, time, uuid, hashlib
from bili_spyder import calc_sign

with open('dist/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
cookie = f"SESSDATA={acc.get('SESSDATA','')}; bili_jct={acc.get('bili_jct','')}; DedeUserID={acc.get('DedeUserID','')}"
bili_jct = acc.get('bili_jct', '')

ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
headers = {
    'User-Agent': ua,
    'Referer': 'https://live.bilibili.com/1791983148',
    'Origin': 'https://live.bilibili.com',
    'Cookie': cookie,
    'Content-Type': 'application/x-www-form-urlencoded'
}

parent_area_id = 3
area_id = 874
room_id = 1791983148

# 生成device
device_id = 'AUTO' + hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16]
device_uuid = str(uuid.uuid4())
device = f'["{device_id}","{device_uuid}"]'

# 1. 请求E接口
ts = int(time.time() * 1000)
e_data = {
    'id': f'[{parent_area_id},{area_id},0,{room_id}]',
    'device': device,
    'is_patch': 0,
    'heart_beat': '[]',
    'csrf_token': bili_jct,
    'csrf': bili_jct,
    'visit_id': '',
    'ts': ts
}
e_resp = requests.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E', headers=headers, data=e_data, timeout=10)
e_result = e_resp.json()
print('E响应code:', e_result.get('code'))
print('E响应data:', json.dumps(e_result.get('data', {}), indent=2))

ets = e_result['data']['timestamp']
heartbeat_interval = e_result['data']['heartbeat_interval']
secret_key = e_result['data']['secret_key']
secret_rule = e_result['data']['secret_rule']

# 2. 计算s签名并请求X接口
time.sleep(2)
ts2 = int(time.time() * 1000)
sign_data = {
    'id': f'[{parent_area_id},{area_id},1,{room_id}]',
    'device': device,
    'ets': ets,
    'benchmark': secret_key,
    'time': heartbeat_interval,
    'ts': ts2,
}
print('\n签名输入data:', json.dumps(sign_data, indent=2))
print('secret_rule:', secret_rule)

s = calc_sign(sign_data, secret_rule)
print('计算得到s:', s)

# 3. 请求X接口
x_data = {
    's': s,
    'id': f'[{parent_area_id},{area_id},1,{room_id}]',
    'device': device,
    'ets': ets,
    'benchmark': secret_key,
    'time': heartbeat_interval,
    'ts': ts2,
    'ua': ua,
    'csrf_token': bili_jct,
    'csrf': bili_jct,
    'visit_id': ''
}
x_resp = requests.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/X', headers=headers, data=x_data, timeout=10)
x_result = x_resp.json()
print('\nX响应状态码:', x_resp.status_code)
print('X响应:', json.dumps(x_result, indent=2, ensure_ascii=False))
