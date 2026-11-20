"""Übersichtsbögen zum Auswählen: python3 kontaktbogen.py <ordner> <ausgabe_prefix>"""
import glob, os, sys
from PIL import Image, ImageDraw
d, pre = sys.argv[1], sys.argv[2]
scenes = sorted({os.path.basename(f).rsplit('_', 1)[0] for f in glob.glob(os.path.join(d, '*.png'))})
for part in range(0, len(scenes), 8):
    group = scenes[part:part + 8]
    out = Image.new('RGB', (4 * 200, len(group) * 356), (20, 20, 20)); dr = ImageDraw.Draw(out)
    for r, s in enumerate(group):
        for i in range(4):
            f = os.path.join(d, f'{s}_{i+1}.png')
            if not os.path.exists(f): continue
            out.paste(Image.open(f).convert('RGB').resize((200, 356)), (i * 200, r * 356))
            dr.text((i * 200 + 5, r * 356 + 5), f'{s} #{i+1}', fill=(255, 220, 0))
    out.save(f'{pre}{part // 8 + 1}.jpg', quality=85); print(f'{pre}{part // 8 + 1}.jpg')
