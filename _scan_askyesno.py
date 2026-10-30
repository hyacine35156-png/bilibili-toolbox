# -*- coding: utf-8 -*-
"""全项目扫描 custom_askyesno 的错误调用"""
import io, os, re, glob

# 正确签名: custom_askyesno(parent, title, message)
files = ['main.py', 'widgets.py', 'dialogs.py', 'storage.py', 'ui/schedule.py',
         'ui/watch_live.py', 'ui/code_export.py', 'ui/rush_reward/__init__.py',
         'ui/rush_reward/new_mode.py', 'ui/rush_reward/scheduled.py',
         'ui/rush_reward/manual_task.py']
files += glob.glob('managers/*.py')
files += glob.glob('ui/*.py')

print('=' * 96)
print('custom_askyesno 全部调用点')
print('=' * 96)
bad = []
good = 0
for f in sorted(set(files)):
    if not os.path.exists(f):
        continue
    try:
        lines = io.open(f, encoding='utf-8', errors='ignore').read().split(chr(10))
    except Exception:
        continue
    for i, ln in enumerate(lines, 1):
        if 'custom_askyesno(' not in ln or 'def custom_askyesno' in ln:
            continue
        s = ln.strip()
        # 取调用参数首段
        m = re.search(r'custom_askyesno\((.*)', s)
        if not m:
            continue
        args = m.group(1)
        first_is_string = args.lstrip().startswith(('"', "'"))
        has_parent_kw = 'parent=' in args
        if first_is_string and has_parent_kw:
            bad.append((f, i, s[:100]))
            print('  [BUG] %-28s %4d: %s' % (os.path.basename(f), i, s[:88]))
        else:
            good += 1

print('')
print('  正确调用: %d 处' % good)
print('  错误调用: %d 处' % len(bad))
