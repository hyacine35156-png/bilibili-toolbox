# -*- coding: utf-8 -*-
"""盘点账户管理页的全部功能和元素"""
import os, sys, tkinter as tk, ctypes, time, pathlib, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
src_f = pathlib.Path('dist/data/schedule_config.json')
bak = pathlib.Path('_inv.json')
if src_f.exists(): shutil.copy2(src_f, bak)
import config
config.BASE_DIR = pathlib.Path('dist/data')
import rush_stats
rush_stats.RESULTS_FILE = pathlib.Path('dist/data/rush_results.jsonl')
rush_stats._task_index['loaded'] = False
rush_stats._task_index['by_id'] = {}
rush_stats._task_index['by_name'] = {}
config.TASKS_FILE = pathlib.Path('dist/data/tasks_official.json')
import tkinter.messagebox as mb
mb.showinfo=lambda *a,**k:None; mb.showwarning=lambda *a,**k:None; mb.showerror=lambda *a,**k:None

import main as M
root = tk.Tk(); root.geometry('1720x1080')
app = M.DanmakuApp(root)
for _ in range(15): root.update(); time.sleep(0.02)
app.switch_tab('account')
for _ in range(20): root.update(); time.sleep(0.02)

print('=' * 96)
print('账户管理页：所有按钮')
print('=' * 96)
btns = []
def collect(w):
    for c in w.winfo_children():
        try:
            if hasattr(c, 'command') and hasattr(c, 'text') and c.winfo_class() == 'Canvas':
                btns.append((str(c.text), getattr(c.command, '__name__', 'lambda')))
        except Exception: pass
        collect(c)
collect(app.account_page)
for i, (t, cmd) in enumerate(btns, 1):
    print('  %2d. %-18s -> %s' % (i, t, cmd))

print('')
print('=' * 96)
print('账户管理页：所有 Label 文字（板块标题）')
print('=' * 96)
def collect_lbl(w):
    for c in w.winfo_children():
        try:
            if c.winfo_class() in ('Label',):
                t = str(c.cget('text'))
                if t.strip(): print('  %s' % t[:70])
        except Exception: pass
        collect_lbl(c)
collect_lbl(app.account_page)

print('')
print('=' * 96)
print('账户管理页：智能提示（Label 里的功能说明）')
print('=' * 96)
import io
src = io.open('main.py', encoding='utf-8').read()
lines = src.split(chr(10))
s = None
for i, ln in enumerate(lines):
    if ln.strip().startswith('def build_account_page'):
        s = i; break
e = len(lines)
for j in range(s+1, len(lines)):
    if lines[j].startswith('    def ') and j > s+2:
        e = j; break
print('  build_account_page: %d-%d' % (s+1, e))
print('  按钮/入口:')
for j in range(s, e):
    ln = lines[j]
    if 'command=self.' in ln or 'text="' in ln:
        if 'command=self.' in ln:
            import re
            m = re.search(r'command=self\.([a-zA-Z_]+)', ln)
            if m: print('    %s' % m.group(1))

root.destroy()
if bak.exists():
    shutil.copy2(bak, src_f); bak.unlink()
