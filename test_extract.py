# -*- coding: utf-8 -*-
"""测试兑换码提取逻辑"""

import sys
sys.path.insert(0, r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot")

# 直接导入函数
import importlib.util
spec = importlib.util.spec_from_file_location("main_gui_pro", r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py")
module = importlib.util.module_from_spec(spec)

# 模拟必要的全局变量
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

try:
    spec.loader.exec_module(module)
    print("✓ 模块加载成功")
except Exception as e:
    print(f"✗ 模块加载失败: {e}")
    # 尝试只提取函数
    import re
    with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取extract_redeem_codes函数
    match = re.search(r'def extract_redeem_codes\(data\):.*?(?=\ndef )', content, re.DOTALL)
    if match:
        func_code = match.group(0)
        print("✓ 提取到extract_redeem_codes函数")
        # 执行函数定义
        exec(func_code)
        
        # 测试数据
        test_data = {
            "had_address": False,
            "list": [
                {
                    "mid": 3690972101740709,
                    "award_id": -483735,
                    "award_name": "星琼*50-上半任务1",
                    "type": "CdKeyV2",
                    "extra_info": {
                        "award_outer_id": "5ERAnwloghvq5x00",
                        "cdkey_content": "KWZJUXEA4CN8",
                        "cdkey_id": "31842322"
                    },
                }
            ]
        }
        
        codes = extract_redeem_codes(test_data)
        print(f"\n提取到 {len(codes)} 个兑换码:")
        for code in codes:
            print(f"  字段: {code['field']}, 值: {code['value']}, 路径: {code['path']}")
    else:
        print("✗ 未提取到函数")
