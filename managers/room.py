# -*- coding: utf-8 -*-
"""直播间管理：增删改查、从账户导入。"""

import requests
from pathlib import Path

from config import BASE_DIR, HEADERS
from storage import atomic_write_json, safe_load_json


class RoomManager:
    """直播间管理器"""
    def __init__(self):
        self.rooms = []
        self.load()

    def load(self):
        config_file = BASE_DIR / "rooms_config.json"
        data = safe_load_json(config_file, {})
        self.rooms = data.get("rooms", []) if isinstance(data, dict) else []

    def save(self):
        config_file = BASE_DIR / "rooms_config.json"
        atomic_write_json(config_file, {"rooms": self.rooms})

    def add_room(self, room_id, name, remark=""):
        room_id = str(room_id).strip()
        if not room_id or not room_id.isdigit():
            return False, "直播间号必须是数字"
        for room in self.rooms:
            if room["id"] == room_id:
                return False, "直播间号已存在"
        self.rooms.append({"id": room_id, "name": name, "remark": remark})
        self.save()
        return True, "添加成功"

    def delete_room(self, room_id):
        self.rooms = [r for r in self.rooms if r["id"] != str(room_id)]
        self.save()

    def update_room(self, room_id, name=None, remark=None):
        for room in self.rooms:
            if room["id"] == str(room_id):
                if name is not None:
                    room["name"] = name
                if remark is not None:
                    room["remark"] = remark
                self.save()
                return True
        return False

    def get_room(self, room_id):
        for room in self.rooms:
            if room["id"] == str(room_id):
                return room
        return None

    def get_room_names(self):
        """获取所有直播间的显示名称列表"""
        return [f"{r['name']}（{r['id']}）" for r in self.rooms]

    def import_from_accounts(self, account_mgr, log_func=None):
        """从账户导入直播间（自动获取所有账户的直播间号）"""
        added = 0
        for acc in account_mgr.accounts:
            name = acc.get("name", "未知")
            mid = acc.get("DedeUserID", "")
            if not mid:
                continue
            try:
                url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                data = resp.json()
                if data.get("code") == 0 and data.get("data"):
                    room_id = data["data"].get("roomid")
                    if room_id and data["data"].get("roomStatus") == 1:
                        room_name = f"{name}的房间"
                        if not self.get_room(room_id):
                            self.add_room(room_id, room_name, "从账户导入")
                            added += 1
                            if log_func:
                                log_func(f"已导入「{name}」的直播间: {room_id}")
            except Exception:
                pass
        if log_func:
            log_func(f"从账户导入完成，共新增 {added} 个直播间")
        return added
