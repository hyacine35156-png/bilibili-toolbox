# -*- coding: utf-8 -*-
import io, os, glob

print('=' * 92)
print('1) get_cookie_string 签名')
print('=' * 92)
for f in glob.glob('managers/*.py') + ['managers.py']:
    if not os.path.exists(f): continue
    src = io.open(f, encoding='utf-8').read()
    if 'def get_cookie_string' in src:
        lines = src.split(chr(10))
        for i, ln in enumerate(lines, 1):
            if 'def get_cookie_string' in ln:
                print('  文件: %s 行 %d' % (f, i))
                for j in range(i-1, min(len(lines), i+14)):
                    print('  %4d: %s' % (j+1, lines[j][:104]))

print('')
print('=' * 92)
print('2) verify_login 签名')
print('=' * 92)
src = io.open('bili_api.py', encoding='utf-8').read()
lines = src.split(chr(10))
for i, ln in enumerate(lines, 1):
    if 'def verify_login' in ln:
        for j in range(i-1, min(len(lines), i+25)):
            print('  %4d: %s' % (j+1, lines[j][:104]))
        break

print('')
print('=' * 92)
print('3) 我写的 _manager_verify_all_accounts')
print('=' * 92)
msrc = io.open('main.py', encoding='utf-8').read()
mlines = msrc.split(chr(10))
s = None
for i, ln in enumerate(mlines):
    if 'def _manager_verify_all_accounts' in ln:
        s = i; break
e = len(mlines)
for j in range(s+1, len(mlines)):
    if mlines[j].startswith('    def ') and j > s+2:
        e = j; break
for j in range(s, min(e, s+45)):
    print('  %4d: %s' % (j+1, mlines[j][:104]))
