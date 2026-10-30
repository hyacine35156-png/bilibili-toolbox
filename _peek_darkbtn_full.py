# -*- coding: utf-8 -*-
import io
lines = io.open('widgets.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('DarkButton.__init__ 完整代码（462-500）')
print('=' * 94)
for j in range(461, 501):
    print('%d: %s' % (j+1, lines[j][:112]))
print('')
print('=' * 94)
print('_render 部分（505-525）')
print('=' * 94)
for j in range(504, 526):
    print('%d: %s' % (j+1, lines[j][:112]))
