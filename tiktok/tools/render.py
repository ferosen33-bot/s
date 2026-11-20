"""Baut ein TikTok-Video (1080x1920) aus Voiceover, Bildern und Untertiteln.

Nutzung (im Ordner der Folge):
    python3 ../tools/render.py szenen.json

szenen.json:
{
  "skript": "skript.md",
  "audio": "audio/take1.mp3",
  "woerter": "audio/take1_words.json",
  "hook": "Text oben in den ersten Sekunden",
  "ausgabe": "video.mp4",
  "szenen": [
    {"ab": "erste Wörter der Szene im Skript", "bild": "pfad.png",
     "von": [cx, cy, zoom], "nach": [cx, cy, zoom]},
    ...
  ]
}
cx/cy = Bildmittelpunkt des Ausschnitts (0..1), zoom = 1 heißt größter
Ausschnitt, der ins Bild passt (9:16 bei Hochformat-Bildern, sonst 4:5); größer = näher heran.
Optional pro Szene: "helligkeit": 0.7 dunkelt sehr helle Bilder ab.
"""
import json, subprocess, sys, os
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import untertitel as ut

W, H, FPS = 1080, 1920, 30
FG_W, FG_H, FG_Y = 1080, 1350, 200     # Bildfenster (4:5), Rest = unscharfer Hintergrund
FADE = 0.35                            # Überblendung in Sekunden
FEATHER = 160                          # weicher Rand oben/unten


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def resolve_times(cfg):
    sw = ut.script_words(open(cfg['skript'], encoding='utf-8').read())
    times = ut.align(sw, json.load(open(cfg['woerter'], encoding='utf-8')))
    starts = []
    for sc in cfg['szenen']:
        aw = sc['ab'].split()
        for i in range(len(sw)):
            if sw[i:i + len(aw)] == aw:
                starts.append(0.0 if not starts else times[i][0]); break
        else:
            sys.exit(f'Anker nicht im Skript gefunden: {sc["ab"]!r}')
    return starts


class Scene:
    def __init__(self, sc, start, end):
        self.start, self.end = start, end
        img = Image.open(sc['bild']).convert('RGB')
        if sc.get('helligkeit', 1.0) != 1.0:   # z. B. 0.7 für sehr helle Zeichnungen
            img = ImageEnhance.Brightness(img).enhance(sc['helligkeit'])
            img = ImageEnhance.Color(img).enhance(0.6)
        self.img = img
        iw, ih = img.size
        # Hochformat-Bilder (9:16) füllen das ganze Video, alle anderen kommen
        # in ein 4:5-Fenster vor einen unscharfen Hintergrund.
        self.full = iw / ih < 0.7
        self.out_w, self.out_h = (W, H) if self.full else (FG_W, FG_H)
        if iw / ih > self.out_w / self.out_h:
            self.bw, self.bh = ih * self.out_w / self.out_h, ih
        else:
            self.bw, self.bh = iw, iw * self.out_h / self.out_w
        self.a, self.b = sc['von'], sc['nach']
        # Hintergrund: Bild füllend, stark unscharf, abgedunkelt
        s = max(W / iw, H / ih)
        bg = img.resize((int(iw * s) + 1, int(ih * s) + 1), Image.BICUBIC)
        l, t = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(45))
        self.bg = ImageEnhance.Brightness(bg).enhance(0.45)

    def box(self, t):
        p = smooth((t - self.start) / max(self.end - self.start, 0.01))
        cx, cy, z = [a + (b - a) * p for a, b in zip(self.a, self.b)]
        iw, ih = self.img.size
        w, h = self.bw / z, self.bh / z
        x0 = min(max(cx * iw - w / 2, 0), iw - w)
        y0 = min(max(cy * ih - h / 2, 0), ih - h)
        return (x0, y0, x0 + w, y0 + h)

    def frame(self, t, mask):
        if self.full:
            return self.img.resize((W, H), Image.LANCZOS, box=self.box(t))
        fg = self.img.resize((FG_W, FG_H), Image.LANCZOS, box=self.box(t))
        out = self.bg.copy()
        out.paste(fg, (0, FG_Y), mask)
        return out


def feather_mask():
    m = Image.new('L', (FG_W, FG_H), 255)
    d = ImageDraw.Draw(m)
    for i in range(FEATHER):
        v = int(255 * smooth(i / FEATHER))
        d.line([(0, i), (FG_W, i)], fill=v)
        d.line([(0, FG_H - 1 - i), (FG_W, FG_H - 1 - i)], fill=v)
    return m


def main(cfg_path):
    cfg = json.load(open(cfg_path, encoding='utf-8'))
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                '-of', 'csv=p=0', cfg['audio']], capture_output=True, text=True).stdout)
    total = dur + 0.8
    starts = resolve_times(cfg)
    ends = starts[1:] + [total]
    scenes = [Scene(sc, s, e + FADE) for sc, s, e in zip(cfg['szenen'], starts, ends)]
    for sc, s in zip(cfg['szenen'], starts):
        print(f'{s:7.2f}s  {os.path.basename(sc["bild"]):40s} {sc["ab"]}')

    # Untertitel + Hook-Text
    ass = 'audio/untertitel_video.ass'
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'untertitel.py'),
                    cfg['skript'], cfg['woerter'], ass], check=True)
    if cfg.get('hook'):
        with open(ass, 'r+', encoding='utf-8') as f:
            txt = f.read()
            txt = txt.replace('Style: Gelb,', 'Style: Hook,Inter ExtraBold,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,3,20,0,8,80,80,290,1\nStyle: Gelb,', 1)
            txt += f'Dialogue: 1,0:00:00.00,0:00:03.80,Hook,,0,0,0,,{{\\fad(150,300)}}{cfg["hook"].upper()}\n'
            f.seek(0); f.write(txt); f.truncate()

    vf = (f"noise=alls=5:allf=t,vignette=PI/4.5,"
          f"fade=t=in:st=0:d=0.4,fade=t=out:st={total - 0.8:.2f}:d=0.8,"
          f"ass={ass},format=yuv420p")
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y',
                           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-i', cfg['audio'], '-vf', vf,
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-maxrate', '6M', '-bufsize', '12M', '-profile:v', 'high',
                           '-c:a', 'aac', '-b:a', '192k', '-af', 'apad', '-shortest',
                           '-movflags', '+faststart', cfg['ausgabe']], stdin=subprocess.PIPE)
    mask = feather_mask()
    n = int(total * FPS)
    for f in range(n):
        t = f / FPS
        i = max(k for k, s in enumerate(starts) if s <= t)
        img = scenes[i].frame(t, mask)
        if i > 0 and t - starts[i] < FADE:  # Überblendung von der vorigen Szene
            prev = scenes[i - 1].frame(t, mask)
            img = Image.blend(prev, img, smooth((t - starts[i]) / FADE))
        ff.stdin.write(img.tobytes())
        if f % (FPS * 10) == 0:
            print(f'  {t:5.0f}s / {total:.0f}s', flush=True)
    ff.stdin.close()
    ff.wait()
    print('fertig:', cfg['ausgabe'])


if __name__ == '__main__':
    main(sys.argv[1])
