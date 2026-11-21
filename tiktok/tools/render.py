"""Baut ein TikTok-Video (1080x1920) aus Voiceover, Bildern und Untertiteln.

Nutzung (im Ordner der Folge):
    python3 ../tools/hochskalieren.py      # einmalig: HD-Bilder nach bilder_hd/
    python3 ../tools/render.py szenen.json

szenen.json:
{
  "skript": "skript.md",
  "audio": "audio/take1.mp3",
  "woerter": "audio/take1_words.json",
  "hook": "Text oben in den ersten Sekunden",
  "ausgabe": "video.mp4",
  "tempo": 1.06,                         (optional, Sprechtempo; Standard 1.06)
  "szenen": [
    {"ab": "erste Wörter der Szene im Skript", "bild": "pfad.png",
     "von": [cx, cy, zoom], "nach": [cx, cy, zoom]},
    ...
  ]
}
cx/cy = Bildmittelpunkt des Ausschnitts (0..1), zoom = 1 heißt größter
Ausschnitt, der ins Bild passt (9:16 bei Hochformat-Bildern, sonst 4:5); größer = näher heran.
Optional pro Szene: "helligkeit": 0.7 dunkelt sehr helle Bilder ab.

Schnitt: Jede Szene wird in Einstellungen von höchstens ~3 s zerlegt (harte
Schnitte mit wechselndem Bildausschnitt). Bildwechsel bekommen einen kurzen
Zoom-Blitz und einen Whoosh. Dazu kommen Drone-Teppich, Impact am Anfang,
Wort-für-Wort-Untertitel und ein leichtes Color Grading.
"""
import json, math, os, re, subprocess, sys
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import untertitel as ut
import sounddesign as sd

W, H, FPS = 1080, 1920, 30
FG_W, FG_H, FG_Y = 1080, 1350, 200     # Bildfenster (4:5), Rest = unscharfer Hintergrund
FEATHER = 160                          # weicher Rand oben/unten
SHOT_MAX = 3.2                         # längste Einstellung in Sekunden
FLASH_IN, FLASH_OUT = 0.22, 0.10       # Zoom-Blitz beim Bildwechsel
PUNCH = [(1.00, 0.00, 0.00), (1.22, 0.04, -0.03), (1.08, -0.04, 0.03), (1.30, 0.02, 0.04)]


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def resolve_times(cfg, sw, times):
    starts = []
    for sc in cfg['szenen']:
        aw = sc['ab'].split()
        for i in range(len(sw)):
            if sw[i:i + len(aw)] == aw:
                starts.append(0.0 if not starts else times[i][0]); break
        else:
            sys.exit(f'Anker nicht im Skript gefunden: {sc["ab"]!r}')
    return starts


def hd_pfad(p):
    hd = os.path.join('bilder_hd', os.path.splitext(os.path.basename(p))[0] + '.png')
    return hd if os.path.exists(hd) else p


class Scene:
    def __init__(self, sc, start, end):
        self.start, self.end = start, end
        img = Image.open(hd_pfad(sc['bild'])).convert('RGB')
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
        s = max(W / iw, H / ih)
        bg = img.resize((int(iw * s) + 1, int(ih * s) + 1), Image.BICUBIC)
        l, t = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(45))
        self.bg = ImageEnhance.Brightness(bg).enhance(0.45)
        # Einstellungen
        n = max(1, math.ceil((end - start) / SHOT_MAX - 0.15))
        self.cuts = [start + (end - start) * k / n for k in range(n)] + [end]

    def shot(self, t):
        return max(k for k, c in enumerate(self.cuts[:-1]) if c <= t + 1e-9)

    def box(self, t, extra=1.0):
        p = smooth((t - self.start) / max(self.end - self.start, 0.01))
        cx, cy, z = [a + (b - a) * p for a, b in zip(self.a, self.b)]
        k = self.shot(t)
        pz, dx, dy = PUNCH[k % len(PUNCH)] if k else PUNCH[0]
        # innerhalb jeder Einstellung leichter Push-in, dazu ein Hauch Kamerawackeln
        q = (t - self.cuts[k]) / max(self.cuts[k + 1] - self.cuts[k], 0.01)
        z = max(z * pz * (1 + 0.05 * q) * extra, 1.0)
        cx += dx + 0.003 * math.sin(2.1 * t) + 0.002 * math.sin(3.7 * t + 1)
        cy += dy + 0.003 * math.sin(1.7 * t + 2)
        iw, ih = self.img.size
        w, h = self.bw / z, self.bh / z
        x0 = min(max(cx * iw - w / 2, 0), iw - w)
        y0 = min(max(cy * ih - h / 2, 0), ih - h)
        return (x0, y0, x0 + w, y0 + h)

    def frame(self, t, mask, extra=1.0):
        if self.full:
            return self.img.resize((W, H), Image.BICUBIC, box=self.box(t, extra))
        fg = self.img.resize((FG_W, FG_H), Image.BICUBIC, box=self.box(t, extra))
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
    tempo = cfg.get('tempo', 1.06)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                '-of', 'csv=p=0', cfg['audio']], capture_output=True, text=True).stdout) / tempo
    total = dur + 0.8
    sw = ut.script_words(open(cfg['skript'], encoding='utf-8').read())
    times = [(s / tempo, e / tempo) for s, e in ut.align(sw, json.load(open(cfg['woerter'], encoding='utf-8')))]
    starts = resolve_times(cfg, sw, times)
    ends = starts[1:] + [total]
    scenes = [Scene(sc, s, e) for sc, s, e in zip(cfg['szenen'], starts, ends)]
    for sc, s, scn in zip(cfg['szenen'], starts, scenes):
        print(f'{s:7.2f}s  {len(scn.cuts) - 1} Einst.  {os.path.basename(sc["bild"]):34s} {sc["ab"]}')

    # Ton: Stimme (schneller) + Drone + Whooshes + Impact
    mixwav = 'audio/mix.wav'
    sd.mix(cfg['audio'], tempo, starts[1:], total, mixwav)

    # Untertitel + Hook
    ass = 'audio/untertitel_video.ass'
    m = re.match(r'(\d+)-', os.path.basename(os.path.abspath('.')))
    n = ut.karaoke_ass(sw, times, ass, cfg.get('hook'), m.group(1) if m else None)
    print(f'{n} Untertitel -> {ass}')

    vf = (f"eq=contrast=1.06:saturation=1.08:gamma=1.03,"
          f"colorbalance=bs=0.04:gs=0.01:rh=0.03:bh=-0.02,"
          f"unsharp=5:5:0.35,noise=alls=6:allf=t,vignette=PI/4.2,"
          f"fade=t=out:st={total - 0.8:.2f}:d=0.8,"
          f"ass={ass},format=yuv420p")
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y',
                           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-i', mixwav, '-vf', vf,
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-maxrate', '8M', '-bufsize', '16M', '-profile:v', 'high',
                           '-c:a', 'aac', '-b:a', '192k', '-shortest',
                           '-movflags', '+faststart', cfg['ausgabe']], stdin=subprocess.PIPE)
    mask = feather_mask()
    nfr = int(total * FPS)
    for f in range(nfr):
        t = f / FPS
        i = max(k for k, s in enumerate(starts) if s <= t)
        sc = scenes[i]
        extra, flash = 1.0, 0.0
        if i > 0 and t - starts[i] < FLASH_IN:            # Bildwechsel: Zoom-Blitz
            p = (t - starts[i]) / FLASH_IN
            extra, flash = 1 + 0.10 * (1 - smooth(p)), 0.55 * (1 - p) ** 2
        elif i + 1 < len(starts) and starts[i + 1] - t < FLASH_OUT:
            extra = 1 + 0.07 * smooth(1 - (starts[i + 1] - t) / FLASH_OUT)
        elif f < 8:                                         # allererster Moment: Schlag ins Bild
            extra, flash = 1 + 0.12 * (1 - f / 8) ** 2, 0.4 * (1 - f / 8) ** 2
        img = sc.frame(t, mask, extra)
        if flash > 0.01:
            img = ImageEnhance.Brightness(img).enhance(1 + flash)
        ff.stdin.write(img.tobytes())
        if f % (FPS * 10) == 0:
            print(f'  {t:5.0f}s / {total:.0f}s', flush=True)
    ff.stdin.close()
    ff.wait()
    print('fertig:', cfg['ausgabe'])


if __name__ == '__main__':
    main(sys.argv[1])
