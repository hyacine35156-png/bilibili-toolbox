FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 添加import re
old = "import struct\nfrom datetime import datetime, timedelta"
new = "import struct\nimport re\nfrom datetime import datetime, timedelta"

if old in content:
    content = content.replace(old, new, 1)
    print("✓ 已添加 import re")
else:
    print("✗ 未找到插入位置")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

# 验证
with open(FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i, line in enumerate(lines[:25]):
        if "import" in line:
            print(f"  行{i+1}: {line.rstrip()}")

print("\n✓ 修改完成")
