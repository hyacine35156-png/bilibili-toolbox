# -*- coding: utf-8 -*-
"""多行解析：找出所有 custom_askyesno 调用并检查参数"""
import io, os, glob

files = ['main.py', 'widgets.py', 'dialogs.py', 'storage.py']
files += glob.glob('ui/*.py') + glob.glob('ui/**/*.py', recursive=True)
files += glob.glob('managers/*.py')

print('=' * 96)
print('custom_askyesno 跨行调用检查')
print('=' * 96)
bad = []
good = 0
for f in sorted(set(files)):
    if not os.path.exists(f) or os.path.basename(f) == 'widgets.py':
        continue
    try:
        src = io.open(f, encoding='utf-8', errors='ignore').read()
    except Exception:
        continue
    lines = src.split(chr(10))
    for i, ln in enumerate(lines):
        if 'custom_askyesno(' not in ln or 'def custom_askyesno' in ln:
            continue
        # 拼接最多 4 行，直到括号平衡
        chunk = ln
        depth = ln.count('(') - ln.count(')')
        j = i + 1
        while depth > 0 and j < len(lines) and j < i + 5:
            chunk += ' ' + lines[j].strip()
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        s = ' '.join(chunk.split())
        first_arg = s.split('custom_askyesno(', 1)[1].lstrip()
        is_str_first = first_arg.startswith(('"', "'"))
        has_parent_kw = 'parent=' in s
        if is_str_first and has_parent_kw:
            bad.append((f, i+1, s[:110]))
            print('  [BUG] %-26s %4d' % (os.path.basename(f), i+1))
            print('        %s' % s[:100])
        else:
            good += 1

print('')
print('  正确: %d 处   错误: %d 处' % (good, len(bad)))
print('')
if bad:
    print('=' * 96)
    print('修复方案：参数顺序改为 (parent, title, message)')
    print('=' * 96)
    for f, ln, s in bad:
        print('  %s:%d' % (os.path.basename(f), ln))
