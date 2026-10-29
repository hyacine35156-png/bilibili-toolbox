import shutil

# 从备份恢复
shutil.copy('main_gui_pro_v5.9.11_backup.py', 'main_gui_pro.py')
print('已从备份恢复 main_gui_pro.py')

# 验证编码
with open('main_gui_pro.py', 'rb') as f:
    raw = f.read()
print(f'文件大小: {len(raw)} 字节')
print(f'前3字节: {raw[:3].hex()}')
if raw[:3] == b'\xef\xbb\xbf':
    print('有BOM，去除BOM')
    with open('main_gui_pro.py', 'wb') as f:
        f.write(raw[3:])
else:
    print('无BOM')
