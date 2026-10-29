import requests, json
accounts_file = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json'
with open(accounts_file, 'r', encoding='utf-8') as f:
    accounts = json.load(f)
target_acc = next((a for a in accounts if a.get('name') == '灵砂是无敌的'), None)
cookies = {'SESSDATA': target_acc['SESSDATA'], 'bili_jct': target_acc['bili_jct']}
if target_acc.get('DedeUserID'):
    cookies['DedeUserID'] = target_acc['DedeUserID']
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, cookies=cookies, timeout=10)
data = resp.json()
print('code:', data.get('code'), ', 用户:', data.get('data', {}).get('uname', '未知'))
