# -*- coding: utf-8 -*-
import io, os

print('=' * 94)
print('1) 顶部导航栏 tab 定义')
print('=' * 94)
src = io.open('main.py', encoding='utf-8').read()
lines = src.split(chr(10))
for i, ln in enumerate(lines, 1):
    if 'tab_account' in ln and ('tk.Label' in ln or 'text=' in ln):
        print('  %d: %s' % (i, ln.strip()[:100]))
    if 'account_page' in ln and 'Frame' in ln:
        print('  %d: %s' % (i, ln.strip()[:100]))

print('')
print('=' * 94)
print('2) 全项目引用「账户管理」的地方')
print('=' * 94)
for root_dir, dirs, files in os.walk('.'):
    if any(x in root_dir for x in ['build', 'dist', '.git', '__pycache__', 'backup', 'versions']):
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root_dir, f)
        try:
            s = io.open(p, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        if '账户管理' in s:
            cnt = s.count('账户管理')
            print('  %-32s 出现 %d 次' % (p, cnt))
            for i, ln in enumerate(s.split(chr(10)), 1):
                if '账户管理' in ln:
                    print('      %d: %s' % (i, ln.strip()[:88]))

print('')
print('=' * 94)
print('3) 当前顶部导航栏所有 tab 文字')
print('=' * 94)
for i, ln in enumerate(lines, 1):
    if 'self.tab_' in ln and 'dark_label' in ln.lower() or ('self.tab_' in ln and '=' in ln and 'Label' in ln):
        print('  %d: %s' % (i, ln.strip()[:100]))
