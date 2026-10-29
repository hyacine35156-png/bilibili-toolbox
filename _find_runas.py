# -*- coding: utf-8 -*-
import io
src = io.open('ui/rush_reward/new_mode.py', encoding='utf-8').read()
lines = src.split(chr(10))
print('=' * 94)
print('搜索 runas / ShellExecuteExW / 提权 出现在哪')
print('=' * 94)
for i, ln in enumerate(lines, 1):
    if any(k in ln for k in ['runas', 'ShellExecuteExW', 'SEE_MASK',
                              '_SHELLEXECUTEINFOW', 'lpVerb']):
        print('  %4d: %s' % (i, ln.strip()[:100]))

print('')
print('=' * 94)
print('_sync_time_worker 里实际怎么执行 PowerShell')
print('=' * 94)
s = None
for i, ln in enumerate(lines):
    if 'def _sync_time_worker' in ln:
        s = i; break
e = len(lines)
for j in range(s+1, len(lines)):
    if lines[j].startswith('    def ') and j > s+2:
        e = j; break
# 打印 ps_path 之后到结束的关键部分
for j in range(s, e):
    ln = lines[j]
    if any(k in ln for k in ['ps_path', 'subprocess', 'Popen', 'run(', 'cmd',
                              'powershell', 'Popen', 'check_output', 'import']):
        print('  %4d: %s' % (j+1, ln.strip()[:100]))
