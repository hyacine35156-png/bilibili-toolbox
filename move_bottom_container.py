#!/usr/bin/env python3
"""把弹幕工具页面的bottom_container移回settings_card之后，恢复v4.6.5布局"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到弹幕工具页面的bottom_container开始和结束
# 开始：第5271行附近，包含"底部容器：日志 + 控制栏（先pack到BOTTOM"
# 结束：status_label.pack之后，settings_card之前

start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "# ===== 底部容器：日志 + 控制栏（先pack到BOTTOM" in line and i > 5200 and i < 5300:
        start_idx = i
    if start_idx is not None and "# 设置卡片" in line and i > start_idx:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    print(f"找到bottom_container代码: 第{start_idx+1}行 - 第{end_idx}行")
    # 提取bottom_container代码
    bottom_container_code = lines[start_idx:end_idx]
    # 删除原来的bottom_container代码
    del lines[start_idx:end_idx]
    print(f"已删除原来的bottom_container代码（{end_idx - start_idx}行）")

    # 找到弹幕列表卡片之前的位置（在settings_card之后）
    # 搜索"# ===== 中间：弹幕列表卡片"
    insert_idx = None
    for i, line in enumerate(lines):
        if "# ===== 中间：弹幕列表卡片" in line and i > start_idx:
            insert_idx = i
            break

    if insert_idx is not None:
        print(f"找到插入位置: 第{insert_idx+1}行之前")
        # 在弹幕列表卡片之前插入bottom_container代码
        # 修改注释，去掉"先pack到BOTTOM"
        modified_code = []
        for line in bottom_container_code:
            if "# ===== 底部容器：日志 + 控制栏（先pack到BOTTOM" in line:
                line = line.replace("（先pack到BOTTOM，确保固定在窗口最底部）", "（固定高度，先pack到BOTTOM）")
            modified_code.append(line)
        lines[insert_idx:insert_idx] = modified_code
        print(f"已在弹幕列表卡片之前插入bottom_container代码（{len(modified_code)}行）")
    else:
        print("未找到插入位置")
else:
    print(f"未找到bottom_container代码: start={start_idx}, end={end_idx}")

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
