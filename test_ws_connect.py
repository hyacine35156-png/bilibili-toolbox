# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json
import time
import threading

# 测试websocket是否可用
try:
    import websocket
    print(f"✓ websocket-client可用，版本: {websocket.__version__}")
except ImportError:
    print("✗ websocket-client未安装")

# 测试弹幕连接
from main_gui_pro import HEADERS

class MockApp:
    def __init__(self):
        self.account_stats = {}
        self.ws_clients = {}
        self.logs = []
    
    def log(self, msg):
        self.logs.append(msg)
        print(f"  [LOG] {msg}")
    
    def get_cookie(self, account):
        return "; ".join([f"{k}={v}" for k, v in {
            "SESSDATA": account.get("sessdata", ""),
            "bili_jct": account.get("bili_jct", ""),
            "DedeUserID": account.get("dede_userid", ""),
        }.items() if v])

# 读取账户
with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = accounts[4]  # 灵砂是无敌的
room_id = "2495037"

print(f"\n测试账户: {account.get('name')}")
print(f"测试直播间: {room_id}")

# 导入类方法
from main_gui_pro import B站工具箱App

# 创建mock实例
import types
app = types.new_class("MockApp", ())()
app.account_stats = {}
app.ws_clients = {}
app.logs = []
def log(msg):
    print(f"  [LOG] {msg}")
app.log = log
def get_cookie(acc):
    return "; ".join([f"{k}={v}" for k, v in {
        "SESSDATA": acc.get("sessdata", ""),
        "bili_jct": acc.get("bili_jct", ""),
        "DedeUserID": acc.get("dede_userid", ""),
    }.items() if v])
app.get_cookie = get_cookie

# 绑定方法
app.get_danmu_token = B站工具箱App.get_danmu_token.__get__(app)
app.connect_ws_danmaku = B站工具箱App.connect_ws_danmaku.__get__(app)

# 测试获取token
print("\n=== 测试获取弹幕token ===")
token, host = app.get_danmu_token(account, room_id)
print(f"token: {token[:30]}..." if len(token) > 30 else f"token: {token}")
print(f"host: {host}")

# 测试建立连接
print("\n=== 测试建立弹幕连接 ===")
app.account_stats[account["name"]] = {"ws_connected": False, "status": "观看中"}
ws_client = app.connect_ws_danmaku(account, room_id)
print(f"ws_client返回: {ws_client is not None}")

# 等待5秒看连接结果
print("\n等待5秒...")
time.sleep(5)

print(f"\n最终ws_connected: {app.account_stats[account['name']].get('ws_connected')}")

# 关闭连接
if ws_client:
    ws_client["running"] = False
