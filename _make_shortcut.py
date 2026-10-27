# -*- coding: utf-8 -*-
"""打包后自动更新桌面快捷方式（v6.4.4 新增，避免遗漏）。

用法: python _make_shortcut.py [版本号]
      版本号省略时从 config.APP_VERSION 读取。

关键点（踩过的坑）:
  1. 桌面路径必须用 GetFolderPath(Desktop) 读取，
     不能硬编码 C:/Users/xxx/Desktop —— 本机真实桌面是 E:/虚拟c盘。
  2. 每次只保留最新一个快捷方式，旧的删掉避免混淆。
  3. 必须验证 TargetPath 指向的 exe 确实存在。
"""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    ver = sys.argv[1] if len(sys.argv) > 1 else None
    if not ver:
        try:
            import config
            ver = config.APP_VERSION
        except Exception:
            print('无法获取版本号')
            return 1

    base = os.path.dirname(os.path.abspath(__file__))
    exe = os.path.join(base, 'dist', 'B站工具箱_%s.exe' % ver)
    if not os.path.exists(exe):
        print('✗ exe 不存在: %s' % exe)
        return 1

    exe_ps = exe.replace('\\', '\\\\')
    ps_lines = [
        '$ErrorActionPreference = "Continue"',
        '$desktop = [Environment]::GetFolderPath("Desktop")',
        '$target = "' + exe_ps + '"',
        '$ver = "' + ver + '"',
        'Write-Output ("桌面路径: " + $desktop)',
        '# 删除旧版快捷方式',
        'Get-ChildItem -LiteralPath $desktop -Filter "B站工具箱*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {',
        '    Write-Output ("  删除旧版: " + $_.Name)',
        '    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue',
        '}',
        '$lnk = Join-Path $desktop ("B站工具箱_" + $ver + ".lnk")',
        '$ws = New-Object -ComObject WScript.Shell',
        '$s = $ws.CreateShortcut($lnk)',
        '$s.TargetPath = $target',
        '$s.WorkingDirectory = Split-Path $target',
        '$s.IconLocation = $target + ",0"',
        '$s.Description = "B站工具箱 " + $ver',
        '$s.Save()',
        'if (Test-Path $lnk) {',
        '    $v = $ws.CreateShortcut($lnk)',
        '    Write-Output ("✓ 快捷方式: " + $lnk)',
        '    Write-Output ("  目标: " + $v.TargetPath)',
        '    Write-Output ("  目标存在: " + (Test-Path $v.TargetPath))',
        '} else {',
        '    Write-Output "✗ 创建失败"',
        '    exit 1',
        '}',
        '$alt = "C:\\Users\\' + os.environ.get('USERNAME', '') + '\\Desktop"',
        'if ((Test-Path $alt) -and ($alt -ne $desktop)) {',
        '    Copy-Item $lnk -Destination $alt -Force -ErrorAction SilentlyContinue',
        '    Write-Output ("  已同步到备用桌面: " + $alt)',
        '}',
    ]
    ps = chr(10).join(ps_lines)

    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True,
                       encoding='utf-8', errors='ignore', timeout=60)
    out = (r.stdout or '') + (r.stderr or '')
    print(out.strip())
    return 0 if r.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())