import re

with open('main_gui_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在__init__中插入新模式初始化
old1 = '''        self.shutdown_remaining = 0  # 剩余秒数

        # 初始化日志文件'''
new1 = '''        self.shutdown_remaining = 0  # 剩余秒数

        # ========== 新模式精准抢码 ==========
        self.new_mode_running = False
        self.new_mode_thread = None
        self.new_mode_stop_flag = {"stop": False}
        self.rush_groups = self.load_rush_groups()
        self.current_group_id = None
        self.new_mode_mode_var = None

        # 初始化日志文件'''
content = content.replace(old1, new1, 1)
print("1. __init__初始化插入完成")

# 2. 在on_close中添加保存任务组
old2 = '''    def on_close(self):
        """保存配置（标签页模式下不需要销毁）"""
        self.save_rush_config()
        self.save_scheduled_tasks()'''
new2 = '''    def on_close(self):
        """保存配置（标签页模式下不需要销毁）"""
        self.save_rush_config()
        self.save_scheduled_tasks()
        self.save_rush_groups()'''
content = content.replace(old2, new2, 1)
print("2. on_close保存任务组完成")

with open('main_gui_pro.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("全部完成")
