import requests, json

with open(r'dist\accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 测试每个账户
for acc in accounts:
    name = acc.get('name', '未知')
    cookie = 'SESSDATA=' + acc.get('SESSDATA','') + '; bili_jct=' + acc.get('bili_jct','') + '; DedeUserID=' + acc.get('DedeUserID','')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Cookie': cookie,
        'Referer': 'https://live.bilibili.com/'
    }
    
    # 主播信息接口
    try:
        resp = requests.get('https://api.live.bilibili.com/live_user/v1/Master/info', headers=headers, timeout=10)
        result = resp.json()
        if result.get('code') == 0:
            data = result.get('data', {})
            room_id = data.get('room_id', 0)
            live_status = data.get('live_status', 0)
            uname = data.get('uname', '')
            area_name = data.get('area_name', '')
            print(f'[{name}] room_id={room_id}, live_status={live_status}, area={area_name}, uname={uname}')
        else:
            print(f'[{name}] 失败: code={result.get("code")}, message={result.get("message")}')
    except Exception as e:
        print(f'[{name}] 异常: {e}')
