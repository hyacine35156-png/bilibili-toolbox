# -*- coding: utf-8 -*-
"""实际测试验证登录 API"""
import sys, json, pathlib, io
sys.path.insert(0, '.')
import config
config.BASE_DIR = pathlib.Path('dist/data')

from bili_api import verify_login
import managers.account as acc_mod

accs = json.loads((pathlib.Path('dist/data/accounts.json')).read_text(encoding='utf-8'))
print('=' * 92)
print('账户数: %d' % len(accs))
print('=' * 92)

# 构造 cookie 字符串（复刻 get_cookie_string 逻辑）
def build_cookie(acc):
    parts = ['SESSDATA=%s' % acc['SESSDATA'], 'bili_jct=%s' % acc['bili_jct']]
    if acc.get('DedeUserID'):
        parts.append('DedeUserID=%s' % acc['DedeUserID'])
    return '; '.join(parts)

for i, a in enumerate(accs, 1):
    name = a.get('name', '?')
    cookie = build_cookie(a)
    print('')
    print('[%d/%d] %s' % (i, len(accs), name))
    print('  SESSDATA 长度: %d' % len(a.get('SESSDATA','')))
    print('  bili_jct 长度: %d' % len(a.get('bili_jct','')))
    print('  DedeUserID: %s' % a.get('DedeUserID'))
    try:
        ok, msg = verify_login(cookie)
        print('  验证结果: ok=%s msg=%s' % (ok, msg))
    except Exception as e:
        print('  异常: %s' % e)
