# -*- coding: utf-8 -*-
"""移除所有自动提取兑换码的逻辑（定时任务+抢码监控），只保留兑换码页面的导入功能"""

import re

FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 移除定时任务路径的兑换码保存逻辑
old_scheduled = '''                        self.log(f"🎉 定时任务「{task_name}」领取成功！（第{attempt}次，账户：{account['name']}）")
                        # 保存兑换码
                        try:
                            _data = msg if isinstance(msg, dict) else None
                            if _data is None:
                                _data = _last_claim_data_global
                            if _data:
                                ok_save, save_msg = save_redeem_code(
                                    task_name, account['name'], _data,
                                    task_period=task.get('period', ''),
                                    task_type=task.get('type', '')
                                )
                                if ok_save:
                                    self.log(f"  🎁 {save_msg}，可在「兑换码」页面查看")
                        except:
                            pass'''

new_scheduled = '''                        self.log(f"🎉 定时任务「{task_name}」领取成功！（第{attempt}次，账户：{account['name']}）")
                        self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")'''

if old_scheduled in content:
    content = content.replace(old_scheduled, new_scheduled, 1)
    print("✓ 已移除定时任务路径的兑换码保存逻辑")
else:
    print("✗ 未找到定时任务路径代码")

# 2. 移除抢码监控自动领取路径的兑换码保存逻辑（有3处类似代码）
# 使用正则表达式匹配所有类似的代码块
pattern = r'''                self\.log\(f"🎉 领取成功：\[\{task\['period'\]\}\]\[\{task\['type'\]\}\]\{task\['name'\]\} -> \{task\['award'\]\}"\)
                # 保存兑换码
                try:
                    if _last_claim_data_global:
                        ok_save, save_msg = save_redeem_code\(
                            task\['name'\], self\.current_account\.get\('name', '未知'\),
                            _last_claim_data_global,
                            task_period=task\.get\('period', ''\),
                            task_type=task\.get\('type', ''\)
                        \)
                        if ok_save:
                            self\.log\(f"  🎁 \{save_msg\}，可在「兑换码」页面查看"\)
                except:
                    pass'''

replacement = '''                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")'''

matches = re.findall(pattern, content)
print(f"\n找到 {len(matches)} 处抢码监控自动领取路径的兑换码保存逻辑")

content = re.sub(pattern, replacement, content)
print(f"✓ 已移除 {len(matches)} 处抢码监控自动领取路径的兑换码保存逻辑")

# 3. 验证：现在应该只有函数定义和import_from_records两处调用
remaining = re.findall(r'save_redeem_code\(', content)
print(f"\n剩余 save_redeem_code 调用数: {len(remaining)}")
print("  (应该是2处：1处函数定义 + 1处import_from_records调用)")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 修改完成")
