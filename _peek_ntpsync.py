# -*- coding: utf-8 -*-
import io
lines = io.open('ui/rush_reward/new_mode.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('nm_ntp_sync 实现（确认是否弹 UAC / 是否真改系统时间）')
print('=' * 94)
s = None
for i, ln in enumerate(lines):
    if 'def nm_ntp_sync' in ln:
        s = i; break
e = len(lines)
for j in range(s+1, len(lines)):
    if lines[j].startswith('    def ') and j > s+2:
        e = j; break
print('  范围 %d-%d (%d行)' % (s+1, e, e-s))
print('')
for j in range(s, min(e, s+50)):
    print('%d: %s' % (j+1, lines[j][:108])
)
