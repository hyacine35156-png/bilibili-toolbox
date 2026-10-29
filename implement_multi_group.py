#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实现方案A：支持同时启动多个任务组，每个组独立线程运行"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"文件总行数: {len(lines)}")

# ============================================================
# 1. 修改 nm_start_rush 函数
# ============================================================
print("\n1. 修改 nm_start_rush 函数")

start_idx = None
for i, line in enumerate(lines):
    if 'def nm_start_rush(self):' in line:
        start_idx = i
        break

if start_idx:
    print(f"  找到起始行: {start_idx+1}")
    end_idx = start_idx + 1
    while end_idx < len(lines):
        if lines[end_idx].strip() and not lines[end_idx].startswith(' ') and not lines[end_idx].startswith('\t'):
            break
        if lines[end_idx].strip().startswith('def ') and end_idx > start_idx + 1:
            break
        end_idx += 1
    print(f"  结束行: {end_idx}")
    
    new_func = '''    def nm_start_rush(self):
        """启动精准抢码（支持多组同时运行）"""
        if not self.current_group_id:
            self.nm_log("请先选择任务组")
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group or not group.get("tasks"):
            self.nm_log("任务组为空，请先添加任务")
            return
        
        group_id = group["group_id"]
        group_name = group["group_name"]
        
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            self.nm_log(f"任务组「{group_name}」已在运行中")
            return
        
        try:
            ms_val = self.nm_ms_entry.get().strip()
            if not ms_val or not ms_val.isdigit():
                ms_val = "000"
            ms_val = ms_val.zfill(3)[:3]
            group["target_time"] = f"{self.nm_hour_var.get()}:{self.nm_minute_var.get()}:{self.nm_second_var.get()}.{ms_val}"
            self.save_rush_groups()
        except Exception:
            pass
        
        self.nm_group_stop_flags[group_id] = {"stop": False}
        self.nm_group_status[group_id] = "running"
        self.nm_update_ui_state()
        
        self.nm_log("=" * 50)
        self.nm_log(f"启动精准抢码: {group_name}")
        self.nm_log(f"目标时间: {group['target_time']}")
        self.nm_log(f"任务数量: {len(group['tasks'])}")
        running_count = len([g for g, t in self.nm_group_threads.items() if t.is_alive()]) + 1
        self.nm_log(f"当前运行组数: {running_count}")
        
        thread = threading.Thread(target=self.nm_rush_worker, args=(group, group_id), daemon=True)
        self.nm_group_threads[group_id] = thread
        thread.start()
'''
    
    lines[start_idx:end_idx] = [l + '\n' for l in new_func.split('\n')]
    print("  已替换 nm_start_rush 函数")

# ============================================================
# 2. 修改 nm_stop_rush 函数
# ============================================================
print("\n2. 修改 nm_stop_rush 函数")

start_idx = None
for i, line in enumerate(lines):
    if 'def nm_stop_rush(self):' in line:
        start_idx = i
        break

if start_idx:
    print(f"  找到起始行: {start_idx+1}")
    end_idx = start_idx + 1
    while end_idx < len(lines):
        if lines[end_idx].strip() and not lines[end_idx].startswith(' ') and not lines[end_idx].startswith('\t'):
            break
        if lines[end_idx].strip().startswith('def ') and end_idx > start_idx + 1:
            break
        end_idx += 1
    print(f"  结束行: {end_idx}")
    
    new_func = '''    def nm_stop_rush(self):
        """停止所有正在运行的精准抢码任务组"""
        running_count = 0
        for group_id, stop_flag in self.nm_group_stop_flags.items():
            if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
                stop_flag["stop"] = True
                running_count += 1
                group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
                group_name = group["group_name"] if group else group_id
                self.nm_log(f"发送停止指令: {group_name}")
        
        if running_count == 0:
            self.nm_log("没有正在运行的任务组")
        else:
            self.nm_log(f"已向 {running_count} 个任务组发送停止指令，等待当前请求完成后停止...")
'''
    
    lines[start_idx:end_idx] = [l + '\n' for l in new_func.split('\n')]
    print("  已替换 nm_stop_rush 函数")

# ============================================================
# 3. 添加 nm_update_ui_state 函数（在 nm_stop_rush 后面）
# ============================================================
print("\n3. 添加 nm_update_ui_state 函数")

insert_idx = None
for i, line in enumerate(lines):
    if 'def nm_stop_rush(self):' in line:
        j = i + 1
        while j < len(lines):
            if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                break
            if lines[j].strip().startswith('def ') and j > i + 1:
                break
            j += 1
        insert_idx = j
        break

if insert_idx:
    print(f"  插入位置: {insert_idx+1}")
    
    new_func = '''
    def nm_update_ui_state(self):
        """更新UI状态（启动按钮/停止按钮/状态标签）"""
        try:
            running_groups = []
            for group_id, thread in self.nm_group_threads.items():
                if thread.is_alive():
                    group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
                    group_name = group["group_name"] if group else group_id
                    running_groups.append(group_name)
            
            running_count = len(running_groups)
            
            current_running = False
            if self.current_group_id and self.current_group_id in self.nm_group_threads:
                current_running = self.nm_group_threads[self.current_group_id].is_alive()
            
            if current_running:
                self.nm_start_btn.config(state=tk.DISABLED)
                self.nm_stop_btn.config(state=tk.NORMAL)
            else:
                self.nm_start_btn.config(state=tk.NORMAL)
                self.nm_stop_btn.config(state=tk.NORMAL if running_count > 0 else tk.DISABLED)
            
            if running_count > 0:
                if running_count == 1:
                    status_text = f"● 运行中: {running_groups[0]}"
                else:
                    status_text = f"● {running_count}个组运行中"
                self.nm_status_label.config(text=status_text, fg=COLORS["success"])
            else:
                self.nm_status_label.config(text="● 未运行", fg=COLORS["text_muted"])
            
            try:
                group_names = []
                for g in self.rush_groups:
                    name = g["group_name"]
                    if g["group_id"] in self.nm_group_threads and self.nm_group_threads[g["group_id"]].is_alive():
                        name = f"▶ {name} (运行中)"
                    group_names.append(name)
                self.nm_group_combo.config(values=group_names)
            except Exception:
                pass
        except Exception:
            pass
'''
    
    lines.insert(insert_idx, new_func)
    print("  已添加 nm_update_ui_state 函数")

# ============================================================
# 4. 修改 nm_rush_worker 函数签名和停止标志
# ============================================================
print("\n4. 修改 nm_rush_worker 函数")

start_idx = None
for i, line in enumerate(lines):
    if 'def nm_rush_worker(self, group):' in line:
        start_idx = i
        break

if start_idx:
    print(f"  找到起始行: {start_idx+1}")
    lines[start_idx] = '    def nm_rush_worker(self, group, group_id=None):\n'
    print("  已修改函数签名")
    
    # 在 try: 后面添加获取停止标志的代码
    try_idx = start_idx + 1
    while try_idx < len(lines) and not lines[try_idx].strip().startswith('try:'):
        try_idx += 1
    
    if try_idx < len(lines):
        print(f"  找到 try: 行: {try_idx+1}")
        insert_code = [
            '        """精准抢码核心线程（支持多组独立运行）"""\n',
            '        if group_id is None:\n',
            '            group_id = group.get("group_id", "default")\n',
            '        if group_id not in self.nm_group_stop_flags:\n',
            '            self.nm_group_stop_flags[group_id] = {"stop": False}\n',
            '        stop_flag = self.nm_group_stop_flags[group_id]\n',
            '        group_name = group.get("group_name", "未知")\n',
        ]
        for idx, code in enumerate(insert_code):
            lines.insert(try_idx + 1 + idx, code)
        print("  已添加获取停止标志的代码")
    
    # 替换 self.new_mode_stop_flag 为 stop_flag
    replace_count = 0
    for i in range(start_idx, min(start_idx + 500, len(lines))):
        if 'self.new_mode_stop_flag["stop"]' in lines[i]:
            lines[i] = lines[i].replace('self.new_mode_stop_flag["stop"]', 'stop_flag["stop"]')
            replace_count += 1
    print(f"  已替换 {replace_count} 处停止标志")
    
    # 修改 finally 块
    for i in range(start_idx, min(start_idx + 500, len(lines))):
        if 'self.new_mode_running = False' in lines[i]:
            indent = '            '
            new_lines = [
                f'{indent}self.nm_group_status[group_id] = "stopped"\n',
                f'{indent}if group_id in self.nm_group_threads:\n',
                f'{indent}    del self.nm_group_threads[group_id]\n',
                f'{indent}try:\n',
                f'{indent}    self.after(0, lambda: self.nm_update_ui_state())\n',
                f'{indent}except Exception:\n',
                f'{indent}    pass\n',
                f'{indent}self.nm_log(f"任务组「{{group_name}}」已结束")\n',
                f'{indent}running_count = len([g for g, t in self.nm_group_threads.items() if t.is_alive()])\n',
                f'{indent}if running_count > 0:\n',
                f'{indent}    self.nm_log(f"还有 {{running_count}} 个任务组正在运行")\n',
            ]
            lines[i:i+1] = new_lines
            print("  已修改 finally 块")
            break
    
    # 删除旧的UI更新代码
    i = start_idx
    while i < min(start_idx + 550, len(lines)):
        if 'self.after(0, lambda: self.nm_start_btn.config(state=tk.NORMAL))' in lines[i]:
            del lines[i:i+4]
            print("  已删除旧的UI更新代码")
            break
        i += 1

# ============================================================
# 5. 修改 nm_on_group_change 函数
# ============================================================
print("\n5. 修改 nm_on_group_change 函数")

for i, line in enumerate(lines):
    if 'def nm_on_group_change(self):' in line:
        j = i + 1
        while j < len(lines):
            if 'self.refresh_new_mode_task_list()' in lines[j]:
                lines.insert(j+1, '            self.nm_update_ui_state()\n')
                print(f"  已在第{j+1}行后添加UI状态更新")
                break
            j += 1
        break

# ============================================================
# 保存文件
# ============================================================
print("\n保存文件...")
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("完成！")
