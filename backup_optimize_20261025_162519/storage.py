# -*- coding: utf-8 -*-
"""数据持久化：原子写入、安全加载、兑换码记录。"""

import json, os, time, threading
from pathlib import Path

from config import (
    CODE_EXPORT_FILE, LOG_DIR, BACKUP_DIR,
    _GLOBAL_LOCK,
)


def atomic_write_json(path, data):
    """原子写入JSON：先写临时文件，fsync后os.replace，断电不损坏"""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, str(path))


def safe_load_json(path, default=None):
    """安全加载JSON：解析失败时备份为.corrupt并告警，不静默清空"""
    if default is None:
        default = []
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        # 备份损坏文件
        try:
            corrupt_path = str(path) + ".corrupt"
            import shutil
            shutil.copy2(path, corrupt_path)
            print(f"⚠ 配置文件损坏已备份: {corrupt_path} ({e})")
        except Exception:
            pass
    return default

# ---------- 兑换码 ----------

def _ensure_code_dir():
    """确保data目录存在"""
    d = os.path.dirname(CODE_EXPORT_FILE)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def extract_redeem_codes(data):
    """从API返回数据中递归提取兑换码"""
    codes = []
    if not data:
        return codes
    # 可能的兑换码字段名
    code_keys = ["cdk", "redeem_code", "redeemCode", "award_code", "awardCode",
                 "gift_code", "giftCode", "exchange_code", "exchangeCode",
                 "code", "key", "ticket", "coupon", "cdkey", "cd_key",
                 "cdkey_content", "cdkeyContent", "cdk_content", "cdkContent"]
    
    def search(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = k.lower()
                # 检查是否是兑换码字段
                if k_lower in [ck.lower() for ck in code_keys]:
                    if isinstance(v, str) and v and len(v) >= 4 and not v.startswith("http"):
                        # 排除明显不是兑换码的值
                        if v not in ["0", "1", "true", "false", "success", "ok"]:
                            codes.append({"field": k, "value": v, "path": path + "." + k})
                    elif isinstance(v, list):
                        for item in v:
                            # P2-M: list分支也做URL和垃圾值过滤，与string分支一致
                            if isinstance(item, str) and item and len(item) >= 4 and not item.startswith("http") and item not in ["0", "1", "true", "false", "success", "ok"]:
                                codes.append({"field": k, "value": item, "path": path + "." + k})
                search(v, path + "." + k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search(item, path + f"[{i}]")
    
    search(data)
    return codes

def save_redeem_code(task_name, account_name, data, task_period="", task_type=""):
    """领取成功后保存兑换码到本地文件（自动去重）"""
    try:
        _ensure_code_dir()
        codes = extract_redeem_codes(data)
        if not codes:
            return False, "未提取到兑换码"
        
        # 读取已有记录
        records = safe_load_json(CODE_EXPORT_FILE, [])
        
        # 构建已有兑换码集合（账户+兑换码 作为唯一键）
        existing_codes = set()
        for r in records:
            key = f"{r.get('account', '')}|{r.get('redeem_code', '')}"
            existing_codes.add(key)
        
        import time as _time
        timestamp = _time.strftime("%Y-%m-%d %H:%M:%S")
        
        saved_count = 0
        skipped_count = 0
        
        for code_info in codes:
            code_value = code_info["value"]
            # 检查是否已存在（相同账户+相同兑换码）
            unique_key = f"{account_name}|{code_value}"
            if unique_key in existing_codes:
                skipped_count += 1
                continue
            
            record = {
                "id": len(records) + 1,
                "time": timestamp,
                "task_name": task_name,
                "task_period": task_period,
                "task_type": task_type,
                "account": account_name,
                "code_field": code_info["field"],
                "redeem_code": code_value,
                "status": "未使用",
                "raw_path": code_info.get("path", "")
            }
            records.append(record)
            existing_codes.add(unique_key)
            saved_count += 1
        
        # 重新编号ID
        for i, r in enumerate(records):
            r["id"] = i + 1
        
        atomic_write_json(CODE_EXPORT_FILE, records)

        # P2-T: saved_count==0时返回False，避免把重复当作已导入
        if saved_count == 0:
            return False, f"全部 {skipped_count} 个兑换码均为重复，未保存"
        if skipped_count > 0:
            return True, f"已保存 {saved_count} 个兑换码，跳过 {skipped_count} 个重复"
        return True, f"已保存 {saved_count} 个兑换码"
    except Exception as e:
        return False, f"保存兑换码失败: {e}"

def load_redeem_codes():
    """读取所有兑换码记录"""
    try:
        if os.path.exists(CODE_EXPORT_FILE):
            with open(CODE_EXPORT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def update_redeem_code_status(record_id, status):
    """更新兑换码状态（P2-P: 找不到id时返回False，用.get()避免KeyError）"""
    try:
        records = load_redeem_codes()
        found = False
        for r in records:
            if r.get("id") == record_id:
                r["status"] = status
                found = True
                break
        if not found:
            return False
        _ensure_code_dir()
        atomic_write_json(CODE_EXPORT_FILE, records)
        return True
    except:
        return False

def delete_redeem_code(record_id):
    """删除单条兑换码记录"""
    try:
        records = load_redeem_codes()
        records = [r for r in records if r["id"] != record_id]
        # 重新编号
        for i, r in enumerate(records):
            r["id"] = i + 1
        _ensure_code_dir()
        atomic_write_json(CODE_EXPORT_FILE, records)
        return True
    except:
        return False

def clear_redeem_codes():
    """清空所有兑换码记录"""
    try:
        _ensure_code_dir()
        atomic_write_json(CODE_EXPORT_FILE, [])
        return True
    except:
        return False
