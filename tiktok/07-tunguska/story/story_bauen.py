"""Story-Teaser für Akte 04 (Tunguska): 12 s Video + Standbild, 1080x1920.
Text nur im mittleren Bereich (oben Profil/Fortschrittsbalken, unten Antwortfeld)."""
import subprocess
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

W, H, FPS, DAUER = 1080, 1920, 30, 12.0
A = Image.open('bilder_hd/01_feuerball_2.png').convert('RGB')
B = Image.open('bilder_hd/12_luft_4.png').convert('RGB')
T_B, T_CTA = 8.4, 10.4

def ausschnitt(img, z, cy=0.5):
    w, h = img.width / z, img.height / z
    x0 = (img.width - w) / 2; y0 = min(max(cy * img.height - h / 2, 0), img.height - h)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))

def s(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)

ass = r"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Label,Inter ExtraBold,46,&H00FFFFFF,&H00FFFFFF,&H002020C8,&H002020C8,-1,0,0,0,100,100,6,0,3,12,0,8,80,80,560,1
Style: Titel,Inter Black,104,&H00E6F0F5,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,2,0,1,6,4,8,60,60,640,1
Style: Text,Inter ExtraBold,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,20,0,5,90,90,0,1
Style: Gold,Inter ExtraBold,58,&H005AAFD4,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,5,3,2,80,80,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 2,0:00:00.00,0:00:12.00,Label,,0,0,0,,{\fad(0,0)}NEUE AKTE
Dialogue: 2,0:00:00.00,0:00:12.00,Titel,,0,0,0,,{\fscx115\fscy115\t(0,180,\fscx100\fscy100)}AKTE 04
Dialogue: 1,0:00:00.30,0:00:08.30,Text,,0,0,0,,{\fad(150,150)}80 MILLIONEN BÄUME\NUMGEKNICKT –\NABER KEIN KRATER
Dialogue: 1,0:00:08.40,0:00:10.30,Text,,0,0,0,,{\fscx120\fscy120\t(0,150,\fscx100\fscy100)}WAS IST 1908\NEXPLODIERT?
Dialogue: 1,0:00:10.40,0:00:12.00,Text,,0,0,0,,{\fad(150,0)}DIE GANZE AKTE:\NJETZT AUF MEINEM PROFIL
Dialogue: 1,0:00:00.00,0:00:12.00,Gold,,0,0,0,,TUNGUSKA · SIBIRIEN 1908
"""
open('story/story.ass', 'w', encoding='utf-8').write(ass)

ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-ss', '0', '-t', str(DAUER), '-i', 'audio/mix.wav',
                       '-vf', 'eq=contrast=1.06:saturation=1.08:gamma=1.03,noise=alls=6:allf=t,vignette=PI/4.2,ass=story/story.ass,format=yuv420p',
                       '-af', f'afade=t=out:st={T_CTA - 0.1}:d=1.6',
                       '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
                       '-shortest', '-movflags', '+faststart', 'story/akte04_story.mp4'], stdin=subprocess.PIPE)
for f in range(int(DAUER * FPS)):
    t = f / FPS
    if t < T_B:
        img = ausschnitt(A, 1.0 + 0.18 * s(t / T_B) + (0.1 * (1 - f / 8) ** 2 if f < 8 else 0), 0.45)
        if f < 8: img = ImageEnhance.Brightness(img).enhance(1 + 0.4 * (1 - f / 8) ** 2)
    else:
        p = (t - T_B) / (DAUER - T_B)
        z = 1.0 + 0.2 * s(p) + 0.1 * max(0, 1 - (t - T_B) / 0.22)
        img = ausschnitt(B, z)
        if t - T_B < 0.22: img = ImageEnhance.Brightness(img).enhance(1 + 0.6 * (1 - (t - T_B) / 0.22) ** 2)
    if t >= T_CTA:
        img = ImageEnhance.Brightness(img).enhance(1 - 0.45 * s((t - T_CTA) / 0.4))
    ff.stdin.write(img.tobytes())
ff.stdin.close(); ff.wait()

# Standbild
img = ImageEnhance.Brightness(ausschnitt(A, 1.08, 0.45)).enhance(0.85)
img.save('story/_hinter.png')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'story/_hinter.png', '-vf',
                "eq=contrast=1.06:saturation=1.08,vignette=PI/4.2,ass=story/story_bild.ass", 'story/akte04_story.png'], check=False)
