"""Story-Teaser (1080x1920) für eine Akte: kurzer Clip mit Stimme bis zum Cliffhanger + Standbild.
Text liegt nur im mittleren Bereich (oben Profil/Fortschrittsbalken, unten Antwortfeld).

Nutzung (im Ordner der Folge, nach render.py, braucht audio/mix.wav):
    python3 ../tools/story.py story.json
story.json: {"akte": "05", "bild_a": "bilder_hd/x.png", "bild_b": "bilder_hd/y.png",
             "wechsel": 10.6, "cta": 12.5, "dauer": 14.2,
             "hook": "ZEILE 1\\NZEILE 2", "frage": "FRAGE?", "ort": "ORT · JAHR"}
"""
import json, os, subprocess, sys
from PIL import Image, ImageEnhance

W, H, FPS = 1080, 1920, 30
STYLES = r"""[Script Info]
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
"""


def ts(t):
    return f'0:00:{t:05.2f}'


def s(x):
    x = min(max(x, 0), 1); return x * x * (3 - 2 * x)


def ausschnitt(img, z, cy=0.5):
    w, h = img.width / z, img.height / z
    x0 = (img.width - w) / 2; y0 = min(max(cy * img.height - h / 2, 0), img.height - h)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))


def main(cfg_path):
    c = json.load(open(cfg_path, encoding='utf-8'))
    os.makedirs('story', exist_ok=True)
    A, B = (Image.open(c[k]).convert('RGB') for k in ('bild_a', 'bild_b'))
    tb, tc, d = c['wechsel'], c['cta'], c['dauer']
    ev = [f'Dialogue: 2,{ts(0)},{ts(d)},Label,,0,0,0,,NEUE AKTE',
          f'Dialogue: 2,{ts(0)},{ts(d)},Titel,,0,0,0,,{{\\fscx115\\fscy115\\t(0,180,\\fscx100\\fscy100)}}AKTE {c["akte"]}',
          f'Dialogue: 1,{ts(0.3)},{ts(tb - 0.1)},Text,,0,0,0,,{{\\fad(150,150)}}{c["hook"]}',
          f'Dialogue: 1,{ts(tb)},{ts(tc - 0.1)},Text,,0,0,0,,{{\\fscx120\\fscy120\\t(0,150,\\fscx100\\fscy100)}}{c["frage"]}',
          f'Dialogue: 1,{ts(tc)},{ts(d)},Text,,0,0,0,,{{\\fad(150,0)}}DIE GANZE AKTE:\\NJETZT AUF MEINEM PROFIL',
          f'Dialogue: 1,{ts(0)},{ts(d)},Gold,,0,0,0,,{c["ort"]}']
    open('story/story.ass', 'w', encoding='utf-8').write(STYLES + '\n'.join(ev) + '\n')
    ziel = f'story/akte{c["akte"]}_story.mp4'
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-t', str(d), '-i', 'audio/mix.wav',
                           '-vf', 'eq=contrast=1.06:saturation=1.08:gamma=1.03,noise=alls=6:allf=t,vignette=PI/4.2,ass=story/story.ass,format=yuv420p',
                           '-af', f'afade=t=out:st={tc - 0.1}:d={d - tc + 0.1}',
                           '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
                           '-shortest', '-movflags', '+faststart', ziel], stdin=subprocess.PIPE)
    for f in range(int(d * FPS)):
        t = f / FPS
        if t < tb:
            img = ausschnitt(A, 1.0 + 0.18 * s(t / tb) + (0.1 * (1 - f / 8) ** 2 if f < 8 else 0), 0.45)
            if f < 8: img = ImageEnhance.Brightness(img).enhance(1 + 0.4 * (1 - f / 8) ** 2)
        else:
            img = ausschnitt(B, 1.0 + 0.2 * s((t - tb) / (d - tb)) + 0.1 * max(0, 1 - (t - tb) / 0.22))
            if t - tb < 0.22: img = ImageEnhance.Brightness(img).enhance(1 + 0.6 * (1 - (t - tb) / 0.22) ** 2)
        if t >= tc:
            img = ImageEnhance.Brightness(img).enhance(1 - 0.45 * s((t - tc) / 0.4))
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    # Standbild
    bild_ev = [ev[0].replace(ts(d), ts(5)), ev[1].replace(ts(d), ts(5)).split(',,', 1)[0] + f',,AKTE {c["akte"]}',
               f'Dialogue: 1,{ts(0)},{ts(5)},Text,,0,0,0,,{c["hook"]}',
               f'Dialogue: 1,{ts(0)},{ts(5)},Gold,,0,0,0,,JETZT AUF MEINEM PROFIL']
    open('story/story_bild.ass', 'w', encoding='utf-8').write(STYLES + '\n'.join(bild_ev) + '\n')
    ImageEnhance.Brightness(ausschnitt(A, 1.08, 0.45)).enhance(0.85).save('story/_hinter.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'story/_hinter.png', '-vf',
                    'eq=contrast=1.06:saturation=1.08,vignette=PI/4.2,ass=story/story_bild.ass',
                    f'story/akte{c["akte"]}_story.png'], check=True)
    os.remove('story/_hinter.png')
    print('fertig:', ziel)


if __name__ == '__main__':
    main(sys.argv[1])
