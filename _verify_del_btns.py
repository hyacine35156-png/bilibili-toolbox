# -*- coding: utf-8 -*-
"""验证：删除按钮能否真正生效 + 按钮尺寸一致"""
import os, sys, tkinter as tk, ctypes, time, pathlib, traceback, shutil, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass

# 严格备份数据
src_f = pathlib.Path('dist/data/schedule_config.json')
bak = pathlib.Path('_del_test_bak.json')
if src_f.exists(): shutil.copy2(src_f, bak)
orig_content = src_f.read_text(encoding='utf-8')

import config
config.BASE_DIR = pathlib.Path('dist/data')
import rush_stats
rush_stats.RESULTS_FILE = pathlib.Path('dist/data/rush_results.jsonl')
rush_stats._task_index['loaded'] = False
rush_stats._task_index['by_id'] = {}
rush_stats._task_index['by_name'] = {}
config.TASKS_FILE = pathlib.Path('dist/data/tasks_official.json')

FAILS=[]
def check(n,c,e=''):
    if c: print('PASS  '+n)
    else:
        print('FAIL  '+n+' -> '+str(e)); FAILS.append(n)

import tkinter.messagebox as mb
mb.showinfo=lambda *a,**k:None; mb.showwarning=lambda *a,**k:None; mb.showerror=lambda *a,**k:None

# 拦截 custom_askyesno: 一律返回 True（模拟用户点"确认"）
import widgets as W
ASKED = []
def fake_ask(parent, title, message):
    ASKED.append((str(title), str(message)))
    return True
W.custom_askyesno = fake_ask

import main as M
import ui.schedule as SCH
SCH.custom_askyesno = fake_ask

root=tk.Tk(); root.geometry('1720x1080')
app=M.DanmakuApp(root)
for _ in range(15): root.update(); time.sleep(0.02)
app.switch_tab('schedule')
for _ in range(25): root.update(); time.sleep(0.02)
sp = app.schedule_page

print('=' * 88)
print('1) 修复前数据')
print('=' * 88)
n0 = len(sp.schedule_tasks)
print('  任务数: %d' % n0)
for t in sp.schedule_tasks:
    print('    %s (id=%s)' % (t.get('name'), t.get('id')))

print('')
print('=' * 88)
print('2) 直接调用 delete_one_task（模拟点 ×）')
print('=' * 88)
target = sp.schedule_tasks[-1]
tid = target['id']
tname = target.get('name')
print('  准备删除: %s (id=%s)' % (tname, tid))
ASKED.clear()
try:
    sp.delete_one_task(tid)
    for _ in range(10): root.update(); time.sleep(0.02)
    n1 = len(sp.schedule_tasks)
    print('  删除后任务数: %d (原 %d)' % (n1, n0))
    print('  确认弹窗被调用: %s' % (ASKED if ASKED else '(未调用!)'))
    check('删除真的生效', n1 == n0 - 1, '%d -> %d' % (n0, n1))
    check('确认弹窗正常弹出', len(ASKED) > 0, ASKED)
    check('目标已从列表移除',
          not any(x['id'] == tid for x in sp.schedule_tasks))
except Exception as e:
    check('delete_one_task 调用', False, str(e)[:150])
    print(traceback.format_exc()[:1500])

print('')
print('=' * 88)
print('3) 验证按钮尺寸一致（遍历表头/数据行的 Canvas 按钮）')
print('=' * 88)
btns = []
def walk(w):
    for c in w.winfo_children():
        try:
            if hasattr(c,'command') and hasattr(c,'text') and c.winfo_class()=='Canvas':
                btns.append((str(c.text), c.winfo_width(), c.winfo_height(), c.winfo_class()))
        except Exception: pass
        walk(c)
walk(sp.task_list_frame)

op_btns = [(t,w,h) for t,w,h,_ in btns if t in ('✏','⧉','▶','⏸','×')]
print('  找到操作按钮 %d 个' % len(op_btns))
for t,w,h in op_btns[:10]:
    print('    %s  %dx%d' % (t, w, h))
if op_btns:
    ws = set(w for _,w,_ in op_btns)
    hs = set(h for _,_,h in op_btns)
    print('  宽度集合: %s' % ws)
    print('  高度集合: %s' % hs)
    check('所有操作按钮宽度一致', len(ws) == 1, ws)
    check('所有操作按钮高度一致', len(hs) == 1, hs)
else:
    check('找到操作按钮', False)

print('')
print('=' * 88)
print('4) 恢复数据')
print('=' * 88)
root.destroy()
if bak.exists():
    shutil.copy2(bak, src_f)
    bak.unlink()
    print('  已从备份恢复 schedule_config.json')
restored = json.loads(src_f.read_text(encoding='utf-8'))
print('  恢复后任务数: %d' % len(restored))
check('数据已恢复', len(restored) == n0, len(restored))

print('')
print('==== 结果: %d 失败 ====' % len(FAILS))
for f in FAILS: print(' - '+f)
