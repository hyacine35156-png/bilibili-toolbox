#!/usr/bin/env python3
"""修改配置文件路径：所有文件存到exe同目录的data子文件夹，旧文件自动迁移"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 修改BASE_DIR定义，添加data子目录和迁移逻辑 ==========
old_base = '''# ========== 常量 ==========
BASE_DIR = Path(__file__).parent if not getattr(__import__("sys"), "frozen", False) else Path(__import__("sys").executable).parent
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"
CONFIG_FILE = BASE_DIR / "config.json"
ACT_ID_CACHE_FILE = BASE_DIR / "act_id_cache.json"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backup"'''

new_base = '''# ========== 常量 ==========
# exe所在目录（用于定位）
_EXE_DIR = Path(__file__).parent if not getattr(__import__("sys"), "frozen", False) else Path(__import__("sys").executable).parent
# 所有配置文件存到data子文件夹，避免铺满桌面
BASE_DIR = _EXE_DIR / "data"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# 自动迁移旧配置文件（从exe同目录迁移到data子目录）
def _migrate_old_files():
    old_files = [
        "accounts.json", "danmaku_list.txt", "config.json",
        "act_id_cache.json", "watch_config.json", "rush_config.json",
        "scheduled_tasks.json", "shutdown_config.json",
    ]
    for fname in old_files:
        old_path = _EXE_DIR / fname
        new_path = BASE_DIR / fname
        if old_path.exists() and not new_path.exists():
            try:
                import shutil
                shutil.move(str(old_path), str(new_path))
                print(f"已迁移配置文件: {fname} -> data/")
            except Exception as e:
                print(f"迁移 {fname} 失败: {e}")
    # 迁移logs和backup目录
    for dname in ["logs", "backup"]:
        old_dir = _EXE_DIR / dname
        new_dir = BASE_DIR / dname
        if old_dir.exists() and old_dir.is_dir() and not new_dir.exists():
            try:
                import shutil
                shutil.move(str(old_dir), str(new_dir))
                print(f"已迁移目录: {dname}/ -> data/{dname}/")
            except Exception as e:
                print(f"迁移 {dname} 失败: {e}")

_migrate_old_files()

ACCOUNTS_FILE = BASE_DIR / "accounts.json"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"
CONFIG_FILE = BASE_DIR / "config.json"
ACT_ID_CACHE_FILE = BASE_DIR / "act_id_cache.json"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backup"'''

content = content.replace(old_base, new_base)
print("1. BASE_DIR改为data子目录，添加自动迁移逻辑")

# ========== 2. 修改日志中的数据目录显示 ==========
old_log_dir = '''self.log("数据目录: " + str(BASE_DIR))'''
new_log_dir = '''self.log("数据目录: " + str(BASE_DIR))
        self.log("(配置文件已自动存到data子文件夹，不会铺满桌面)")'''
content = content.replace(old_log_dir, new_log_dir)
print("2. 日志添加data目录说明")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n修改完成！")
