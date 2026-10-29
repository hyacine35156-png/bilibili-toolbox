#!/usr/bin/env python3
"""v5.0.0: 修复送礼[-401]未登录(sessdata大小写) + 防重复启动"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 修复所有小写sessdata -> 大写SESSDATA（送礼相关）
# ============================================================
count = content.count('account.get("sessdata", "")')
content = content.replace('account.get("sessdata", "")', 'account.get("SESSDATA", "")')
print(f"1. 已修复 {count} 处 sessdata 大小写问题")

# ============================================================
# 2. start_gift添加防重复调用检查
# ============================================================
old_start_check = '''    def start_gift(self):
        """开始送礼"""
        room_id = self.gift_room_combo.get().strip()'''

new_start_check = '''    def start_gift(self):
        """开始送礼"""
        # 防重复调用
        if self.gift_running:
            self.log("⚠ 送礼任务已在运行中，请勿重复点击")
            return
        room_id = self.gift_room_combo.get().strip()'''

if old_start_check in content:
    content = content.replace(old_start_check, new_start_check)
    print("2. start_gift已添加防重复调用检查")
else:
    print("2. 未找到start_gift开头")

# ============================================================
# 3. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.9"', 'APP_VERSION = "v5.0.0"')
print("3. 版本号: v4.9.9 -> v5.0.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
