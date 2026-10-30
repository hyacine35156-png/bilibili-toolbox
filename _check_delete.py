# -*- coding: utf-8 -*-
import io
src = io.open('ui/schedule.py', encoding='utf-8').read()
lines = src.split(chr(10))
print('=' * 94)
print('delete_one_task 是否存在及实现')
print('=' * 94)
s = None
for i, ln in enumerate(lines):
    if 'def delete_one_task' in ln:
        s = i; break
if s is None:
    print('  !!! delete_one_task 未定义')
    print('  搜索所有 delete 相关方法:')
    for i, ln in enumerate(lines, 1):
        if 'def ' in ln and 'delete' in ln.lower():
            print('    %4d: %s' % (i, ln.strip()[:90]))
else:
    e = len(lines)
    for j in range(s+1, len(lines)):
        if lines[j].startswith('    def ') and j > s+2:
            e = j; break
    print('  行 %d-%d (%d行)' % (s+1, e, e-s))
    for j in range(s, e):
        print('  %4d: %s' % (j+1, lines[j][:108]))

print('')
print('=' * 94)
print('其它操作方法的定义位置')
print('=' * 94)
for name in ['_edit_task_by_id', 'copy_schedule_task', 'run_task_now', 'toggle_task_enabled', 'delete_one_task']:
    found = False
    for i, ln in enumerate(lines, 1):
        if 'def ' + name in ln:
            print('  %-26s 行 %d' % (name, i))
            found = True
            break
    if not found:
        print('  %-26s !!! 未定义' % name)
