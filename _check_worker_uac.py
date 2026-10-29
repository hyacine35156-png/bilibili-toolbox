# -*- coding: utf-8 -*-
import io
lines = io.open('ui/rush_reward/new_mode.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('_sync_time_worker 的提权逻辑')
print('=' * 94)
s = None
for i, ln in enumerate(lines):
    if 'def _sync_time_worker' in ln:
        s = i; break
e = len(lines)
for j in range(s+1, len(lines)):
    if lines[j].startswith('    def ') and j > s+2:
        e = j; break
print('  范围 %d-%d (%d行)' % (s+1, e, e-s))
print('')
for j in range(s, min(e, s+70)):
    ln = lines[j]
    if any(k in ln for k in ['lpVerb', 'runas', 'ShellExecuteExW', 'IsUserAnAdmin',
                               'Set-Date', 'nShow', 'lpFile', 'lpParameters',
                               '管理员', 'UAC', '提权']):
        print('  %4d: %s' % (j+1, ln.strip()[:100]))
