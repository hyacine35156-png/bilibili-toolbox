import json
with open('dist/data/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)
for i, a in enumerate(accounts):
    name = a.get('name', '未知')
    uid = a.get('DedeUserID', '')
    print(f'{i+1}. {name} (UID={uid})')
print(f'共{len(accounts)}个账户')
