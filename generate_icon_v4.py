#!/usr/bin/env python3
"""生成超清晰ICO - 确保所有尺寸都正确写入"""
from PIL import Image, ImageDraw

def draw_icon(size):
    """为每个尺寸单独精确绘制"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # B站粉纯色背景 - 圆角矩形
    bg_color = (251, 114, 153, 255)
    radius = max(2, int(size * 0.22))
    draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=bg_color)

    # 白色播放按钮 - 大尺寸
    play_w = int(size * 0.42)
    play_h = int(size * 0.50)
    cx = size // 2
    cy = size // 2
    p1 = (cx - play_w//2, cy - play_h//2)
    p2 = (cx - play_w//2, cy + play_h//2)
    p3 = (cx + play_w//2, cy)
    draw.polygon([p1, p2, p3], fill=(255, 255, 255, 255))

    return img

# 生成所有尺寸
sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
icons = [draw_icon(s) for s in sizes]

# 方法1：用最大尺寸的图作为基础，sizes参数指定所有尺寸
# PIL会自动从大图缩放到指定尺寸
base = icons[-1]  # 256px
base.save('app_icon.ico', format='ICO', sizes=[(s, s) for s in sizes])

# 验证
ico = Image.open('app_icon.ico')
saved_sizes = list(ico.ico.sizes())
print(f"方法1保存的尺寸: {saved_sizes}")
print(f"共 {len(saved_sizes)} 个尺寸")

# 如果尺寸不全，用方法2：逐个append
if len(saved_sizes) < len(sizes):
    print("尺寸不全，使用方法2重新保存...")
    icons[0].save('app_icon.ico', format='ICO')
    for i in range(1, len(icons)):
        icons[i].save('app_icon.ico', format='ICO', append_images=[icons[i]])
    ico2 = Image.open('app_icon.ico')
    saved_sizes2 = list(ico2.ico.sizes())
    print(f"方法2保存的尺寸: {saved_sizes2}")
    print(f"共 {len(saved_sizes2)} 个尺寸")

# 保存预览
icons[-1].save('app_icon_preview.png')
icons[sizes.index(48)].save('app_icon_48.png')
print("预览图已保存")
