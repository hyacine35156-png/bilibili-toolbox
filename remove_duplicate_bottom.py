#!/usr/bin/env python3
"""删除弹幕工具页面原来的bottom_container代码（已移到上面）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到原来的bottom_container开始行（第5415行，索引5414）
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "# ===== 底部容器：日志 + 控制栏（固定高度，先pack到BOTTOM）=====" in line and i > 5300:
        start_idx = i
    if start_idx is not None and "# ===== 中间：弹幕列表卡片（expand=True，占据剩余空间）=====" in line and i > start_idx:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    print(f"找到原来的bottom_container: 第{start_idx+1}行 - 第{end_idx}行")
    # 删除从start_idx到end_idx-1的行，保留end_idx行（弹幕列表卡片注释）
    del lines[start_idx:end_idx]
    print(f"已删除 {end_idx - start_idx} 行")
else:
    print(f"未找到原来的bottom_container: start={start_idx}, end={end_idx}")

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
