#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡密系统后端API自动化测试"""

import urllib.request
import urllib.error
import json
import random
import string
from datetime import datetime, timedelta, timezone

API_BASE = "https://precious-tanuki-c4b16d.netlify.app/api"
ADMIN_PWD = "hyacine2024"

MACHINE_A = "test-machine-A-001"
MACHINE_B = "test-machine-B-002"

results = []
passed = 0
failed = 0
test_cards = []  # 记录生成的测试卡密ID，最后清理


def api(path, payload=None, method=None):
    """调用API，返回(ok, data)。HTTP错误码也解析body返回(True, body)，调用方判断业务码"""
    url = f"{API_BASE}/{path}"
    if payload is not None and method is None:
        method = "POST"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        # HTTP错误但body是JSON业务错误，视为"成功到达后端"
        try:
            return True, json.loads(e.read().decode())
        except Exception:
            return False, {"code": -999, "msg": f"HTTP {e.code}"}
    except Exception as e:
        return False, {"code": -999, "msg": str(e)}


def check(name, condition, detail=""):
    """记录测试结果"""
    global passed, failed
    if condition:
        passed += 1
        results.append(f"  ✅ PASS  {name}{'  | ' + detail if detail else ''}")
    else:
        failed += 1
        results.append(f"  ❌ FAIL  {name}{'  | ' + detail if detail else ''}")


def gen_code():
    chars = string.ascii_uppercase + string.digits
    return "-".join("".join(random.choice(chars) for _ in range(4)) for _ in range(4))


print("=" * 60)
print("卡密系统后端API自动化测试")
print("=" * 60)

# ========== 1. 生成卡密 ==========
print("\n[1] 生成卡密测试")
ok, r = api("generate-cards", {"count": 2, "card_type": "monthly", "duration_days": 30, "notes": "自测月卡", "password": ADMIN_PWD})
check("正常生成月卡x2", ok and r.get("code") == 0 and len(r.get("cards", [])) == 2, str(r.get("msg")))
if ok and r.get("code") == 0:
    for c in r["cards"]:
        test_cards.append(c["id"])
    card1 = r["cards"][0]["card_code"]
    card1_id = r["cards"][0]["id"]
else:
    card1, card1_id = None, None

# 无密码
ok, r = api("generate-cards", {"count": 1, "card_type": "monthly", "duration_days": 30})
check("无密码被拒", ok and r.get("code") == -1, str(r.get("msg")))

# 错密码
ok, r = api("generate-cards", {"count": 1, "card_type": "monthly", "duration_days": 30, "password": "wrong"})
check("错密码被拒", ok and r.get("code") == -1, str(r.get("msg")))

# 0数量
ok, r = api("generate-cards", {"count": 0, "card_type": "monthly", "duration_days": 30, "password": ADMIN_PWD})
check("count=0报错", ok and r.get("code") != 0, str(r.get("msg")))

# 超上限
ok, r = api("generate-cards", {"count": 1001, "card_type": "monthly", "duration_days": 30, "password": ADMIN_PWD})
check("count=1001报错", ok and r.get("code") != 0, str(r.get("msg")))

# 小数天数（10分钟）
ok, r = api("generate-cards", {"count": 1, "card_type": "test_10min", "duration_days": 0.00694, "notes": "自测10分钟卡", "password": ADMIN_PWD})
check("小数天数(10分钟)生成", ok and r.get("code") == 0, str(r.get("msg")))
if ok and r.get("code") == 0:
    for c in r["cards"]:
        test_cards.append(c["id"])

# 永久卡
ok, r = api("generate-cards", {"count": 1, "card_type": "permanent", "notes": "自测永久卡", "password": ADMIN_PWD})
check("永久卡生成", ok and r.get("code") == 0 and r["cards"][0]["duration_days"] == 0, str(r.get("msg")))
if ok and r.get("code") == 0:
    for c in r["cards"]:
        test_cards.append(c["id"])
    perm_code = r["cards"][0]["card_code"]
    perm_id = r["cards"][0]["id"]
else:
    perm_code, perm_id = None, None

# 负数天数
ok, r = api("generate-cards", {"count": 1, "card_type": "monthly", "duration_days": -5, "password": ADMIN_PWD})
check("负数天数报错", ok and r.get("code") != 0, str(r.get("msg")))

# ========== 2. 验证/激活卡密 ==========
print("\n[2] 验证/激活测试")
if card1:
    # 首次激活
    ok, r = api("verify-card", {"card_code": card1, "machine_code": MACHINE_A})
    check("首次激活成功", ok and r.get("code") == 0 and r.get("expires_at"), str(r.get("msg")))
    activated_expires = r.get("expires_at") if ok else None
    if activated_expires:
        exp_dt = datetime.fromisoformat(activated_expires.replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        diff = (exp_dt - now_utc).total_seconds()
        check("过期时间≈30天", 25*86400 < diff < 31*86400, f"差值{diff/86400:.1f}天")

    # 重复激活（同机器码）
    ok, r = api("verify-card", {"card_code": card1, "machine_code": MACHINE_A})
    check("同机器码重复验证", ok and r.get("code") == 0, str(r.get("msg")))

    # 换设备
    ok, r = api("verify-card", {"card_code": card1, "machine_code": MACHINE_B})
    check("换设备被拒", ok and r.get("code") == -5, str(r.get("msg")))

    # 错误卡密
    ok, r = api("verify-card", {"card_code": "AAAA-BBBB-CCCC-DDDD", "machine_code": MACHINE_A})
    check("错误卡密不存在", ok and r.get("code") == -1, str(r.get("msg")))

    # 已激活卡缺机器码
    ok, r = api("verify-card", {"card_code": card1})
    check("已激活卡缺机器码被拒", ok and r.get("code") == -7, str(r.get("msg")))

# ========== 3. 更新卡密 ==========
print("\n[3] 更新卡密测试")
if card1_id:
    # 封禁
    ok, r = api("update-card", {"id": card1_id, "action": "ban", "password": ADMIN_PWD})
    check("封禁成功", ok and r.get("code") == 0, str(r.get("msg")))

    # 封禁后验证
    ok, r = api("verify-card", {"card_code": card1, "machine_code": MACHINE_A})
    check("封禁后验证被拒", ok and r.get("code") == -2, str(r.get("msg")))

    # 解封
    ok, r = api("update-card", {"id": card1_id, "action": "unban", "password": ADMIN_PWD})
    check("解封成功", ok and r.get("code") == 0, str(r.get("msg")))

    # 解封后验证
    ok, r = api("verify-card", {"card_code": card1, "machine_code": MACHINE_A})
    check("解封后验证恢复", ok and r.get("code") == 0, str(r.get("msg")))

    # 重置机器码
    ok, r = api("update-card", {"id": card1_id, "action": "reset_machine", "password": ADMIN_PWD})
    check("重置机器码成功", ok and r.get("code") == 0, str(r.get("msg")))

    # 重置后新机器码可激活
    ok, r = api("verify-card", {"card_code": card1, "machine_code": MACHINE_B})
    check("重置后新设备可激活", ok and r.get("code") == 0, str(r.get("msg")))

    # 延长30天
    ok, r = api("update-card", {"id": card1_id, "action": "extend", "extra_days": 30, "password": ADMIN_PWD})
    check("延长30天成功", ok and r.get("code") == 0, str(r.get("msg")))

    # 延长0天报错
    ok, r = api("update-card", {"id": card1_id, "action": "extend", "extra_days": 0, "password": ADMIN_PWD})
    check("延长0天报错", ok and r.get("code") != 0, str(r.get("msg")))

    # 编辑备注
    ok, r = api("update-card", {"id": card1_id, "action": "edit_notes", "notes": "自测修改后的备注", "password": ADMIN_PWD})
    check("编辑备注成功", ok and r.get("code") == 0, str(r.get("msg")))

    # 无权限操作
    ok, r = api("update-card", {"id": card1_id, "action": "ban"})
    check("无密码操作被拒", ok and r.get("code") == -1, str(r.get("msg")))

    # 无效操作
    ok, r = api("update-card", {"id": card1_id, "action": "hack", "password": ADMIN_PWD})
    check("无效操作报错", ok and r.get("code") != 0, str(r.get("msg")))

    # 不存在的卡
    ok, r = api("update-card", {"id": "00000000-0000-0000-0000-000000000000", "action": "ban", "password": ADMIN_PWD})
    check("不存在的卡报错", ok and r.get("code") == -3, str(r.get("msg")))

# ========== 4. 列表/搜索/筛选 ==========
print("\n[4] 列表/搜索/筛选测试")
ok, r = api("list-cards", {"password": ADMIN_PWD, "page": 1, "page_size": 20})
check("列表第1页", ok and r.get("code") == 0 and isinstance(r.get("data"), list), str(r.get("msg")))
total_all = r.get("total") if ok else 0

if card1:
    ok, r = api("list-cards", {"password": ADMIN_PWD, "search": card1, "page": 1, "page_size": 20})
    check("按卡密号搜索", ok and r.get("code") == 0 and any(c["card_code"] == card1 for c in r.get("data", [])), str(r.get("msg")))

ok, r = api("list-cards", {"password": ADMIN_PWD, "status": "active", "page": 1, "page_size": 20})
check("按状态筛选active", ok and r.get("code") == 0, str(r.get("msg")))

ok, r = api("list-cards", {"password": ADMIN_PWD, "card_type": "monthly", "page": 1, "page_size": 20})
check("按类型筛选monthly", ok and r.get("code") == 0, str(r.get("msg")))

ok, r = api("list-cards", {"password": "wrong", "page": 1, "page_size": 20})
check("列表无密码被拒", ok and r.get("code") == -1, str(r.get("msg")))

# 备注确认
if card1:
    ok, r = api("list-cards", {"password": ADMIN_PWD, "search": card1, "page": 1, "page_size": 20})
    if ok and r.get("code") == 0 and r.get("data"):
        found = r["data"][0]
        check("备注已更新为", found.get("notes") == "自测修改后的备注", str(found.get("notes")))

# ========== 5. 统计 ==========
print("\n[5] 统计测试")
ok, r = api("stats", {"password": ADMIN_PWD})
check("统计成功", ok and r.get("code") == 0 and isinstance(r.get("data"), dict), str(r.get("msg")))
if ok and r.get("data"):
    s = r["data"]
    check("统计字段齐全", all(k in s for k in ["total", "inactive", "active", "expired", "banned"]), json.dumps(s, ensure_ascii=False))

ok, r = api("stats")
check("统计无密码被拒", ok and r.get("code") == -1, str(r.get("msg")))

# ========== 6. 过期卡测试 ==========
print("\n[6] 过期卡测试")
# 生成一个10分钟卡，直接把expires_at改成过去（通过SQL太麻烦，用extend无法减，跳过）
# 改为：生成10分钟卡并激活，验证expires_at正确
ok, r = api("generate-cards", {"count": 1, "card_type": "test_10min", "duration_days": 0.00694, "notes": "自测过期逻辑", "password": ADMIN_PWD})
if ok and r.get("code") == 0:
    short_code = r["cards"][0]["card_code"]
    test_cards.append(r["cards"][0]["id"])
    ok2, r2 = api("verify-card", {"card_code": short_code, "machine_code": MACHINE_A})
    if ok2 and r2.get("code") == 0:
        exp_dt = datetime.fromisoformat(r2["expires_at"].replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        diff_min = (exp_dt - now_utc).total_seconds() / 60
        check("10分钟卡过期时间正确", 8 < diff_min < 12, f"剩余{diff_min:.1f}分钟")
    else:
        check("10分钟卡激活", False, str(r2.get("msg")))

# ========== 7. 清理测试数据 ==========
print("\n[7] 清理测试数据")
cleaned = 0
for cid in test_cards:
    ok, r = api("update-card", {"id": cid, "action": "delete", "password": ADMIN_PWD})
    if ok and r.get("code") == 0:
        cleaned += 1
check(f"删除{len(test_cards)}张测试卡", cleaned == len(test_cards), f"成功{cleaned}/{len(test_cards)}")

# ========== 汇总 ==========
print("\n" + "=" * 60)
print(f"测试完成: PASS {passed} | FAIL {failed}")
print("=" * 60)
for line in results:
    print(line)

if failed > 0:
    exit(1)
else:
    print("\n🎉 全部通过！")
