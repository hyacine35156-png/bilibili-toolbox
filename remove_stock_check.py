# -*- coding: utf-8 -*-
file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 删除连接预热阶段的库存查询代码，恢复原来的简单逻辑
old_prewarm = '''                    # 直接使用任务配置中保存的act_id构造task_info
                    task_info = self.build_task_info_from_task(task)
                    # 预热时同时查询任务状态（用于已领取的任务直接跳过）
                    try:
                        cookies_dict = {"SESSDATA": account.get("sessdata", ""), "bili_jct": account.get("bili_jct", "")}
                        mission_info = get_mission_info(task["task_id"], cookies_dict)
                        if mission_info:
                            task_info["mission_status"] = mission_info.get("status", -1)
                            task_info["mission_message"] = mission_info.get("message", "")
                            day_s, total_s, _, _, _, _, _ = parse_stock_info(mission_info)
                            task_info["total_stock"] = total_s
                            task_info["stock_checked"] = True
                    except Exception:
                        pass
                    task_infos[task["task_id"]] = task_info
                    status_text = ""
                    if task_info.get("stock_checked"):
                        ms = task_info.get("mission_status", -1)
                        if ms == 6:
                            status_text = ", 已领取"
                        elif ms == 2:
                            status_text = ", 每日上限"
                        else:
                            status_text = f", 库存={task_info.get('total_stock', '?')}%"
                    self.nm_log(f"  ✓ {task['name']}: 连接已建立, RTT={_rtt:.0f}ms, act_id={task_info.get('act_id', '')}{status_text}")'''

new_prewarm = '''                    # 直接使用任务配置中保存的act_id构造task_info
                    task_info = self.build_task_info_from_task(task)
                    task_infos[task["task_id"]] = task_info
                    self.nm_log(f"  ✓ {task['name']}: 连接已建立, RTT={_rtt:.0f}ms, act_id={task_info.get('act_id', '')}")'''

if old_prewarm in content:
    content = content.replace(old_prewarm, new_prewarm)
    print("1. 已删除连接预热阶段的库存查询代码")
else:
    print("1. 未找到连接预热代码")

# 2. 删除任务开始前的已领取检测代码
old_skip = '''                # 检测任务状态：只有已领取(status=6)才跳过，库存为0不跳过（可能是还没发放）
                task_info_for_check = task_infos.get(task["task_id"], {})
                if task_info_for_check.get("stock_checked") and task_info_for_check.get("mission_status") == 6:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] {task['name']}: 已领取，直接跳过")
                    continue

                self.nm_log(f"[优先级{task.get('priority', '?')}] 开始: {task['name']} => {task['award']} (窗口期{task.get('window_seconds', 15)}秒)")'''

new_skip = '''                self.nm_log(f"[优先级{task.get('priority', '?')}] 开始: {task['name']} => {task['award']} (窗口期{task.get('window_seconds', 15)}秒)")'''

if old_skip in content:
    content = content.replace(old_skip, new_skip)
    print("2. 已删除任务开始前的已领取检测代码")
else:
    print("2. 未找到已领取检测代码")

# 3. 把预热时间从5秒改回3秒
old_prewarm_time = '''            # ===== 阶段2: 等待到目标时间前5秒，连接预热（库存查询需要额外时间）=====
            prewarm_time = target_timestamp - 5'''

new_prewarm_time = '''            # ===== 阶段2: 等待到目标时间前3秒，连接预热 =====
            prewarm_time = target_timestamp - 3'''

if old_prewarm_time in content:
    content = content.replace(old_prewarm_time, new_prewarm_time)
    print("3. 已把预热时间从5秒改回3秒")
else:
    print("3. 未找到预热时间代码")

# 4. 更新日志描述
old_log = '''            self.nm_log("[连接预热] 提前5秒建立TCP连接并查询库存（act_id已在添加任务时获取）...")'''

new_log = '''            self.nm_log("[连接预热] 提前3秒建立TCP连接（act_id已在添加任务时获取）...")'''

if old_log in content:
    content = content.replace(old_log, new_log)
    print("4. 已更新连接预热日志描述")
else:
    print("4. 未找到连接预热日志代码")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n所有修改完成！")
