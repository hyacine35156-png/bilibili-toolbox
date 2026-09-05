#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站工具箱打包脚本
功能：
1. 自动备份旧版本exe到backup目录
2. 自动读取当前版本号
3. 执行PyInstaller打包
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# 项目目录
BASE_DIR = Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"
BACKUP_DIR = BASE_DIR / "backup"
MAIN_FILE = BASE_DIR / "main_gui_pro.py"
EXE_NAME = "B站弹幕工具.exe"

def get_version():
    """从源代码中读取版本号"""
    try:
        with open(MAIN_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        # 查找 APP_VERSION = "vX.X.X"
        import re
        match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"读取版本号失败: {e}")
    return "unknown"

def backup_old_version():
    """备份旧版本exe"""
    old_exe = DIST_DIR / EXE_NAME
    if old_exe.exists():
        BACKUP_DIR.mkdir(exist_ok=True)
        version = get_version()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"B站弹幕工具_{version}_{timestamp}.exe"
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(old_exe, backup_path)
        print(f"✓ 已备份旧版本: {backup_name}")
        return True
    else:
        print("ℹ 未找到旧版本，跳过备份")
        return False

def build():
    """执行打包"""
    version = get_version()
    print(f"=" * 60)
    print(f"B站工具箱打包脚本")
    print(f"当前版本: {version}")
    print(f"=" * 60)

    # 1. 备份旧版本
    print("\n[1/3] 备份旧版本...")
    backup_old_version()

    # 2. 关闭正在运行的程序
    print("\n[2/3] 关闭正在运行的程序...")
    os.system(f'taskkill /f /im "{EXE_NAME}" 2>nul')

    # 3. 执行PyInstaller打包
    print("\n[3/3] 执行PyInstaller打包...")
    cmd = (
        f'pyinstaller --onefile --windowed --name "B站弹幕工具" '
        f'--clean "{MAIN_FILE}"'
    )
    print(f"执行命令: {cmd}")
    result = os.system(cmd)

    if result == 0:
        new_exe = DIST_DIR / EXE_NAME
        if new_exe.exists():
            size_mb = new_exe.stat().st_size / (1024 * 1024)
            print(f"\n✓ 打包成功!")
            print(f"  版本: {version}")
            print(f"  文件: {new_exe}")
            print(f"  大小: {size_mb:.2f} MB")
        else:
            print(f"\n✗ 打包失败: 未找到输出文件")
    else:
        print(f"\n✗ 打包失败: 错误码 {result}")

    print(f"\n{'=' * 60}")
    print(f"备份目录: {BACKUP_DIR}")
    print(f"输出目录: {DIST_DIR}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    build()
