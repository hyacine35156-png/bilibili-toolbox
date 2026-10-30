# -*- coding: utf-8 -*-
import io
lines = io.open('ui/schedule.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('846 行附近（模板删除）')
print('=' * 94)
for j in range(838, 856):
    print('%d: %s' % (j+1, lines[j][:112]))
print('')
print('=' * 94)
print('验证参数错误（实测抛异常）')
print('=' * 94)
import sys
sys.path.insert(0, '.')
# 模拟调用签名
def custom_askyesno(parent, title, message):
    return True
try:
    r = custom_askyesno("确认删除", "确定删除?", parent="ROOT")
    print('  调用成功: %s' % r)
except TypeError as e:
    print('  TypeError: %s' % e)
