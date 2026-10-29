# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

with open('main_gui_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('ALL_TASKS = [')
end = content.find(']', start) + 1
tasks_code = content[start:end]

namespace = {}
exec(tasks_code, namespace)
ALL_TASKS = namespace['ALL_TASKS']

VERSION_DEFAULT_ACT_ID = {
    '鸣潮3.6': '1ERAzwloghvn7l00',
    '原神7.0': '1ERAzwloghvcpc00',
    '崩坏星穹铁道4.5': '1ERAzwloghvb5600',
}

print('=' * 60)
print('任务自检报告')
print('=' * 60)

versions = {}
for t in ALL_TASKS:
    v = t.get('version', '未知')
    versions[v] = versions.get(v, 0) + 1

print('\n总任务数: %d' % len(ALL_TASKS))
for v, count in versions.items():
    act_id = VERSION_DEFAULT_ACT_ID.get(v, '未找到')
    print('  %s: %d个任务, act_id=%s' % (v, count, act_id))

required_fields = ['version', 'period', 'type', 'name', 'task_id', 'award']
missing_fields = []
for i, t in enumerate(ALL_TASKS):
    for f in required_fields:
        if f not in t or not t[f]:
            name = t.get('name', '未知')
            missing_fields.append('任务#%d (%s) 缺少字段: %s' % (i+1, name, f))

if missing_fields:
    print('\n❌ 缺少字段的任务:')
    for m in missing_fields:
        print('  %s' % m)
else:
    print('\n✅ 所有任务都有完整的必填字段')

task_ids = [t['task_id'] for t in ALL_TASKS]
duplicates = [tid for tid in set(task_ids) if task_ids.count(tid) > 1]
if duplicates:
    print('\n❌ 重复的task_id:')
    for d in duplicates:
        print('  %s' % d)
else:
    print('\n✅ 没有重复的task_id')

unknown_versions = set()
for t in ALL_TASKS:
    v = t.get('version', '')
    if v not in VERSION_DEFAULT_ACT_ID:
        unknown_versions.add(v)
if unknown_versions:
    print('\n❌ 未知版本:')
    for v in unknown_versions:
        print('  %s' % v)
else:
    print('\n✅ 所有版本都有对应的act_id')

print('\n' + '=' * 60)
print('详细任务列表')
print('=' * 60)
for v in ['鸣潮3.6', '原神7.0', '崩坏星穹铁道4.5']:
    v_tasks = [t for t in ALL_TASKS if t['version'] == v]
    print('\n【%s】共%d个任务:' % (v, len(v_tasks)))
    types = {}
    for t in v_tasks:
        ty = t.get('type', '未知')
        types[ty] = types.get(ty, 0) + 1
    for ty, count in types.items():
        print('  %s: %d个' % (ty, count))
    for t in v_tasks:
        print('    [%s][%s] %s => %s (task_id: %s)' % (
            t['period'], t['type'], t['name'], t['award'], t['task_id']))

print('\n' + '=' * 60)
print('自检完成')
print('=' * 60)
