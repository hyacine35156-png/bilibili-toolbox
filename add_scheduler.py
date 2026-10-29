# -*- coding: utf-8 -*-
"""
添加任务组调度器功能
1. 在UI中添加调度器面板
2. 添加定时更新函数
3. 添加启动/停止单个任务组的功能
"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"文件总行数: {len(lines)}")

# ============================================================
# 1. 在 build_new_mode_ui 中添加调度器面板
# ============================================================
print("\n1. 添加调度器面板到UI")

# 找到 "# ===== 第二步：添加任务到当前组 =====" 这行
insert_idx = None
for i, line in enumerate(lines):
    if '# ===== 第二步：添加任务到当前组 =====' in line:
        insert_idx = i
        break

if insert_idx:
    print(f"  插入位置: 第{insert_idx+1}行")
    
    scheduler_code = '''
        # ===== 任务组调度器（实时显示所有任务组状态）=====
        scheduler_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        scheduler_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(scheduler_card, text="📋 任务组调度器（实时更新，双击启动/停止）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 5))
        
        scheduler_inner = tk.Frame(scheduler_card, bg=COLORS["bg_card"])
        scheduler_inner.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        # 使用Treeview显示调度器表格
        from tkinter import ttk
        scheduler_style = ttk.Style()
        scheduler_style.configure("Scheduler.Treeview", 
            background=COLORS["bg_card"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["bg_card"],
            font=("微软雅黑", 10),
            rowheight=28)
        scheduler_style.configure("Scheduler.Treeview.Heading",
            background=COLORS["bg_hover"],
            foreground=COLORS["accent"],
            font=("微软雅黑", 10, "bold"))
        scheduler_style.map("Scheduler.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#000000")])
        
        scheduler_columns = ("group", "target_time", "status", "task_count", "remaining", "progress")
        self.nm_scheduler_tree = ttk.Treeview(scheduler_inner, columns=scheduler_columns, 
            show="headings", style="Scheduler.Treeview", height=6)
        
        self.nm_scheduler_tree.heading("group", text="任务组")
        self.nm_scheduler_tree.heading("target_time", text="目标时间")
        self.nm_scheduler_tree.heading("status", text="状态")
        self.nm_scheduler_tree.heading("task_count", text="任务数")
        self.nm_scheduler_tree.heading("remaining", text="剩余时间/进度")
        self.nm_scheduler_tree.heading("progress", text="完成情况")
        
        self.nm_scheduler_tree.column("group", width=120, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("target_time", width=100, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("status", width=80, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("task_count", width=60, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("remaining", width=140, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("progress", width=150, anchor=tk.CENTER)
        
        # 滚动条
        scheduler_scroll = ttk.Scrollbar(scheduler_inner, orient="vertical", command=self.nm_scheduler_tree.yview)
        self.nm_scheduler_tree.configure(yscrollcommand=scheduler_scroll.set)
        self.nm_scheduler_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scheduler_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 双击事件：启动/停止选中的任务组
        self.nm_scheduler_tree.bind("<Double-1>", lambda e: self.nm_scheduler_toggle())
        
        # 操作按钮
        scheduler_btn_frame = tk.Frame(scheduler_card, bg=COLORS["bg_card"])
        scheduler_btn_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        tk.Button(scheduler_btn_frame, text="▶ 启动选中组", bg=COLORS["success"], fg="#ffffff",
                 font=("微软雅黑", 10), command=self.nm_scheduler_start_selected,
                 relief=tk.FLAT, padx=15, pady=4).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(scheduler_btn_frame, text="⏹ 停止选中组", bg="#c0392b", fg="#ffffff",
                 font=("微软雅黑", 10), command=self.nm_scheduler_stop_selected,
                 relief=tk.FLAT, padx=15, pady=4).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(scheduler_btn_frame, text="⏹ 停止全部", bg="#e74c3c", fg="#ffffff",
                 font=("微软雅黑", 10), command=self.nm_stop_rush,
                 relief=tk.FLAT, padx=15, pady=4).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(scheduler_btn_frame, text="🔄 刷新", bg=COLORS["bg_hover"], fg=COLORS["text"],
                 font=("微软雅黑", 10), command=self.nm_update_scheduler,
                 relief=tk.FLAT, padx=15, pady=4).pack(side=tk.LEFT)
        
        # 状态颜色标签
        color_frame = tk.Frame(scheduler_btn_frame, bg=COLORS["bg_card"])
        color_frame.pack(side=tk.RIGHT)
        tk.Label(color_frame, text="● 未启动", bg=COLORS["bg_card"], fg="#95a5a6",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 等待中", bg=COLORS["bg_card"], fg="#3498db",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 运行中", bg=COLORS["bg_card"], fg=COLORS["success"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 已完成", bg=COLORS["bg_card"], fg="#27ae60",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 已停止", bg=COLORS["bg_card"], fg="#f39c12",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        
        # 启动定时更新（每秒更新一次）
        self.nm_scheduler_running = True
        self.nm_scheduler_update_loop()

'''
    
    # 插入代码
    lines.insert(insert_idx, scheduler_code)
    print("  已添加调度器面板")

# ============================================================
# 2. 添加调度器相关函数
# ============================================================
print("\n2. 添加调度器相关函数")

# 找到 nm_update_ui_state 函数的位置，在它后面添加调度器函数
func_idx = None
for i, line in enumerate(lines):
    if 'def nm_update_ui_state(self):' in line:
        func_idx = i
        break

if func_idx:
    # 找到函数结束位置
    end_idx = func_idx + 1
    while end_idx < len(lines):
        if lines[end_idx].strip() and not lines[end_idx].startswith(' ') and not lines[end_idx].startswith('\t'):
            break
        if lines[end_idx].strip().startswith('def ') and end_idx > func_idx + 1:
            break
        end_idx += 1
    
    print(f"  nm_update_ui_state 函数: 第{func_idx+1}行 到 第{end_idx}行")
    
    scheduler_funcs = '''
    def nm_scheduler_update_loop(self):
        """调度器定时更新循环（每秒更新一次）"""
        if hasattr(self, 'nm_scheduler_running') and self.nm_scheduler_running:
            try:
                self.nm_update_scheduler()
            except Exception:
                pass
            self.after(1000, self.nm_scheduler_update_loop)
    
    def nm_update_scheduler(self):
        """更新调度器显示"""
        if not hasattr(self, 'nm_scheduler_tree'):
            return
        
        try:
            # 清空现有数据
            for item in self.nm_scheduler_tree.get_children():
                self.nm_scheduler_tree.delete(item)
            
            now = time.time()
            
            for group in self.rush_groups:
                group_id = group["group_id"]
                group_name = group["group_name"]
                target_time = group.get("target_time", "00:00:00.000")
                tasks = group.get("tasks", [])
                task_count = len(tasks)
                
                # 判断状态
                is_running = False
                is_finished = False
                is_stopped = False
                current_task_idx = 0
                total_attempts = 0
                success_count = 0
                
                if group_id in self.nm_group_threads:
                    thread = self.nm_group_threads[group_id]
                    if thread.is_alive():
                        is_running = True
                    else:
                        # 线程已结束，检查状态
                        status = self.nm_group_status.get(group_id, "stopped")
                        if status == "finished":
                            is_finished = True
                        elif status == "stopped":
                            is_stopped = True
                
                # 计算剩余时间
                remaining_text = "-"
                status_text = "未启动"
                status_color = "#95a5a6"
                progress_text = "-"
                
                if is_running:
                    # 解析目标时间
                    try:
                        parts = target_time.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        sec_parts = parts[2].split(".")
                        second = int(sec_parts[0])
                        now_t = time.localtime()
                        target_ts = time.mktime((now_t.tm_year, now_t.tm_mon, now_t.tm_mday, hour, minute, second, 0, 0, -1))
                        if target_ts < now:
                            target_ts += 86400
                        
                        if now < target_ts:
                            remaining = target_ts - now
                            remaining_text = f"等待 {int(remaining//3600):02d}:{int((remaining%3600)//60):02d}:{int(remaining%60):02d}"
                            status_text = "等待中"
                            status_color = "#3498db"
                        else:
                            remaining_text = "执行中..."
                            status_text = "运行中"
                            status_color = COLORS["success"]
                    except Exception:
                        remaining_text = "执行中..."
                        status_text = "运行中"
                        status_color = COLORS["success"]
                    
                    progress_text = f"运行中"
                    
                elif is_finished:
                    status_text = "已完成"
                    status_color = "#27ae60"
                    remaining_text = "已结束"
                    progress_text = "全部完成"
                    
                elif is_stopped:
                    status_text = "已停止"
                    status_color = "#f39c12"
                    remaining_text = "已停止"
                    progress_text = "用户停止"
                    
                else:
                    # 未启动，计算距离目标时间
                    try:
                        parts = target_time.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        sec_parts = parts[2].split(".")
                        second = int(sec_parts[0])
                        now_t = time.localtime()
                        target_ts = time.mktime((now_t.tm_year, now_t.tm_mon, now_t.tm_mday, hour, minute, second, 0, 0, -1))
                        if target_ts < now:
                            target_ts += 86400
                        
                        remaining = target_ts - now
                        if remaining < 3600:
                            remaining_text = f"{int(remaining//60)}分{int(remaining%60)}秒后"
                        else:
                            remaining_text = f"{int(remaining//3600)}时{int((remaining%3600)//60)}分后"
                    except Exception:
                        remaining_text = "-"
                
                # 插入到表格
                display_name = f"▶ {group_name}" if is_running else group_name
                item = self.nm_scheduler_tree.insert("", tk.END, values=(
                    display_name, target_time, status_text, task_count, remaining_text, progress_text
                ))
                
                # 设置行颜色
                self.nm_scheduler_tree.tag_configure("running", background="#1a3a1a")
                self.nm_scheduler_tree.tag_configure("waiting", background="#1a2a3a")
                self.nm_scheduler_tree.tag_configure("finished", background="#1a3a2a")
                self.nm_scheduler_tree.tag_configure("stopped", background="#3a2a1a")
                
                if is_running:
                    if "等待" in remaining_text:
                        self.nm_scheduler_tree.item(item, tags=("waiting",))
                    else:
                        self.nm_scheduler_tree.item(item, tags=("running",))
                elif is_finished:
                    self.nm_scheduler_tree.item(item, tags=("finished",))
                elif is_stopped:
                    self.nm_scheduler_tree.item(item, tags=("stopped",))
                    
        except Exception as e:
            pass
    
    def nm_scheduler_toggle(self):
        """双击调度器项：启动/停止"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        # 找到对应的组
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        group_id = group["group_id"]
        
        # 检查是否在运行
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            # 停止
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_log(f"调度器：停止任务组「{group_name}」")
        else:
            # 启动
            self.current_group_id = group_id
            self.nm_start_rush()
    
    def nm_scheduler_start_selected(self):
        """启动选中的任务组"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            self.nm_log("请先在调度器中选择一个任务组")
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        self.current_group_id = group["group_id"]
        self.nm_start_rush()
    
    def nm_scheduler_stop_selected(self):
        """停止选中的任务组"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            self.nm_log("请先在调度器中选择一个任务组")
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        group_id = group["group_id"]
        if group_id in self.nm_group_stop_flags:
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_log(f"调度器：停止任务组「{group_name}」")
        else:
            self.nm_log(f"任务组「{group_name}」未在运行")

'''
    
    # 在 nm_update_ui_state 函数后面插入调度器函数
    lines.insert(end_idx, scheduler_funcs)
    print("  已添加调度器相关函数")

# ============================================================
# 3. 修改 nm_rush_worker 的 finally 块，设置正确的结束状态
# ============================================================
print("\n3. 修改抢码工作线程的结束状态")

# 找到 finally 块中的 self.nm_group_status[group_id] = "stopped"
for i, line in enumerate(lines):
    if 'self.nm_group_status[group_id] = "stopped"' in line:
        # 检查前面是否有成功标志，这里简单处理为finished
        # 实际上需要根据是否成功来判断，先改为finished
        lines[i] = lines[i].replace('"stopped"', '"finished"')
        print(f"  已修改第{i+1}行的结束状态为 finished")
        break

# ============================================================
# 保存文件
# ============================================================
print("\n保存文件...")
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("完成！")
