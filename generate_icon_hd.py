#!/usr/bin/env python3
"""生成高清B站工具箱图标 - 512px绘制后高质量缩小"""
from PIL import Image, ImageDraw, ImageFont
import math

def create_hd_icon():
    """512x512高清绘制"""
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角矩形背景
    radius = int(size * 0.22)
    # 先画一个基础的圆角矩形（纯色，后面叠加渐变）
    draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=(251, 114, 153, 255))

    # 创建粉蓝渐变遮罩
    gradient = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    for y in range(size):
        t = y / size
        r = int(251 * (1-t) + 0 * t)
        g = int(114 * (1-t) + 161 * t)
        b = int(153 * (1-t) + 214 * t)
        gd.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # 用圆角矩形裁剪渐变
    mask = Image.new('L', (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=255)
    img.paste(gradient, (0, 0), mask)

    # 白色播放按钮（三角形）- 更粗更清晰
    play_w = int(size * 0.32)
    play_h = int(size * 0.36)
    cx = size // 2
    cy = int(size * 0.46)
    # 等腰三角形，左边垂直，右边尖
    p1 = (cx - play_w//2, cy - play_h//2)  # 左上
    p2 = (cx - play_w//2, cy + play_h//2)  # 左下
    p3 = (cx + play_w//2, cy)               # 右尖
    draw.polygon([p1, p2, p3], fill=(255, 255, 255, 255))

    # 底部 "B" 字母 - 粗体
    try:
        font_size = int(size * 0.16)
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    text = "B"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (size - tw) // 2
    ty = int(size * 0.70)
    draw.text((tx, ty), text, fill=(255, 255, 255, 240), font=font)

    return img

# 生成512px高清原图
hd = create_hd_icon()
hd.save('app_icon_hd.png')
print("高清原图已生成: app_icon_hd.png (512x512)")

# 高质量缩小到各尺寸（LANCZOS重采样）
sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
icons = []
for s in sizes:
    resized = hd.resize((s, s), Image.LANCZOS)
    icons.append(resized)

# 保存为ico（包含所有尺寸）
icons[0].save('app_icon.ico', format='ICO',
               sizes=[(s, s) for s in sizes],
               append_images=icons[1:])
print("图标已生成: app_icon.ico (包含10个尺寸)")

# 保存256px预览
icons[-1].save('app_icon_preview.png')
print("预览图已生成: app_icon_preview.png (256x256)")
