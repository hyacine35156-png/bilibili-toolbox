# -*- coding: utf-8 -*-
"""移除最后一处抢码监控自动领取路径的兑换码保存逻辑"""

FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 移除最后一处抢码监控自动领取路径的兑换码保存逻辑
old_code = '''                        self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                        # 保存兑换码
                        try:
                            if _last_claim_data_global:
                                ok_save, save_msg = save_redeem_code(
                                    task['name'], self.current_account.get('name', '未知'),
                                    _last_claim_data_global,
                                    task_period=task.get('period', ''),
                                    task_type=task.get('type', '')
                                )
                                if ok_save:
                                    self.log(f"  🎁 {save_msg}，可在「兑换码」页面查看")
                        except:
                            pass'''

new_code = '''                        self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                        self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")'''

if old_code in content:
    content = content.replace(old_code, new_code, 1)
    print("✓ 已移除最后一处抢码监控自动领取路径的兑换码保存逻辑")
else:
    print("✗ 未找到代码")

# 验证
import re
remaining = re.findall(r'save_redeem_code\(', content)
print(f"\n剩余 save_redeem_code 调用数: {len(remaining)}")
print("  (应该是2处：1处函数定义 + 1处import_from_records调用)")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 修改完成")
