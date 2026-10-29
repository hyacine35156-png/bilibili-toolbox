# -*- coding: utf-8 -*-
import io
lines = io.open('ui/rush_reward/new_mode.py', encoding='utf-8').read().split(chr(10))

print('=' * 94)
print('阶段1 NTP同步的现有实现（是否弹UAC）')
print('=' * 94)
s = None
for i, ln in enumerate(lines):
    if '# ===== 阶段1: NTP同步' in ln:
        s = i; break
for j in range(s, min(len(lines), s+30)):
    print('%d: %s' % (j+1, lines[j][:110])
)
