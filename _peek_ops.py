# -*- coding: utf-8 -*-
import io
lines = io.open('ui/schedule.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('操作列（cell7）按钮创建代码')
print('=' * 94)
for i, ln in enumerate(lines, 1):
    if 'cell7' in ln or ('操作' in ln and 'cell' in ln):
        print('  %4d: %s' % (i, ln.rstrip()[:110]))
