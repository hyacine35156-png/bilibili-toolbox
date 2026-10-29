with open('main_gui_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在save_scheduled_tasks方法后面添加load_rush_groups和save_rush_groups
old = '''    def save_scheduled_tasks(self):
        """保存定时任务列表"""
        try:
            tasks_file = BASE_DIR / "scheduled_tasks.json"
            # 保存时不包含线程对象
            tasks_to_save = []
            for task in self.scheduled_tasks:
                task_copy = {k: v for k, v in task.items() if k != "thread"}
                tasks_to_save.append(task_copy)
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(tasks_to_save, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_rush_config(self):'''

new = '''    def save_scheduled_tasks(self):
        """保存定时任务列表"""
        try:
            tasks_file = BASE_DIR / "scheduled_tasks.json"
            # 保存时不包含线程对象
            tasks_to_save = []
            for task in self.scheduled_tasks:
                task_copy = {k: v for k, v in task.items() if k != "thread"}
                tasks_to_save.append(task_copy)
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(tasks_to_save, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_rush_groups(self):
        """加载新模式任务组配置"""
        groups_file = BASE_DIR / "rush_groups.json"
        if groups_file.exists():
            try:
                with open(groups_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_rush_groups(self):
        """保存新模式任务组配置"""
        try:
            groups_file = BASE_DIR / "rush_groups.json"
            with open(groups_file, "w", encoding="utf-8") as f:
                json.dump(self.rush_groups, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_rush_config(self):'''

if old in content:
    content = content.replace(old, new, 1)
    with open('main_gui_pro.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("任务组加载保存方法添加完成")
else:
    print("未找到匹配位置")
