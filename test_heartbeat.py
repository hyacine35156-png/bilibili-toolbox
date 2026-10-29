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

# 获取房间信息（大分区、小分区）
room_resp = requests.get('https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id=1791983148', headers=headers, timeout=10)
room_data = room_resp.json()
print('房间信息code:', room_data.get('code'))
if room_data.get('code') == 0:
    room_info = room_data['data']['room_info']
    parent_area_id = room_info['parent_area_id']
    area_id = room_info['area_id']
    print(f'大分区: {parent_area_id}, 小分区: {area_id}')

    # 请求E接口（进入房间）
    ts = int(time.time() * 1000)
    e_data = {
        'id': f'[{parent_area_id},{area_id},0,1791983148]',
        'device': '["AUTO000000000000000","00000000-0000-0000-0000-000000000000"]',
        'is_patch': 0,
        'heart_beat': '[]',
        'csrf_token': bili_jct,
        'csrf': bili_jct,
        'visit_id': '',
        'ts': ts
    }
    print('\nE请求参数:', json.dumps(e_data, indent=2, ensure_ascii=False))
    
    e_resp = requests.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E', headers=headers, data=e_data, timeout=10)
    print('\nE响应状态码:', e_resp.status_code)
    print('E响应:', json.dumps(e_resp.json(), indent=2, ensure_ascii=False))
