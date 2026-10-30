# -*- coding: utf-8 -*-
import io

MSG = """fix: v6.7.7 修复启动报错 Could not create temporary directory!

## 用户报错
程序启动时弹出：
    Error
    Could not create temporary directory!

## 排查过程

### 第一步：检查环境
  TEMP 目录存在且可写        OK
  磁盘剩余 C: 19.34GB        充足
  临时目录创建测试           成功
  -> 环境本身没问题

### 第二步：发现大量残留目录
  %TEMP% 下 _MEI* 目录数量: 108 个
  总占用: 2892.1 MB (2.8 GB)
  最早: 10/20 16:05
  最新: 10/30 11:33

  根因：PyInstaller 单文件 exe 每次运行会把自身解压到
        %TEMP%/_MEIxxxxxx（约 37MB）。正常退出会自动删除，
        但进程被【强杀】（任务管理器结束 / 崩溃 / 反复测试）时
        目录会残留不清理。

        本次开发中反复 Kill 进程做测试，累积了 108 个残留目录，
        占满临时目录空间导致新建解压目录失败。

### 第三步：清理
  删除 108 个 _MEI 目录，释放 2892.1 MB
  C 盘剩余空间: 19.34GB -> 22.18GB
  清理后启动恢复正常（664ms）

## 修复：启动时自动清理残留目录

新增 main._cleanup_stale_mei_dirs()，在程序入口调用。

### 策略（务必保守，避免误删正在运行的实例）
  1. 只处理 sys.frozen（真 exe），源码运行完全不动
  2. 跳过当前进程自己的 _MEIPASS 目录
  3. 只删【1 小时以上未修改】的目录
     —— 正在运行的实例 mtime 会持续更新，不会被误删
  4. rmtree(ignore_errors=True)，删不掉就跳过

### 踩到的坑（重要）
  第一版实现永远返回 0，排查发现：
    main.py 模块级【没有 import sys】，
    函数里 getattr(sys, frozen) 触发 NameError，
    被外层 except Exception: return 0 静默吞掉。
  修复：函数内单独 import sys as _sys。
  （这也暴露了 except 吞异常难以排查的问题，已在注释里说明）

## 验证

### 单元测试（4 项全部 PASS）
  源码模式: 返回 0，不清理                     PASS
  frozen + 旧目录: 已删除                       PASS
  frozen + 新目录: 保留                         PASS
  frozen + 自己的目录(即使很旧): 保留           PASS

### 端到端测试（真实 exe）
  制造 3 个假的 3 小时前 _MEI 目录
  启动 B站工具箱_v6.7.7.exe
  结果:
    _MEI_fake_e2e_1  已删除 OK
    _MEI_fake_e2e_2  已删除 OK
    _MEI_fake_e2e_3  已删除 OK
    清理了 3/3 个
    当前只保留自己正在用的 1 个（36.6MB）
  结论: PASS

## 附带：清理项目临时文件
  第一轮: 删除 116 个 _*.py 临时诊断脚本（保留 _make_shortcut.py）
          备份 archives/temp_scripts_20261030_113404.zip
  第二轮: 删除 43 个 .bak 备份 / 截图 / 临时 txt
          备份 archives/bak_and_shots_20261030_113501.zip
  清理后完整验证: 模块导入 / 8页面 / 数据 / 列宽 全部正常

## 验证清单
- compileall（-W error::SyntaxWarning 严格模式）OK
- 22 项单元测试 OK
- 版本 v6.7.7
- 端到端: 真实 exe 自动清理 3/3 假残留目录
- 数据完好: 4日程/7账户/5直播间/7任务组
- exe 19.59MB
- 桌面快捷方式已更新 v6.7.7
"""

io.open('_msg_v677.txt', 'w', encoding='utf-8').write(MSG)
print('generated')