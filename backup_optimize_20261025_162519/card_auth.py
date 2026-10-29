# -*- coding: utf-8 -*-
"""卡密验证：转发 PyArmor 加密的 card_verify 模块。"""

try:
    from card_verify import (
        get_machine_code, verify_card_online, load_saved_card,
        is_card_expired, save_card_info, clear_saved_card,
        get_card_remaining_text, CARD_FILE, CARD_API_BASE, CARD_VERIFY_URL
    )
except ImportError:
    # 开发环境缺 card_verify 时给占位，避免整个程序无法导入
    def get_machine_code(): return ""
    def verify_card_online(*a, **k): return False, {"code": -99, "msg": "card_verify 缺失"}
    def load_saved_card(): return None
    def is_card_expired(*a, **k): return True
    def save_card_info(*a, **k): return None
    def clear_saved_card(*a, **k): return None
    def get_card_remaining_text(): return ""
    CARD_FILE = CARD_API_BASE = CARD_VERIFY_URL = ""
