#!/usr/bin/env python3
"""v4.5.0: 日程方案管理 - 保存/加载/删除日程方案"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在__init__中初始化方案列表
# ============================================================
old_init = '''        self.selected_ids = set()  # 多选的任务ID集合
        self.build_ui()
        self.load_schedule()'''

new_init = '''        self.selected_ids = set()  # 多选的任务ID集合
        self.schedule_presets = self.load_schedule_presets()  # 日程方案列表
        self.build_ui()
        self.load_schedule()'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("1. 在__init__中初始化方案列表")
else:
    print("1. 未找到__init__代码")

# ============================================================
# 2. 在build_ui的按钮行下面添加方案管理行
# ============================================================
old_buttons_end = '''        # 调度器状态
        self.scheduler_status_label = tk.Label(row3, text="● 调度器运行中", bg=COLORS["bg_card"],
                                                fg=COLORS["success"], font=("微软雅黑", 10, "bold"))
        self.scheduler_status_label.pack(side=tk.RIGHT)

        # 底部：任务列表 + 日志'''

new_buttons_end = '''        # 调度器状态
        self.scheduler_status_label = tk.Label(row3, text="● 调度器运行中", bg=COLORS["bg_card"],
                                                fg=COLORS["success"], font=("微软雅黑", 10, "bold"))
        self.scheduler_status_label.pack(side=tk.RIGHT)

        # 方案管理行
        preset_row = tk.Frame(add_inner, bg=COLORS["bg_card"])
        preset_row.pack(fill=tk.X, pady=(8, 0))

        tk.Label(preset_row, text="📦 方案管理:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)

        tk.Label(preset_row, text="方案名:", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.preset_name_entry = DarkEntry(preset_row, width=15)
        self.preset_name_entry.pack(side=tk.LEFT)

        DarkButton(preset_row, "💾 保存方案", command=self.save_schedule_preset,
                   width=90, height=28, bg_color="#27ae60", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(preset_row, text="选择方案:", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(15, 2))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_row, textvariable=self.preset_var,
                                           values=[], state="readonly", width=15, font=("微软雅黑", 9))
        self.preset_combo.pack(side=tk.LEFT)

        DarkButton(preset_row, "📂 加载方案", command=self.load_schedule_preset,
                   width=90, height=28, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(preset_row, "🗑 删除方案", command=self.delete_schedule_preset,
                   width=90, height=28, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        self._refresh_preset_combo()

        # 底部：任务列表 + 日志'''

if old_buttons_end in content:
    content = content.replace(old_buttons_end, new_buttons_end)
    print("2. 在build_ui中添加方案管理行")
else:
    print("2. 未找到按钮行结束代码")

# ============================================================
# 3. 在save_schedule方法后面添加方案管理相关方法
# ============================================================
old_save_schedule = '''    def save_schedule(self):
        """保存日程配置到文件"""
        try:
            config_file = BASE_DIR / "schedule_config.json"'''

# 先找到save_schedule方法的结束位置
import re
# 找到save_schedule方法的完整内容
match = re.search(r'(    def save_schedule\(self\):.*?)(?=\n    def )', content, re.DOTALL)
if match:
    save_schedule_method = match.group(1)
    print("3. 找到save_schedule方法，长度:", len(save_schedule_method))

    # 在save_schedule方法后面添加新方法
    new_methods = save_schedule_method + '''
    def load_schedule_presets(self):
        """加载日程方案列表"""
        try:
            preset_file = BASE_DIR / "schedule_presets.json"
            if preset_file.exists():
                with open(preset_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载日程方案失败: {e}")
        return {}

    def save_schedule_presets_to_file(self):
        """保存日程方案列表到文件"""
        try:
            preset_file = BASE_DIR / "schedule_presets.json"
            with open(preset_file, "w", encoding="utf-8") as f:
                json.dump(self.schedule_presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"✗ 保存日程方案失败: {e}")

    def _refresh_preset_combo(self):
        """刷新方案下拉列表"""
        try:
            preset_names = list(self.schedule_presets.keys())
            self.preset_combo.config(values=preset_names)
            if preset_names and not self.preset_var.get():
                self.preset_var.set(preset_names[0])
        except Exception:
            pass

    def save_schedule_preset(self):
        """保存当前日程为方案"""
        preset_name = self.preset_name_entry.get().strip()
        if not preset_name:
            messagebox.showwarning("提示", "请输入方案名称")
            return

        # 深拷贝当前日程任务，避免后续修改影响方案
        import copy
        preset_data = {
            "name": preset_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tasks": copy.deepcopy(self.schedule_tasks)
        }

        self.schedule_presets[preset_name] = preset_data
        self.save_schedule_presets_to_file()
        self._refresh_preset_combo()
        self.log(f"💾 已保存方案「{preset_name}」（包含 {len(self.schedule_tasks)} 个任务）")

    def load_schedule_preset(self):
        """加载方案到当前日程"""
        preset_name = self.preset_var.get()
        if not preset_name or preset_name not in self.schedule_presets:
            messagebox.showwarning("提示", "请选择要加载的方案")
            return

        # 确认是否覆盖当前日程
        if self.schedule_tasks:
            result = messagebox.askyesno("确认", f"当前有 {len(self.schedule_tasks)} 个日程任务，加载方案将覆盖当前日程，是否继续？")
            if not result:
                return

        import copy
        preset_data = self.schedule_presets[preset_name]
        self.schedule_tasks = copy.deepcopy(preset_data["tasks"])

        # 重置任务状态
        for task in self.schedule_tasks:
            task["status"] = "等待中"
            task["last_run"] = ""
            task["enabled"] = task.get("enabled", True)

        self.save_schedule()
        self.refresh_task_list()
        self.log(f"📂 已加载方案「{preset_name}」（包含 {len(self.schedule_tasks)} 个任务）")

    def delete_schedule_preset(self):
        """删除选中的方案"""
        preset_name = self.preset_var.get()
        if not preset_name or preset_name not in self.schedule_presets:
            messagebox.showwarning("提示", "请选择要删除的方案")
            return

        result = messagebox.askyesno("确认", f"确定要删除方案「{preset_name}」吗？")
        if not result:
            return

        del self.schedule_presets[preset_name]
        self.save_schedule_presets_to_file()
        self._refresh_preset_combo()
        self.preset_name_entry.delete(0, tk.END)
        self.log(f"🗑 已删除方案「{preset_name}」")
'''

    content = content.replace(save_schedule_method, new_methods)
    print("3. 添加方案管理相关方法")
else:
    print("3. 未找到save_schedule方法")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.9"', 'APP_VERSION = "v4.5.0"')
print("4. 版本号已更新到 v4.5.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
