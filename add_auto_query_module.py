#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加任务状态自动查询模块"""

import re

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ===== 1. 修改表头，添加状态列 =====
old_header = 'headers = [("优先级", 5), ("任务名称", 28), ("奖励", 14), ("窗口期", 6), ("账户", 12), ("操作(↑↓✎×)", 22)]'
new_header = 'headers = [("状态", 4), ("优先级", 4), ("任务名称", 26), ("奖励", 12), ("窗口期", 5), ("账户", 10), ("操作(↑↓✎🔍×)", 22)]'
content = content.replace(old_header, new_header)

# ===== 2. 修改任务渲染，添加状态圆点和手动查询按钮 =====
# 找到任务渲染的起始位置
old_task_render_start = '''        for i, task in enumerate(tasks):
            row = tk.Frame(self.nm_task_list_frame, bg=COLORS["bg_card"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=str(task.get("priority", i+1)), bg=COLORS["bg_card"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"), width=5, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("name", "")[:30], bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 10), width=28, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("award", "")[:14], bg=COLORS["bg_card"],
                     fg=COLORS["success"], font=("微软雅黑", 10), width=14, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=f"{task.get('window_seconds', 15)}秒", bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=6, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("account_name", "")[:12], bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=5)'''

new_task_render_start = '''        for i, task in enumerate(tasks):
            row = tk.Frame(self.nm_task_list_frame, bg=COLORS["bg_card"])
            row.pack(fill=tk.X, pady=2)
            # 状态圆点
            status_color = task.get("status_color", "gray")
            color_map = {"green": "#2ecc71", "red": "#e74c3c", "gray": "#7f8c8d"}
            dot_color = color_map.get(status_color, "#7f8c8d")
            status_text = task.get("status_text", "未查询")
            tk.Label(row, text="●", bg=COLORS["bg_card"], fg=dot_color,
                     font=("微软雅黑", 12, "bold"), width=4, anchor=tk.W,
                     textvariable=None).pack(side=tk.LEFT, padx=5)
            # 给状态圆点添加tooltip
            try:
                from tkinter import ttk as _ttk
                status_label = row.winfo_children()[-1]
                ToolTip(status_label, status_text)
            except Exception:
                pass
            tk.Label(row, text=str(task.get("priority", i+1)), bg=COLORS["bg_card"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"), width=4, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("name", "")[:26], bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 10), width=26, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("award", "")[:12], bg=COLORS["bg_card"],
                     fg=COLORS["success"], font=("微软雅黑", 10), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=f"{task.get('window_seconds', 15)}秒", bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=5, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("account_name", "")[:10], bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=5)'''

content = content.replace(old_task_render_start, new_task_render_start)

# ===== 3. 在操作按钮中添加手动查询按钮（🔍）=====
old_buttons = '''            tk.Button(btn_frame, text="✎", bg="#3498db", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda t=task: self.nm_edit_task(t)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="×", bg="#c0392b", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_remove_task(tid)).pack(side=tk.LEFT, padx=1)'''

new_buttons = '''            tk.Button(btn_frame, text="✎", bg="#3498db", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda t=task: self.nm_edit_task(t)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="🔍", bg="#f39c12", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda t=task: self.nm_query_single_task(t)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="×", bg="#c0392b", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_remove_task(tid)).pack(side=tk.LEFT, padx=1)'''

content = content.replace(old_buttons, new_buttons)

# ===== 4. 在添加任务时，初始化状态字段并启动自动查询 =====
old_task_append = '''            group["tasks"].append({
                "task_id": task["task_id"],
                "name": task["name"],
                "award": task["award"],
                "period": task["period"],
                "type": task["type"],
                "version": task["version"],
                "account_name": account_name,
                "priority": priority,
                "window_seconds": window_seconds,
                "base_interval": base_interval,
                "act_id": act_id
            })
            self.save_rush_groups()
            self.nm_save_ui_settings()
            self.refresh_new_mode_task_list()
            self.nm_log(f"添加任务: {task['name']} (优先级{priority}, 窗口期{window_seconds}秒, 基础间隔{int(base_interval*1000)}ms)")'''

new_task_append = '''            new_task = {
                "task_id": task["task_id"],
                "name": task["name"],
                "award": task["award"],
                "period": task["period"],
                "type": task["type"],
                "version": task["version"],
                "account_name": account_name,
                "priority": priority,
                "window_seconds": window_seconds,
                "base_interval": base_interval,
                "act_id": act_id,
                "status_color": "gray",
                "status_text": "查询中...",
                "task_finished": None,
                "stock_available": None
            }
            group["tasks"].append(new_task)
            self.save_rush_groups()
            self.nm_save_ui_settings()
            self.refresh_new_mode_task_list()
            self.nm_log(f"添加任务: {task['name']} (优先级{priority}, 窗口期{window_seconds}秒, 基础间隔{int(base_interval*1000)}ms)")
            # 异步查询任务状态
            self.after(100, lambda t=new_task: self.nm_query_task_status_async(t))'''

content = content.replace(old_task_append, new_task_append)

# ===== 5. 在nm_edit_task方法前添加查询相关方法 =====
old_edit_method = '    def nm_edit_task(self, task):'
new_query_methods = '''    def nm_query_task_status_async(self, task):
        """异步查询任务状态（在后台线程中执行，避免阻塞UI）"""
        import threading
        def query_thread():
            try:
                result = self._do_query_task_status(task)
                # 回到主线程更新UI
                self.after(0, lambda: self._update_task_status(task, result))
            except Exception as e:
                self.after(0, lambda: self._update_task_status(task, {"error": str(e)}))
        threading.Thread(target=query_thread, daemon=True).start()

    def _do_query_task_status(self, task):
        """实际执行任务状态查询（在后台线程中调用）"""
        try:
            account_name = task.get("account_name", "")
            account = self.account_mgr.get_account(account_name)
            if not account:
                return {"error": "账户不存在"}
            cookies = cookies_from_account(account)
            info, msg = get_mission_info(task["task_id"], cookies)
            if not info:
                return {"error": msg or "查询失败"}
            task_finished = info.get("task_finished", False)
            stock_info = info.get("stock_info", {})
            # 库存总量判断：total_stock > 0 或 total_remain_num > 0
            total_stock = stock_info.get("total_stock", 0)
            total_remain = stock_info.get("total_remain_num", 0)
            stock_available = (total_stock > 0) or (total_remain > 0)
            # 也检查描述中的库存
            reward_info = info.get("reward_info", {})
            award_desc = reward_info.get("award_description", "")
            import re as _re
            desc_match = _re.search(r'共(\\d+)份', award_desc)
            if desc_match and total_stock == 0:
                stock_available = int(desc_match.group(1)) > 0
            status = info.get("status", -1)
            status_map = {0: "可领取", 1: "可领取", 2: "已领取/每日上限", 6: "已领取过", 7: "无资格", 11: "未到时间"}
            status_text = status_map.get(status, f"状态{status}")
            return {
                "task_finished": task_finished,
                "stock_available": stock_available,
                "total_stock": total_stock,
                "total_remain": total_remain,
                "status": status,
                "status_text": status_text
            }
        except Exception as e:
            return {"error": str(e)}

    def _update_task_status(self, task, result):
        """更新任务状态并刷新UI（在主线程中调用）"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        for t in group["tasks"]:
            if t.get("task_id") == task.get("task_id"):
                if "error" in result:
                    t["status_color"] = "gray"
                    t["status_text"] = f"查询失败: {result['error'][:20]}"
                    t["task_finished"] = None
                    t["stock_available"] = None
                else:
                    t["task_finished"] = result.get("task_finished")
                    t["stock_available"] = result.get("stock_available")
                    # 绿色：已完成 AND 库存>0
                    if result.get("task_finished") and result.get("stock_available"):
                        t["status_color"] = "green"
                        t["status_text"] = f"✓ 可抢 | 已完成 | 库存充足 | {result.get('status_text', '')}"
                    else:
                        t["status_color"] = "red"
                        reasons = []
                        if not result.get("task_finished"):
                            reasons.append("未完成")
                        if not result.get("stock_available"):
                            reasons.append("库存为0")
                        t["status_text"] = f"✗ 不可抢 | {','.join(reasons)} | {result.get('status_text', '')}"
                break
        self.save_rush_groups()
        self.refresh_new_mode_task_list()
        if "error" not in result:
            self.nm_log(f"[状态查询] {task.get('name', '')}: {task.get('status_text', '')}")

    def nm_query_single_task(self, task):
        """手动查询单个任务状态"""
        task["status_color"] = "gray"
        task["status_text"] = "查询中..."
        self.refresh_new_mode_task_list()
        self.nm_log(f"[手动查询] {task.get('name', '')}...")
        self.nm_query_task_status_async(task)

    def nm_query_all_tasks(self):
        """查询当前组内所有任务状态"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group or not group.get("tasks"):
            return
        self.nm_log(f"[批量查询] 开始查询 {len(group['tasks'])} 个任务状态...")
        for task in group["tasks"]:
            task["status_color"] = "gray"
            task["status_text"] = "查询中..."
        self.refresh_new_mode_task_list()
        # 逐个查询，间隔1秒避免风控
        import threading
        def query_all_thread():
            for task in group["tasks"]:
                try:
                    result = self._do_query_task_status(task)
                    self.after(0, lambda t=task, r=result: self._update_task_status(t, r))
                except Exception as e:
                    self.after(0, lambda t=task, err=str(e): self._update_task_status(t, {"error": err}))
                time.sleep(1.0)
            self.after(0, lambda: self.nm_log("[批量查询] 全部查询完成"))
        threading.Thread(target=query_all_thread, daemon=True).start()

    def nm_edit_task(self, task):'''

content = content.replace(old_edit_method, new_query_methods)

# ===== 6. 在组内任务列表标题旁添加"批量查询"按钮 =====
old_list_title = '''        tk.Label(list_card, text="组内任务（按优先级依次执行）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))'''

new_list_title = '''        list_title_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_title_frame.pack(fill=tk.X, padx=15, pady=(10, 8))
        tk.Label(list_title_frame, text="组内任务（按优先级依次执行）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        self.nm_query_all_btn = tk.Button(list_title_frame, text="🔍 批量查询状态", bg="#f39c12", fg="#ffffff",
                                          font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2",
                                          command=self.nm_query_all_tasks)
        self.nm_query_all_btn.pack(side=tk.RIGHT, ipadx=8, ipady=2)
        tk.Label(list_title_frame, text="●=可抢  ●=不可抢  ●=未查询", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=10)'''

content = content.replace(old_list_title, new_list_title)

# ===== 7. 编辑任务保存后也重新查询状态 =====
old_edit_save = '''            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"[编辑] 任务「{task.get('name', '')}」已更新: 窗口期={window_val}秒, 账户={account_var.get()}, 间隔={interval_ms}ms")
            edit_win.destroy()'''

new_edit_save = '''            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"[编辑] 任务「{task.get('name', '')}」已更新: 窗口期={window_val}秒, 账户={account_var.get()}, 间隔={interval_ms}ms")
            edit_win.destroy()
            # 编辑后重新查询状态
            for t in group.get("tasks", []):
                if t.get("task_id") == task.get("task_id"):
                    t["status_color"] = "gray"
                    t["status_text"] = "查询中..."
                    self.refresh_new_mode_task_list()
                    self.nm_query_task_status_async(t)
                    break'''

content = content.replace(old_edit_save, new_edit_save)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("自动查询模块添加完成！")
print("1. 任务列表添加状态列（绿色/红色/灰色圆点）")
print("2. 添加任务时自动查询状态")
print("3. 每个任务添加手动查询按钮🔍")
print("4. 组内任务列表添加批量查询按钮")
print("5. 编辑任务后自动重新查询")
print("6. 绿色=已完成且库存>0，红色=未完成或库存=0，灰色=未查询/查询中")
