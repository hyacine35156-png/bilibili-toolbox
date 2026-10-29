#!/usr/bin/env python3
"""v4.4.5: 获取任务actid改成一开始就获取，而不是最后5秒提前查询"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 第一处：单个定时任务的等待逻辑（约1596行）
# 把"最后5秒提前查询"改成"一开始就获取"
# ============================================================
old_first = '''            # 精确等待到目标时间，最后5秒提前查询任务信息
            task_info = {
                "act_id": "",
                "act_name": task_name,
                "task_name": task_name,
                "reward_info": {"award_name": task.get("award", "")},
            }
            task_info_fetched = False
            while not stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if remaining <= 0:
                    break
                # 最后5秒提前查询任务信息，到点后可以立即领取
                if remaining <= 5 and not task_info_fetched:
                    task_info_fetched = True
                    try:
                        cookies = cookies_from_account(accounts[0])
                        info, msg = get_mission_info(task["task_id"], cookies)
                        if info:
                            task_info = info
                            self.log(f"  ✓ 提前获取任务信息")
                        else:
                            self.log(f"  ⚠ 提前查询任务信息失败: {msg}，使用备用数据")
                    except Exception as e:
                        self.log(f"  ⚠ 提前查询任务信息异常: {e}，使用备用数据")
                if remaining > 3:
                    time.sleep(0.2)
                else:
                    time.sleep(0.005)'''

new_first = '''            # 一开始就获取任务信息（actid），到点后可以立即领取
            task_info = {
                "act_id": "",
                "act_name": task_name,
                "task_name": task_name,
                "reward_info": {"award_name": task.get("award", "")},
            }
            try:
                cookies = cookies_from_account(accounts[0])
                info, msg = get_mission_info(task["task_id"], cookies)
                if info:
                    task_info = info
                    act_id = info.get("act_id", "")
                    self.log(f"  ✓ 已获取任务信息，act_id: {act_id}")
                else:
                    self.log(f"  ⚠ 获取任务信息失败: {msg}，使用备用数据")
            except Exception as e:
                self.log(f"  ⚠ 获取任务信息异常: {e}，使用备用数据")

            # 精确等待到目标时间
            while not stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if remaining <= 0:
                    break
                if remaining > 3:
                    time.sleep(0.2)
                else:
                    time.sleep(0.005)'''

if old_first in content:
    content = content.replace(old_first, new_first)
    print("1. 第一处：定时任务actid改成一开始就获取")
else:
    print("1. 未找到第一处代码")

# ============================================================
# 第二处：另一个定时领取逻辑（约2274行）
# 把"最后5秒提前查询"改成"一开始就获取"
# ============================================================
old_second = '''        # 精确等待到目标时间
        last_log = 0
        task_info = self.build_task_info_from_task(task)  # 备用任务信息
        task_info_fetched = False
        while self.running:
            remaining = target_timestamp - time.time()
            if remaining <= 0:
                break
            # 每10秒输出一次剩余时间
            if int(remaining) != last_log and int(remaining) % 10 == 0 and int(remaining) > 0:
                last_log = int(remaining)
                self.log(f"  还剩 {int(remaining)} 秒...")
            # 最后5秒提前查询任务信息，到点后可以立即领取
            if remaining <= 5 and not task_info_fetched:
                task_info_fetched = True
                try:
                    first_account = accounts[0]
                    cookies = cookies_from_account(first_account)
                    info, msg = get_mission_info(task["task_id"], cookies)
                    if info:
                        task_info = info
                        act_id = info.get('act_id', '')
                        self.log(f"  ✓ 提前获取任务信息，act_id: {act_id}")
                    else:
                        self.log(f"  ⚠ 提前查询任务信息失败: {msg}，使用备用数据")
                except Exception as e:
                    self.log(f"  ⚠ 提前查询任务信息异常: {e}，使用备用数据")
            # 最后3秒用更短的睡眠间隔提高精度
            if remaining > 3:
                time.sleep(0.2)
            else:
                time.sleep(0.005)'''

new_second = '''        # 一开始就获取任务信息（actid），到点后可以立即领取
        task_info = self.build_task_info_from_task(task)  # 备用任务信息
        try:
            first_account = accounts[0]
            cookies = cookies_from_account(first_account)
            info, msg = get_mission_info(task["task_id"], cookies)
            if info:
                task_info = info
                act_id = info.get('act_id', '')
                self.log(f"  ✓ 已获取任务信息，act_id: {act_id}")
            else:
                self.log(f"  ⚠ 获取任务信息失败: {msg}，使用备用数据")
        except Exception as e:
            self.log(f"  ⚠ 获取任务信息异常: {e}，使用备用数据")

        # 精确等待到目标时间
        last_log = 0
        while self.running:
            remaining = target_timestamp - time.time()
            if remaining <= 0:
                break
            # 每10秒输出一次剩余时间
            if int(remaining) != last_log and int(remaining) % 10 == 0 and int(remaining) > 0:
                last_log = int(remaining)
                self.log(f"  还剩 {int(remaining)} 秒...")
            # 最后3秒用更短的睡眠间隔提高精度
            if remaining > 3:
                time.sleep(0.2)
            else:
                time.sleep(0.005)'''

if old_second in content:
    content = content.replace(old_second, new_second)
    print("2. 第二处：定时领取actid改成一开始就获取")
else:
    print("2. 未找到第二处代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.4"', 'APP_VERSION = "v4.4.5"')
print("3. 版本号已更新到 v4.4.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
