#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试卡密验证弹窗GUI"""

import sys
sys.path.insert(0, r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot")

import tkinter as tk
from main_gui_pro import CardAuthDialog, COLORS

print("创建主窗口...")
root = tk.Tk()
root.title("测试")
root.geometry("300x200")

# 不隐藏主窗口，测试弹窗
print("创建卡密验证弹窗...")
try:
    dialog = CardAuthDialog(root)
    print("✓ 弹窗创建成功")
    print(f"弹窗标题: {dialog.dialog.title()}")
    print(f"弹窗尺寸: {dialog.dialog.geometry()}")
    
    # 3秒后自动关闭
    root.after(3000, lambda: (dialog.dialog.destroy(), root.destroy()))
    print("3秒后自动关闭...")
    
    root.mainloop()
    print(f"验证结果: success={dialog.result}")
except Exception as e:
    print(f"✗ 弹窗创建失败: {e}")
    import traceback
    traceback.print_exc()
    root.destroy()
