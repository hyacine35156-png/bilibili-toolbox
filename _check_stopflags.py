# -*- coding: utf-8 -*-
"""检查 ScheduleFrame 有哪些 stop_flags 属性"""
import io
src = io.open('ui/schedule.py', encoding='utf-8').read()
lines = src.split(chr(10))
print('=' * 90)
print('schedule.py 里所有 stop_flag 相关属性')
print('=' * 90)
for i, ln in enumerate(lines, 1):
    if 'stop_flag' in ln.lower() or 'stop_flags' in ln:
        print('  %4d: %s' % (i, ln.strip()[:100]))
print('')
print('=' * 90)
print('ScheduleFrame.__init__ 里的属性定义')
print('=' * 90)
s = None
for i, ln in enumerate(lines):
    if 'class ScheduleFrame' in ln:
        s = i; break
e = len(lines)
for j in range(s+1, len(lines)):
    if lines[j].startswith('    def ') and j > s+5:
        e = j; break
for j in range(s, min(e, s+45)):
    print('  %4d: %s' % (j+1, lines[j][:104]))
