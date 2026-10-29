#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提高播放模拟频率到每分钟一次，确保5人同时观看"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 修改播放模拟的触发条件：从每5轮心跳改为每1轮心跳（每分钟一次）
old_condition = '''                # 模拟播放器播放（每5轮心跳播放一次，避免请求过于频繁）
                if stats["heartbeat_count"] % (5 * len(room_ids)) < len(room_ids):'''

new_condition = '''                # 模拟播放器播放（每分钟一次，确保5人同时观看状态）
                if True:'''

content = content.replace(old_condition, new_condition, 1)

# 更新版本号
content = content.replace('APP_VERSION = "v3.7.0"', 'APP_VERSION = "v3.7.1"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.7.1")
print(f"文件大小: {len(content)} 字符")
