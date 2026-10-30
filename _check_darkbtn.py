# -*- coding: utf-8 -*-
import io
lines = io.open('widgets.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('DarkButton.__init__ 签名与 compact 处理')
print('=' * 94)
s = None
for i, ln in enumerate(lines):
    if 'class DarkButton' in ln:
        s = i; break
e = len(lines)
for j in range(s+1, len(lines)):
    if lines[j].startswith('class ') and j > s+2:
        e = j; break
print('  DarkButton 类: 行 %d-%d' % (s+1, e))
for j in range(s, min(e, s+70)):
    ln = lines[j]
    if any(k in ln for k in ['def __init__', 'compact', 'width', 'height',
                              '_estimate_text_width', '_measure_button_width',
                              'font=', 'radius']):
        print('  %4d: %s' % (j+1, ln.rstrip()[:108]))
