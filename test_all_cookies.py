import requests, json
accounts_file = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json'
with open(accounts_file, 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 测试所有账户
for acc in accounts:
    cookies = {'SESSDATA': acc['SESSDATA'], 'bili_jct': acc['bili_jct']}
    if acc.get('DedeUserID'):
        cookies['DedeUserID'] = acc['DedeUserID']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, cookies=cookies, timeout=10)
        data = resp.json()
        print(acc['name'], ': code=', data.get('code'), ', 用户=', data.get('data', {}).get('uname', '未知'))
    except Exception as e:
        print(acc['name'], ': 异常 -', e)
