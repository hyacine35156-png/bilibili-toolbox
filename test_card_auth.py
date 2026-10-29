#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试卡密验证功能"""

import sys
sys.path.insert(0, r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot")

# 先测试导入
print("测试导入...")
try:
    import main_gui_pro
    print("✓ 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试机器码获取
print("\n测试机器码获取...")
try:
    machine_code = main_gui_pro.get_machine_code()
    print(f"✓ 机器码: {machine_code}")
except Exception as e:
    print(f"✗ 机器码获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试卡密验证
print("\n测试卡密验证...")
try:
    test_card = "5INF-OBEB-VVO5-4DZ8"  # 未激活的测试卡密
    machine_code = main_gui_pro.get_machine_code()
    success, result = main_gui_pro.verify_card_online(test_card, machine_code)
    print(f"验证结果: success={success}, result={result}")
except Exception as e:
    print(f"✗ 卡密验证失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成！")
