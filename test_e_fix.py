import requests, json, time, uuid

with open(r'dist\accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)
acc = accounts[0]
cookie = 'SESSDATA=' + acc.get('SESSDATA','') + '; bili_jct=' + acc.get('bili_jct','') + '; DedeUserID=' + acc.get('DedeUserID','')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Cookie': cookie}
resp = requests.get('https://api.bilibili.com/x/frontend/finger/spi', headers=headers, timeout=10)
buvid = resp.json()['data']['b_3']
uuid_str = str(uuid.uuid4())

room_id = 1791983148
bili_jct = acc.get('bili_jct', '')
ts = int(time.time() * 1000)
form = {
    'id': json.dumps([3, 874, 0, room_id], separators=(',', ':')),
    'device': json.dumps([buvid, uuid_str], separators=(',', ':')),
    'ts': ts, 'is_patch': 0, 'heart_beat': '[]',
    'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'csrf_token': bili_jct, 'csrf': bili_jct, 'visit_id': '', 'ruid': 3690972101740709,
}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Content-Type': 'application/x-www-form-urlencoded', 'Cookie': cookie, 'Origin': 'https://live.bilibili.com', 'Referer': 'https://live.bilibili.com/1791983148'}
resp = requests.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E', data=form, headers=headers, timeout=15)
result = resp.json()
print('code:', result.get('code'))
print('message:', result.get('message'))
if result.get('code') == 0:
    print('data:', json.dumps(result.get('data'), ensure_ascii=False))
    print('E接口成功！room_id用int修复有效')
else:
    print('仍然失败')
