file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找ALL_TASKS的开始和结束位置
start_line = None
end_line = None
for i, line in enumerate(lines):
    if 'ALL_TASKS = [' in line:
        start_line = i
    if start_line is not None and i > start_line and line.strip() == ']':
        end_line = i
        break

print(f"ALL_TASKS开始行: {start_line + 1}")
print(f"ALL_TASKS结束行: {end_line + 1}")
print(f"结束行内容: {lines[end_line].strip()}")

# 显示结束行前后的内容
print("\n结束行前5行:")
for i in range(max(0, end_line-5), end_line):
    print(f"  {i+1}: {lines[i].rstrip()}")
print("\n结束行后5行:")
for i in range(end_line, min(len(lines), end_line+5)):
    print(f"  {i+1}: {lines[i].rstrip()}")
