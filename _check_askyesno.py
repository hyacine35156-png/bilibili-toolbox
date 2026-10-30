# -*- coding: utf-8 -*-
import io
lines = io.open('widgets.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('custom_askyesno 签名')
print('=' * 94)
s = None
for i, ln in enumerate(lines):
    if 'def custom_askyesno' in ln:
        s = i; break
if s is None:
    print('  未找到')
else:
    e = len(lines)
    for j in range(s+1, len(lines)):
        if lines[j].startswith('def ') and j > s+2:
            e = j; break
    for j in range(s, min(e, s+30)):
        print('  %4d: %s' % (j+1, lines[j][:108]))

print('')
print('=' * 94)
print('schedule.py 里 custom_askyesno 的所有调用')
print('=' * 94)
sl = io.open('ui/schedule.py', encoding='utf-8').read().split(chr(10))
for i, ln in enumerate(sl, 1):
    if 'custom_askyesno' in ln:
        print('  %4d: %s' % (i, ln.strip()[:104]))
