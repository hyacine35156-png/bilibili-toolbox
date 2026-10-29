#!/usr/bin/env python3
"""v4.6.7: 加大抢码工具设置区域字体（标签9->11，下拉框9->11，账户列表8->10）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到抢码设置区域的起始和结束位置
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'text="抢码设置"' in line:
        start_idx = i
    if start_idx is not None and "# 定时任务列表区域" in line:
        end_idx = i
        break

print(f"抢码设置区域: 第{start_idx+1}行 - 第{end_idx+1}行")

# 在这个区域内替换字体
count_9 = 0
count_8 = 0
for i in range(start_idx, end_idx):
    # 标签和下拉框：9号 -> 11号
    if 'font=("微软雅黑", 9)' in lines[i]:
        lines[i] = lines[i].replace('font=("微软雅黑", 9)', 'font=("微软雅黑", 11)')
        count_9 += 1
    elif 'font=("微软雅黑", 9, "bold")' in lines[i]:
        lines[i] = lines[i].replace('font=("微软雅黑", 9, "bold")', 'font=("微软雅黑", 11, "bold")')
        count_9 += 1
    # 账户列表：8号 -> 10号
    elif 'font=("微软雅黑", 8)' in lines[i]:
        lines[i] = lines[i].replace('font=("微软雅黑", 8)', 'font=("微软雅黑", 10)')
        count_8 += 1

print(f"替换9号字体: {count_9}处")
print(f"替换8号字体: {count_8}处")

# 版本号
for i, line in enumerate(lines):
    if 'APP_VERSION = "v4.6.6"' in line:
        lines[i] = line.replace('APP_VERSION = "v4.6.6"', 'APP_VERSION = "v4.6.7"')
        print("版本号: v4.6.6 -> v4.6.7")
        break

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
