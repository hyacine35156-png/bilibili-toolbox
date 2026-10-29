# -*- coding: utf-8 -*-
import json, glob, os

# 查找任务组配置文件
config_files = glob.glob("dist/data/*rush*group*.json") + glob.glob("dist/data/*group*.json")
print("配置文件:", config_files)

# 也检查config.json
for cf in ["dist/data/config.json", "dist/data/rush_groups.json"]:
    if os.path.exists(cf):
        with open(cf, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 查找包含300播放的任务
        def find_task(obj, path=""):
            if isinstance(obj, dict):
                if "300播放" in str(obj.get("name", "")) or "300播放" in str(obj.get("task_name", "")):
                    print(f"  找到: {path} -> task_id={obj.get('task_id')}, name={obj.get('name')}, version={obj.get('version')}")
                for k, v in obj.items():
                    find_task(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    find_task(v, f"{path}[{i}]")
        find_task(data, cf)
