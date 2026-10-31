# 打包与发布流程（含踩坑记录）

## 标准步骤

```powershell
# 1. 杀掉运行中的进程（否则 exe 文件被锁，打包失败 WinError 5）
Get-Process | Where-Object { $_.ProcessName -like "*工具箱*" } | ForEach-Object { try { $_.Kill() } catch {} }
Start-Sleep -Seconds 3

# 2. 备份当前 dist/data（防止打包过程破坏用户数据）
Copy-Item -Recurse -Force "dist\data" "dist\data_backup_xxx"

# 3. 从上一个版本的 spec 复制并改版本号
Copy-Item "B站工具箱_v6.4.4.spec" "B站工具箱_vX.Y.Z.spec"
(Get-Content "B站工具箱_vX.Y.Z.spec" -Raw -Encoding utf8) -replace "v6.4.4", "vX.Y.Z" | Set-Content "B站工具箱_vX.Y.Z.spec" -Encoding utf8 -NoNewline

# 4. 清理并打包
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
python -m PyInstaller 'B站工具箱_vX.Y.Z.spec' --clean --noconfirm

# 5. 恢复数据
Copy-Item -Recurse -Force "dist\data_backup_xxx\*" "dist\data"; Remove-Item dist\data_backup_xxx -Recurse -Force

# 6. 【必做】更新桌面快捷方式（v6.4.4 起有专用脚本）
python _make_shortcut.py vX.Y.Z
```

## 踩坑记录

### 坑1：桌面路径不是 C:\Users\xxx\Desktop

本机 `[Environment]::GetFolderPath("Desktop")` 返回 **`E:\虚拟c盘`**，
而硬编码的 `C:\Users\15868\Desktop` 只是个空目录（或不同步）。

**教训**：桌面路径必须动态读取，永远不要硬编码。

### 坑2：打包后忘记创建快捷方式

v6.4.4 打包后直接提交了，漏了快捷方式步骤，导致用户桌面看不到新版。

**教训**：v6.4.4 起用 `_make_shortcut.py` 一键生成，
并且脚本会自动删除旧版快捷方式、同步到备用桌面、验证目标存在。

### 坑3：exe 文件被占用导致打包失败

`PyInstaller` 覆盖 dist 目录的 exe 时，如果程序正在运行会报 `WinError 5`。

**教训**：打包前必须 kill 所有 `*工具箱*` 进程。

### 坑4：dist/data 被清空

PyInstaller `--clean` 不会删 data 目录，但重建 dist 时可能丢失。

**教训**：打包前后各做一次 data 备份+恢复。

## 验收清单

- [ ] exe 启动成功（记录启动耗时）
- [ ] 进程路径包含正确版本号
- [ ] dist/data 数据完好（任务组数、账户数、记录数）
- [ ] 桌面快捷方式存在且 TargetPath 正确
- [ ] 快捷方式实际双击能启动
- [ ] 版本号已更新（config.APP_VERSION）
- [ ] 单元测试通过
- [ ] git commit 并 push