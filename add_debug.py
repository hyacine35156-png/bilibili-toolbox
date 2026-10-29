#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加调试输出，打印完整的stock_info结构"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 stock_info = info.get("stock_info", {}) 这行
for i, line in enumerate(lines):
    if 'stock_info = info.get("stock_info", {})' in line and 'i' in line[:10]:
        print(f"找到目标行: 第{i+1}行: {line.rstrip()}")
        # 在这行后面添加调试输出
        indent = '            '  # 12个空格
        debug_lines = [
            f'{indent}# 调试：打印完整的stock_info结构\n',
            f'{indent}import json as _json\n',
            f'{indent}print(f"[调试] 任务 {{task.get(\'name\', \'\')}} stock_info: {{_json.dumps(stock_info, ensure_ascii=False)}}")\n',
            f'{indent}print(f"[调试] 任务 {{task.get(\'name\', \'\')}} status: {{info.get(\'status\')}}, task_finished: {{task_finished}}")\n',
        ]
        lines[i+1:i+1] = debug_lines
        print(f"已在第{i+2}行添加调试输出")
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("修改完成！")
