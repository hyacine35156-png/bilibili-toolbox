# -*- coding: utf-8 -*-
import io, os, glob

print('=' * 94)
print('1) spec 文件是否要求管理员权限 (uac_admin)')
print('=' * 94)
for f in sorted(glob.glob('B站工具箱_v6.6.10.spec')):
    s = io.open(f, encoding='utf-8', errors='ignore').read()
    print('  %s' % f)
    print('    含 uac_admin: %s' % ('uac_admin' in s))
    print('    含 uac_uiaccess: %s' % ('uac_uiaccess' in s))
    for i, ln in enumerate(s.split(chr(10)), 1):
        if 'uac' in ln.lower() or 'manifest' in ln.lower():
            print('      %d: %s' % (i, ln.strip()[:90]))

print('')
print('=' * 94)
print('2) 快捷方式是否设置"以管理员身份运行"')
print('=' * 94)
import subprocess, json
ps = r'''
$desktop = [Environment]::GetFolderPath("Desktop")
$lnks = Get-ChildItem "$desktop*.lnk" | Where-Object { $_.Name -like "*工具箱*" }
foreach ($l in $lnks) {
    $bytes = [System.IO.File]::ReadAllBytes($l.FullName)
    # 查找 RunAs 标志 (0x00 0x1F 0x00 0x00 pattern 附近)
    $hasRunAs = $false
    for ($i = 0; $i -lt $bytes.Length - 20; $i++) {
        # RunAs = 0x00000001 在 ExtraData 块中
        if ($bytes[$i] -eq 0x1F -and $bytes[$i+1] -eq 0x00) {
            # 检查后续 4 字节是否为 1
            $val = [BitConverter]::ToUInt32($bytes, $i+4)
            if ($val -eq 1) { $hasRunAs = $true; break }
        }
    }
    "$($l.Name) -> RunAs标志: $hasRunAs"
}
'''
r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='ignore', timeout=60)
out = ((r.stdout or '') + (r.stderr or '')).strip()
for ln in out.split(chr(10)):
    if ln.strip():
        print('  ' + ln.strip()[:100])
