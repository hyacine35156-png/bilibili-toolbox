# -*- coding: utf-8 -*-
"""配置与常量：路径、版本、颜色、API地址。无外部依赖。"""

import os
import threading
from pathlib import Path

# ========== 閰嶈壊鏂规 ==========
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_input": "#0f3460",
    "accent": "#00d9ff",
    "accent_hover": "#00b8d9",
    "danger": "#ff4757",
    "success": "#2ed573",
    "warning": "#ffa502",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b8",
    "text_muted": "#6c6c8a",
    "border": "#2a2a4a",
}

# ========== 甯搁噺 ==========
# exe鎵€鍦ㄧ洰褰曪紙鐢ㄤ簬瀹氫綅锛?
_EXE_DIR = Path(__file__).parent if not getattr(__import__("sys"), "frozen", False) else Path(__import__("sys").executable).parent
# 鎵€鏈夐厤缃枃浠跺瓨鍒癲ata瀛愭枃浠跺す锛岄伩鍏嶉摵婊℃闈?
BASE_DIR = _EXE_DIR / "data"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 閰嶇疆鏂囦欢璺緞 ----------

ACCOUNTS_FILE = BASE_DIR / "accounts.json"
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"
CONFIG_FILE = BASE_DIR / "config.json"
CONFIG_FILE = BASE_DIR / "config.json"
ACT_ID_CACHE_FILE = BASE_DIR / "act_id_cache.json"
ACT_ID_CACHE_FILE = BASE_DIR / "act_id_cache.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backup"

# ---------- 鐗堟湰 ----------
# 绋嬪簭鐗堟湰鍙?
APP_VERSION = "v6.0.4"

# ---------- API 鍦板潃 ----------

SEND_API = "https://api.live.bilibili.com/msg/send"
SEND_API = "https://api.live.bilibili.com/msg/send"
USER_INFO_API = "https://api.bilibili.com/x/web-interface/nav"
# 鎶㈢爜鐩稿叧API
MISSION_INFO_API = "https://api.bilibili.com/x/activity_components/mission/info"
# 鎶㈢爜鐩稿叧API
MISSION_INFO_API = "https://api.bilibili.com/x/activity_components/mission/info"
MISSION_RECEIVE_API = "https://api.bilibili.com/x/activity_components/mission/receive"
MISSION_RECEIVE_API = "https://api.bilibili.com/x/activity_components/mission/receive"
MISSION_MYLIST_API = "https://api.bilibili.com/x/activity_components/mission/mylist"

# ---------- 鍗″瘑鏈嶅姟 ----------
# ========== 鍗″瘑楠岃瘉閰嶇疆 ==========
CARD_API_BASE = "https://precious-tanuki-c4b16d.netlify.app/api"
# ========== 鍗″瘑楠岃瘉閰嶇疆 ==========
CARD_API_BASE = "https://precious-tanuki-c4b16d.netlify.app/api"
CARD_VERIFY_URL = f"{CARD_API_BASE}/verify-card"
CARD_VERIFY_URL = f"{CARD_API_BASE}/verify-card"
CARD_FILE = BASE_DIR / "card_auth.json"

# ---------- 缂撳瓨 ----------
# ========== 浠诲姟淇℃伅缂撳瓨 ==========
# 缂撳瓨宸插垽瀹氫负"宸查鍙?鎴?鏃犲墿浣欐€婚噺"鐨勪换鍔′俊鎭紝閬垮厤閲嶅鏌ヨAPI
# key: task_id, value: {finished, status, message, total_stock, day_stock, timestamp}
_mission_info_cache = {}
# 缂撳瓨鏈夋晥鏈燂細24灏忔椂锛堢锛?
_MISSION_CACHE_TTL = 24 * 3600
# ========== 鎶㈢爜鐩稿叧鍑芥暟 ==========
# WBI瀵嗛挜缂撳瓨锛堝噺灏戦噸澶嶇綉缁滆姹傦級
_WBI_KEY_CACHE = {}  # {cookie_hash: (img_key, sub_key, expire_time)}
# ========== 鎶㈢爜鐩稿叧鍑芥暟 ==========
# WBI瀵嗛挜缂撳瓨锛堝噺灏戦噸澶嶇綉缁滆姹傦級
_WBI_KEY_CACHE = {}  # {cookie_hash: (img_key, sub_key, expire_time)}
_WBI_CACHE_TTL = 3600  # 缂撳瓨1灏忔椂

# ---------- 鍏变韩閿佷笌鍏ㄥ眬鐘舵€?----------
# task_id鍒癮ct_id鐨勭紦瀛樺瓧鍏革紙鏌ヨ鎴愬姛鏃惰嚜鍔ㄤ繚瀛橈紝鏌ヨ澶辫触鏃朵娇鐢級
# 鍏ㄥ眬鍙橀噺绾跨▼閿?
_GLOBAL_LOCK = threading.Lock()
# ========== 鏁版嵁绠＄悊 ==========
_last_claim_data_global = None
# ========== 鏁版嵁绠＄悊 ==========
_last_claim_data_global = None
_last_claim_result_global = None

TASK_GUIDE_TEXT = """B站工具箱 使用说明

【一、账户管理】
  1.1 导入账户
    点击添加账户，输入账户昵称、SESSDATA、bili_jct、DedeUserID(可选)
    系统自动验证登录有效性，成功后自动保存
    获取Cookie: 浏览器F12 -> Application -> Cookies -> bilibili.com
  1.2 直播间管理
    添加直播间: 手动输入直播间号+名称+备注
    从账户导入: 自动获取所有已导入账户的直播间
    所有功能(弹幕/看播/送礼)共用此列表

【二、抢码工具】
  自动监控并领取B站直播任务奖励
  选择任务、账户、领取时间，点击开始监控
  多个任务间隔5秒顺序启动，避免请求频率过高

【三、弹幕工具】
  多账户自动发送弹幕到指定直播间
  选择账户、直播间、弹幕内容、发送间隔
  发送间隔建议不低于5秒

【四、看播任务】
  模拟真实用户观看直播，建立弹幕连接+视频流下载
  选择账户、直播间、每日时长、心跳间隔(默认60秒)
  多账户同时观看，每个账户独立连接

【五、送礼功能】
  多账户自动赠送礼物到指定直播间
  选择账户、直播间、礼物、数量、间隔、次数
  送礼会消耗真实电池，请谨慎使用

【六、日程任务】
  定时自动执行各种任务: 抢码/看播/弹幕/送礼/关机
  支持方案保存/加载/删除，适合不同场景快速切换

【七、定时关机】
  定时或延时自动关闭电脑
  关机前有确认提示，可点击取消

常见问题:
  Q: 看播显示接口失败?
  A: 心跳上报失败，不影响弹幕连接和视频流播放
  Q: 抢码提示请求频率过高?
  A: 系统已自动间隔和退避重试，无需手动干预
  Q: 账户数据会泄露吗?
  A: 所有数据保存在本地data/目录，不上传任何服务器
"""


# ---------- 璇锋眰澶?----------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
}

# ---------- 鍏戞崲鐮佽褰曟枃浠?----------
CODE_EXPORT_FILE = str(BASE_DIR / "兑换码记录.json")

# ---------- 寮瑰箷姹?----------
# 甯哥敤寮瑰箷璇嶅簱锛?00鏉★紝鐢ㄤ簬鎵归噺鐢熸垚锛?
DANMAKU_POOL = [
    "666", "主播好强", "来了来了", "哈哈哈哈", "学到了", "太强了", "牛逼",
    "666666", "主播牛逼", "哈哈", "这波操作可以", "厉害了", "我的天",
    "好看好看", "支持主播", "打卡", "签到", "晚上好", "主播好",
    "第一次来", "老粉了", "主播加油", "冲冲冲", "可以可以", "牛啊",
    "这也太强了吧", "学到了学到了", "哈哈笑死", "主播声音好听",
    "关注了关注了", "已关注", "主播今天状态不错", "这把稳了",
    "漂亮", "好吃", "精彩", "666主播", "爱了爱了", "绝了",
    "这操作绝了", "主播太厉害了", "笑死我了", "哈哈哈哈太搞笑了",
    "前排", "沙发", "来啦", "打卡签到", "今日份打卡", "来咯来咯",
    "主播辛苦了", "感谢主播", "谢谢主播", "主播早点休息", "晚安",
    "下次一定", "一定一定", "必须的", "没毛病", "说得对", "有道理",
    "涨知识了", "干货满满", "收藏了", "转发了", "推荐推荐",
    "这把能赢吗", "稳了稳了", "翻了翻了", "可惜了", "差一点",
    "没事没事", "下一把", "再来一把", "继续继续", "不慌不慌",
    "问题不大", "小问题", "这波不亏", "血赚", "血亏", "赚翻了",
    "亏麻了", "赢麻了", "杀疯了", "秀起来了", "操作起来了",
    "家人们谁懂啊", "真的会谢", "我不理解", "离大谱", "太离谱了",
    "就这", "就这水平", "不过如此", "拿下拿下", "拿捏了",
]

# ---------- WBI 娣锋穯琛?----------
# WBI绛惧悕鏄犲皠琛?
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
    25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]
