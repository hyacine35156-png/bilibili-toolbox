# -*- coding: utf-8 -*-
"""移除所有自动提取兑换码的逻辑，只保留兑换码页面的导入功能"""

FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 移除手动领取路径的兑换码提取逻辑
old_manual = '''            self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
            # 保存兑换码（从领取记录API获取，因为CdKeyV2类型的兑换码不在领取API返回中）
            try:
                # 获取活动ID
                activity_id = ""
                info, _ = get_mission_info(task["task_id"], cookies_from_account(acc))
                if info:
                    activity_id = info.get("act_id", "")
                if not activity_id:
                    activity_id = VERSION_DEFAULT_ACT_ID.get(task.get("version", ""), "")

                if activity_id:
                    self.log(f"  ⏳ 正在查询领取记录获取兑换码...")
                    record_data, record_msg = get_award_record(activity_id, cookies_from_account(acc))
                    if record_data and record_data.get("list"):
                        self.log(f"  ✓ 查询到 {len(record_data['list'])} 条领取记录")
                        # 遍历每条领取记录，分别保存兑换码（使用正确的任务名称：活动名称+奖励名称）
                        total_saved = 0
                        total_skipped = 0
                        for record_item in record_data["list"]:
                            # 构建任务名称：活动名称(简化) + 奖励名称
                            activity_name = record_item.get("activity_name", "")
                            award_name = record_item.get("award_name", "未知奖励")
                            
                            # 简化活动名称：去掉"版本激励计划"等后缀
                            if activity_name:
                                activity_name = re.sub(r'版本激励计划.*$', '', activity_name)
                                activity_name = re.sub(r'激励计划.*$', '', activity_name)
                                activity_name = activity_name.strip()
                            
                            if activity_name:
                                record_task_name = f"{activity_name} {award_name}"
                            else:
                                record_task_name = award_name
                            
                            # 保存单条记录的兑换码
                            ok_save, save_msg = save_redeem_code(
                                record_task_name, acc.get('name', '未知'),
                                record_item,
                                task_period="",
                                task_type=record_item.get("type", "")
                            )
                            if ok_save:
                                total_saved += 1
                            else:
                                total_skipped += 1
                        
                        if total_saved > 0:
                            self.log(f"  🎁 已保存 {total_saved} 个兑换码，跳过 {total_skipped} 个（重复），可在「兑换码」页面查看")
                        else:
                            self.log(f"  ⚠ 兑换码已全部存在（跳过 {total_skipped} 个重复）")
                    else:
                        self.log(f"  ⚠ 领取记录为空或查询失败: {record_msg}")
                        self.log(f"  💡 提示: CdKeyV2类型的兑换码可能需要等待一段时间后才会出现在领取记录中")
                else:
                    self.log(f"  ⚠ 无法获取活动ID，跳过兑换码查询")
            except Exception as _e:
                self.log(f"  ⚠ 兑换码查询异常: {_e}")
            self.log(f"  账户：{acc['name']}")'''

new_manual = '''            self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
            self.log(f"  账户：{acc['name']}")
            self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")'''

if old_manual in content:
    content = content.replace(old_manual, new_manual, 1)
    print("✓ 已移除手动领取路径的兑换码提取逻辑")
else:
    print("✗ 未找到手动领取路径代码")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ 修改完成")
