# -*- coding: utf-8 -*-
file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 把预热时间从5秒改回3秒
old_prewarm_time = '''            # ===== 阶段2: 等待到目标时间前5秒，连接预热（避免网络波动导致错过目标时间）=====
            prewarm_time = target_timestamp - 5'''

new_prewarm_time = '''            # ===== 阶段2: 等待到目标时间前3秒，连接预热 =====
            prewarm_time = target_timestamp - 3'''

if old_prewarm_time in content:
    content = content.replace(old_prewarm_time, new_prewarm_time)
    print("1. 已把预热时间从5秒改回3秒")
else:
    print("1. 未找到预热时间代码")

# 2. 更新日志描述
old_log = '''            self.nm_log("[连接预热] 提前5秒建立TCP连接（act_id已在添加任务时获取）...")'''

new_log = '''            self.nm_log("[连接预热] 提前3秒建立TCP连接（act_id已在添加任务时获取）...")'''

if old_log in content:
    content = content.replace(old_log, new_log)
    print("2. 已更新连接预热日志描述")
else:
    print("2. 未找到连接预热日志代码")

# 3. 去掉RTT测量，简化预热流程
old_prewarm = '''            sessions = {}
            task_infos = {}
            prewarm_rtts = []
            for task in sorted(group["tasks"], key=lambda t: t.get("priority", 99)):
                account = self.account_mgr.get_account(task["account_name"])
                if not account:
                    self.nm_log(f"  ⚠ 账户不存在: {task['account_name']}")
                    continue
                session = requests.Session()
                session.headers.update(HEADERS)
                sessions[task["task_id"]] = session
                # 轻量连接建立：访问B站首页，只建立TCP+TLS连接，不调用任务API
                try:
                    _t0 = time.time()
                    session.get("https://www.bilibili.com", timeout=5)
                    _rtt = (time.time() - _t0) * 1000
                    prewarm_rtts.append(_rtt)
                    # 【重要】清除预热时自动获取的cookie（buvid3/b_nut等），
                    # 避免与用户cookie合并导致B站反作弊返回[-351]错误
                    session.cookies.clear()
                    # 直接使用任务配置中保存的act_id构造task_info
                    task_info = self.build_task_info_from_task(task)
                    task_infos[task["task_id"]] = task_info
                    self.nm_log(f"  ✓ {task['name']}: 连接已建立, RTT={_rtt:.0f}ms, act_id={task_info.get('act_id', '')}")
                except Exception as e:
                    task_info = self.build_task_info_from_task(task)
                    task_infos[task["task_id"]] = task_info
                    self.nm_log(f"  ⚠ {task['name']}: 连接预热异常: {e}, 使用保存的act_id={task_info.get('act_id', '')}")
                # 轻量请求间隔300ms
                time.sleep(0.3)'''

new_prewarm = '''            sessions = {}
            task_infos = {}
            for task in sorted(group["tasks"], key=lambda t: t.get("priority", 99)):
                account = self.account_mgr.get_account(task["account_name"])
                if not account:
                    self.nm_log(f"  ⚠ 账户不存在: {task['account_name']}")
                    continue
                session = requests.Session()
                session.headers.update(HEADERS)
                sessions[task["task_id"]] = session
                # 轻量连接建立：访问B站首页，只建立TCP+TLS连接，不调用任务API
                try:
                    session.get("https://www.bilibili.com", timeout=5)
                    # 【重要】清除预热时自动获取的cookie（buvid3/b_nut等），
                    # 避免与用户cookie合并导致B站反作弊返回[-351]错误
                    session.cookies.clear()
                    # 直接使用任务配置中保存的act_id构造task_info
                    task_info = self.build_task_info_from_task(task)
                    task_infos[task["task_id"]] = task_info
                    self.nm_log(f"  ✓ {task['name']}: 连接已建立, act_id={task_info.get('act_id', '')}")
                except Exception as e:
                    task_info = self.build_task_info_from_task(task)
                    task_infos[task["task_id"]] = task_info
                    self.nm_log(f"  ⚠ {task['name']}: 连接预热异常: {e}, 使用保存的act_id={task_info.get('act_id', '')}")
                # 轻量请求间隔300ms
                time.sleep(0.3)'''

if old_prewarm in content:
    content = content.replace(old_prewarm, new_prewarm)
    print("3. 已去掉RTT测量，简化预热流程")
else:
    print("3. 未找到预热代码")

# 4. 去掉动态提前量计算中的RTT相关代码
old_advance = '''            # 计算固定提前量：使用固定值，确保请求延后到达目标时间
            # 优化说明：预热RTT包含TCP+TLS握手时间（约500ms），与实际请求耗时（100-150ms）差异很大
            # 使用预热RTT/2计算会导致提前量偏大，请求提前到达，第一次请求无效（返回"未到领取时间"）
            # 优化策略：使用固定提前量50ms，请求会在目标时间后50-100ms到达，确保第一次请求有效
            if prewarm_rtts:
                avg_rtt = sum(prewarm_rtts) / len(prewarm_rtts)
            else:
                avg_rtt = 0
            dynamic_advance = 400  # 固定提前量400ms，高峰期延迟高，确保延后到达
            self.nm_log(f"[固定提前量] {dynamic_advance:.0f}ms (预热RTT={avg_rtt:.0f}ms参考, 确保延后到达)")'''

new_advance = '''            # 计算固定提前量：使用固定值，确保请求延后到达目标时间
            dynamic_advance = 400  # 固定提前量400ms，高峰期延迟高，确保延后到达
            self.nm_log(f"[固定提前量] {dynamic_advance:.0f}ms (确保延后到达)")'''

if old_advance in content:
    content = content.replace(old_advance, new_advance)
    print("4. 已去掉提前量计算中的RTT相关代码")
else:
    print("4. 未找到提前量计算代码")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n所有修改完成！")
