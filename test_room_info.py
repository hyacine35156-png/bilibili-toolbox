import json, requests

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)
acc = accounts[5]
sessdata = acc.get('SESSDATA','')
cookies = {'SESSDATA':sessdata}
headers = {'User-Agent':'Mozilla/5.0'}

room_id = '1791983148'

# 方法1: room/v1/Room/get_info
print("=== 方法1: room/v1/Room/get_info ===")
url1 = f'https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}'
r1 = requests.get(url1, cookies=cookies, headers=headers, timeout=10)
d1 = r1.json()
print('code:', d1.get('code'))
if d1.get('code') == 0:
    data = d1.get('data', {})
    print('uid(主播):', data.get('uid'))
    print('room_id:', data.get('room_id'))
    print('title:', data.get('title'))

# 方法2: xlivedata/v1/DataSource/getData
print("\n=== 方法2: xlivedata/v1/DataSource/getData ===")
url2 = f'https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}'
r2 = requests.get(url2, cookies=cookies, headers=headers, timeout=10)
d2 = r2.json()
print('code:', d2.get('code'))
if d2.get('code') == 0:
    room_info = d2.get('data', {}).get('room_info', {})
    print('uid(主播):', room_info.get('uid'))
    print('room_id:', room_info.get('room_id'))

# 方法3: 直接用直播间网页获取
print("\n=== 方法3: live.bilibili.com/room/v1/Room/room_init ===")
url3 = f'https://api.live.bilibili.com/room/v1/Room/room_init?id={room_id}'
r3 = requests.get(url3, cookies=cookies, headers=headers, timeout=10)
d3 = r3.json()
print('code:', d3.get('code'))
if d3.get('code') == 0:
    data = d3.get('data', {})
    print('uid(主播):', data.get('uid'))
    print('room_id:', data.get('room_id'))
    print('short_id:', data.get('short_id'))
