# -*- coding: utf-8 -*-
import io
lines = io.open('ui/rush_reward/__init__.py', encoding='utf-8').read().split(chr(10))
print('=' * 94)
print('详细仪表盘弹窗特征（用户要求"类似详细仪表盘的弹窗"）')
print('=' * 94)
for i, ln in enumerate(lines):
    if 'def open_stats_dashboard' in ln:
        for j in range(i, min(len(lines), i+40)):
            t = lines[j]
            if any(k in t for k in ['Toplevel', 'geometry', 'minsize', 'title',
                                     'transient', 'grab_set', 'resizable',
                                     'attributes', 'protocol']):
                print('  %d: %s' % (j+1, t.strip()[:100]))
        break
