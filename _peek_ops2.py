# -*- coding: utf-8 -*-
import io
lines = io.open('ui/schedule.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('操作列完整代码（1200-1300）')
print('=' * 94)
for j in range(1199, 1300):
    print('%d: %s' % (j+1, lines[j][:112]))
