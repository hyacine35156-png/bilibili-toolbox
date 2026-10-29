#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在标题栏显示卡密剩余时间"""

FILE_PATH = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 is_card_expired 函数后添加 get_card_remaining_text 函数
old_func = '''def clear_saved_card():
    """清除保存的卡密"""
    try:
        if CARD_FILE.exists():
            CARD_FILE.unlink()
    except Exception:
        pass'''

new_func = '''def clear_saved_card():
    """清除保存的卡密"""
    try:
        if CARD_FILE.exists():
            CARD_FILE.unlink()
    except Exception:
        pass


def get_card_remaining_text():
    """获取卡密剩余时间的显示文本"""
    saved = load_saved_card()
    if not saved:
        return ""
    
    card_type = saved.get("card_type", "")
    if card_type == "permanent":
        return " | 卡密: 永久"
    
    expires_at = saved.get("expires_at")
    if not expires_at:
        return " | 卡密: 未知"
    
    try:
        # 尝试多种日期格式
        expiry = None
        for fmt in ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", 
                    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]:
            try:
                expiry = datetime.strptime(expires_at, fmt)
                break
            except ValueError:
                continue
        
        if not expiry:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        
        now = datetime.now()
        if expiry.tzinfo:
            now = now.replace(tzinfo=expiry.tzinfo)
        
        remaining = expiry - now
        days = remaining.days
        
        if days < 0:
            return " | 卡密: 已过期"
        elif days == 0:
            hours = remaining.seconds // 3600
            return f" | 卡密: 剩余{hours}小时"
        else:
            return f" | 卡密: 剩余{days}天"
    except Exception:
        return " | 卡密: 未知"'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("✓ 已添加 get_card_remaining_text 函数")
else:
    print("✗ 未找到 clear_saved_card")

# 2. 修改标题栏，添加卡密剩余时间
old_title = '''        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务+日程任务")'''

new_title = '''        card_text = get_card_remaining_text()
        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务+日程任务{card_text}")'''

if old_title in content:
    content = content.replace(old_title, new_title)
    print("✓ 标题栏已添加卡密剩余时间")
else:
    print("✗ 未找到标题栏设置")

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n修改完成！")
