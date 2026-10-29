import requests, json

with open('dist/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
cookie = f"SESSDATA={acc.get('SESSDATA','')}; bili_jct={acc.get('bili_jct','')}; DedeUserID={acc.get('DedeUserID','')}"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://live.bilibili.com/1791983148',
    'Origin': 'https://live.bilibili.com',
    'Cookie': cookie
}

resp = requests.get('https://api.live.bilibili.com/room/v1/Room/playUrl?cid=1791983148&quality=4&platform=web', headers=headers, timeout=10)
result = resp.json()
print('API code:', result.get('code'))
if result.get('code') == 0:
    durl = result['data'].get('durl', [])
    if durl:
        play_url = durl[0]['url']
        print('播放地址:', play_url[:120])
        resp2 = requests.get(play_url, headers=headers, timeout=10, stream=True)
        print('状态码:', resp2.status_code)
        print('Content-Type:', resp2.headers.get('Content-Type'))
        chunk = resp2.raw.read(32)
        print('前16字节:', chunk[:16])
        print('是否FLV:', chunk[:3] == b'FLV')
        resp2.close()
