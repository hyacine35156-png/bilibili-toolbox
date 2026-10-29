# -*- coding: utf-8 -*-
"""旧版定时领取任务：定时任务列表与工作线程。

以 Mixin 形式提供，由 RushRewardFrame 继承。
"""

import json, random, threading, time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox

from config import COLORS, BASE_DIR
from tasks_config import ALL_TASKS
from widgets import DarkButton
from storage import atomic_write_json, safe_load_json
from bili_api import cookies_from_account, get_mission_info, parse_stock_info, receive_reward, verify_login
from widgets import custom_askyesno


class ScheduledMixin:
    """旧版定时领取子系统（12 个方法）。"""


    def load_scheduled_tasks(self):
        """加载定时任务列表，自动过滤掉已从ALL_TASKS中删除的任务"""
        tasks_file = BASE_DIR / "scheduled_tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                # 过滤掉已从ALL_TASKS中删除的任务
                valid_task_ids = {t["task_id"] for t in ALL_TASKS}
                original_count = len(tasks)
                tasks = [t for t in tasks if t.get("task_id") in valid_task_ids]
                # 重置所有任务状态为等待中
                for task in tasks:
                    task["status"] = "等待中"
                # 如果有任务被清理，保存清理后的结果
                if len(tasks) != original_count:
                    try:
                        atomic_write_json(tasks_file, tasks)
                    except Exception:
                        pass
                return tasks
            except Exception:
                pass
        return []

    def save_scheduled_tasks(self):
        """保存定时任务列表"""
        try:
            tasks_file = BASE_DIR / "scheduled_tasks.json"
            # 保存时不包含线程对象
            tasks_to_save = []
            for task in self.scheduled_tasks:
                task_copy = {k: v for k, v in task.items() if k != "thread"}
                tasks_to_save.append(task_copy)
            atomic_write_json(tasks_file, tasks_to_save)
        except Exception:
            pass
    # ========== 定时任务相关方法 ==========
    def refresh_scheduled_task_list(self):
        """刷新定时任务列表显示"""
        # 清空现有内容
        for widget in self.schedule_list_frame.winfo_children():
            widget.destroy()

        if not self.scheduled_tasks:
            tk.Label(self.schedule_list_frame, text="暂无定时任务，设置好参数后点击「+ 添加当前设置」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(pady=10)
            return

        for idx, task in enumerate(self.scheduled_tasks):
            row_frame = tk.Frame(self.schedule_list_frame, bg=COLORS["bg_card"])
            row_frame.pack(fill=tk.X, pady=3)

            # 交替背景色
            if idx % 2 == 0:
                row_frame.configure(bg=COLORS["bg_input"])

            # 用固定像素宽度的Frame容器，确保和表头严格对齐
            col_widths = [550, 140, 300, 160, 110, 240]

            # 任务名称（加版本信息括号，长文字自动换行）
            task_name = task.get("task_name", "未知任务")
            version = task.get("version", "")
            period = task.get("period", "")
            if version or period:
                version_info = f"{version}{period}" if version and period else (version or period)
                name_text = f"{task_name}（{version_info}）"
            else:
                name_text = task_name
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=60)
            col1.pack(side=tk.LEFT, padx=(25, 0))
            col1.pack_propagate(False)
            tk.Label(col1, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), anchor=tk.W, wraplength=col_widths[0]-20, justify=tk.LEFT).pack(side=tk.LEFT, padx=8, pady=8)

            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=60)
            col2.pack(side=tk.LEFT, padx=(18, 0))
            col2.pack_propagate(False)
            tk.Label(col2, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=60)
            col3.pack(side=tk.LEFT, padx=(18, 0))
            col3.pack_propagate(False)
            tk.Label(col3, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:10] if accounts else "未设置"
            col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=60)
            col4.pack(side=tk.LEFT, padx=(35, 0))
            col4.pack_propagate(False)
            tk.Label(col4, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=60)
            col5.pack(side=tk.LEFT, padx=(18, 0))
            col5.pack_propagate(False)
            tk.Label(col5, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 操作按钮
            col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=60)
            col6.pack(side=tk.LEFT, padx=(18, 0))
            col6.pack_propagate(False)
            btn_frame = tk.Frame(col6, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=4, pady=14)

            task_id = task.get("id")
            if status in ["等待中", "已完成", "已领取", "失败"]:
                DarkButton(btn_frame, "开始", command=lambda tid=task_id: self.start_scheduled_task(tid),
                           width=75, height=28, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 4))
            else:
                DarkButton(btn_frame, "停止", command=lambda tid=task_id: self.stop_scheduled_task(tid),
                           width=75, height=28, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 4))

            DarkButton(btn_frame, "删除", command=lambda tid=task_id: self.delete_scheduled_task(tid),
                       width=75, height=28, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

    def add_scheduled_task(self):
        """添加当前设置为定时任务"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return

        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return

        try:
            duration = float(self.duration_entry.get())
            interval_mode = self.interval_mode.get()
            if interval_mode == "fixed":
                fixed_interval = float(self.fixed_interval_entry.get())
                min_interval = fixed_interval
                max_interval = fixed_interval
            else:
                min_interval = float(self.min_interval_entry.get())
                max_interval = float(self.max_interval_entry.get())
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval
            h = int(self.schedule_hour_var.get().strip())
            m = int(self.schedule_minute_var.get().strip())
            s = int(self.schedule_second_var.get().strip())
            if h < 0 or h > 23 or m < 0 or m > 59 or s < 0 or s > 59:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的时间参数")
            return

        # 生成唯一ID
        import uuid
        task_id = str(uuid.uuid4())[:8]

        scheduled_task = {
            "id": task_id,
            "task_id": task["task_id"],
            "task_name": task["name"],
            "award": task.get("award", ""),
            "version": task.get("version", ""),
            "period": task.get("period", ""),
            "task_type": task.get("type", ""),
            "schedule_hour": f"{h:02d}",
            "schedule_minute": f"{m:02d}",
            "schedule_second": f"{s:02d}",
            "duration": str(duration),
            "interval_mode": interval_mode,
            "fixed_interval": str(fixed_interval) if interval_mode == "fixed" else "",
            "min_interval": str(min_interval),
            "max_interval": str(max_interval),
            "account_names": [acc["name"] for acc in accounts],
            "status": "等待中",
        }

        self.scheduled_tasks.append(scheduled_task)
        self.save_scheduled_tasks()
        self.refresh_scheduled_task_list()
        self.log(f"✓ 已添加定时任务: {task['name']} @ {h:02d}:{m:02d}:{s:02d}")

    def start_scheduled_task(self, task_id):
        """启动单个定时任务"""
        task = None
        for t in self.scheduled_tasks:
            if t["id"] == task_id:
                task = t
                break

        if not task:
            return

        if task.get("status") == "运行中":
            return

        # 获取账户对象
        accounts = []
        for acc_name in task.get("account_names", []):
            for acc in self.account_mgr.accounts:
                if acc["name"] == acc_name:
                    accounts.append(acc)
                    break

        if not accounts:
            self.log(f"✗ 定时任务「{task['task_name']}」启动失败：未找到账户")
            return

        # 设置停止标志
        stop_flag = {"stop": False}
        self.scheduled_task_stop_flags[task_id] = stop_flag

        # 更新状态
        task["status"] = "运行中"
        self.refresh_scheduled_task_list()

        # 启动线程
        thread = threading.Thread(
            target=self.scheduled_task_worker,
            args=(task, accounts, stop_flag),
            daemon=True
        )
        self.scheduled_task_threads[task_id] = thread
        thread.start()

        self.log(f"▶ 定时任务已启动: {task['task_name']} @ {task['schedule_hour']}:{task['schedule_minute']}:{task['schedule_second']}")

    def stop_scheduled_task(self, task_id):
        """停止单个定时任务"""
        if task_id in self.scheduled_task_stop_flags:
            self.scheduled_task_stop_flags[task_id]["stop"] = True

        for task in self.scheduled_tasks:
            if task["id"] == task_id:
                task["status"] = "已停止"
                break

        self.refresh_scheduled_task_list()
        self.log(f"■ 定时任务已停止")

    def delete_scheduled_task(self, task_id):
        """删除定时任务"""
        # 先停止
        if task_id in self.scheduled_task_stop_flags:
            self.scheduled_task_stop_flags[task_id]["stop"] = True

        # 从列表中删除
        self.scheduled_tasks = [t for t in self.scheduled_tasks if t["id"] != task_id]

        # 清理线程和标志
        self.scheduled_task_threads.pop(task_id, None)
        self.scheduled_task_stop_flags.pop(task_id, None)

        self.save_scheduled_tasks()
        self.refresh_scheduled_task_list()
        self.log(f"✓ 定时任务已删除")

    def start_all_scheduled_tasks(self):
        """启动所有定时任务（每隔5秒启动一个，避免请求频率过高）"""
        tasks_to_start = []
        for task in self.scheduled_tasks:
            if task.get("status") != "运行中":
                tasks_to_start.append(task["id"])

        if not tasks_to_start:
            self.log("⚠ 没有需要启动的定时任务")
            return

        self.log(f"▶ 即将循序启动 {len(tasks_to_start)} 个定时任务（每个间隔5秒）")

        # 用后台线程循序启动
        def _start_sequentially():
            for i, task_id in enumerate(tasks_to_start):
                if i > 0:
                    self.log(f"  ⏳ 等待5秒后启动下一个任务...")
                    time.sleep(5)
                self.start_scheduled_task(task_id)
            self.log(f"✓ 全部 {len(tasks_to_start)} 个定时任务已启动完成")

        threading.Thread(target=_start_sequentially, daemon=True).start()

    def stop_all_scheduled_tasks(self):
        """停止所有定时任务"""
        for task_id in list(self.scheduled_task_stop_flags.keys()):
            self.scheduled_task_stop_flags[task_id]["stop"] = True

        for task in self.scheduled_tasks:
            if task.get("status") == "运行中":
                task["status"] = "已停止"

        self.refresh_scheduled_task_list()
        self.log(f"■ 已停止所有定时任务")

    def scheduled_task_worker(self, task, accounts, stop_flag):
        """定时任务工作线程"""
        task_id = task["id"]
        task_name = task["task_name"]

        try:
            # 计算目标时间
            h = int(task["schedule_hour"])
            m = int(task["schedule_minute"])
            s = int(task["schedule_second"])
            target_seconds = h * 3600 + m * 60 + s

            now = time.localtime()
            current_seconds = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec
            wait_seconds = target_seconds - current_seconds
            if wait_seconds < 0:
                wait_seconds += 86400  # 等到明天

            target_timestamp = time.time() + wait_seconds
            self.log(f"⏰ 定时任务「{task_name}」等待 {wait_seconds:.0f} 秒后领取")

            # 一开始就获取任务信息（actid），到点后可以立即领取
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
                    time.sleep(0.005)

            if stop_flag["stop"]:
                self.log(f"■ 定时任务「{task_name}」已取消")
                return

            # 到点了，开始领取（任务信息已提前查询好）
            self.log(f"★ 定时任务「{task_name}」到点！开始领取")

            duration = float(task["duration"])
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                fixed_interval = float(task.get("fixed_interval", 699))
                min_interval = fixed_interval / 1000.0
                max_interval = fixed_interval / 1000.0
            else:
                min_interval = float(task.get("min_interval", 600)) / 1000.0
                max_interval = float(task.get("max_interval", 800)) / 1000.0
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval

            # 领取循环
            start_time = time.time()
            attempt = 0
            success = False
            acc_index = 0
            stock_empty_count = 0  # 连续检测到库存为空的次数
            max_stock_seen = 0  # 见过的最大库存（用于判断库存是否曾经>0）
            last_stock_check = 0  # 上次查询库存的时间

            # 领取开始前先查询一次库存，记录初始库存
            try:
                first_account = accounts[0]
                cookies = cookies_from_account(first_account)
                info, _ = get_mission_info(task["task_id"], cookies)
                if info:
                    day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                    initial_stock = day_s
                    if initial_stock > max_stock_seen:
                        max_stock_seen = initial_stock
                    self.log(f"  初始库存: 今日剩余={day_s}%, 剩余总量={total_s}%")
            except Exception:
                pass

            while not stop_flag["stop"] and (time.time() - start_time) < duration and not success:
                account = accounts[acc_index % len(accounts)]
                acc_index += 1
                attempt += 1

                # 每隔5次尝试或每隔5秒查询一次库存，跟踪库存变化
                current_time = time.time()
                if attempt % 5 == 1 or (current_time - last_stock_check) > 5:
                    last_stock_check = current_time
                    try:
                        cookies = cookies_from_account(account)
                        info, _ = get_mission_info(task["task_id"], cookies)
                        if info:
                            day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                            current_stock = day_s
                            if current_stock > max_stock_seen:
                                max_stock_seen = current_stock
                    except Exception:
                        pass

                try:
                    ok, msg = self.do_receive_fast(task, task_info, account, None)
                except Exception as e:
                    ok, msg = False, f"异常: {e}"

                if ok:
                    success = True
                    if "已领取" in msg:
                        self.log(f"✓ 定时任务「{task_name}」已领取（第{attempt}次）")
                        for t in self.scheduled_tasks:
                            if t["id"] == task_id:
                                t["status"] = "已领取"
                                break
                    else:
                        self.log(f"🎉 定时任务「{task_name}」领取成功！（第{attempt}次，账户：{account['name']}）")
                        self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                        for t in self.scheduled_tasks:
                            if t["id"] == task_id:
                                t["status"] = "已完成"
                                break
                    break
                else:
                    self.log(f"  第{attempt}次: {msg} ({account['name']})")

                # 检测奖励是否已结束（202129），直接停止
                if "202129" in msg or "奖励领取已结束" in msg:
                    self.log(f"  ⚠ 奖励领取已结束，自动停止领取")
                    break

                # 检测库存是否为空（错误码75255或消息包含"库存已经使用完"）
                if "库存已经使用完" in msg or "75255" in msg:
                    if max_stock_seen > 0:
                        # 曾经见过库存>0，现在掉到0，说明确实抢完了，再抢一次后停止
                        stock_empty_count += 1
                        if stock_empty_count == 1:
                            self.log(f"  ⚠ 库存曾有{max_stock_seen}%现已为空，将再尝试一次后停止")
                        elif stock_empty_count >= 2:
                            self.log(f"  ⚠ 库存确认为空，自动停止领取")
                            break
                    else:
                        # 一直没见过库存>0，可能是还没到发放时间，继续抢不停止
                        stock_empty_count = 0
                        if attempt % 5 == 0:
                            self.log(f"  ⚠ 库存持续为空（尚未见发放），继续等待抢码")
                else:
                    stock_empty_count = 0  # 重置计数

                # 随机等待间隔（模拟人类点击）
                import random
                random_interval = random.uniform(min_interval, max_interval)
                self.log(f"  第{attempt}次后等待 {random_interval*1000:.0f}ms")
                next_attempt = time.time() + random_interval
                while time.time() < next_attempt and not stop_flag["stop"]:
                    time.sleep(0.001)

            elapsed = time.time() - start_time
            if not success and not stop_flag["stop"]:
                self.log(f"✗ 定时任务「{task_name}」领取结束，共尝试 {attempt} 次，未成功")
                for t in self.scheduled_tasks:
                    if t["id"] == task_id:
                        t["status"] = "失败"
                        break
            elif stop_flag["stop"]:
                self.log(f"■ 定时任务「{task_name}」已停止")
                for t in self.scheduled_tasks:
                    if t["id"] == task_id:
                        t["status"] = "已停止"
                        break

        except Exception as e:
            self.log(f"✗ 定时任务「{task_name}」异常: {e}")
            for t in self.scheduled_tasks:
                if t["id"] == task_id:
                    t["status"] = "失败"
                    break

        # 刷新UI
        self.after(0, self.refresh_scheduled_task_list)
        # 清理
        self.scheduled_task_threads.pop(task_id, None)
        self.scheduled_task_stop_flags.pop(task_id, None)

    def schedule_receive(self):
        """定时领取：在指定时间开始，持续领取指定时长"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return

        # 解析参数
        try:
            duration = float(self.duration_entry.get())
            interval_mode = self.interval_mode.get()
            if interval_mode == "fixed":
                fixed_interval = float(self.fixed_interval_entry.get()) / 1000.0
                min_interval = fixed_interval
                max_interval = fixed_interval
                if duration <= 0 or fixed_interval <= 0:
                    raise ValueError
            else:
                min_interval = float(self.min_interval_entry.get()) / 1000.0
                max_interval = float(self.max_interval_entry.get()) / 1000.0
                if duration <= 0 or min_interval <= 0 or max_interval <= 0:
                    raise ValueError
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的领取时长（秒）和间隔（毫秒）")
            return

        try:
            h = int(self.schedule_hour_var.get().strip())
            m = int(self.schedule_minute_var.get().strip())
            s = int(self.schedule_second_var.get().strip())
            if h < 0 or h > 23 or m < 0 or m > 59 or s < 0 or s > 59:
                raise ValueError
            target_seconds = h * 3600 + m * 60 + s
        except ValueError:
            messagebox.showwarning("提示", "定时时间格式错误，时(0-23) 分(0-59) 秒(0-59)")
            return

        # 验证账户
        valid_accounts = []
        for acc in accounts:
            ok, msg = verify_login(self.account_mgr.get_cookie_string(acc["name"]))
            if ok:
                valid_accounts.append(acc)
            else:
                self.log(f"⚠ 账户「{acc['name']}」登录失效，已跳过")
        if not valid_accounts:
            messagebox.showerror("登录失效", "所有账户登录验证都失败了")
            return

        self.running = True
        self.manual_receive_btn.set_state("disabled")
        self.start_receive_now_btn.set_state("disabled")
        self.schedule_receive_btn.set_state("disabled")
        self.start_rush_btn.set_state("disabled")
        self.stop_rush_btn.set_state("normal")
        self.rush_status.config(text="● 等待定时", fg=COLORS["warning"])

        self.log("=" * 40)
        self.log(f"定时领取已设置 | 目标时间: {h:02d}:{m:02d}:{s:02d}")
        self.log(f"任务: [{task['period']}][{task['type']}] {task['name']} => {task['award']}")
        if interval_mode == "fixed":
            self.log(f"领取时长: {duration}秒 | 固定间隔: {min_interval*1000:.0f}毫秒")
        else:
            self.log(f"领取时长: {duration}秒 | 随机间隔: {min_interval*1000:.0f}~{max_interval*1000:.0f}毫秒")
        self.log(f"账户: {', '.join([a['name'] for a in valid_accounts])}")
        self.log("-" * 40)

        self.rush_thread = threading.Thread(
            target=self.schedule_receive_loop,
            args=(task, valid_accounts, target_seconds, duration, min_interval, max_interval),
            daemon=True
        )
        self.rush_thread.start()

    def schedule_receive_loop(self, task, accounts, target_seconds, duration, min_interval, max_interval):
        """定时领取循环：精确等待到目标时间，然后快速领取"""
        # 计算目标时间戳
        now = time.localtime()
        current_seconds = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec
        wait_seconds = target_seconds - current_seconds
        if wait_seconds < 0:
            wait_seconds += 86400  # 等到明天

        target_timestamp = time.time() + wait_seconds
        self.log(f"等待 {wait_seconds:.0f} 秒后开始领取（目标: {time.strftime('%H:%M:%S', time.localtime(target_timestamp))}）")

        # 一开始就获取任务信息（actid），到点后可以立即领取
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
                time.sleep(0.005)

        if not self.running:
            self.log("定时领取已取消")
            return

        # 到点了，立即开始领取（任务信息已提前查询好）
        actual_start = time.time()
        try:
            self.after(0, lambda: self.rush_status.config(text="● 领取中", fg=COLORS["success"]))
        except Exception:
            pass
        self.log(f"★ 到点！立即开始领取（延迟 {actual_start - target_timestamp:.3f} 秒）")
        if min_interval == max_interval:
            self.log(f"  持续 {duration} 秒，固定间隔 {min_interval*1000:.0f} 毫秒")
        else:
            self.log(f"  持续 {duration} 秒，随机间隔 {min_interval*1000:.0f}~{max_interval*1000:.0f} 毫秒")

        # 快速领取循环
        start_time = time.time()
        attempt = 0
        success = False
        acc_index = 0
        stock_empty_count = 0  # 连续检测到库存为空的次数
        max_stock_seen = 0  # 见过的最大库存（用于判断库存是否曾经>0）
        last_stock_check = 0  # 上次查询库存的时间

        # 从提前查询的任务信息中获取初始库存
        try:
            if task_info:
                day_s, total_s, _, _, _, _, _ = parse_stock_info(task_info)
                initial_stock = day_s
                if initial_stock > max_stock_seen:
                    max_stock_seen = initial_stock
                self.log(f"  初始库存: 今日剩余={day_s}%, 剩余总量={total_s}%")
        except Exception:
            pass

        while self.running and (time.time() - start_time) < duration and not success:
            account = accounts[acc_index % len(accounts)]
            acc_index += 1
            attempt += 1

            # 每隔5次尝试或每隔5秒查询一次库存，跟踪库存变化
            current_time = time.time()
            if attempt % 5 == 1 or (current_time - last_stock_check) > 5:
                last_stock_check = current_time
                try:
                    cookies = cookies_from_account(account)
                    info, _ = get_mission_info(task["task_id"], cookies)
                    if info:
                        day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                        current_stock = day_s
                        if current_stock > max_stock_seen:
                            max_stock_seen = current_stock
                except Exception:
                    pass

            try:
                ok, msg = self.do_receive_fast(task, task_info, account, None)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                self.log(f"  账户：{account['name']} | 第{attempt}次尝试")
                break
            else:
                self.log(f"  第{attempt}次: {msg} ({account['name']})")

            # 检测奖励是否已结束（202129），直接停止
            if "202129" in msg or "奖励领取已结束" in msg:
                self.log(f"  ⚠ 奖励领取已结束，自动停止领取")
                break

            # 检测库存是否为空（错误码75255或消息包含"库存已经使用完"）
            if "库存已经使用完" in msg or "75255" in msg:
                if max_stock_seen > 0:
                    # 曾经见过库存>0，现在掉到0，说明确实抢完了，再抢一次后停止
                    stock_empty_count += 1
                    if stock_empty_count == 1:
                        self.log(f"  ⚠ 库存曾有{max_stock_seen}%现已为空，将再尝试一次后停止")
                    elif stock_empty_count >= 2:
                        self.log(f"  ⚠ 库存确认为空，自动停止领取")
                        break
                else:
                    # 一直没见过库存>0，可能是还没到发放时间，继续抢不停止
                    stock_empty_count = 0
                    if attempt % 5 == 0:
                        self.log(f"  ⚠ 库存持续为空（尚未见发放），继续等待抢码")
            else:
                stock_empty_count = 0  # 重置计数

            # 随机等待间隔（模拟人类点击）
            import random
            random_interval = random.uniform(min_interval, max_interval)
            self.log(f"  第{attempt}次后等待 {random_interval*1000:.0f}ms")
            next_attempt_time = time.time() + random_interval
            while time.time() < next_attempt_time and self.running:
                time.sleep(0.001)

        elapsed = time.time() - start_time
        if not success:
            self.log(f"领取结束，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒，未成功")
        else:
            self.log(f"领取完成，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒")

        try:
            self.after(0, self.stop_rush)
        except Exception:
            pass
