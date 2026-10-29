# -*- coding: utf-8 -*-
import py_compile
py_compile.compile('tasks_config.py', doraise=True)
print('语法检查通过')

from tasks_config import ALL_TASKS, VERSION_DEFAULT_ACT_ID
zzz = [t for t in ALL_TASKS if t['version'].startswith('绝区零')]
print(f'绝区零任务数: {len(zzz)}')
versions = set(t['version'] for t in zzz)
print(f'版本: {versions}')
print(f'act_id: {VERSION_DEFAULT_ACT_ID.get("绝区零3.3")}')

types = {}
for t in zzz:
    types[t['type']] = types.get(t['type'], 0) + 1
print(f'分类: {types}')

ids = [t['task_id'] for t in zzz]
print(f'ID总数: {len(ids)}, 去重后: {len(set(ids))}')
