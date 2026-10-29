# -*- coding: utf-8 -*-
"""数据备份与自愈（O2）。

解决的历史问题：
  - 曾误删 dist 导致用户数据不可恢复
  - dist/data 不完整导致卡密校验失败、任务组丢失

提供三件事：
  1. check_integrity()  启动时校验关键文件，缺失/损坏则从最近快照恢复
  2. daily_backup()     每天首次启动自动打包 data/，滚动保留最近 N 份
  3. verify_dist_data() 打包后比对源码 data 与 dist/data 的完整性

所有操作失败都不抛异常，只返回结果，避免影响主流程启动。
"""

import json
import os
import shutil
import time
import zipfile
from pathlib import Path

from config import BASE_DIR, BACKUP_DIR

# 关键文件：缺失会导致卡密失效/任务组丢失/账号丢失
CRITICAL_FILES = [
    "accounts.json",
    "card_auth.json",
    "rush_groups.json",
    "rush_config.json",
    "rooms_config.json",
    "watch_config.json",
]

# 允许缺失（首次运行正常生成）
OPTIONAL_FILES = [
    "manual_tasks.json",
    "hidden_tasks.json",
    "scheduled_tasks.json",
    "shutdown_config.json",
    "watch_history.json",
    "兑换码记录.json",
    "danmaku_list.txt",
    "config.json",
]

BACKUP_KEEP = 7          # 保留最近 7 份每日备份
DAILY_MARKER = BASE_DIR / ".last_backup_date"

INTEGRITY_LOG = []


def _log(msg):
    INTEGRITY_LOG.append(msg)
    try:
        print(f"[数据自愈] {msg}")
    except Exception:
        pass


def _is_valid_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except Exception:
        return False


def _latest_backup_zip():
    """找 backup 目录下最新的 data 备份 zip。"""
    try:
        if not BACKUP_DIR.exists():
            return None
        zips = sorted(BACKUP_DIR.glob("data_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        return zips[0] if zips else None
    except Exception:
        return None


def _restore_from_zip(zip_path, filenames):
    """从备份 zip 中恢复指定文件。返回恢复成功的文件名列表。"""
    restored = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            for fn in filenames:
                if fn not in names:
                    continue
                target = BASE_DIR / fn
                try:
                    with zf.open(fn) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    restored.append(fn)
                except Exception as e:
                    _log(f"恢复 {fn} 失败: {e}")
    except Exception as e:
        _log(f"打开备份 {zip_path} 失败: {e}")
    return restored


def check_integrity():
    """启动自检：校验关键文件，缺失或损坏则从最近备份恢复。

    返回 dict：{missing: [...], corrupt: [...], restored: [...]}
    """
    result = {"missing": [], "corrupt": [], "restored": []}
    try:
        if not BASE_DIR.exists():
            BASE_DIR.mkdir(parents=True, exist_ok=True)

        # 1) 检查缺失 / 损坏
        need_restore = []
        for fn in CRITICAL_FILES:
            p = BASE_DIR / fn
            if not p.exists():
                result["missing"].append(fn)
                need_restore.append(fn)
            elif fn.endswith(".json") and not _is_valid_json(p):
                result["corrupt"].append(fn)
                # 损坏文件先备份，再恢复
                try:
                    shutil.copy2(p, str(p) + ".corrupt_" + time.strftime("%Y%m%d%H%M%S"))
                except Exception:
                    pass
                need_restore.append(fn)

        # 2) 尝试从最近备份恢复
        if need_restore:
            zp = _latest_backup_zip()
            if zp:
                restored = _restore_from_zip(zp, need_restore)
                result["restored"] = restored
                if restored:
                    _log(f"已从 {zp.name} 恢复: {', '.join(restored)}")
                remain = [f for f in need_restore if f not in restored]
                if remain:
                    _log(f"以下文件备份中也没有，将使用默认值: {', '.join(remain)}")
            else:
                _log(f"关键文件缺失/损坏且无可用备份: {', '.join(need_restore)}")
        return result
    except Exception as e:
        _log(f"完整性检查异常: {e}")
        return result


def daily_backup(force=False, keep=BACKUP_KEEP):
    """每天首次启动自动打包 data/，滚动保留最近 keep 份。

    返回 (是否执行, 备份文件路径 或 None, 说明)
    """
    try:
        today = time.strftime("%Y-%m-%d")
        if not force:
            try:
                if DAILY_MARKER.exists():
                    last = DAILY_MARKER.read_text(encoding="utf-8").strip()
                    if last == today:
                        return False, None, "今日已备份"
            except Exception:
                pass

        if not BACKUP_DIR.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        zip_path = BACKUP_DIR / f"data_{stamp}.zip"

        # 只备份根目录的数据文件，不备份 backup/ 自身和 logs（体积大）
        count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in BASE_DIR.iterdir():
                if not item.is_file():
                    continue
                if item.name.startswith(".last_backup"):
                    continue
                if item.suffix in (".tmp", ".corrupt"):
                    continue
                if ".corrupt_" in item.name:
                    continue
                try:
                    zf.write(item, item.name)
                    count += 1
                except Exception:
                    pass

        # 滚动清理
        try:
            zips = sorted(BACKUP_DIR.glob("data_*.zip"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
            for old in zips[keep:]:
                try:
                    old.unlink()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            DAILY_MARKER.write_text(today, encoding="utf-8")
        except Exception:
            pass

        _log(f"已备份 {count} 个文件 -> {zip_path.name}")
        return True, str(zip_path), f"已备份 {count} 个文件"
    except Exception as e:
        _log(f"自动备份失败: {e}")
        return False, None, f"备份失败: {e}"


def list_backups():
    """列出所有数据备份（新到旧）。"""
    try:
        if not BACKUP_DIR.exists():
            return []
        out = []
        for p in sorted(BACKUP_DIR.glob("data_*.zip"),
                        key=lambda x: x.stat().st_mtime, reverse=True):
            st = p.stat()
            out.append({
                "name": p.name,
                "path": str(p),
                "size_kb": round(st.st_size / 1024, 1),
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
            })
        return out
    except Exception:
        return []


def verify_dist_data(source_data, dist_data):
    """打包后校验：比对源码 data 与 dist/data 的关键文件是否齐全。

    返回 (是否通过, 问题列表)
    """
    problems = []
    try:
        sd = Path(source_data)
        dd = Path(dist_data)
        if not dd.exists():
            return False, [f"dist/data 不存在: {dd}"]

        for fn in CRITICAL_FILES:
            sp = sd / fn
            dp = dd / fn
            if sp.exists() and not dp.exists():
                problems.append(f"dist 缺少 {fn}（源码侧存在）")
        # dist 侧关键文件不能为空
        for fn in CRITICAL_FILES:
            dp = dd / fn
            if dp.exists() and dp.stat().st_size == 0:
                problems.append(f"dist/{fn} 是空文件")

        # 账号数量对比
        try:
            sa = json.load(open(sd / "accounts.json", encoding="utf-8"))
            da = json.load(open(dd / "accounts.json", encoding="utf-8"))
            if isinstance(sa, list) and isinstance(da, list) and len(da) < len(sa):
                problems.append(f"dist 账号数 {len(da)} 少于源码 {len(sa)}")
        except Exception:
            pass

        return (len(problems) == 0), problems
    except Exception as e:
        return False, [f"校验异常: {e}"]


def startup_maintenance():
    """启动时统一入口：先自检恢复，再按需每日备份。

    返回 (integrity_result, backup_result)
    """
    integrity = check_integrity()
    backup = daily_backup()
    return integrity, backup
