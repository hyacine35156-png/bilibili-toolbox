# -*- coding: utf-8 -*-
"""核实：UAC 弹窗的条件 + 当前进程权限 + 同步按钮的提权逻辑"""
import ctypes, io, os, sys

print('=' * 96)
print('1) 当前进程是否管理员权限')
print('=' * 96)
try:
    is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    print('  IsUserAnAdmin: %s' % is_admin)
    if is_admin:
        print('  >>> 已是管理员：ShellExecuteExW(runas) 不会弹 UAC')
    else:
        print('  >>> 不是管理员：ShellExecuteExW(runas) 会弹 UAC')
except Exception as e:
    print('  检测失败: %s' % e)

print('')
print('=' * 96)
print('2) nm_sync_system_time 的提权方式')
print('=' * 96)
src = io.open('ui/rush_reward/new_mode.py', encoding='utf-8').read()
lines = src.split(chr(10))
s = None
for i, ln in enumerate(lines):
    if 'def nm_sync_system_time' in ln:
        s = i; break
e = len(lines)
for j in range(s+1, len(lines)):
    if lines[j].startswith('    def ') and j > s+2:
        e = j; break
print('  函数 %d-%d' % (s+1, e))
for j in range(s, e):
    ln = lines[j]
    if any(k in ln for k in ['lpVerb', 'runas', 'ShellExecuteExW', 'IsUserAnAdmin',
                               'Set-Date', 'SEE_MASK', 'nShow']):
        print('  %4d: %s' % (j+1, ln.strip()[:96]))

print('')
print('=' * 96)
print('3) 是否有"已是管理员就不提权"的判断')
print('=' * 96)
seg = chr(10).join(lines[s:e])
has_admin_check = 'IsUserAnAdmin' in seg
print('  nm_sync_system_time 里有 IsUserAnAdmin 判断: %s' % has_admin_check)
print('  >>> 如果没有，则无论是否管理员都会走 runas 分支')
print('  >>> （但已是管理员时，runas 不会弹窗，直接继承权限）')
